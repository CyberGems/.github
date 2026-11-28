#!/usr/bin/env python3
"""Validate that every announced keyboard shortcut has a handler.

A shortcut can be announced in a tooltip, a menu row, a shortcut sheet or an
accelerator label. If no keyboard code resolves the same chord, the hint is a
dead link: the user presses it and nothing happens.

The check is static on purpose, like check_tray_tooltips.py. It reads the
announcement surfaces and the keyboard handlers of each app, normalizes both
sides to the same chord spelling and reports every announced chord that the
handlers never produce.

Usage:
    python3 scripts/check_shortcuts.py path/to/AppRepo [more repos...]

With no arguments the current directory is checked.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

# Chords the platform owns. Apps announce them but never resolve them: the
# shell or the window manager does, so they are not dead links.
PLATFORM_CHORDS = {
    "Alt+F4",
    "Win+Up",
    "Win+Down",
    "Win+Left",
    "Win+Right",
    # Windows and platform conventions kept by the suite on purpose.
    "Ctrl+Shift+S",
    "Ctrl+Shift+Z",
    "Ctrl+Shift+N",
    "Ctrl+Shift+T",
    "Ctrl+Shift+Tab",
    "Ctrl+Shift+I",
    "Ctrl+Shift+Home",
    "Ctrl+Shift+End",
    "Shift+Tab",
}

# Surfaces that announce a chord. Every pattern keeps the chord in group 1.
TOOLTIP_ATTR = r'data-tooltip-kbd="([^"]+)"'
ARIA_KEYS = r'(?:aria-keyshortcuts|data-keyshortcuts)="([^"]+)"'
MENU_SPAN = r'class="menu-shortcut"[^>]*>([^<]+)<'
JS_SHORTCUT = r"\bshortcut\s*[:=]\s*[\"']([^\"']+)[\"']"
JS_KEYSHORTCUTS = r"\bkeyshortcuts\s*[:=]\s*[\"']([^\"']+)[\"']"
# A tooltip built as withShortcut(label, 'Ctrl+H'): the chord is an argument,
# not a property, so JS_SHORTCUT never sees it.
JS_WITH_SHORTCUT = r"withShortcut\([^,\n]*,\s*[\"']([^\"']+)[\"']"
# A keycap rendered inline: <kbd className="...">Esc</kbd>.
JS_KEYCAP = r"<kbd[^>]*>([^<]{1,20})</kbd>"
# A chord written in tooltip text: `${t.search} (Alt+F)` or `(Shift+Enter)`.
JS_PAREN_CHORD = (
    r"\(((?:Ctrl|Alt|Shift|Win)(?:\+(?:Ctrl|Alt|Shift|Win))*\+[A-Za-z0-9]+)\)"
)
DOTNET_WITH_SHORTCUT = r"WithShortcut(?:Hint)?\([^,]*,\s*\"([^\"]+)\""
DOTNET_CONST_SHORTCUT = r"WithShortcut(?:Hint)?\([^,]*,\s*KeyboardShortcuts\.(\w+)"
DOTNET_GESTURE = r"InputGestureText\s*=\s*\"([^\"]+)\""
DOTNET_CONST_GESTURE = r"InputGestureText\s*=\s*KeyboardShortcuts\.(\w+)"
# A themed tooltip attaches the chord as the third lambda:
#   Attach(control, () => "Zoom in", () => "Ctrl++")
# Both branches of a state ternary count (maximize announces Win+Up and Win+Down).
DOTNET_ATTACH_SHORTCUT = r"Attach\([^;]*?,\s*\(\)\s*=>[^;]*?,\s*\(\)\s*=>[^;]*?\"([^\"]+)\""
DOTNET_ATTACH_ALT = r"Attach\([^;]*?,\s*\(\)\s*=>[^;]*?,\s*\(\)\s*=>[^;]*?\?[^;]*?:\s*\"([^\"]+)\""
XAML_GESTURE = r'InputGestureText="([^"]+)"'

MODIFIERS = {
    "control": "Ctrl",
    "ctrl": "Ctrl",
    "cmdorctrl": "Ctrl",
    "commandorcontrol": "Ctrl",
    "meta": "Win",
    "cmd": "Win",
    "win": "Win",
    "super": "Win",
    "alt": "Alt",
    "shift": "Shift",
    "⇧": "Shift",
}

MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")

KEYS = {
    "esc": "Esc",
    "escape": "Esc",
    "del": "Delete",
    "delete": "Delete",
    "space": "Space",
    "spacebar": "Space",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "backspace": "Backspace",
    "ins": "Insert",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "arrowleft": "Left",
    "arrowright": "Right",
    "arrowup": "Up",
    "arrowdown": "Down",
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "←": "Left",
    "→": "Right",
    "↑": "Up",
    "↓": "Down",
    "↵": "Enter",
    "⇥": "Tab",
    "⌫": "Backspace",
}

ENTITY_KEYS = {
    "&#8679;": "Shift",
    "&#8593;": "Up",
    "&#8595;": "Down",
    "&#8592;": "Left",
    "&#8594;": "Right",
}

KEY_ALIASES = {
    "oemcomma": ",",
    "oemperiod": ".",
    "oemquestion": "?",
    "oemplus": "+",
    "oemminus": "-",
    "oempipe": "|",
    "oemsemicolon": ";",
    "oemquotes": "'",
    "oemtilde": "`",
    "oemopenbrackets": "[",
    "oemclosebrackets": "]",
}


def decode(text: str) -> str:
    for entity, key in ENTITY_KEYS.items():
        text = text.replace(entity, key)
    text = html.unescape(text)
    return text.replace("&#8679;", "Shift").replace("&#8593;", "Up").replace("&#8595;", "Down")


def normalize(chord: str) -> str | None:
    """Return the canonical chord, or None when the label is not a chord."""
    chord = decode(chord).strip()
    if not chord or len(chord) > 40:
        return None
    if re.fullmatch(r"\d+", chord):
        return None
    # A plus key is written either as Ctrl++ or Ctrl+Plus; splitting on "+"
    # would drop it, so name it before parsing.
    if chord.endswith("++"):
        chord = f"{chord[:-2]}+Plus"
    parts = [part.strip() for part in chord.split("+") if part.strip()]
    if not parts:
        return None

    modifiers: list[str] = []
    key = None
    for part in parts:
        lowered = part.lower()
        if lowered in MODIFIERS:
            modifier = MODIFIERS[lowered]
            if modifier not in modifiers:
                modifiers.append(modifier)
            continue
        if key is not None:
            return None
        key = KEYS.get(lowered, part)
        if lowered in KEY_ALIASES:
            key = KEY_ALIASES[lowered]
        # Punctuation is spelled one way everywhere, so the minus and plus keys
        # compare equal whether they come from a tooltip or from Keys.Oemplus.
        key = {"+": "Plus", "-": "Minus"}.get(key, key)
        # Single letters, digits, F-keys, navigation and a few punctuation keys
        # are keyboard keys. Words such as "Rueda" or "Arrastrar" are gestures.
        if not (
            re.fullmatch(r"[A-Za-z0-9]", key)
            or re.fullmatch(r"F([1-9]|1[0-9]|2[0-4])", key, re.IGNORECASE)
            or key in {
                "Esc", "Enter", "Space", "Tab", "Backspace", "Delete", "Insert",
                "Home", "End", "PageUp", "PageDown", "Left", "Right", "Up", "Down",
                "?", ",", ".", "-", "=", "[", "]", ";", "'", "`", "\\", "/",
                "Plus", "Minus",
            }
        ):
            return None

    if key is None:
        return None
    # Punctuation alone is not a shortcut: it collides with prose, JSON escapes
    # and `replace('shortcut:', '')` snippets. The same key with a modifier is
    # unambiguous and stays.
    if not modifiers and key in {",", ".", ";", "/", "-", "=", "[", "]", "'", "`", "\\"}:
        return None
    if re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", key, re.IGNORECASE):
        key = key.upper()
    elif len(key) == 1:
        key = key.upper()
    modifiers.sort(key=lambda item: MODIFIER_ORDER.index(item))
    return "+".join([*modifiers, key])


def announcements(text: str, patterns: list[str], constants: dict[str, str]) -> set[str]:
    found: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1)
            if value in constants:
                value = constants[value]
            chord = normalize(value)
            if chord:
                found.add(chord)
    return found


def kbd_sheet_chords(text: str) -> set[str]:
    """Read a shortcut sheet: one <dt> holding one or more <kbd> keycaps."""
    found: set[str] = set()
    for row in re.finditer(r"<dt[^>]*>(.*?)</dt>", text, re.DOTALL):
        keys = re.findall(r"<kbd[^>]*>(.*?)</kbd>", row.group(1), re.DOTALL)
        if not keys:
            continue
        chord = normalize("+".join(re.sub(r"<[^>]+>", "", key).strip() for key in keys))
        if chord:
            found.add(chord)
    return found


# ── Handler evidence ─────────────────────────────────────────────────────────

KEY_COMPARE = re.compile(
    r"(?:(?:\b(?:e|event|ev|keyEvent)\.)?(?:key|code|Key)(?:\.toLowerCase\(\))?|"
    r"keyCode|KeyCode)\s*(?:={2,3}|!={1,2})\s*"
    r"(?:['\"]([^'\"]{1,14})['\"]|(?:Key|Keys)\.(\w+)|(\d+))"
)
CASE_KEY = re.compile(r"\bcase\s+['\"]([^'\"]{1,14})['\"]\s*:")
SHORT_VAR_COMPARE = re.compile(
    r"\b([a-zA-Z_$][\w$]{0,2})\s*(?:={2,3}|!={1,2})\s*['\"]([^'\"]{1,14})['\"]"
)
SHIFT_TERNARY = re.compile(r"shiftKey\s*\?\s*['\"]([^'\"]{1,8})['\"]\s*:\s*['\"]([^'\"]{1,8})['\"]")
CS_KEY = re.compile(r"\b(?:Key|Keys)\.(\w+)")
CS_MODIFIER = re.compile(
    r"ModifierKeys\.(Control|Alt|Shift|Windows)"
    r"(?:\s*(?:\||,)\s*ModifierKeys\.(Control|Alt|Shift|Windows))*"
)
CS_EVENT_MODIFIER = re.compile(r"\b(?:e|event|ev)\.(Control|Alt|Shift)\b")
CS_MODIFIER_NAMES = {"control", "alt", "shift", "windows", "none"}
CHORD_LITERAL = re.compile(
    r"(?:Ctrl|Control|Alt|Shift|Win|Meta|Cmd|Super)"
    r"(?:\+(?:Ctrl|Control|Alt|Shift|Win|Meta|Cmd|Super))*\+[A-Za-z0-9?.,;'\[\]/`=\\-]+"
)
ANNOUNCEMENT_LINE = re.compile(
    r"shortcut\s*[:=]|keyshortcuts|data-tooltip-kbd|aria-keyshortcuts|"
    r"WithShortcut|menu-shortcut|InputGestureText|const\s+string\s+\w+\s*="
)
NEGATED = re.compile(
    r"!\s*(?:e\.|event\.|ev\.)?"
    r"(ctrlKey|metaKey|altKey|shiftKey|isCtrl|isAlt|isShift|isCtrlOrCmd|isCmdOrCtrl|ctrl|alt|shift)\b"
)


def modifier_flags(fragment: str) -> dict[str, bool]:
    """Read positive and negated modifier mentions out of one expression."""
    flags: dict[str, bool] = {}
    for match in NEGATED.finditer(fragment):
        name = match.group(1).lower()
        if "ctrl" in name or "meta" in name:
            flags["Ctrl"] = False
        elif "alt" in name:
            flags["Alt"] = False
        elif "shift" in name:
            flags["Shift"] = False
    cleaned = NEGATED.sub("", fragment)
    for name, modifier in (
        ("ctrlKey", "Ctrl"), ("metaKey", "Ctrl"), ("isCtrl", "Ctrl"),
        ("altKey", "Alt"), ("isAlt", "Alt"),
        ("shiftKey", "Shift"), ("isShift", "Shift"),
        ("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"),
        ("isCtrlOrCmd", "Ctrl"), ("isCmdOrCtrl", "Ctrl"),
    ):
        if re.search(rf"\b{name}\b", cleaned):
            flags[modifier] = True
    return flags


def make_chord(flags: dict[str, bool], key: str) -> str | None:
    if key == " ":
        key = "Space"
    if key.startswith("Key") and len(key) > 3:
        key = key[3:]
    elif key.startswith("Digit") and len(key) > 5:
        key = key[5:]
    elif key.startswith("Numpad") and len(key) > 6:
        key = key[6:]
    key = KEYS.get(key.lower(), key)
    if key.lower() in KEY_ALIASES:
        key = KEY_ALIASES[key.lower()]
    if len(key) == 1:
        key = key.upper()
    if key.lower().startswith("vk_"):
        key = key[3:]
    if re.fullmatch(r"[a-z]", key):
        key = key.upper()
    if re.fullmatch(r"d(\d)", key.lower()):
        key = key[1]
    elif re.fullmatch(r"numpad(\d)", key.lower()):
        key = key[6:]
    modifiers = [modifier for modifier in MODIFIER_ORDER if flags.get(modifier)]
    return normalize("+".join([*modifiers, key]))


def guard_flags(line: str) -> dict[str, bool]:
    """Modifiers required by an early-return guard such as `if (!e.altKey) return;`."""
    if not re.search(r"\)\s*(?:return|continue|break)\b", line):
        return {}
    flags: dict[str, bool] = {}
    for group in re.findall(r"!\(([^)]*)\)", line):
        for name, modifier in (("ctrlKey", "Ctrl"), ("metaKey", "Ctrl"), ("altKey", "Alt"), ("shiftKey", "Shift")):
            if name in group:
                flags[modifier] = True
    for name in NEGATED.findall(line):
        if "ctrl" in name or "meta" in name:
            flags["Ctrl"] = True
        elif "alt" in name:
            flags["Alt"] = True
        elif "shift" in name:
            flags["Shift"] = True
    return flags


def following_modifiers(lines: list[str], index: int) -> dict[str, bool]:
    """Modifiers checked inside the body of a case label."""
    for line in lines[index + 1:index + 4]:
        if not re.search(r"\b(if|else\s+if)\s*\(", line):
            continue
        if KEY_COMPARE.search(line) or CASE_KEY.search(line):
            continue
        flags = modifier_flags(line)
        if flags:
            return flags
    return {}


def nested_modifier_branches(
    lines: list[str], index: int, distance: int = 30
) -> list[dict[str, bool]]:
    """Modifier checks made inside the block opened on lines[index].

    A sibling check below a closed block (`if (e.key === 'Enter') { … }\n
    if (e.shiftKey) { … }`) does not handle that chord, so the walk stops at
    the brace that closes the key check.
    """
    depth = lines[index].count("{") - lines[index].count("}")
    if depth <= 0:
        return []
    branches: list[dict[str, bool]] = []
    for line in lines[index + 1:index + 1 + distance]:
        if depth <= 0:
            break
        stripped = line.lstrip()
        if (
            not stripped.startswith("}")
            and re.search(r"\bif\s*\(", line)
            and not KEY_COMPARE.search(line)
        ):
            flags = modifier_flags(line)
            if flags and any(flags.values()):
                branches.append(flags)
        depth += line.count("{") - line.count("}")
    return branches


def preceding_modifiers(lines: list[str], index: int) -> dict[str, bool]:
    """Modifiers of the if-condition that gates a key comparison."""
    merged: dict[str, bool] = {}
    for line in reversed(lines[max(0, index - 60):index]):
        if KEY_COMPARE.search(line) or CASE_KEY.search(line):
            continue
        guard = guard_flags(line)
        if guard:
            return guard
        flags = modifier_flags(line)
        if flags:
            for modifier, value in flags.items():
                merged.setdefault(modifier, value)
        if re.search(r"\b(if|else\s+if)\s*\(", line) and merged:
            return merged
    return merged


def guard_before(lines: list[str], index: int, distance: int = 40) -> dict[str, bool]:
    """Nearest early-return guard above a line, ignoring intervening code."""
    for line in reversed(lines[max(0, index - distance):index]):
        flags = guard_flags(line)
        if flags:
            return flags
    return {}


def case_context_flags(lines: list[str], index: int) -> dict[str, bool]:
    """Modifiers of the if that wraps the switch owning a case label."""
    switch = None
    for position in range(index, max(0, index - 80), -1):
        if re.search(r"\bswitch\s*\(", lines[position]):
            switch = position
            break
    if switch is None:
        return {}
    return preceding_modifiers(lines, switch)


def js_handler_chords(text: str) -> set[str]:
    found: set[str] = set()
    # `const keyLower = e.key.toLowerCase()` is the same comparison as `e.key`;
    # fold the alias back so the patterns below can read it.
    aliases = set(
        re.findall(
            r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:[\w.$]+\.)?(?:key|code)(?:\.toLowerCase\(\))?\b",
            text,
        )
    )
    # A local named altKey/ctrlKey is a modifier capture (e.altKey), not a key
    # alias; folding it would erase the modifier from every comparison.
    aliases -= {"key", "code", "tag", "altKey", "ctrlKey", "shiftKey", "metaKey"}
    # A one-letter alias such as `const k = event.key` would also rewrite the
    # 'k' inside a comparison or a keycap string, so leave it alone; longer
    # aliases (`keyLower`) are unambiguous.
    for alias in (name for name in aliases if len(name) > 1):
        text = re.sub(rf"\b{re.escape(alias)}\b", "key", text)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if ANNOUNCEMENT_LINE.search(line):
            continue
        if re.search(r"\b(if|case|===|==|matchShortcut|accelerator|keyMatches|shortcutMatches)\b", line):
            for literal in CHORD_LITERAL.finditer(line):
                chord = normalize(literal.group(0))
                if chord:
                    found.add(chord)
        for match in SHORT_VAR_COMPARE.finditer(line):
            if match.group(1) in {"key", "code", "Key", "tag"}:
                continue
            flags = modifier_flags(line) or preceding_modifiers(lines, index)
            chord = make_chord(flags, match.group(2))
            if chord:
                found.add(chord)
        for match in KEY_COMPARE.finditer(line):
            raw = match.group(1) or match.group(2) or match.group(3)
            if raw and raw.isdigit():
                raw = f"F{raw}" if 112 <= int(raw) <= 135 else chr(int(raw)) if 65 <= int(raw) <= 90 else raw
            if not raw:
                continue
            if raw.startswith("Key") and len(raw) > 3:
                raw = raw[3:]
            elif raw.startswith("Digit") and len(raw) > 5:
                raw = raw[5:]
            elif raw.startswith("Numpad") and len(raw) > 6:
                raw = raw[6:]
            candidates = [modifier_flags(line)]
            if not any(candidates[0].values()) or len(KEY_COMPARE.findall(line)) > 1:
                candidates.append(preceding_modifiers(lines, index))
            for flags in candidates:
                chord = make_chord(flags, raw)
                if chord:
                    found.add(chord)
            # A key check whose block branches on a modifier handles both:
            #   if (e.key === 'Enter') { if (e.shiftKey) previous(); }
            for nested in nested_modifier_branches(lines, index):
                chord = make_chord(nested, raw)
                if chord:
                    found.add(chord)
        case = CASE_KEY.search(line)
        if case and not KEY_COMPARE.search(line):
            # A switch over e.key inherits the modifiers around it, and a case
            # body may narrow that with its own modifier check. Both forms are
            # real bindings, so each one contributes.
            candidates = [modifier_flags(line)]
            if not candidates[0]:
                candidates.extend([
                    case_context_flags(lines, index),
                    following_modifiers(lines, index),
                ])
            for flags in candidates:
                chord = make_chord(flags, case.group(1))
                if chord:
                    found.add(chord)
        keyed_action = re.match(r"\s*((?:Key[A-Z]|Digit\d|Numpad\d|F\d{1,2}))\s*:", line)
        if keyed_action:
            flags = guard_before(lines, index) or preceding_modifiers(lines, index)
            chord = make_chord(flags, keyed_action.group(1))
            if chord:
                found.add(chord)
        ternary = SHIFT_TERNARY.search(line)
        if ternary:
            for key in ternary.groups():
                chord = make_chord({"Shift": True}, key)
                if chord:
                    found.add(chord)
                plain = make_chord({}, key)
                if plain:
                    found.add(plain)
    # Range handlers: Alt+0..9 and the digit/numpad branches are real bindings
    # even though no single key comparison names them.
    if re.search(r"\baltKey\b", text) and re.search(
        r"startsWith\(['\"]Digit['\"]\)|key\s*>=\s*['\"]0['\"]\s*&&[^\n]*key\s*<=\s*['\"]9['\"]", text
    ):
        found.update(f"Alt+{digit}" for digit in range(10))
    return found


def cs_handler_chords(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        if ANNOUNCEMENT_LINE.search(line):
            # Constants announce, they do not handle. The resolver still names
            # the same key on its own line.
            continue
        for literal in CHORD_LITERAL.finditer(line):
            chord = normalize(literal.group(0))
            if chord:
                found.add(chord)

        keys = [token for token in CS_KEY.findall(line) if token.lower() not in CS_MODIFIER_NAMES]
        if not keys:
            continue

        mapping = {"Control": "Ctrl", "Alt": "Alt", "Shift": "Shift", "Windows": "Win"}
        modifier_sets: list[frozenset[str]] = []

        names = re.findall(r"ModifierKeys\.(Control|Alt|Shift|Windows)", line)
        names.extend(name for name in CS_KEY.findall(line) if name.lower() in {"control", "alt", "shift"})
        if names:
            modifier_sets.append(frozenset(mapping[name] for name in names))
            # A line may hold alternatives (Ctrl or Ctrl+Shift) for the same
            # key, so each modifier alone is also a real mapping.
            modifier_sets.extend(frozenset({mapping[name]}) for name in names)
        event_modifiers = CS_EVENT_MODIFIER.findall(line)
        if event_modifiers:
            modifier_sets.append(frozenset(mapping[name] for name in event_modifiers))
        unique_sets = list(dict.fromkeys(modifier_sets)) or [frozenset()]

        for flags in unique_sets:
            for key in keys:
                chord = make_chord({flag: True for flag in flags}, key)
                if chord:
                    found.add(chord)
    return found


def rust_handler_chords(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        for literal in CHORD_LITERAL.finditer(line):
            chord = normalize(literal.group(0))
            if chord:
                found.add(chord)
    return found


# ── Per-app rules ────────────────────────────────────────────────────────────

APPS: dict[str, dict] = {
    "CyberClock": {
        "kind": "js",
        "handlers": ["src/main/app.js", "src/float/float.js", "src/float/cal.js", "src/tray/tray.js"],
        "announce": [
            ("src/main/index.html", [TOOLTIP_ATTR, JS_PAREN_CHORD]),
            ("src/main/app.js", [JS_SHORTCUT, JS_PAREN_CHORD]),
        ],
    },
    "CyberFeeds": {
        "kind": "js",
        "handlers": [
            "src/renderer/src/App.tsx",
            "src/renderer/src/components/ArticleList.tsx",
            "src/renderer/src/components/ArticleViewer.tsx",
            "src/renderer/src/components/TopBar.tsx",
            "src/shared/shortcuts.ts",
            "src/main/index.ts",
        ],
        "announce": [
            (
                "src/renderer/src/**/*.tsx",
                [
                    TOOLTIP_ATTR,
                    JS_SHORTCUT,
                    JS_WITH_SHORTCUT,
                    JS_KEYCAP,
                    JS_PAREN_CHORD,
                    ARIA_KEYS,
                ],
            )
        ],
    },
    "CyberFiles": {
        "kind": "js",
        "handlers": ["src/App.tsx", "src/components"],
        "extra_handlers": [("rust", "src-tauri/src/main.rs")],
        "announce": [
            ("src/**/*.tsx", [JS_SHORTCUT, JS_KEYSHORTCUTS, TOOLTIP_ATTR, JS_PAREN_CHORD])
        ],
        # The Delete branch receives e.shiftKey as an argument and opens the
        # permanent-delete mode; there is no modifier `if` to read.
        "allow": {"Shift+Delete": "Delete handler passes e.shiftKey"},
    },
    "CyberGo": {
        "kind": "js",
        "handlers": ["src/App.tsx", "src/components/TitleBar.tsx", "electron/main.ts"],
        "announce": [("src/**/*.tsx", [JS_SHORTCUT, TOOLTIP_ATTR, JS_PAREN_CHORD])],
    },
    "CyberLauncher": {
        "kind": "js",
        "handlers": ["src/App.tsx", "src/CyberTerminal.tsx", "electron/main.ts"],
        "announce": [
            ("src/**/*.tsx", [JS_SHORTCUT, JS_KEYSHORTCUTS, TOOLTIP_ATTR, JS_PAREN_CHORD])
        ],
        # Text fields and the embedded terminal implement editing natively; the
        # context-menu rows name those native actions, not app bindings.
        "allow": {
            "Ctrl+A": "native text editing",
            "Ctrl+C": "native text editing",
            "Ctrl+V": "native text editing",
            "Ctrl+X": "native text editing",
            "Ctrl+Y": "native text editing",
            "Ctrl+Z": "native text editing",
        },
    },
    "CyberManager": {
        "kind": "cs",
        "handlers": [
            "src/CyberManager.UI/MainWindow.xaml.cs",
            "src/CyberManager.UI/Controls/KeyboardShortcuts.cs",
            "src/CyberManager.UI/Controls/CompactProcessView.xaml.cs",
            "src/CyberManager.UI/Dialogs/ProcessPropertiesWindow.xaml.cs",
            "src/CyberManager.UI/Services/GlobalHotkeyService.cs",
        ],
        "announce": [
            ("src/CyberManager.UI/**/*.cs", [DOTNET_WITH_SHORTCUT, DOTNET_CONST_SHORTCUT, DOTNET_GESTURE, DOTNET_CONST_GESTURE]),
            ("src/CyberManager.UI/**/*.xaml", [XAML_GESTURE]),
        ],
    },
    "CyberNotes": {
        "kind": "js",
        "handlers": [
            "src/components/MainApp.tsx", "src/components/NoteEditor.tsx",
            "src/components/NoteList.tsx", "src/components/TitleBar.tsx",
            "src/App.tsx", "electron/main.ts",
        ],
        "announce": [
            ("src/**/*.tsx", [JS_SHORTCUT, JS_KEYSHORTCUTS, TOOLTIP_ATTR, JS_PAREN_CHORD])
        ],
        # The editor engine owns these: TipTap binds Mod-b/i/u and Mod-z/y, and
        # the clipboard chords are native inside the contenteditable.
        "allow": {
            "Ctrl+B": "TipTap bold binding",
            "Ctrl+I": "TipTap italic binding",
            "Ctrl+U": "TipTap underline binding",
            "Ctrl+Z": "TipTap undo binding",
            "Ctrl+Y": "TipTap redo binding",
            "Ctrl+C": "native clipboard",
            "Ctrl+V": "native clipboard",
        },
    },
    "CyberPaste": {
        "kind": "js",
        "handlers": [
            "frontend/src/App.tsx", "frontend/src/hooks",
            "frontend/src/components", "frontend/src/windows",
        ],
        "announce": [
            (
                "frontend/src/**/*.tsx",
                [JS_SHORTCUT, JS_KEYSHORTCUTS, TOOLTIP_ATTR, JS_PAREN_CHORD],
            )
        ],
        # Context-menu mnemonics are resolved at runtime from `keyHint`, so a
        # single letter has no literal comparison to find.
        "allow": {"T": "context-menu keyHint"},
    },
    "CyberPDF": {
        "kind": "cs",
        "handlers": ["src/CyberPDF.UI/MainWindow.cs", "src/CyberPDF.UI/Controls/PageViewer.cs"],
        "announce": [
            (
                "src/CyberPDF.UI/MainWindow.cs",
                [DOTNET_WITH_SHORTCUT, DOTNET_GESTURE, DOTNET_ATTACH_SHORTCUT, DOTNET_ATTACH_ALT],
            ),
        ],
    },
    "CyberSnap": {
        "kind": "cs",
        "handlers": [
            "src/CyberSnap/UI/Editor/EditorForm.cs",
            "src/CyberSnap/UI/Editor/EditorForm.Toolbar.cs",
            "src/CyberSnap/UI/Editor/EditorToolHotkeyHelper.cs",
            "src/CyberSnap/UI/Controls",
            "src/CyberSnap/Capture",
            "src/CyberSnap/App",
        ],
        "announce": [
            ("src/CyberSnap/UI/**/*.cs", [DOTNET_WITH_SHORTCUT, DOTNET_GESTURE]),
            ("src/CyberSnap/Capture/**/*.cs", [DOTNET_WITH_SHORTCUT, DOTNET_GESTURE]),
        ],
    },
    "CyberTray": {
        "kind": "js",
        "handlers": ["src/App.tsx", "electron/main.ts"],
        "announce": [
            (
                "src/**/*.tsx",
                [
                    JS_SHORTCUT,
                    TOOLTIP_ATTR,
                    JS_WITH_SHORTCUT,
                    JS_KEYCAP,
                    JS_PAREN_CHORD,
                    ARIA_KEYS,
                ],
            )
        ],
    },
    "CyberViewer": {
        "kind": "js",
        "handlers": ["js/app.js", "js/workspace.js", "js/video-player.js", "main.js"],
        "announce": [
            ("CyberViewer.html", [TOOLTIP_ATTR, MENU_SPAN, ARIA_KEYS, JS_PAREN_CHORD]),
        ],
        "kbd_sheet": ["CyberViewer.html"],
    },
    "CyberWall": {
        "kind": "cs",
        "handlers": [
            "src/CyberWall.UI/MainWindow.xaml.cs",
            "src/CyberWall.UI/Controls/KeyboardShortcuts.cs",
            "src/CyberWall.UI/Views/SettingsView.xaml.cs",
        ],
        "announce": [
            ("src/CyberWall.UI/**/*.cs", [DOTNET_WITH_SHORTCUT, DOTNET_CONST_SHORTCUT, DOTNET_GESTURE, DOTNET_CONST_GESTURE]),
            ("src/CyberWall.UI/**/*.xaml", [XAML_GESTURE]),
        ],
    },
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def is_test_file(path: Path) -> bool:
    name = path.name.lower()
    return ".test." in name or ".spec." in name or "/tests/" in path.as_posix()


def is_glob(source: str) -> bool:
    return any(character in source for character in "*?[")


def gather(repo: Path, patterns: list[tuple[str, list[str]]]) -> tuple[set[str], dict[str, str], list[Path]]:
    """Return announced chords, constants and the files that were examined."""
    chords: set[str] = set()
    constants: dict[str, str] = {}
    examined: set[Path] = set()
    for source, _ in patterns:
        for path in sorted(repo.glob(source)):
            if not path.is_file() or is_test_file(path):
                continue
            text = read(path)
            examined.add(path)
            for name, value in re.findall(r"const\s+string\s+(\w+)\s*=\s*\"([^\"]+)\"", text):
                constants[name] = value
    for source, regexes in patterns:
        for path in sorted(repo.glob(source)):
            if not path.is_file() or is_test_file(path):
                continue
            chords |= announcements(read(path), regexes, constants)
    return chords, constants, sorted(examined)


def handler_chords(repo: Path, rules: dict) -> tuple[set[str], list[Path]]:
    found: set[str] = set()
    examined: set[Path] = set()
    extractors = {"js": js_handler_chords, "cs": cs_handler_chords, "rust": rust_handler_chords}

    def add(kind: str, path: Path) -> None:
        if path.is_file() and not is_test_file(path):
            found.update(extractors[kind](read(path)))
            examined.add(path)

    for relative in rules["handlers"]:
        path = repo / relative
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix in {".cs", ".ts", ".tsx", ".js", ".jsx"}:
                    add(rules["kind"], child)
        else:
            add(rules["kind"], path)
    for kind, relative in rules.get("extra_handlers", []):
        add(kind, repo / relative)
    return found, sorted(examined)


def check_repo(repo: Path) -> tuple[list[str], str]:
    rules = APPS.get(repo.name)
    if rules is None:
        if any(repo.glob("*.sln")) or any(repo.glob("package.json")):
            return [f"{repo.name}: no shortcut rules are registered for this app"], ""
        return [], ""

    announced, _, announce_files = gather(repo, rules["announce"])
    examined_announcements = set(announce_files)
    problems: list[str] = []
    for relative in rules.get("kbd_sheet", []):
        path = repo / relative
        if path.is_file():
            announced |= kbd_sheet_chords(read(path))
            examined_announcements.add(path)
        else:
            problems.append(f"{repo.name}: shortcut sheet {relative} is gone")

    handled, handler_files = handler_chords(repo, rules)
    handled |= set(rules.get("handled_extra", []))

    # A rule only guards the app while its sources still exist. A renamed
    # directory or file would otherwise leave both sides empty and the check
    # green without examining anything.
    for source, _ in rules["announce"]:
        if not is_glob(source) and not (repo / source).is_file():
            problems.append(f"{repo.name}: announcement source {source} is gone")
    for relative in [*rules["handlers"], *[path for _, path in rules.get("extra_handlers", [])]]:
        if not (repo / relative).exists():
            problems.append(f"{repo.name}: handler source {relative} is gone")
    if not examined_announcements:
        problems.append(f"{repo.name}: no announcement source matched; nothing was examined")
    if not handler_files:
        problems.append(f"{repo.name}: no handler source matched; nothing was examined")
    if not handled:
        problems.append(f"{repo.name}: no handler chord was resolved; the handler files hold no keyboard code")

    allowed = rules.get("allow", {})
    for chord in sorted(announced - handled - PLATFORM_CHORDS - set(allowed)):
        problems.append(f"{repo.name}: announces {chord} but no handler resolves it")
    summary = (
        f"{len(examined_announcements)} announcement file(s), {len(handler_files)} handler file(s), "
        f"{len(announced)} announced, {len(handled)} resolved"
    )
    return problems, summary


def main(argv: list[str]) -> int:
    targets = [Path(argument) for argument in argv[1:]] or [Path.cwd()]
    failures: list[str] = []
    for target in targets:
        repo = target.resolve()
        problems, summary = check_repo(repo)
        if problems:
            failures.extend(problems)
            for problem in problems:
                print(f"FAIL {problem}")
        else:
            print(f"OK   {repo.name}: announced shortcuts have handlers ({summary})")
    if failures:
        print(f"\n{len(failures)} shortcut problem(s) found.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
