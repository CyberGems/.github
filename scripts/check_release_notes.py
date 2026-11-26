#!/usr/bin/env python3
"""Release note coverage checker for CyberGems.

The tool is mechanical on purpose. It cannot decide whether a highlight is well
written, but it does prove that the whole commit range was seen, that every
user-facing commit is covered by a highlight, that English and Spanish match,
and that no template leftovers remain.

Usage:
  python check_release_notes.py inventory --repo PATH --from TAG \
      [--to HEAD] [--out AUDIT.json]

  python check_release_notes.py check --repo PATH --from TAG \
      [--to HEAD] --notes DRAFT.md --audit AUDIT.json [--version TAG]

Workflow:
  1. Run inventory. It writes a JSON with every commit in the range, a
     suggested impact and an empty coverage list.
  2. Review the suggested impact values (user / internal / noise) and fill
     coverage with the highlight IDs that describe each user-facing commit.
     Highlight IDs are H1, H2, ... in the English section.
  3. Write the release draft, then run check. Exit code 1 means the draft is
     not ready. The audit file is local scratch; keep it out of commits.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

NOISE = re.compile(
    r"\b(chore|ci|tests?|deps|dependencies|bump|typos?|comments?|formatting|"
    r"lint|readme|docs|doc|document|documentation|disclosure|funding|sponsor|"
    r"badge|workflows?|actions|hooks?|exclude|backup|license|smoke|scripts?|"
    r"metadata|template)\b",
    re.I,
)
INTERNAL = re.compile(
    r"\b(refactor|rename|renamed|moved|restructure|internal|optimi[sz]e|"
    r"simplif(?:y|ied)|migrate|migration|upgrade|build|tooling|cleanup|"
    r"clean up|guard|validation|validator|winget|manifest|submission|markers|"
    r"line endings)\b",
    re.I,
)
TOPICS = [
    ("tray", r"\btray|flyout|taskbar|notification area\b"),
    ("theme", r"\btheme|dark|light|gray|color|colour|palette\b"),
    ("shortcut", r"\bhotkey|shortcut|keybinding|keyboard\b"),
    ("settings", r"\bsettings?|preferences|config\b"),
    ("installer", r"\binstaller|setup|nsis|portable|winget|update\b"),
    ("ui", r"\bui|window|dialog|menu|button|layout|icon|tooltip|caption\b"),
    ("language", r"\btranslation|spanish|english|i18n|locale|language\b"),
    ("media", r"\baudio|video|image|media|visualizer\b"),
    ("search", r"\bsearch|find|filter\b"),
    ("docs", r"\breadme|docs?|wiki|changelog\b"),
    ("ci", r"\bci|workflow|test|lint|smoke|hook\b"),
]


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def commits_in_range(repo: Path, from_ref: str, to_ref: str) -> list[dict]:
    output = run_git(
        repo, "log", "--no-merges", f"--pretty=format:%h%x09%s", f"{from_ref}..{to_ref}"
    )
    commits = []
    for line in output.splitlines():
        if "\t" not in line:
            continue
        short, subject = line.split("\t", 1)
        commits.append({"hash": short, "subject": subject})
    return commits


def guess_impact(subject: str) -> str:
    if NOISE.search(subject):
        return "noise"
    if INTERNAL.search(subject):
        return "internal"
    return "user"


def guess_topic(subject: str) -> str:
    for label, pattern in TOPICS:
        if re.search(pattern, subject, re.I):
            return label
    return "general"


def make_inventory(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    commits = commits_in_range(repo, args.from_ref, args.to)
    audit = {
        "schema": 1,
        "repo": str(repo),
        "from": args.from_ref,
        "to": args.to,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commits": [
            {
                "hash": c["hash"],
                "subject": c["subject"],
                "impact": guess_impact(c["subject"]),
                "topic": guess_topic(c["subject"]),
                "coverage": [],
            }
            for c in commits
        ],
    }
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    counts = {k: sum(c["impact"] == k for c in audit["commits"]) for k in ("user", "internal", "noise")}
    print(f"Commits in {args.from_ref}..{args.to}: {len(commits)}")
    print(f"Suggested impact: user={counts['user']} internal={counts['internal']} noise={counts['noise']}")
    print(f"Audit written to {out}")
    print("Review every impact value, then fill coverage with H1, H2, ... before running check.")
    return 0


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def parse_summary(text: str) -> str:
    match = re.search(
        r"<!--\s*changelog-summary:start\s*-->(.*?)<!--\s*changelog-summary:end\s*-->",
        text,
        re.S | re.I,
    )
    if match:
        return " ".join(match.group(1).split())
    heading = re.search(
        r"^###\s+[^\n]*(?:What's new|Novedades de esta versión)[^\n]*$", text, re.M | re.I
    )
    if heading:
        for line in text[heading.end():].splitlines():
            value = line.strip()
            if not value or value.startswith(("<!--", ">", "#", "---")):
                continue
            return " ".join(value.split())
    return ""


def parse_highlights(text: str, spanish: bool) -> list[str]:
    pattern = (
        r"^###\s+[^\n]*(?:Novedades destacadas|Destacados)[^\n]*$"
        if spanish
        else r"^###\s+[^\n]*(?:Key Features|Highlights)[^\n]*$"
    )
    heading = re.search(pattern, text, re.M | re.I)
    if not heading:
        return []
    bullets = []
    for line in text[heading.end():].splitlines():
        stripped = line.strip()
        if stripped.startswith("###") or stripped.startswith("</details>") or stripped == "---":
            break
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def word_count(text: str) -> int:
    return len(re.findall(r"[\w’'-]+", text, re.UNICODE))


def normalize_for_stale(text: str) -> str:
    return re.sub(r"\{\{[^}]+\}\}", "{{X}}", " ".join(text.split()))


def check_draft(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    notes_path = Path(args.notes).resolve()
    audit_path = Path(args.audit).resolve()
    if not notes_path.is_file():
        print(f"[FAIL] Draft not found: {notes_path}")
        return 1
    if not audit_path.is_file():
        print(f"[FAIL] Audit not found: {audit_path}. Run the inventory command first.")
        return 1

    notes = load_text(notes_path)
    audit = json.loads(load_text(audit_path))
    commits = commits_in_range(repo, args.from_ref, args.to)
    actual = [c["hash"] for c in commits]
    recorded = [c.get("hash") for c in audit.get("commits", [])]
    missing = sorted(set(actual) - set(recorded))
    extra = sorted(set(recorded) - set(actual))

    en = parse_highlights(notes, spanish=False)
    es = parse_highlights(notes, spanish=True)
    en_summary = parse_summary(notes)
    es_summary = parse_summary(notes[notes.find("<details>") + 9:] if "<details>" in notes else notes)
    audit_user_count = sum(c.get("impact") == "user" for c in audit.get("commits", []))
    maintenance_note = bool(re.search(r"maintenance|mantenimiento|no user-facing", notes, re.I))

    failures: list[str] = []
    warnings: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(audit.get("schema") == 1, "audit schema must be 1")
    require(not missing, f"audit omits commits in range: {', '.join(missing)}")
    require(not extra, f"audit lists commits outside range: {', '.join(extra)}")
    for c in audit.get("commits", []):
        require(
            c.get("impact") in {"user", "internal", "noise"},
            f"invalid impact for {c.get('hash')}: {c.get('impact')!r}",
        )

    placeholders = sorted(set(re.findall(r"\{\{[^}]+\}\}", notes)))
    require(not placeholders, f"unresolved template placeholders: {', '.join(placeholders)}")
    require(bool(en_summary), "English summary not found")
    require(bool(es_summary), "Spanish summary not found")
    if en_summary:
        count = word_count(en_summary)
        require(25 <= count <= 45, f"English summary has {count} words, expected 25-45")
    if es_summary:
        count = word_count(es_summary)
        if not 20 <= count <= 50:
            warnings.append(f"Spanish summary has {count} words, expected roughly 25-45")
    require(
        bool(en) or (audit_user_count == 0 and maintenance_note),
        "English highlights not found",
    )
    require(len(en) == len(es), f"highlight parity mismatch: EN={len(en)} ES={len(es)}")

    template_path = repo / ".github" / "release-template.md"
    if template_path.is_file():
        template = load_text(template_path)
        t_summary = normalize_for_stale(parse_summary(template))
        if en_summary and t_summary and normalize_for_stale(en_summary) == t_summary:
            failures.append("summary still matches the previous release template")
        t_highlights = [normalize_for_stale(h) for h in parse_highlights(template, False)]
        if en and t_highlights and [normalize_for_stale(h) for h in en] == t_highlights:
            failures.append("highlights still match the previous release template")

    valid_ids = {f"H{i}" for i in range(1, len(en) + 1)}
    user_commits = [c for c in audit.get("commits", []) if c.get("impact") == "user"]
    total = len(audit.get("commits", []))
    uncovered = []
    bad_ids = []
    for c in user_commits:
        coverage = c.get("coverage") or []
        if not coverage:
            uncovered.append(f"{c.get('hash')} {c.get('subject', '')}")
        bad_ids.extend(
            f"{c.get('hash')}:{item}" for item in coverage if item not in valid_ids
        )
    require(not uncovered, "user-facing commits without highlight coverage:\n  " + "\n  ".join(uncovered))
    require(not bad_ids, "invalid highlight IDs: " + ", ".join(bad_ids))

    referenced = {
        item for c in audit.get("commits", []) for item in (c.get("coverage") or [])
    }
    for highlight_id in sorted(valid_ids - referenced):
        if user_commits:
            failures.append(f"{highlight_id} has no supporting commit (possible padding)")
        else:
            warnings.append(f"{highlight_id} has no supporting commit")

    require(
        not (len(user_commits) >= 15 and len(en) < 6),
        f"{len(user_commits)} user-facing commits but only {len(en)} highlights; redo the audit",
    )
    require(
        not (total >= 40 and len(en) < 8),
        f"{total} commits but only {len(en)} highlights; redo the audit",
    )
    version = args.version or args.to
    if re.match(r"^v?\d+\.\d+\.[1-9]\d*$", version) and len(en) > 3:
        warnings.append("patch release has more than 3 highlights; check for padding")

    for message in failures:
        print(f"[FAIL] {message}")
    for message in warnings:
        print(f"[WARN] {message}")
    if not failures:
        print(
            f"[PASS] {total} commits reviewed, {len(user_commits)} user-facing, "
            f"{len(en)} highlights in each language."
        )
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", required=True, help="repository path")
        p.add_argument("--from", dest="from_ref", required=True, help="previous release tag")
        p.add_argument("--to", default="HEAD", help="current ref (default: HEAD)")

    inv = sub.add_parser("inventory", help="write a reviewable commit audit")
    common(inv)
    inv.add_argument("--out", required=True, help="audit JSON path (local scratch)")
    inv.set_defaults(func=make_inventory)

    chk = sub.add_parser("check", help="validate a release draft")
    common(chk)
    chk.add_argument("--notes", required=True, help="draft markdown path")
    chk.add_argument("--audit", required=True, help="reviewed audit JSON path")
    chk.add_argument("--version", help="release tag, used for patch detection")
    chk.set_defaults(func=check_draft)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
