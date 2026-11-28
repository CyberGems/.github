"""Tests for check_shortcuts.py.

Each test builds a tiny repository with the real CyberViewer or CyberLauncher
layout, so the per-app rules are exercised instead of a simplified copy.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_shortcuts.py"
SPEC = importlib.util.spec_from_file_location("check_shortcuts", SCRIPT)
assert SPEC and SPEC.loader
check_shortcuts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_shortcuts)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ViewerRepo:
    """A CyberViewer-shaped repository: HTML announcements and js handlers."""

    def __init__(self, root: Path, announcements: str, script: str) -> None:
        self.path = root / "CyberViewer"
        self.path.mkdir()
        write(self.path / "package.json", "{}")
        write(
            self.path / "CyberViewer.html",
            f"<!doctype html>\n<button {announcements}></button>\n",
        )
        write(self.path / "js" / "app.js", script)
        # The app rules declare these too; the checker now fails when one is
        # missing, so the fixture mirrors the real layout.
        write(self.path / "js" / "workspace.js", "")
        write(self.path / "js" / "video-player.js", "")
        write(self.path / "main.js", "")

    def check(self) -> tuple[list[str], str]:
        return check_shortcuts.check_repo(self.path)


class CheckShortcutsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_announced_chord_with_handler_passes(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+O"',
            "document.addEventListener('keydown', (e) => {\n"
            "  if (e.altKey && !e.ctrlKey && e.key === 'o') openFolder();\n"
            "});\n",
        )
        problems, summary = repo.check()
        self.assertEqual(problems, [])
        self.assertIn("1 announcement file(s)", summary)
        self.assertIn("4 handler file(s)", summary)

    def test_announced_chord_without_handler_fails(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Ctrl+Shift+F"',
            "document.addEventListener('keydown', (e) => {\n"
            "  if (e.altKey && e.key === 'o') openFolder();\n"
            "});\n",
        )
        problems, _ = repo.check()
        self.assertEqual(len(problems), 1)
        self.assertIn("Ctrl+Shift+F", problems[0])
        self.assertIn("no handler resolves it", problems[0])

    def test_platform_chords_are_exempt(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+F4" data-keyshortcuts="Ctrl+Shift+T"',
            "if (e.altKey && e.key === 'o') openFolder();\n",
        )
        problems, _ = repo.check()
        self.assertEqual(problems, [])

    def test_app_allowlist_is_exempt(self) -> None:
        repo = self.root / "CyberLauncher"
        write(repo / "package.json", "{}")
        write(repo / "src" / "App.tsx", "const item = { shortcut: 'Ctrl+A' };\n")
        write(repo / "src" / "CyberTerminal.tsx", "")
        write(
            repo / "electron" / "main.ts",
            "if (e.altKey && e.key === 'p') pinPrompt();\n",
        )
        problems, _ = check_shortcuts.check_repo(repo)
        self.assertEqual(problems, [])

    def test_missing_announcement_source_fails(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+O"',
            "if (e.altKey && e.key === 'o') openFolder();\n",
        )
        (repo.path / "CyberViewer.html").unlink()
        problems, _ = repo.check()
        self.assertTrue(any("announcement source CyberViewer.html is gone" in p for p in problems))
        self.assertTrue(any("no announcement source matched" in p for p in problems))

    def test_missing_handler_source_fails(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+O"',
            "if (e.altKey && e.key === 'o') openFolder();\n",
        )
        for name in ("app.js", "workspace.js", "video-player.js"):
            (repo.path / "js" / name).unlink()
        (repo.path / "main.js").unlink()
        problems, _ = repo.check()
        self.assertTrue(any("handler source js/app.js is gone" in p for p in problems))
        self.assertTrue(any("no handler source matched" in p for p in problems))

    def test_handler_without_keyboard_code_fails(self) -> None:
        repo = ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+O"',
            "// Refactored: the keyboard code was moved somewhere else.\n",
        )
        problems, _ = repo.check()
        self.assertTrue(any("no handler chord was resolved" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
