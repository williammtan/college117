"""Fuzzy-match a syllabus reading citation to a downloaded file in a week folder.

Citations look like ``Moreau, Y. (2019). Crack down on genomic surveillance.
Nature ...`` and files like ``Moreau, Y. (2019). Crack down on genomic
surveillance..ExternalUrl.url`` or ``COLLEGE May 13 2026 Lecture- Genomic
Surveillance...pdf``. Scoring on author-surname + distinctive title tokens is
robust because Canvas item titles (which name the files) mirror the citations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "what", "when", "where",
    "your", "their", "are", "was", "were", "http", "https", "www", "com", "org",
    "edu", "doi", "pdf", "url", "html", "stanford", "oclc", "idm", "ncbi", "nlm",
    "nih", "gov", "article", "articles", "retrieved", "press", "university",
    "vol", "no", "pp", "in", "of", "a", "an", "on", "to", "is", "it", "as",
    "externalurl", "page", "assignment", "college", "lecture", "slides", "final",
    "vfinal", "vfinalv", "draft", "spring", "quarter",
}
_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")


def _split_camel(s: str) -> str:
    # "KateCrawford" -> "Kate Crawford"; "ATheoryofJustice" -> "A Theoryof Justice"
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z]{2})(?=[A-Z][a-z])", " ", s)
    return re.sub(r"[^A-Za-z]+", " ", s)


def _tokens(s: str) -> set[str]:
    s = re.sub(r"https?://\S+", " ", s)
    s = _split_camel(s)
    raw = re.findall(r"[A-Za-z]{3,}", s.lower())
    return {w for w in raw if w not in _STOP and w not in _MONTHS}


_CONTENT_CACHE: dict[str, set[str]] = {}


def _pdf_head_tokens(path: Path, pages: int = 2) -> set[str]:
    """Token set from the first pages of a PDF (filenames are often mangled)."""
    key = str(path)
    if key in _CONTENT_CACHE:
        return _CONTENT_CACHE[key]
    toks: set[str] = set()
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            chunk = " ".join(
                (p.extract_text() or "") for p in pdf.pages[:pages]
            )
        toks = _tokens(chunk[:4000])
    except Exception:  # noqa: BLE001  — scanned/locked PDFs just yield no tokens
        toks = set()
    _CONTENT_CACHE[key] = toks
    return toks


def _surnames(citation: str) -> set[str]:
    """Author surnames: capitalized words near the start, before year/title."""
    head = re.split(r"\(\d{4}\)|\.\s+[A-Z]|[“\"]", citation)[0][:120]
    names = re.findall(r"[A-Z][a-z]{2,}", head)
    return {n.lower() for n in names if n.lower() not in _STOP}


@dataclass
class Match:
    citation: str
    path: Path | None
    score: float
    is_url_pointer: bool


def _candidate_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [p for p in sorted(folder.iterdir())
            if p.is_file() and p.suffix.lower() in (".pdf", ".url")
            and not p.name.startswith(".")]


def _looks_like_lecture(name: str) -> bool:
    n = name.lower()
    return ("lecture" in n or "slides" in n
            or (n.startswith("college") and n.endswith(".pdf")))


def _score(citation_tok: set[str], citation_sur: set[str], cand_tok: set[str]) -> float:
    if not cand_tok:
        return 0.0
    title_overlap = len(citation_tok & cand_tok) / max(1, len(citation_tok))
    surname_hit = len(citation_sur & cand_tok) / max(1, len(citation_sur))
    return 0.65 * title_overlap + 0.35 * surname_hit


def match_reading(citation: str, folder: Path) -> Match:
    cite_tok = _tokens(citation)
    cite_sur = _surnames(citation)
    best_pdf: tuple[float, Path | None] = (0.0, None)
    best_url: tuple[float, Path | None] = (0.0, None)

    for f in _candidate_files(folder):
        is_pdf = f.suffix.lower() == ".pdf"
        score = _score(cite_tok, cite_sur, _tokens(f.name))
        if is_pdf:
            # Filenames are often mangled — also match on the PDF's own text.
            score = max(score, _score(cite_tok, cite_sur,
                                      _pdf_head_tokens(f)))
            if _looks_like_lecture(f.name):
                score *= 0.4  # slide decks shouldn't win article citations
            if score > best_pdf[0]:
                best_pdf = (score, f)
        else:
            if score > best_url[0]:
                best_url = (score, f)

    # Prefer the real PDF when it plausibly matches: it is the actual content,
    # whereas a .url is only a Canvas redirect pointer.
    if best_pdf[1] is not None and best_pdf[0] >= 0.22:
        chosen = best_pdf
    elif best_url[0] >= 0.18:
        chosen = best_url
    elif best_pdf[0] >= 0.18:
        chosen = best_pdf
    else:
        chosen = (0.0, None)

    return Match(
        citation=citation,
        path=chosen[1],
        score=round(chosen[0], 3),
        is_url_pointer=bool(chosen[1] and chosen[1].suffix.lower() == ".url"),
    )


def find_lecture_deck(folder: Path, session_date) -> Path | None:
    """Find the slide deck for a session by date tokens / 'Lecture' in filename."""
    if not folder.exists():
        return None
    md = session_date.strftime("%B").lower()       # e.g. "may"
    day = str(session_date.day)
    decks = [p for p in _candidate_files(folder)
             if p.suffix.lower() == ".pdf" and _looks_like_lecture(p.name)]
    # Prefer a deck whose filename names this session's month + day.
    for p in decks:
        n = p.name.lower()
        if md in n and re.search(rf"\b{day}\b", n):
            return p
    # Otherwise the single deck in the folder, if unambiguous.
    if len(decks) == 1:
        return decks[0]
    # Fall back: deck with the month name only.
    for p in decks:
        if md in p.name.lower():
            return p
    return decks[0] if decks else None
