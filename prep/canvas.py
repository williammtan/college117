"""Targeted Canvas fetcher.

`download.sh` grabs the whole course. For on-demand section prep we only want one
week's module: download its File items as real files, and resolve
``module_item_redirect`` / ExternalUrl items to their final URL (downloading the
content when it is a PDF, otherwise recording a `.url` pointer + best-effort HTML).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

API = "https://canvas.stanford.edu/api/v1"


def load_env(root: Path) -> dict[str, str]:
    """Read CANVAS_TOKEN / COURSE_ID from the gitignored .env (env vars win)."""
    env: dict[str, str] = {}
    dotenv = root / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    token = os.environ.get("CANVAS_TOKEN") or env.get("CANVAS_TOKEN")
    course = os.environ.get("COURSE_ID") or env.get("COURSE_ID") or "225539"
    if not token:
        raise SystemExit(
            "No CANVAS_TOKEN. Create a gitignored .env with:\n"
            "  CANVAS_TOKEN=<token>\n  COURSE_ID=225539"
        )
    return {"token": token, "course": course}


def _curl(args: list[str], token: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["curl", "-sS", "-H", f"Authorization: Bearer {token}", *args],
        capture_output=True, text=True,
    )


def _paginate(url: str, token: str) -> list[dict]:
    """Walk RFC-5988 next links, concatenating JSON array pages."""
    out: list[dict] = []
    while url:
        r = subprocess.run(
            ["curl", "-sS", "-D", "-", "-H", f"Authorization: Bearer {token}", url],
            capture_output=True, text=True,
        )
        head, _, body = r.stdout.partition("\r\n\r\n")
        if not body:
            head, _, body = r.stdout.partition("\n\n")
        try:
            page = json.loads(body)
            if isinstance(page, list):
                out.extend(page)
            else:
                out.append(page)
        except json.JSONDecodeError:
            pass
        nxt = ""
        for part in re.split(r",\s*", head.split("Link:", 1)[-1] if "Link:" in head else ""):
            if 'rel="next"' in part:
                m = re.search(r"<([^>]+)>", part)
                if m:
                    nxt = m.group(1)
        url = nxt
    return out


def _sanitize(name: str) -> str:
    name = name.replace("/", "_")
    name = re.sub(r"[\x00-\x1f]", "", name)
    return re.sub(r"\s{2,}", " ", name).strip()


@dataclass
class FetchedItem:
    title: str
    kind: str          # "file" | "url"
    path: Path | None  # local file if downloaded
    url: str | None    # resolved external URL if not a file


def list_modules(token: str, course: str) -> list[dict]:
    return _paginate(f"{API}/courses/{course}/modules?per_page=100", token)


def pick_module(modules: list[dict], week_number: int | None, week_title: str | None) -> dict | None:
    """Match a Canvas module to a syllabus week by number, then title keywords."""
    if week_number is not None:
        for m in modules:
            if re.search(rf"\bWeek\s*{week_number}\b", m.get("name", ""), re.IGNORECASE):
                return m
    if week_title:
        kws = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", week_title)}
        best, score = None, 0
        for m in modules:
            mn = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", m.get("name", ""))}
            s = len(kws & mn)
            if s > score:
                best, score = m, s
        if score:
            return best
    return None


def _resolve_redirect(url: str, token: str) -> str:
    """Follow Canvas redirects (auth) without downloading the body; return final URL."""
    r = _curl(["-o", "/dev/null", "-w", "%{url_effective}", "-L", "-I", url], token)
    final = (r.stdout or "").strip()
    return final or url


def sync_module(
    token: str, course: str, module: dict, out_dir: Path
) -> list[FetchedItem]:
    """Download a module's items into out_dir; return what was fetched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    items = _paginate(
        f"{API}/courses/{course}/modules/{module['id']}/items?per_page=100", token
    )
    fetched: list[FetchedItem] = []
    for it in items:
        typ = it.get("type")
        title = it.get("title", "untitled")
        if typ == "File":
            cid = it.get("content_id")
            meta = json.loads(_curl([f"{API}/files/{cid}"], token).stdout or "{}")
            url = meta.get("url")
            fname = meta.get("display_name") or meta.get("filename") or f"{title}.bin"
            if not url:
                continue
            dest = out_dir / _sanitize(fname)
            if not dest.exists() or dest.stat().st_size == 0:
                _curl(["-L", "-o", str(dest), url], token)
            fetched.append(FetchedItem(title, "file", dest, None))
        elif typ in ("ExternalUrl", "Page", "ExternalTool", "Assignment", "Discussion", "Quiz"):
            raw = it.get("html_url") or it.get("external_url") or it.get("url") or ""
            final = _resolve_redirect(raw, token) if raw else ""
            ptr = out_dir / f"{_sanitize(title)}.{typ}.url"
            ptr.write_text((final or raw) + "\n")
            # If the resolved URL is itself a PDF, grab it.
            dest = None
            if final.lower().split("?")[0].endswith(".pdf"):
                dest = out_dir / _sanitize(f"{title}.pdf")
                _curl(["-L", "-o", str(dest), final], token)
            fetched.append(
                FetchedItem(title, "file" if dest else "url", dest, final or raw)
            )
    return fetched


def sync_week(
    root: Path,
    week_number: int | None,
    week_title: str | None,
    out_root: Path | None = None,
) -> tuple[Path, list[FetchedItem]]:
    """High-level: resolve creds, pick the week's module, download it."""
    creds = load_env(root)
    out_root = out_root or (root / "files")
    modules = list_modules(creds["token"], creds["course"])
    mod = pick_module(modules, week_number, week_title)
    if mod is None:
        raise SystemExit(
            f"No Canvas module matched week {week_number} / {week_title!r}. "
            f"Modules: {[m.get('name') for m in modules]}"
        )
    pos = mod.get("position", 0)
    folder = out_root / f"{int(pos):02d}_{_sanitize(mod['name'])}"
    items = sync_module(creds["token"], creds["course"], mod, folder)
    return folder, items


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parent.parent
    wk = int(sys.argv[1]) if len(sys.argv) > 1 else None
    folder, items = sync_week(root, wk, None)
    print(f"Synced -> {folder}")
    for f in items:
        loc = f.path.name if f.path else f.url
        print(f"  [{f.kind}] {f.title}  ->  {loc}")
