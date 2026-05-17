# COLLEGE 117 — Section Prep Toolkit

On-demand: for a given date, summarize the readings due + the previous
lecture, and produce color-coded highlighted PDFs of the readings.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install pdfplumber pypdf reportlab pytesseract pdf2image
```

Optional, for a live Canvas pull, create a gitignored `.env`:

```
CANVAS_TOKEN=<canvas access token>
COURSE_ID=225539
```

Without a token, `fetch` falls back to the committed PDFs under `files/`.

## Daily loop

```bash
# 1. resolve date -> readings due + prior lecture; pull + extract text
./.venv/bin/python section_prep.py plan  today          # preview only
./.venv/bin/python section_prep.py fetch today           # add --no-fetch to skip Canvas

# 2. read data/section_prep/<date>/text/*.txt, write summaries, and author
#    data/section_prep/<date>/phrases.json  (8-15 phrases per category per PDF)

# 3. burn in the highlights
./.venv/bin/python section_prep.py highlight data/section_prep/<date>/phrases.json
```

`<date>` is `YYYY-MM-DD`, `today`, or `tomorrow`.

## Layout

- `prep/syllabus.py` — parse `syllabus.md`; map a date to current/previous sessions
- `prep/canvas.py` — targeted Canvas fetch (token via `.env`)
- `prep/match.py` — match a citation to a downloaded file (content-aware)
- `prep/highlight.py` — pdfplumber → pypdf color-coded highlighter + legend page
- `section_prep.py` — `plan` / `fetch` / `highlight` driver

## phrases.json shape

```json
{ "files/08_Week 8.../Reading.pdf": {
    "title": "Legend subtitle",
    "argument": ["exact phrase from the PDF", "..."],
    "evidence": ["..."], "concept": ["..."],
    "application": ["..."], "implication": ["..."] } }
```

Color scheme: 🟡 argument · 🟢 evidence · 🟣 concept · 🔵 application · 🟠 implication.
The highlighter normalizes ligatures/quotes/dashes and rejoins line-broken
words, so phrases just need to be the readable text as it appears.
