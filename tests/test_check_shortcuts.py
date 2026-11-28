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

    def test_with_shortcut_argument_is_announced(self) -> None:
        text = '<Tooltip label={withShortcut(t.about, "F1")} />'
        chords = check_shortcuts.announcements(text, [check_shortcuts.JS_WITH_SHORTCUT], {})
        self.assertEqual(chords, {"F1"})

    def test_keycap_is_announced(self) -> None:
        text = '<kbd className="welcome-kbd">J</kbd><kbd>Shift+Enter</kbd>'
        chords = check_shortcuts.announcements(text, [check_shortcuts.JS_KEYCAP], {})
        self.assertEqual(chords, {"J", "Shift+Enter"})

    def test_attach_lambda_announces_both_ternary_branches(self) -> None:
        text = (
            '_toolTip.Attach(_open, () => "Open", () => "Ctrl+O");\n'
            '_toolTip.Attach(_max, () => "Restore",\n'
            '    () => WindowState == FormWindowState.Maximized ? "Win+↓" : "Win+↑");\n'
        )
        chords = check_shortcuts.announcements(
            text,
            [check_shortcuts.DOTNET_ATTACH_SHORTCUT, check_shortcuts.DOTNET_ATTACH_ALT],
            {},
        )
        self.assertEqual(chords, {"Ctrl+O", "Win+Down", "Win+Up"})

    def test_parenthesized_tooltip_chord_is_announced(self) -> None:
        text = (
            '<Tooltip label={`${t.articleViewer.searchInArticle} (Alt+F)`} />\n'
            '<Tooltip label={`${t.articleViewer.prevMatch} (Shift+Enter)`} />\n'
        )
        chords = check_shortcuts.announcements(text, [check_shortcuts.JS_PAREN_CHORD], {})
        self.assertEqual(chords, {"Alt+F", "Shift+Enter"})

    def test_nested_modifier_branch_resolves_chord(self) -> None:
        script = (
            "if (e.key === 'Enter') {\n"
            "  e.preventDefault()\n"
            "  if (e.shiftKey) { previous() } else { next() }\n"
            "}\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Enter", chords)
        self.assertIn("Shift+Enter", chords)

    def test_modifier_argument_inside_block_resolves_chord(self) -> None:
        script = (
            "if (e.key === 'Delete') {\n"
            "  removeSelection({ permanently: e.shiftKey })\n"
            "}\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Delete", chords)
        self.assertIn("Shift+Delete", chords)

    def test_short_alias_does_not_rewrite_key_literals(self) -> None:
        script = (
            "const k = event.key.toLowerCase()\n"
            "if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {\n"
            "  setLink()\n"
            "}\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Ctrl+K", chords)
        self.assertNotIn("Ctrl+Key", chords)

    def test_space_key_normalizes(self) -> None:
        self.assertEqual(check_shortcuts.make_chord({"Ctrl": True}, " "), "Ctrl+Space")

    def test_spanish_key_names_normalize(self) -> None:
        self.assertEqual(check_shortcuts.normalize("Ctrl+Espacio"), "Ctrl+Space")
        self.assertEqual(check_shortcuts.normalize("Ctrl+Supr"), "Ctrl+Delete")
        self.assertEqual(check_shortcuts.normalize("Ctrl+Mayús+S"), "Ctrl+Shift+S")
        self.assertEqual(check_shortcuts.normalize("Ctrl+RePág"), "Ctrl+PageUp")
        self.assertEqual(check_shortcuts.normalize("Alt+Inicio"), "Alt+Home")

    def test_global_shortcut_registration_is_a_handler(self) -> None:
        script = (
            "if (!globalShortcut.register('Alt+G', () => quickCapture())) return\n"
            "const item = { label: 'Show', accelerator: 'Alt+Shift+R', global: true }\n"
            "globalShortcut.register(shortcuts.showHide.accelerator, () => show())\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Alt+G", chords)
        self.assertIn("Alt+Shift+R", chords)
        self.assertEqual(len(chords), 2)

    def test_sibling_modifier_block_does_not_resolve_chord(self) -> None:
        script = (
            "if (e.key === 'Enter') {\n"
            "  next()\n"
            "}\n"
            "if (e.shiftKey) {\n"
            "  previous()\n"
            "}\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Enter", chords)
        self.assertNotIn("Shift+Enter", chords)

    def test_plus_and_minus_keys_normalize(self) -> None:
        self.assertEqual(check_shortcuts.normalize("Ctrl++"), "Ctrl+Plus")
        self.assertEqual(check_shortcuts.normalize("Ctrl+Plus"), "Ctrl+Plus")
        self.assertEqual(check_shortcuts.normalize("Ctrl+-"), "Ctrl+Minus")

    def test_key_alias_is_resolved_without_losing_modifiers(self) -> None:
        script = (
            "const keyLower = e.key.toLowerCase();\n"
            "if (e.altKey && keyLower === 'm') { toggleMenu(); }\n"
            "if (keyLower === 'j') { next(); }\n"
        )
        chords = check_shortcuts.js_handler_chords(script)
        self.assertIn("Alt+M", chords)
        self.assertIn("J", chords)

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
