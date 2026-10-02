#!/usr/bin/env python3
"""Run the reviewed RTK binary with private, project-scoped local state."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys


BINARY = Path(__file__).resolve().parent / "rtk-0.49.0" / "rtk"


def project_root() -> Path:
    cwd = Path.cwd().resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        root = Path(result.stdout.strip()).resolve()
        return root if root.is_dir() and cwd.is_relative_to(root) else cwd
    except (OSError, ValueError, subprocess.SubprocessError):
        return cwd


def main() -> None:
    root = project_root()
    key = hashlib.sha256(os.fsencode(root)).hexdigest()
    directory = Path.home() / ".local" / "state" / "rtk" / "projects" / key
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = os.environ.copy()
    env["RTK_DB_PATH"] = str(directory / "rtk.db")
    env["RTK_TELEMETRY_DISABLED"] = "1"
    env["RTK_RECALL"] = "0"
    env["RTK_TEE"] = "0"
    os.execve(BINARY, [str(BINARY), *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
