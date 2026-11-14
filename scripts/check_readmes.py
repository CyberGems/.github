#!/usr/bin/env python3
"""Check that README.md and README.es.md stay in sync.

The Spanish file is a translation, so the prose differs on purpose. What must
match is the structure: the same heading levels in the same order, the same
number of tables with the same data rows (file names are not translated; the
header row is, so it is excluded), the same number of code blocks, and a link
from each file to the other.

Usage: python3 check_readmes.py [repository-root]
Without an argument the repository root is two levels above this script, which
is what the .github repository needs. App repositories pass their own root when
this script is checked out from CyberGems/.github.
"""

from __future__ import annotations

import pathlib
import re
import sys

SEPARATOR_CELLS = {"-", ":", " "}

# In this repository the tables list file names, so the first cell must match.
# App READMEs use tables of translated prose, so there only the shape is
# comparable. Set with --tables=labels or --tables=counts.
TABLE_MODE = "labels"


def root_dir() -> pathlib.Path:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        return pathlib.Path(sys.argv[1]).resolve()
    return pathlib.Path(__file__).resolve().parent.parent


def strip_fenced_blocks(text: str) -> str:
    """Remove fenced code blocks so their contents are not parsed as markdown."""
    return re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)


def headings(text: str) -> list[tuple[int, str]]:
    result = []
    for line in strip_fenced_blocks(text).splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            result.append((len(match.group(1)), match.group(2).strip()))
    return result


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Return (header, data rows) for every markdown table."""
    block: list[str] = []
    blocks: list[list[str]] = []
    for line in strip_fenced_blocks(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            block.append(stripped)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)

    parsed = []
    for rows in blocks:
        cells = [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
        separator = next(
            (index for index, row in enumerate(cells) if row and all(set(cell) <= SEPARATOR_CELLS for cell in row)),
            None,
        )
        if separator is None:
            continue
        parsed.append((cells[0], cells[separator + 1:]))
    return parsed


def code_blocks(text: str) -> int:
    return len(re.findall(r"^```", text, flags=re.MULTILINE)) // 2


def links_to(text: str, target: str) -> bool:
    """Accept markdown links and raw HTML anchors, with or without ./."""
    pattern = (
        r"(\]\(\s*\.?/?" + re.escape(target) + r"\s*\))"
        r"|(href\s*=\s*[\"']\.?/?" + re.escape(target) + r"[\"'])"
    )
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def check() -> list[str]:
    root = root_dir()
    english = root / "README.md"
    spanish = root / "README.es.md"
    problems: list[str] = []

    if not english.is_file():
        return [f"{english} is missing"]
    if not spanish.is_file():
        return [f"{spanish} is missing"]

    en_text = english.read_text(encoding="utf-8")
    es_text = spanish.read_text(encoding="utf-8")

    en_levels = [level for level, _ in headings(en_text)]
    es_levels = [level for level, _ in headings(es_text)]
    if en_levels != es_levels:
        problems.append(
            f"heading structure differs: README.md has levels {en_levels}, README.es.md has {es_levels}"
        )

    en_tables = tables(en_text)
    es_tables = tables(es_text)
    if len(en_tables) != len(es_tables):
        problems.append(f"table count differs: README.md has {len(en_tables)}, README.es.md has {len(es_tables)}")
    else:
        for table_index, ((en_header, en_rows), (es_header, es_rows)) in enumerate(zip(en_tables, es_tables)):
            if len(en_header) != len(es_header):
                problems.append(
                    f"table {table_index + 1} has {len(en_header)} columns in README.md "
                    f"and {len(es_header)} in README.es.md"
                )
            if len(en_rows) != len(es_rows):
                problems.append(
                    f"table {table_index + 1} has {len(en_rows)} data rows in README.md "
                    f"and {len(es_rows)} in README.es.md"
                )
                continue
            for row_index, (en_row, es_row) in enumerate(zip(en_rows, es_rows)):
                if len(en_row) != len(es_row):
                    problems.append(
                        f"table {table_index + 1} row {row_index + 1} has {len(en_row)} cells in README.md "
                        f"and {len(es_row)} in README.es.md"
                    )
                elif TABLE_MODE == "labels" and en_row[0] != es_row[0]:
                    problems.append(
                        f"table {table_index + 1} row {row_index + 1} starts with {en_row[0]!r} in README.md "
                        f"but {es_row[0]!r} in README.es.md"
                    )

    en_blocks = code_blocks(en_text)
    es_blocks = code_blocks(es_text)
    if en_blocks != es_blocks:
        problems.append(f"code blocks differ: README.md has {en_blocks}, README.es.md has {es_blocks}")

    if not links_to(en_text, "README.es.md"):
        problems.append("README.md does not link to README.es.md")
    if not links_to(es_text, "README.md"):
        problems.append("README.es.md does not link to README.md")

    return problems


def main() -> int:
    global TABLE_MODE
    for argument in sys.argv[1:]:
        if argument.startswith("--tables="):
            value = argument.split("=", 1)[1]
            if value not in {"labels", "counts"}:
                print(f"unknown --tables mode: {value}", file=sys.stderr)
                return 2
            TABLE_MODE = value

    root = root_dir()
    problems = check()
    if problems:
        print(f"README sync check failed for {root}:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    en_text = (root / "README.md").read_text(encoding="utf-8")
    en_headings = headings(en_text)
    rows = sum(len(data) for _, data in tables(en_text))
    print(
        f"README.md and README.es.md in sync in {root.name}: {len(en_headings)} headings, "
        f"{rows} table rows, code blocks and mutual links match"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
