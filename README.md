# Codex project toolkit

A small, reproducible setup for **Codex projects on macOS Apple Silicon**. It uses native Codex agents for work, Ruflo for project decisions, Codebase Memory for optional code navigation, RTK for selective output compression, and three reviewed skills. Company HQ is optional; this setup does not start an HQ server, graph, board, or task scheduler.

## Install once per macOS user

```sh
git clone https://github.com/Dhanunjay-Divi/codex-project-toolkit.git
cd codex-project-toolkit
python3 bootstrap.py check
python3 bootstrap.py install
```

Requires Python 3.11+, Node.js/npm, Git, and macOS `sandbox-exec`. The installer downloads two version-pinned release archives over HTTPS, verifies archive and binary SHA-256 hashes, and runs `npm ci` from the committed lockfile with lifecycle scripts disabled. It never asks for or copies account credentials. Run it for each OS user or machine; switching Codex accounts in the same OS user keeps local tools but each account still needs its own provider sign-ins and plugin connections. Restart Codex or start a new chat after installing; existing MCP processes do not reload configuration mid-chat.

The installer backs up an existing `~/.codex/config.toml` once, preserves unrelated configuration, and replaces only `ruflo` and `codebase_memory` MCP commands. It adds a marked block to global `AGENTS.md` and leaves existing skills and RTK binaries in place. It does not change your approval policy, sandbox setting, provider settings, or project repositories.

## What is shared and what stays separate

| Component | Scope | Use |
| --- | --- | --- |
| Native Codex agents | Current chat/project | Delegate bounded work and review it |
| Ruflo MCP | Separate private state per canonical project path | Task/decision memory only; no execution |
| Codebase Memory MCP | Separate private index per Git worktree root | Code navigation on demand |
| RTK | Separate private database per Git worktree root | Selective compression of noisy shell output |
| Skills and Agency Agents examples | Installed once per OS user | Load relevant guidance on demand |
| Provider logins and plugins | Codex account | Connect in Codex; never exported here |

Ruflo receives an explicit `project_root`. Codebase Memory and RTK resolve the current Git worktree root, then keep data outside the source tree. On a fresh project, Codebase Memory will show an empty index until you ask it to index that project. Tools alone do not make every agent use them; global guidance and task instructions tell agents when they help. Agents remain subject to Codex permissions and the project's `AGENTS.md`.

If another tool is already installed, the installer leaves it in place. Check `~/.codex/config.toml` and `~/.local/bin/rtk` if you previously customized these names. The two MCP commands are intentionally replaced with project-scoped launchers. No automatic model calls, repo hooks, global command rewriting, or hidden background agent loops are installed.

## Included references

- [Ruflo](https://github.com/ruvnet/ruflo) is pinned by its npm lockfile; the local MCP facade only exposes an allowlisted memory/task subset.
- [Codebase Memory MCP](https://github.com/DeusData/codebase-memory-mcp) v0.10.8 runs behind a bounded-root guard.
- [RTK](https://github.com/rtk-ai/rtk) v0.49.0 is wrapped for project-local state. Codex has no automatic command hook; invoke it intentionally.
- [Agency Agents](https://github.com/msitarzewski/agency-agents) contributes ten selected role references, not a second agent runtime.
- UI/UX Pro Max and Ponytail Review are optional, task-specific skills. Pinky, NOOP, Bluey, and other project operating skills remain specific to their own repos and are not bundled here.

The source pins and checksums are in [manifest.json](manifest.json); included upstream license files remain in `payload/`. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
