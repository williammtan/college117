"""Parse syllabus.md into class sessions and resolve which session(s) a date maps to.

The syllabus lists Monday/Wednesday sessions under week tables. Each session has a
date header like ``**Wednesday, May 13th: Genomic surveillance ...**`` followed by a
``Required Pre-Class Work:`` numbered list and an optional ``Optional:`` list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

# Spring Quarter 2026 — every date in the syllabus falls in these months.
_YEAR = 2026
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

_SESSION_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday),?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?",
    re.IGNORECASE,
)
_WEEK_RE = re.compile(r"Week\s+(\d+)\s*:\s*([^|]+?)(?:\s{2,}|Learning Goals|\*\*|\||$)", re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.*)")
_BULLET_RE = re.compile(r"^\s*[\*\-]\s+(.*)")
_NO_CLASS_RE = re.compile(r"holiday|no class|canceled|cancelled", re.IGNORECASE)


def _strip_md(text: str) -> str:
    """Drop markdown emphasis/heading markers and collapse whitespace."""
    text = re.sub(r"[#*_`]+", "", text)
    text = text.replace("\\", "")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Session:
    date: date
    weekday: str
    title: str
    week_number: int | None
    week_title: str | None
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    no_class: bool = False

    @property
    def label(self) -> str:
        return f"{self.date.isoformat()} ({self.weekday}) — {self.title or 'Session'}"


def parse(syllabus_path: str | Path) -> list[Session]:
    """Return all class sessions in chronological order."""
    lines = Path(syllabus_path).read_text(encoding="utf-8").splitlines()

    cur_week_num: int | None = None
    cur_week_title: str | None = None
    sessions: list[Session] = []
    cur: Session | None = None
    mode: str | None = None  # "required" | "optional" | None

    def flush_continuation(buf: list[str], target: list[str]) -> None:
        if buf and target:
            target[-1] = (target[-1] + " " + " ".join(buf)).strip()
        buf.clear()

    cont: list[str] = []

    for raw in lines:
        line = raw.rstrip()
        plain = _strip_md(line)

        wk = _WEEK_RE.search(line)
        if wk and "Week" in line and ":" in line:
            cur_week_num = int(wk.group(1))
            cur_week_title = _strip_md(wk.group(2))
            # Week header lines are tables; they never also start a session.

        sess = _SESSION_RE.search(plain)
        is_header = sess and (line.strip().startswith("**") or line.strip().startswith("#"))
        if is_header:
            if cur is not None:
                flush_continuation(cont, cur.required if mode == "required" else cur.optional if mode == "optional" else [])
                sessions.append(cur)
            weekday = sess.group(1).capitalize()
            month = _MONTHS[sess.group(2).lower()]
            day = int(sess.group(3))
            d = date(_YEAR, month, day)
            # Title = everything in the header after the date, cleaned.
            after = plain[sess.end():].lstrip(" :–-").strip()
            cur = Session(
                date=d,
                weekday=weekday,
                title=after,
                week_number=cur_week_num,
                week_title=cur_week_title,
                no_class=bool(_NO_CLASS_RE.search(plain)),
            )
            mode = None
            cont.clear()
            continue

        if cur is None:
            continue

        low = plain.lower()
        if "required pre-class work" in low or "required reading" in low:
            flush_continuation(cont, cur.required if mode == "required" else cur.optional if mode == "optional" else [])
            mode = "required"
            continue
        if low.startswith("optional"):
            flush_continuation(cont, cur.required if mode == "required" else cur.optional if mode == "optional" else [])
            mode = "optional"
            continue
        if _NO_CLASS_RE.search(plain):
            cur.no_class = True

        if mode is None:
            continue

        target = cur.required if mode == "required" else cur.optional
        m = _LIST_ITEM_RE.match(line)
        b = _BULLET_RE.match(line)
        if m:
            flush_continuation(cont, target)
            target.append(_strip_md(m.group(2)))
        elif b:
            flush_continuation(cont, target)
            target.append(_strip_md(b.group(1)))
        elif plain and not plain.startswith("|"):
            # Continuation of the current reading citation (wrapped line / URL).
            cont.append(plain)
        else:
            flush_continuation(cont, target)

    if cur is not None:
        flush_continuation(cont, cur.required if mode == "required" else cur.optional if mode == "optional" else [])
        sessions.append(cur)

    sessions.sort(key=lambda s: s.date)
    return sessions


@dataclass
class Resolution:
    target: date
    current: Session | None  # session whose readings are "due" for/around target
    previous: Session | None  # the class session immediately before `current`

    def describe(self) -> str:
        parts = []
        parts.append(f"Target date: {self.target.isoformat()}")
        parts.append(f"  current : {self.current.label if self.current else '(none)'}")
        parts.append(f"  previous: {self.previous.label if self.previous else '(none)'}")
        return "\n".join(parts)


def resolve(sessions: list[Session], target: date) -> Resolution:
    """Map a date to the relevant session pair.

    ``current``  = the session on ``target`` if class meets that day, otherwise the
                   next upcoming session (its readings are what's "due" next).
    ``previous`` = the class session immediately before ``current`` (its lecture is
                   "the lecture the day before").
    """
    teaching = [s for s in sessions if not s.no_class]

    current = next((s for s in teaching if s.date == target), None)
    if current is None:
        current = next((s for s in teaching if s.date > target), None)
    if current is None:  # past the end of term — fall back to the last session
        current = teaching[-1] if teaching else None

    previous = None
    if current is not None:
        before = [s for s in teaching if s.date < current.date]
        previous = before[-1] if before else None

    return Resolution(target=target, current=current, previous=previous)


def _parse_date(s: str) -> date:
    s = s.strip().lower()
    if s in ("", "today"):
        return date.today()
    if s == "tomorrow":
        from datetime import timedelta
        return date.today() + timedelta(days=1)
    return datetime.strptime(s, "%Y-%m-%d").date()


if __name__ == "__main__":
    import sys

    here = Path(__file__).resolve().parent.parent
    sess = parse(here / "syllabus.md")
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        for s in sess:
            tag = " [NO CLASS]" if s.no_class else ""
            print(f"{s.date} {s.weekday:9s} W{s.week_number}  {s.title[:50]}{tag}")
            for r in s.required:
                print(f"    - {r[:90]}")
    else:
        tgt = _parse_date(sys.argv[1] if len(sys.argv) > 1 else "today")
        res = resolve(sess, tgt)
        print(res.describe())
        for tag, s in (("CURRENT", res.current), ("PREVIOUS", res.previous)):
            if not s:
                continue
            print(f"\n[{tag}] {s.label}")
            print("  required:")
            for r in s.required:
                print(f"    - {r}")
