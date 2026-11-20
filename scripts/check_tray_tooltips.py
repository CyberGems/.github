#!/usr/bin/env python3
"""Validate the suite-wide tray tooltip standard.

Every CyberGems app with a tray icon must build its hover text as
`<App> · <segment>`, with at most one segment (state first, otherwise the
global shortcut), no version, and a 63-character cap ending in an ellipsis.

The check is static on purpose: it runs in every repository without building
the app, and it points at the exact function that formats the tooltip. It
catches the regressions seen in practice, a version written straight into the
tray text and a rebuild path that bypasses the shared formatter.

Usage:
    python3 scripts/check_tray_tooltips.py path/to/AppRepo [more repos...]

With no arguments the current directory is checked.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LEN = 63
ELLIPSIS = "…"
SEPARATOR = " · "

APPS: dict[str, dict] = {
    "CyberClock": {
        "blocks": [
            ("src-tauri/src/lib.rs", ["fn format_tray_tooltip", "fn clamp_tray_tooltip"]),
        ],
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberFeeds": {
        "blocks": [
            (
                "src/main/tray-tooltip.ts",
                ["function clampTrayTooltip", "function formatTrayTooltip"],
            ),
        ],
        "tooltip_calls": ("buildTrayTooltip", ["src/main/tray.ts"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LEN": "src/main/tray-tooltip.ts"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberFiles": {
        "blocks": [
            ("src-tauri/src/main.rs", ["fn format_tray_tooltip", "fn clamp_tray_tooltip"]),
        ],
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberGo": {
        "blocks": [
            ("electron/tray-tooltip.ts", ["function formatTrayTooltip"]),
        ],
        "tooltip_calls": ("formatTrayTooltip", ["electron/main.ts"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LENGTH": "electron/tray-tooltip.ts"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberLauncher": {
        "blocks": [
            ("electron/tray-tooltip.ts", ["function formatTrayTooltip"]),
        ],
        "tooltip_calls": ("formatTrayTooltip", ["electron/main.ts"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LENGTH": "electron/tray-tooltip.ts"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberManager": {
        "blocks": [
            (
                "src/CyberManager.UI/Services/TrayTooltipFormatter.cs",
                ["static string Format(string? segment)"],
            ),
        ],
        "limit_constants": {
            "MaxLength": "src/CyberManager.UI/Services/TrayTooltipFormatter.cs"
        },
        "forbid": ["GetCurrentVersionLabel", "127"],
    },
    "CyberNotes": {
        "blocks": [
            ("electron/tray-tooltip.ts", ["function formatTrayTooltip"]),
        ],
        "tooltip_calls": ("formatTrayTooltip", ["electron/main.ts"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LENGTH": "electron/tray-tooltip.ts"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberPaste": {
        "blocks": [
            ("src-tauri/src/lib.rs", ["fn format_tray_tooltip", "fn clamp_tray_tooltip"]),
        ],
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberSnap": {
        "blocks": [
            (
                "src/CyberSnap.AppModel/TrayTooltipText.cs",
                ["static string Format(string? segment)"],
            ),
        ],
        "limit_constants": {"MaxLength": "src/CyberSnap.AppModel/TrayTooltipText.cs"},
        "forbid": ["GetCurrentVersionLabel"],
    },
    "CyberTray": {
        "blocks": [
            ("electron/tray-tooltip.ts", ["function formatTrayTooltip"]),
        ],
        "tooltip_calls": ("formatTrayTooltip", ["electron/main.ts"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LENGTH": "electron/tray-tooltip.ts"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberViewer": {
        "blocks": [
            ("lib/tray-tooltip.js", ["function formatTrayTooltip"]),
        ],
        "tooltip_calls": ("formatTrayTooltip", ["main.js"]),
        "limit_constants": {"TRAY_TOOLTIP_MAX_LENGTH": "lib/tray-tooltip.js"},
        "forbid": ["getVersion", "GetCurrentVersionLabel"],
    },
    "CyberWall": {
        "blocks": [
            (
                "src/CyberWall.Common/TrayTooltipText.cs",
                ["static string Format(string? segment)"],
            ),
        ],
        "limit_constants": {"MaxLength": "src/CyberWall.Common/TrayTooltipText.cs"},
        "forbid": ["GetCurrentVersionLabel"],
    },
}


def extract_block(text: str, marker: str) -> str | None:
    """Return the source of the function that starts at marker."""
    start = text.find(marker)
    if start < 0:
        return None

    brace = text.find("{", start)
    arrow = text.find("=>", start, brace if brace >= 0 else start + 200)
    # Expression-bodied members have no braces, so fall back to the line block.
    if brace >= 0 and brace - start < 200 and arrow < 0:
        depth = 0
        for index in range(brace, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]

    end = text.find("\n\n", start + len(marker))
    return text[start : end if end >= 0 else start + 600]


def check_repo(repo: Path) -> list[str]:
    name = repo.name
    rules = APPS.get(name)
    if rules is None:
        return [f"{name}: no tray tooltip rules are registered for this repository"]

    problems: list[str] = []
    blocks: list[str] = []

    for relative, markers in rules["blocks"]:
        path = repo / relative
        if not path.is_file():
            problems.append(f"{name}: missing {relative}")
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for marker in markers:
            block = extract_block(text, marker)
            if block is None:
                problems.append(f"{name}: {relative} has no {marker.strip()}")
            else:
                blocks.append(block)

    string_entries: list[str] = []
    for relative, prefix in rules.get("strings", []):
        path = repo / relative
        if not path.is_file():
            problems.append(f"{name}: missing {relative}")
            continue
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        entries = [line.strip() for line in text.splitlines() if line.strip().startswith(f"[{prefix}")]
        if not entries:
            problems.append(f"{name}: {relative} has no {prefix} entries")
        for entry in entries:
            string_entries.append(entry)
            if f"{name}{SEPARATOR}" not in entry:
                problems.append(f"{name}: tray tooltip string lacks `{name}{SEPARATOR}`: {entry}")
            if "—" in entry or f"{name}: " in entry:
                problems.append(f"{name}: tray tooltip string uses a deprecated separator: {entry}")

    joined = "\n".join(blocks + string_entries)
    if joined and f"{name}{SEPARATOR}" not in joined:
        problems.append(f"{name}: the tooltip builder does not use `{name}{SEPARATOR}`")
    has_limit = str(MAX_LEN) in joined
    for constant, relative in rules.get("limit_constants", {}).items():
        path = repo / relative
        if constant in joined and path.is_file():
            source = path.read_text(encoding="utf-8")
            if re.search(rf"\b{constant}\s*=\s*{MAX_LEN}\b", source):
                has_limit = True
    if joined and not has_limit:
        problems.append(f"{name}: the tooltip builder has no {MAX_LEN}-character cap")
    if joined and ELLIPSIS not in joined:
        problems.append(f"{name}: the {MAX_LEN}-character cap does not end in an ellipsis")
    for token in rules.get("forbid", []):
        if token in joined:
            problems.append(f"{name}: the tooltip builder still references {token}")

    tooltip_calls = rules.get("tooltip_calls")
    if tooltip_calls:
        allowed_call, files = tooltip_calls
        for relative in files:
            path = repo / relative
            if not path.is_file():
                problems.append(f"{name}: missing {relative}")
                continue
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                if "setToolTip(" not in line:
                    continue
                if allowed_call not in line:
                    problems.append(
                        f"{name}: {relative}:{number} sets the tooltip without {allowed_call}"
                    )

    return problems


def main(argv: list[str]) -> int:
    targets = [Path(argument) for argument in argv[1:]] or [Path.cwd()]
    failures: list[str] = []

    for target in targets:
        repo = target.resolve()
        problems = check_repo(repo)
        if problems:
            failures.extend(problems)
            for problem in problems:
                print(f"FAIL {problem}")
        else:
            print(f"OK   {repo.name}: tray tooltip format")

    if failures:
        print(f"\n{len(failures)} tray tooltip problem(s) found.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
