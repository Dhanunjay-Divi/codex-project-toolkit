import hashlib
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_config_preserves_other_sections_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            codex = root / ".codex"
            codex.mkdir()
            (codex / "config.toml").write_text(
                'model = "existing"\n[mcp_servers.other]\ncommand = "keep"\n'
                '[mcp_servers.ruflo]\ncommand = "old"\nargs = []\n'
            )
            bootstrap.configure_codex(codex, root / "toolkit")
            first = (codex / "config.toml").read_text()
            bootstrap.configure_codex(codex, root / "toolkit")
            self.assertEqual(first, (codex / "config.toml").read_text())
            self.assertIn('model = "existing"', first)
            self.assertIn('command = "keep"', first)
            self.assertEqual(first.count("[mcp_servers.ruflo]"), 1)
            self.assertEqual(first.count("[mcp_servers.codebase_memory]"), 1)
            self.assertIn("multi_agent = true", first)
            self.assertTrue((codex / "config.toml.pre-project-toolkit").exists())
            self.assertEqual((codex / "AGENTS.md").read_text().count("<!-- codex-project-toolkit:start -->"), 1)

    def test_binary_archive_requires_matching_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = b"reviewed-test-binary"
            archive = root / "test.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("nested/tool")
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
            entry = {
                "binary": "tool",
                "archiveSha256": bootstrap.sha256(archive),
                "binarySha256": hashlib.sha256(content).hexdigest(),
            }
            target = root / "out" / "tool"
            bootstrap.fetch_binary(entry, target, archive)
            self.assertEqual(target.read_bytes(), content)
            self.assertTrue(os.access(target, os.X_OK))
            target.unlink()
            entry["binarySha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                bootstrap.fetch_binary(entry, target, archive)
            self.assertFalse(target.exists())

    def test_install_wires_fresh_user_without_project_files(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)

            def fake_binary(_entry, target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"fake test binary")

            with patch.object(bootstrap, "ensure_platform"), patch.object(bootstrap, "fetch_binary", side_effect=fake_binary), patch.object(bootstrap.subprocess, "run") as run:
                bootstrap.install(home)
                arena = home / ".codex" / "skills" / "arena-review" / "SKILL.md"
                alerts = home / ".codex" / "skills" / "owner-alerts" / "SKILL.md"
                arena.write_bytes(b"private arena customization\n")
                alerts.write_bytes(b"private owner-alert customization\n")
                bootstrap.install(home)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(arena.read_bytes(), b"private arena customization\n")
            self.assertEqual(alerts.read_bytes(), b"private owner-alert customization\n")
            for call in run.call_args_list:
                self.assertEqual(call.args[0][:2], ["npm", "ci"])
            self.assertTrue((home / ".local" / "bin" / "rtk").is_symlink())
            self.assertTrue(os.access(home / ".local" / "share" / "codex-project-toolkit" / "rtk-wrapper.py", os.X_OK))
            self.assertTrue((home / ".codex" / "skills" / "agent-toolkit" / "SKILL.md").is_file())
            self.assertTrue((home / ".codex" / "skills" / "arena-review" / "SKILL.md").is_file())
            self.assertTrue((home / ".codex" / "skills" / "owner-alerts" / "SKILL.md").is_file())
            self.assertEqual((home / ".codex" / "config.toml").read_text().count("[mcp_servers.ruflo]"), 1)
            self.assertFalse((home / ".codex" / "auth.json").exists())
            self.assertNotIn("owner-alerts", (home / ".codex" / "config.toml").read_text())
            self.assertNotIn("phone", (home / ".codex" / "config.toml").read_text().lower())


if __name__ == "__main__":
    unittest.main()
