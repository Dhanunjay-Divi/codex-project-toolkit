#!/usr/bin/env python3
"""Install a small, reviewed Codex project toolkit for one macOS user."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

try:
    import tomllib
except ImportError as exc:
    raise SystemExit("Python 3.11 or newer is required") from exc

SOURCE = Path(__file__).resolve().parent
MANIFEST = json.loads((SOURCE / "manifest.json").read_text())
MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
AGENT_NOTE = """\
## Shared project tools

Use native Codex agents for delegation; name a task owner and review their work.
Use Ruflo for decisions and task metadata with the canonical absolute `project_root`.
Use Codebase Memory only after attaching a project; its index is private to that project.
Use RTK selectively for noisy, low-risk shell output. Keep raw test and security output when exact evidence matters.
Load skills only when relevant. Agency Agents is a role-reference library, not an automatic workforce.
Do not copy credentials, tasks, memory, or indexes across projects or accounts.
"""
RTK_NOTE = """\
# RTK

The `rtk` command is installed and stores its database outside the repo, scoped by the Git worktree root.
Use it selectively for verbose, low-risk output. Run raw commands when exact stdout, stderr, exit status,
security evidence, or release checks matter. Codex does not automatically rewrite shell commands to RTK.
"""


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_platform():
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("This reviewed binary bundle currently supports macOS Apple Silicon only")
    missing = [item for item in ("git", "node", "npm") if not shutil.which(item)]
    if not Path("/usr/bin/sandbox-exec").is_file():
        missing.append("sandbox-exec")
    if missing:
        raise SystemExit("Install these prerequisites first: " + ", ".join(missing))


def fetch_binary(entry, target, offline_archive=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and sha256(target) == entry["binarySha256"]:
        return
    with tempfile.TemporaryDirectory(prefix="codex-toolkit-") as temp:
        archive = Path(temp) / "release.tar.gz"
        if offline_archive:
            shutil.copyfile(offline_archive, archive)
        else:
            with urllib.request.urlopen(entry["url"], timeout=40) as response, archive.open("wb") as out:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError("release archive exceeds size limit")
                    out.write(chunk)
        if sha256(archive) != entry["archiveSha256"]:
            raise ValueError("release archive checksum mismatch: " + entry["binary"])
        with tarfile.open(archive, "r:gz") as tar:
            members = [member for member in tar.getmembers()
                       if member.isfile() and Path(member.name).name == entry["binary"]]
            if len(members) != 1:
                raise ValueError("expected one release binary: " + entry["binary"])
            if members[0].size > 512 * 1024 * 1024:
                raise ValueError("release binary exceeds size limit")
            stream = tar.extractfile(members[0])
            if stream is None:
                raise ValueError("release binary could not be read")
            candidate = Path(temp) / "binary"
            with candidate.open("wb") as out:
                shutil.copyfileobj(stream, out)
        if sha256(candidate) != entry["binarySha256"]:
            raise ValueError("release binary checksum mismatch: " + entry["binary"])
        candidate.chmod(0o755)
        os.replace(candidate, target)


def copy_tree_if_absent(source, target):
    if target.exists():
        print("Keeping existing:", target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def replace_mcp_section(content, name, command):
    header = f"[mcp_servers.{name}]"
    block = header + "\ncommand = " + json.dumps(str(command)) + "\nargs = []\n"
    pattern = re.compile(r"(?ms)^" + re.escape(header) + r"\n.*?(?=^\[|\Z)")
    if pattern.search(content):
        return pattern.sub(lambda _: block + "\n", content, count=1)
    return content.rstrip() + "\n\n" + block + "\n"


def enable_native_agents(content):
    pattern = re.compile(r"(?ms)^\[features\]\n.*?(?=^\[|\Z)")
    match = pattern.search(content)
    if not match:
        return content.rstrip() + "\n\n[features]\nmulti_agent = true\n"
    section = match.group()
    setting = re.compile(r"(?m)^multi_agent[ \t]*=[ \t]*(?:true|false)[ \t]*$")
    if setting.search(section):
        updated = setting.sub("multi_agent = true", section, count=1)
    else:
        updated = section.rstrip() + "\nmulti_agent = true\n\n"
    return content[:match.start()] + updated + content[match.end():]


def configure_codex(codex_dir, install_dir):
    codex_dir.mkdir(parents=True, exist_ok=True)
    config = codex_dir / "config.toml"
    original = config.read_text() if config.exists() else ""
    revised = enable_native_agents(original)
    revised = replace_mcp_section(revised, "ruflo", install_dir / "ruflo-integration" / "ruflo-mcp")
    revised = replace_mcp_section(revised, "codebase_memory", install_dir / "codebase-memory-mcp-0.10.8" / "bin" / "project-mcp")
    tomllib.loads(revised)
    if revised != original:
        if config.exists():
            backup = codex_dir / "config.toml.pre-project-toolkit"
            if not backup.exists():
                shutil.copy2(config, backup)
                backup.chmod(0o600)
        temp = config.with_suffix(".toml.tmp")
        temp.write_text(revised)
        temp.chmod(0o600)
        os.replace(temp, config)
    agents = codex_dir / "AGENTS.md"
    marker_start = "<!-- codex-project-toolkit:start -->"
    marker_end = "<!-- codex-project-toolkit:end -->"
    block = marker_start + "\n" + AGENT_NOTE + marker_end
    old = agents.read_text() if agents.exists() else ""
    if marker_start in old and marker_end in old:
        new = re.sub(re.escape(marker_start) + r".*?" + re.escape(marker_end),
                     lambda _: block, old, flags=re.S)
    else:
        new = old.rstrip() + "\n\n" + block + "\n"
    if new != old:
        agents.write_text(new)
    rtk_doc = codex_dir / "RTK.md"
    if not rtk_doc.exists():
        rtk_doc.write_text(RTK_NOTE)


def install(home):
    ensure_platform()
    payload = SOURCE / "payload"
    if sha256(payload / "ruflo-3.41.2" / "package-lock.json") != MANIFEST["ruflo"]["packageLockSha256"]:
        raise ValueError("Ruflo lockfile checksum mismatch")
    base = home / ".local" / "share" / "codex-project-toolkit"
    base.mkdir(parents=True, exist_ok=True)
    for item in ("ruflo-integration", "ruflo-3.41.2", "codebase-memory-mcp-0.10.8"):
        shutil.copytree(payload / item, base / item, dirs_exist_ok=True)
    shutil.copy2(payload / "rtk-wrapper.py", base / "rtk-wrapper.py")
    (base / "rtk-wrapper.py").chmod(0o755)
    fetch_binary(MANIFEST["rtk"], base / "rtk-0.49.0" / "rtk")
    fetch_binary(MANIFEST["codebaseMemory"], base / "codebase-memory-mcp-0.10.8" / "bin" / "codebase-memory-mcp")
    npm_dir = base / "ruflo-3.41.2"
    if not (npm_dir / "node_modules" / "@claude-flow" / "cli").exists():
        subprocess.run(["npm", "ci", "--ignore-scripts", "--omit=optional", "--no-audit", "--no-fund"],
                       cwd=npm_dir, check=True, timeout=600)
    for executable in (base / "ruflo-integration" / "ruflo-mcp",
                       base / "codebase-memory-mcp-0.10.8" / "bin" / "project-mcp"):
        executable.chmod(0o755)
    link = home / ".local" / "bin" / "rtk"
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and link.resolve() == (base / "rtk-wrapper.py").resolve():
        pass
    elif link.exists() or link.is_symlink():
        print("Keeping existing RTK command:", link)
    else:
        link.symlink_to(base / "rtk-wrapper.py")
    for skill in ("ui-ux-pro-max", "ponytail-review", "agent-toolkit"):
        copy_tree_if_absent(payload / "skills" / skill, home / ".codex" / "skills" / skill)
    copy_tree_if_absent(payload / "agency-agents", base / "agency-agents")
    configure_codex(home / ".codex", base)
    print("Installed. Restart Codex or open a new chat to load the MCP servers and skills.")
    print("Provider sign-ins, plugins, and account limits remain tied to each Codex account.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "check"))
    args = parser.parse_args()
    if args.command == "check":
        ensure_platform()
        for key in ("rtk", "codebaseMemory"):
            print(key, MANIFEST[key]["version"], MANIFEST[key]["url"])
        print("Ruflo lockfile verified:", sha256(SOURCE / "payload" / "ruflo-3.41.2" / "package-lock.json") == MANIFEST["ruflo"]["packageLockSha256"])
    else:
        install(Path.home())


if __name__ == "__main__":
    main()
