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


class CheckShortcutsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_announced_chord_with_handler_passes(self) -> None:
        ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+O"',
            "document.addEventListener('keydown', (e) => {\n"
            "  if (e.altKey && !e.ctrlKey && e.key === 'o') openFolder();\n"
            "});\n",
        )
        self.assertEqual(check_shortcuts.check_repo(self.root / "CyberViewer"), [])

    def test_announced_chord_without_handler_fails(self) -> None:
        ViewerRepo(
            self.root,
            'data-tooltip-kbd="Ctrl+Shift+F"',
            "document.addEventListener('keydown', (e) => {\n"
            "  if (e.altKey && e.key === 'o') openFolder();\n"
            "});\n",
        )
        problems = check_shortcuts.check_repo(self.root / "CyberViewer")
        self.assertEqual(len(problems), 1)
        self.assertIn("Ctrl+Shift+F", problems[0])
        self.assertIn("no handler resolves it", problems[0])

    def test_platform_chords_are_exempt(self) -> None:
        ViewerRepo(
            self.root,
            'data-tooltip-kbd="Alt+F4" data-keyshortcuts="Ctrl+Shift+T"',
            "",
        )
        self.assertEqual(check_shortcuts.check_repo(self.root / "CyberViewer"), [])

    def test_app_allowlist_is_exempt(self) -> None:
        repo = self.root / "CyberLauncher"
        write(repo / "package.json", "{}")
        write(repo / "src" / "App.tsx", "const item = { shortcut: 'Ctrl+A' };\n")
        self.assertEqual(check_shortcuts.check_repo(repo), [])


if __name__ == "__main__":
    unittest.main()
