#!/usr/bin/env python3
"""Check that README.md and README.es.md stay in sync.

The Spanish file is a translation, so the prose differs on purpose. What must
match is the structure: the same heading levels in the same order, the same
number of tables with the same data rows (file names are not translated; the
header row is, so it is excluded), the same number of code blocks, and a link
from each file to the other.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGLISH = ROOT / "README.md"
SPANISH = ROOT / "README.es.md"

SEPARATOR_CELLS = {"-", ":", " "}


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


def check() -> list[str]:
    problems: list[str] = []

    if not ENGLISH.is_file():
        return ["README.md is missing"]
    if not SPANISH.is_file():
        return ["README.es.md is missing"]

    en_text = ENGLISH.read_text(encoding="utf-8")
    es_text = SPANISH.read_text(encoding="utf-8")

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
                elif en_row[0] != es_row[0]:
                    problems.append(
                        f"table {table_index + 1} row {row_index + 1} starts with {en_row[0]!r} in README.md "
                        f"but {es_row[0]!r} in README.es.md"
                    )

    en_blocks = code_blocks(en_text)
    es_blocks = code_blocks(es_text)
    if en_blocks != es_blocks:
        problems.append(f"code blocks differ: README.md has {en_blocks}, README.es.md has {es_blocks}")

    if not re.search(r"\]\(README\.es\.md\)", en_text):
        problems.append("README.md does not link to README.es.md")
    if not re.search(r"\]\(README\.md\)", es_text):
        problems.append("README.es.md does not link to README.md")

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("README sync check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    en_headings = headings(ENGLISH.read_text(encoding="utf-8"))
    en_tables = tables(ENGLISH.read_text(encoding="utf-8"))
    rows = sum(len(data) for _, data in en_tables)
    print(
        f"README.md and README.es.md in sync: {len(en_headings)} headings, "
        f"{len(en_tables)} table(s) with {rows} data rows, code blocks and mutual links match"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
