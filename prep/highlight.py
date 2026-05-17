"""Color-coded PDF highlighter.

Pipeline (text PDFs):
  1. pdfplumber extracts char-level text + bboxes per page
  2. each phrase -> regex joining tokens with ``\\s*`` (handles line-break joins),
     matched against a normalized char stream (ligatures/quotes/dashes resolved)
  3. match offsets -> source char bboxes, grouped into per-line rectangles
  4. pdfplumber top-origin coords -> PDF bottom-origin coords
  5. pypdf ``Highlight`` annotations with QuadPoints + category color
  6. a reportlab legend page is prepended as page 1

Image-only PDFs (0 chars) fall back to OCR (pytesseract + pdf2image), drawing
PIL rectangles and re-exporting.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Highlight
from pypdf.generic import ArrayObject, FloatObject, NameObject, TextStringObject

# ---------------------------------------------------------------------------
# Color scheme — adapt phrase lists per paper; categories themselves are fixed.
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, tuple[str, str]] = {
    # key: (hex color without '#', legend description)
    "argument":     ("FFF176", "Core argument / thesis statements"),
    "evidence":     ("AED581", "Evidence / empirical studies / case facts"),
    "concept":      ("CE93D8", "Key concepts and definitions"),
    "application":  ("64B5F6", "Domain applications or case studies"),
    "implication":  ("FFB74D", "Policy / societal / structural implications"),
}
_EMOJI = {"argument": "🟡", "evidence": "🟢", "concept": "🟣",
          "application": "🔵", "implication": "🟠"}

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------
_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
    "ﬅ": "ft", "ﬆ": "st",
}
_QUOTES = {"‘": "'", "’": "'", "‚": "'", "‛": "'",
           "“": '"', "”": '"', "„": '"', "´": "'", "`": "'"}
_DASHES = {"–": "-", "—": "-", "‐": "-", "‑": "-",
           "‒": "-", "―": "-", "−": "-"}
_SPACES = {" ": " ", " ": " ", " ": " ", " ": " ",
           " ": " ", "\t": " "}


def _normalize_char(ch: str) -> str:
    if ch in _LIGATURES:
        return _LIGATURES[ch]
    if ch in _QUOTES:
        return _QUOTES[ch]
    if ch in _DASHES:
        return "-"
    if ch in _SPACES:
        return " "
    if ch == "­":  # soft hyphen
        return ""
    if ch == "…":  # ellipsis
        return "..."
    return ch


def normalize_text(s: str) -> str:
    return "".join(_normalize_char(c) for c in s)


# ---------------------------------------------------------------------------
# Char-stream model
# ---------------------------------------------------------------------------
@dataclass
class _PageStream:
    text: str
    # owners[i] = index into `chars` of the source char producing text[i]
    owners: list[int]
    chars: list[dict]
    width: float
    height: float


def _build_stream(page) -> _PageStream:
    chars = page.chars
    text_parts: list[str] = []
    owners: list[int] = []
    n = len(chars)
    for i, c in enumerate(chars):
        norm = _normalize_char(c.get("text", ""))
        # Drop a hyphen that ends a line (next char sits on a lower line).
        if norm == "-" and i + 1 < n:
            nxt = chars[i + 1]
            if nxt.get("top", 0) - c.get("top", 0) > (c.get("height", 8) * 0.5):
                continue
        for ch in norm:
            text_parts.append(ch)
            owners.append(i)
    return _PageStream("".join(text_parts), owners, chars,
                       float(page.width), float(page.height))


def _phrase_regex(phrase: str) -> re.Pattern:
    """Tokens joined with ``\\s*`` so cross-line / re-spaced text still matches."""
    norm = normalize_text(phrase)
    tokens = [t for t in re.split(r"\s+", norm.strip()) if t]
    pattern = r"\s*".join(re.escape(t) for t in tokens)
    return re.compile(pattern, re.IGNORECASE)


def _rects_for_match(stream: _PageStream, start: int, end: int) -> list[tuple]:
    """Source-char bboxes for text[start:end], merged into per-line rectangles."""
    src_idx = sorted({stream.owners[i] for i in range(start, end)})
    lines: dict[int, list[dict]] = {}
    for si in src_idx:
        c = stream.chars[si]
        key = round(c["top"] / 3.0)  # cluster chars onto the same visual line
        lines.setdefault(key, []).append(c)
    rects = []
    for group in lines.values():
        x0 = min(c["x0"] for c in group)
        x1 = max(c["x1"] for c in group)
        top = min(c["top"] for c in group)
        bottom = max(c["bottom"] for c in group)
        rects.append((x0, top, x1, bottom))
    return rects


@dataclass
class _Hit:
    page: int
    category: str
    rects: list[tuple]  # (x0, top, x1, bottom) in pdfplumber top-origin coords
    phrase: str


def _find_hits(pdf_path: Path, phrases: dict[str, list[str]]) -> tuple[list[_Hit], int]:
    hits: list[_Hit] = []
    total_chars = 0
    with pdfplumber.open(str(pdf_path)) as pdf:
        streams = []
        for page in pdf.pages:
            s = _build_stream(page)
            total_chars += len(s.text)
            streams.append(s)
        for category, plist in phrases.items():
            for phrase in plist:
                if not phrase.strip():
                    continue
                rx = _phrase_regex(phrase)
                for pi, s in enumerate(streams):
                    placed = False
                    for m in rx.finditer(s.text):
                        rects = _rects_for_match(s, m.start(), m.end())
                        if rects:
                            hits.append(_Hit(pi, category, rects, phrase))
                            placed = True
                    # Only first page of occurrence matters; keep scanning all
                    # pages so repeated key terms get highlighted throughout.
                    _ = placed
    return hits, total_chars


def _annotate(reader_path: Path, hits: list[_Hit], legend_pdf: bytes,
              out_path: Path) -> None:
    src = PdfReader(str(reader_path))
    writer = PdfWriter()

    # Page 1: legend.
    legend_reader = PdfReader(io.BytesIO(legend_pdf))
    writer.add_page(legend_reader.pages[0])
    for p in src.pages:
        writer.add_page(p)

    by_page: dict[int, list[_Hit]] = {}
    for h in hits:
        by_page.setdefault(h.page, []).append(h)

    for pi, page_hits in by_page.items():
        page = src.pages[pi]
        ph = float(page.mediabox.height)
        page_in_writer = pi + 1  # +1 for prepended legend
        for h in page_hits:
            color = CATEGORIES[h.category][0]
            for (x0, top, x1, bottom) in h.rects:
                y_top = ph - top
                y_bottom = ph - bottom
                quad = ArrayObject([
                    FloatObject(x0), FloatObject(y_top),
                    FloatObject(x1), FloatObject(y_top),
                    FloatObject(x0), FloatObject(y_bottom),
                    FloatObject(x1), FloatObject(y_bottom),
                ])
                ann = Highlight(
                    rect=(x0, y_bottom, x1, y_top),
                    quad_points=quad,
                    highlight_color=color,
                )
                ann[NameObject("/T")] = TextStringObject(h.category)
                writer.add_annotation(page_number=page_in_writer, annotation=ann)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as fh:
        writer.write(fh)


def _legend_pdf(title: str, phrases: dict[str, list[str]]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as rcanvas

    buf = io.BytesIO()
    c = rcanvas.Canvas(buf, pagesize=letter)
    W, H = letter
    y = H - 1 * inch
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, y, "Highlight Legend")
    y -= 0.35 * inch
    c.setFont("Helvetica", 10)
    c.setFillGray(0.35)
    c.drawString(1 * inch, y, title[:90])
    c.setFillGray(0)
    y -= 0.5 * inch

    for key, (hexcol, desc) in CATEGORIES.items():
        r = int(hexcol[0:2], 16) / 255
        g = int(hexcol[2:4], 16) / 255
        b = int(hexcol[4:6], 16) / 255
        c.setFillColorRGB(r, g, b)
        c.rect(1 * inch, y - 4, 0.45 * inch, 0.22 * inch, fill=1, stroke=0)
        c.setFillGray(0)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1.65 * inch, y, desc)
        c.setFont("Helvetica", 9)
        c.setFillGray(0.4)
        n = len(phrases.get(key, []))
        c.drawString(1.65 * inch, y - 0.16 * inch, f"{n} passage(s) highlighted")
        c.setFillGray(0)
        y -= 0.62 * inch

    y -= 0.2 * inch
    c.setFont("Helvetica-Oblique", 8)
    c.setFillGray(0.5)
    c.drawString(1 * inch, y, "Auto-generated for COLLEGE 117 section prep.")
    c.showPage()
    c.save()
    return buf.getvalue()


def _ocr_highlight(pdf_path: Path, phrases: dict[str, list[str]],
                   legend_pdf: bytes, out_path: Path) -> None:
    """Fallback for image-only PDFs: OCR word boxes, draw PIL rects, re-export."""
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageDraw

    images = convert_from_path(str(pdf_path), dpi=200)
    rgb_colors = {
        k: tuple(int(v[0][i:i + 2], 16) for i in (0, 2, 4))
        for k, v in CATEGORIES.items()
    }
    out_imgs: list[Image.Image] = []

    for img in images:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = data["text"]
        norm_words = [normalize_text(w) for w in words]
        overlay = img.convert("RGB")
        draw = ImageDraw.Draw(overlay, "RGBA")
        for category, plist in phrases.items():
            col = rgb_colors[category] + (90,)
            for phrase in plist:
                toks = [normalize_text(t).lower()
                        for t in re.split(r"\s+", phrase.strip()) if t]
                if not toks:
                    continue
                for i in range(len(norm_words)):
                    if norm_words[i].lower() != toks[0]:
                        continue
                    if [norm_words[i + j].lower() if i + j < len(norm_words) else None
                            for j in range(len(toks))] == toks:
                        xs, ys, xe, ye = 1e9, 1e9, 0, 0
                        for j in range(len(toks)):
                            k = i + j
                            xs = min(xs, data["left"][k])
                            ys = min(ys, data["top"][k])
                            xe = max(xe, data["left"][k] + data["width"][k])
                            ye = max(ye, data["top"][k] + data["height"][k])
                        draw.rectangle([xs, ys, xe, ye], fill=col)
        out_imgs.append(overlay)

    body = io.BytesIO()
    out_imgs[0].save(body, format="PDF", save_all=True,
                     append_images=out_imgs[1:])
    body.seek(0)

    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(legend_pdf)).pages[0])
    for p in PdfReader(body).pages:
        writer.add_page(p)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as fh:
        writer.write(fh)


def highlight_pdf(in_path: str | Path, out_path: str | Path,
                  phrases: dict[str, list[str]], title: str | None = None) -> dict:
    """Highlight `phrases` (category -> list) in `in_path`, write to `out_path`.

    Returns a small report dict.
    """
    in_path = Path(in_path)
    out_path = Path(out_path)
    title = title or in_path.stem
    legend = _legend_pdf(title, phrases)

    hits, total_chars = _find_hits(in_path, phrases)
    if total_chars == 0:
        _ocr_highlight(in_path, phrases, legend, out_path)
        return {"mode": "ocr", "hits": "n/a (image PDF)", "out": str(out_path)}

    _annotate(in_path, hits, legend, out_path)
    per_cat: dict[str, int] = {}
    for h in hits:
        per_cat[h.category] = per_cat.get(h.category, 0) + 1
    missing = {
        cat: [p for p in plist
              if not any(h.phrase == p and h.category == cat for h in hits)]
        for cat, plist in phrases.items()
    }
    return {
        "mode": "text",
        "out": str(out_path),
        "hits_by_category": per_cat,
        "total_hit_rects": sum(len(h.rects) for h in hits),
        "unmatched": {k: v for k, v in missing.items() if v},
    }


if __name__ == "__main__":
    import json
    import sys

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(
        src.stem + " [highlighted].pdf")
    demo = {
        "argument": ["justice"],
        "concept": ["genomic"],
    }
    print(json.dumps(highlight_pdf(src, dst, demo), indent=2, ensure_ascii=False))
