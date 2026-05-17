#!/usr/bin/env python3
"""On-demand COLLEGE 117 section prep.

Subcommands
-----------
  plan  [DATE]                 resolve a date -> sessions + reading list (no network)
  fetch [DATE] [--no-fetch]    pull the relevant week(s) from Canvas, match
                               readings to files, extract text -> a manifest
  highlight PHRASES_JSON       apply color-coded highlights from a phrases spec

DATE is YYYY-MM-DD, or "today" / "tomorrow" (default: today).

Typical flow:
  1. ./.venv/bin/python section_prep.py fetch today
  2. (Claude reads the extracted .txt files, writes summaries, and emits a
     phrases JSON choosing 8-15 passages per color category per reading)
  3. ./.venv/bin/python section_prep.py highlight data/section_prep/<date>/phrases.json
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pdfplumber

from prep import canvas, match, syllabus
from prep.highlight import highlight_pdf

ROOT = Path(__file__).resolve().parent
OUT_BASE = ROOT / "data" / "section_prep"


def _extract_text(pdf_path: Path, max_pages: int = 40) -> str:
    parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            parts.append(f"\n--- page {i + 1} ---\n")
            parts.append(page.extract_text() or "")
    return "".join(parts)


def _session_dict(s: syllabus.Session | None) -> dict | None:
    if s is None:
        return None
    return {
        "date": s.date.isoformat(),
        "weekday": s.weekday,
        "title": s.title,
        "week_number": s.week_number,
        "week_title": s.week_title,
        "required": s.required,
    }


def cmd_plan(target: date) -> None:
    sess = syllabus.parse(ROOT / "syllabus.md")
    res = syllabus.resolve(sess, target)
    print(res.describe())
    for tag, s in (("CURRENT (readings due)", res.current),
                   ("PREVIOUS (lecture to review)", res.previous)):
        if not s:
            continue
        print(f"\n[{tag}] {s.label}  (Week {s.week_number})")
        for r in s.required:
            print(f"   - {r[:110]}")


def _resolve_week_folder(s: syllabus.Session, do_fetch: bool) -> Path | None:
    """Return the local week folder, fetching from Canvas first if requested."""
    if do_fetch:
        try:
            folder, items = canvas.sync_week(ROOT, s.week_number, s.week_title)
            print(f"  fetched {len(items)} item(s) -> {folder.name}")
            return folder
        except SystemExit as e:
            print(f"  ! Canvas fetch skipped: {e}")
    # Local fallback: existing files/NN_Week N: ... folder.
    for p in sorted((ROOT / "files").glob(f"*Week {s.week_number}*")):
        if p.is_dir():
            return p
    return None


def cmd_fetch(target: date, do_fetch: bool) -> None:
    sess = syllabus.parse(ROOT / "syllabus.md")
    res = syllabus.resolve(sess, target)
    print(res.describe())

    out_dir = OUT_BASE / target.isoformat()
    txt_dir = out_dir / "text"
    txt_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "target": target.isoformat(),
        "current": _session_dict(res.current),
        "previous": _session_dict(res.previous),
        "readings": [],
        "lecture": None,
    }

    folders: dict[int, Path | None] = {}

    def folder_for(s: syllabus.Session) -> Path | None:
        if s.week_number not in folders:
            print(f"\nWeek {s.week_number} ({s.week_title}):")
            folders[s.week_number] = _resolve_week_folder(s, do_fetch)
        return folders[s.week_number]

    # Readings: current session's required list (what's "due"), plus the
    # previous session's required list ("the day before").
    reading_sessions = []
    if res.current:
        reading_sessions.append(("current", res.current))
    if res.previous:
        reading_sessions.append(("previous", res.previous))

    for which, s in reading_sessions:
        folder = folder_for(s)
        if folder is None:
            print(f"  ! no folder for Week {s.week_number}")
            continue
        for cite in s.required:
            m = match.match_reading(cite, folder)
            entry = {
                "session": which,
                "session_date": s.date.isoformat(),
                "citation": cite,
                "matched_file": str(m.path) if m.path else None,
                "match_score": m.score,
                "external_only": m.is_url_pointer,
                "text_file": None,
            }
            if m.path and m.path.suffix.lower() == ".pdf":
                try:
                    text = _extract_text(m.path)
                    tf = txt_dir / (m.path.stem[:80] + ".txt")
                    tf.write_text(text, encoding="utf-8")
                    entry["text_file"] = str(tf)
                    entry["chars"] = len(text)
                except Exception as e:  # noqa: BLE001
                    entry["error"] = repr(e)
            elif m.path and m.path.suffix.lower() == ".url":
                entry["external_url"] = m.path.read_text().strip()
            manifest["readings"].append(entry)
            tick = "✓" if entry["text_file"] else ("↗" if m.is_url_pointer else "?")
            print(f"  [{tick}] ({which}) {Path(cite).name[:70]}  "
                  f"-> {Path(m.path).name if m.path else 'NO MATCH'} ({m.score})")

    # Lecture to review = the PREVIOUS session's slide deck.
    if res.previous:
        folder = folder_for(res.previous)
        deck = match.find_lecture_deck(folder, res.previous.date) if folder else None
        if deck:
            text = _extract_text(deck)
            tf = txt_dir / ("LECTURE_" + deck.stem[:70] + ".txt")
            tf.write_text(text, encoding="utf-8")
            manifest["lecture"] = {
                "session_date": res.previous.date.isoformat(),
                "title": res.previous.title,
                "file": str(deck),
                "text_file": str(tf),
            }
            print(f"\n  lecture deck: {deck.name}")
        else:
            print("\n  ! no lecture deck found for previous session")

    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nManifest -> {mpath}")
    print("Next: read the .txt files, then build a phrases JSON and run "
          "`section_prep.py highlight <phrases.json>`.")


def cmd_highlight(spec_path: Path) -> None:
    """Apply highlights. Spec JSON: {pdf_path: {title?, <category>: [phrases]}}."""
    spec = json.loads(Path(spec_path).read_text())
    for pdf_path, cats in spec.items():
        src = Path(pdf_path)
        if not src.exists():
            print(f"  ! missing: {src}")
            continue
        title = cats.pop("title", None)
        out = src.with_name(src.stem + " [highlighted].pdf")
        report = highlight_pdf(src, out, cats, title=title)
        print(f"  {src.name}")
        print(f"    -> {report}")


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "highlight":
        if not rest:
            print("usage: section_prep.py highlight PHRASES_JSON")
            return 2
        cmd_highlight(Path(rest[0]))
        return 0

    do_fetch = "--no-fetch" not in rest
    rest = [a for a in rest if a != "--no-fetch"]
    target = syllabus._parse_date(rest[0]) if rest else date.today()

    if cmd == "plan":
        cmd_plan(target)
    elif cmd == "fetch":
        cmd_fetch(target, do_fetch)
    else:
        print(f"unknown command: {cmd}")
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
