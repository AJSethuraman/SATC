#!/usr/bin/env python3
"""Screens for a walk of a tool that has no browser: the terminal and the workbook.

The canon `walk` skill drives a product through its screens and keeps one
screenshot per step. This tool has two screens a person sees: the terminal
where the commands are typed, and the spreadsheet where the answer is read.
This module captures both, marked to the step, with headless Chromium:

  terminal(...)   runs the command exactly as typed, keeps the output, and
                  renders the exchange as a terminal window with the command
                  ringed. The text is the real output; the window is a
                  rendering of it, and the procedure says so.
  sheet(...)      renders the workbook with LibreOffice, finds the page whose
                  text carries a heading, and shows it with a ring around a
                  region and, where asked, a zoomed crop of it beside.
  textfile(...)   shows a text file (the question file) as an editor would,
                  with the lines that matter highlighted.

No image library is needed: pdftoppm crops and zooms, and Chromium composes
the ring and the zoom from HTML. Nothing here reads a clock.
"""

from __future__ import annotations

import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = os.environ.get("WALK_CHROME") or next(
    (p for p in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", shutil.which("chromium") or "",
                 shutil.which("google-chrome") or "") if p and Path(p).exists()), "")

_CSS = """
body{margin:0;background:#F5F7F4;font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;color:#1B2430}
.term{width:1040px;background:#14181D;color:#E8ECEF;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.25);overflow:hidden;margin:16px}
.bar{background:#2A313A;color:#9AA6B2;font-size:13px;padding:7px 12px;letter-spacing:.04em}
pre{margin:0;padding:14px 16px;font:14px/1.45 'IBM Plex Mono',ui-monospace,Consolas,monospace;white-space:pre-wrap;word-break:break-word}
.cmd{display:inline-block;border:3px solid #E4573D;border-radius:6px;padding:2px 8px;margin:-5px -11px;background:rgba(228,87,61,.08)}
.prompt{color:#6CC38F}
.shot{position:relative;display:inline-block;margin:16px;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.2)}
.shot img{display:block}
.ring{position:absolute;border:4px solid #E4573D;border-radius:8px;box-shadow:0 0 0 3px rgba(255,255,255,.7)}
.row{display:flex;align-items:flex-start;gap:8px}
.zoom{margin:16px 16px 16px 0;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.2);border:4px solid #E4573D;border-radius:8px;overflow:hidden}
.zoom img{display:block}
.zoom .cap{font-size:13px;color:#5B6673;padding:6px 10px;background:#FBE9E5}
.editor{width:1040px;background:#fff;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.2);overflow:hidden;margin:16px}
.editor .bar{background:#E3EEF3;color:#1F6F8B}
.editor pre{color:#1B2430}
.ln{color:#9AA6B2;display:inline-block;width:3ch;text-align:right;margin-right:12px;user-select:none}
.hl{background:#FBE9E5;display:block;margin:0 -16px;padding:0 16px;border-left:4px solid #E4573D}
"""


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _shoot(html_text: str, out: Path, width: int, height: int = 900) -> Path:
    """Render `html_text` to a PNG exactly `width` x `height` pixels.

    Chromium prints the page to a PDF whose page size is set from CSS, and
    pdftoppm rasterises it at 96 dpi, so one CSS pixel is one image pixel.
    (Chromium's own --screenshot lays the page out in a viewport shorter than
    --window-size by the height of a toolbar it does not draw, and a box taller
    than that viewport is cut, so it is not used.)"""
    if not CHROME:
        raise RuntimeError("no headless Chromium found; set WALK_CHROME")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="walkshot-"))
    page = tmp / "page.html"
    page.write_text(f"<style>@page{{size:{width}px {height}px;margin:0}}"
                    f"*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style>{html_text}",
                    encoding="utf-8")
    pdf = tmp / "page.pdf"
    # a scratch profile keeps Chromium from touching the real one
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                    f"--user-data-dir={tmp / 'profile'}", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", f"file://{page}"],
                   capture_output=True, text=True, timeout=120)
    if not pdf.exists():
        raise RuntimeError(f"Chromium printed nothing for {out}")
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    if pages != 1:
        # a box that does not fit the page is moved whole to a second page,
        # and a one-page capture would silently lose it
        raise RuntimeError(f"{out.name}: the content overran the {width}x{height} window onto {pages} pages")
    subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "96", "-png", "-singlefile", str(pdf), str(out.with_suffix(""))],
                   capture_output=True, text=True, timeout=120)
    shutil.rmtree(tmp, ignore_errors=True)
    if not out.exists():
        raise RuntimeError(f"pdftoppm wrote no image for {out}")
    return out


def _text_height(text: str, cols: int = 118) -> int:
    """Window height for a terminal or editor window: the bar, the padding, and
    one 20.3px line per rendered line, wrapping long ones at `cols`."""
    lines = 0
    for ln in text.splitlines() or [""]:
        lines += max(1, -(-len(ln) // cols))
    return int(32 + 32 + 28 + lines * 20.3 + 2)


_MEASURE = ""


def terminal(cmd: list[str], cwd: Path, out: Path, title: str = "Terminal", prompt: str = "pack> ",
             env: dict | None = None, timeout: int = 1200) -> tuple[int, str, str]:
    """Run `cmd` in `cwd` as typed, render the exchange, return (rc, stdout, stderr)."""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    shown = " ".join(cmd)
    # what a person sees: the summary the tool prints (stderr) and, when the
    # JSON status is short, that too
    body = r.stderr.rstrip()
    if r.stdout.strip() and len(r.stdout) < 900:
        body = (body + "\n" if body else "") + r.stdout.rstrip()
    elif r.stdout.strip():
        body = (body + "\n" if body else "") + r.stdout.strip().splitlines()[0] + "\n  … (the status, as JSON, continues)"
    text = (f'<span class="prompt">{html.escape(prompt)}</span><span class="cmd">{html.escape(shown)}</span>\n'
            f'{html.escape(body)}\n<span class="prompt">{html.escape(prompt)}</span>')
    doc = f"<style>{_CSS}</style>{_MEASURE}<div class='term'><div class='bar'>{html.escape(title)}</div><pre>{text}</pre></div>"
    _shoot(doc, out, 1080, _text_height(f"{prompt}{shown}\n{body}\n{prompt}"))
    return r.returncode, r.stdout, r.stderr


def textfile(path: Path, out: Path, highlight: list[int] = (), title: str | None = None,
             first: int = 1, last: int | None = None) -> Path:
    """An editor's view of a text file, lines `first`..`last`, with `highlight` lines marked."""
    lines = path.read_text(encoding="utf-8").splitlines()
    last = last or len(lines)
    rows = []
    for n in range(first, min(last, len(lines)) + 1):
        ln = f'<span class="ln">{n}</span>{html.escape(lines[n - 1])}'
        # a highlighted row is a block, which breaks the line by itself
        rows.append(f'<span class="hl">{ln}</span>' if n in highlight else ln + "\n")
    doc = (f"<style>{_CSS}</style>{_MEASURE}<div class='editor'><div class='bar'>{html.escape(title or path.name)}</div>"
           f"<pre>{''.join(rows)}</pre></div>")
    return _shoot(doc, out, 1080, _text_height("\n".join(lines[first - 1:last]), cols=100) + 24)


class Workbook:
    """A built pack rendered once by LibreOffice, pages found by their heading."""

    def __init__(self, pack: Path, work: Path):
        self.pack = pack
        self.work = work
        work.mkdir(parents=True, exist_ok=True)
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            raise RuntimeError("LibreOffice (soffice) is not on PATH")
        env = dict(os.environ)
        home = Path(tempfile.mkdtemp(prefix="walk-lo-"))
        env["HOME"] = str(home)
        subprocess.run([soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", str(work), str(pack)],
                       capture_output=True, text=True, timeout=300, env=env)
        shutil.rmtree(home, ignore_errors=True)
        self.pdf = work / (pack.stem + ".pdf")
        if not self.pdf.exists():
            raise RuntimeError(f"LibreOffice did not render {pack}")
        info = subprocess.run(["pdfinfo", str(self.pdf)], capture_output=True, text=True).stdout
        self.pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        self._text: dict[int, str] = {}

    def text(self, page: int) -> str:
        if page not in self._text:
            r = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), str(self.pdf), "-"],
                               capture_output=True, text=True, timeout=60)
            self._text[page] = r.stdout
        return self._text[page]

    def page_with(self, heading: str, after: int = 0) -> int | None:
        for i in range(after + 1, self.pages + 1):
            if heading in self.text(i):
                return i
        return None

    def find(self, page: int, phrase: str, pad: float = 0.006) -> tuple[float, float, float, float] | None:
        """The box, as fractions of the page (x, y, w, h), of the first line whose
        text carries `phrase`. Rings are aimed by text, never by eye."""
        import xml.etree.ElementTree as ET
        r = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox-layout", str(self.pdf), "-"],
                           capture_output=True, text=True, timeout=60)
        root = ET.fromstring(r.stdout)
        ns = {"x": "http://www.w3.org/1999/xhtml"}
        pg = root.find(".//x:page", ns)
        W, H = float(pg.get("width")), float(pg.get("height"))
        for line in root.iter("{http://www.w3.org/1999/xhtml}line"):
            words = [w.text or "" for w in line.iter("{http://www.w3.org/1999/xhtml}word")]
            if phrase in " ".join(words):
                x0, y0 = float(line.get("xMin")) / W, float(line.get("yMin")) / H
                x1, y1 = float(line.get("xMax")) / W, float(line.get("yMax")) / H
                return (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
        return None

    def span(self, page: int, first: str, last: str, pad: float = 0.006, full_width: bool = False) -> tuple[float, float, float, float] | None:
        """The box covering the line with `first` down to the line with `last`."""
        a, b = self.find(page, first, pad), self.find(page, last, pad)
        if not a or not b:
            return None
        x0 = 0.0 + pad if full_width else min(a[0], b[0])
        x1 = 1.0 - pad if full_width else max(a[0] + a[2], b[0] + b[2])
        y0, y1 = min(a[1], b[1]), max(a[1] + a[3], b[1] + b[3])
        return (x0, y0, x1 - x0, y1 - y0)

    def size_pts(self, page: int) -> tuple[float, float]:
        info = subprocess.run(["pdfinfo", "-f", str(page), "-l", str(page), str(self.pdf)],
                              capture_output=True, text=True).stdout
        m = re.search(rf"Page\s+{page}\s+size:\s+([\d.]+) x ([\d.]+)", info) or re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
        return float(m.group(1)), float(m.group(2))

    def render(self, page: int, out_stem: Path, dpi: int = 110, crop: tuple[float, float, float, float] | None = None) -> Path:
        """PNG of a page, or of a fractional region (x, y, w, h) of it, at `dpi`."""
        args = ["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-singlefile"]
        if crop:
            wpt, hpt = self.size_pts(page)
            sx, sy = wpt / 72 * dpi, hpt / 72 * dpi
            x, y, w, h = crop
            args += ["-x", str(int(x * sx)), "-y", str(int(y * sy)), "-W", str(int(w * sx)), "-H", str(int(h * sy))]
        subprocess.run(args + [str(self.pdf), str(out_stem)], capture_output=True, text=True, timeout=120)
        png = out_stem.with_suffix(".png")
        if not png.exists():
            raise RuntimeError(f"pdftoppm wrote nothing for page {page}")
        return png


def sheet(wb: Workbook, page: int, out: Path, ring: tuple[float, float, float, float] | None = None,
          zoom: tuple[float, float, float, float] | None = None, zoom_caption: str = "zoomed",
          title: str | None = None, width_px: int = 1000, zoom_width: int = 520, stack: bool = False,
          page_crop: tuple[float, float, float, float] | None = None) -> Path:
    """The page with a ring around `ring` (fractions of the page: x, y, w, h)
    and, when `zoom` is given, that region rendered large beside it (or under
    it, with `stack`). `page_crop` shows only that region of the page as the
    "full" view, for a sheet that prints small on a mostly empty page; ring
    and zoom are still given as fractions of the whole page."""
    tmp = Path(tempfile.mkdtemp(prefix="walk-sheet-"))
    full = wb.render(page, tmp / "full", dpi=110, crop=page_crop)
    if ring and page_crop:
        cx, cy, cw, ch = page_crop
        ring = ((ring[0] - cx) / cw, (ring[1] - cy) / ch, ring[2] / cw, ring[3] / ch)
    parts = [f"<style>{_CSS}</style>{_MEASURE}"]
    if title:
        parts.append(f"<div style='margin:16px 16px 0;font-size:14px;color:#5B6673'>{html.escape(title)}</div>")
    parts.append("<div class='row'>" if not stack else "<div>")
    parts.append(f"<div class='shot'><img src='data:image/png;base64,{_b64(full)}' style='width:{width_px}px'>")
    if ring:
        x, y, w, h = ring
        parts.append(f"<div class='ring' style='left:{x * 100:.2f}%;top:{y * 100:.2f}%;width:{w * 100:.2f}%;height:{h * 100:.2f}%'></div>")
    parts.append("</div>")
    total_w = width_px + 32
    if zoom:
        z = wb.render(page, tmp / "zoom", dpi=260, crop=zoom)
        zw = zoom_width
        parts.append(f"<div class='zoom' style='width:{zw}px;{'margin-left:16px' if stack else ''}'><img src='data:image/png;base64,{_b64(z)}' style='width:{zw}px'>"
                     f"<div class='cap'>{html.escape(zoom_caption)}</div></div>")
        if not stack:
            total_w += zw + 24
    parts.append("</div>")
    doc = "".join(parts)
    wpt, hpt = wb.size_pts(page)
    pw, ph = (wpt * page_crop[2], hpt * page_crop[3]) if page_crop else (wpt, hpt)
    h = 16 + int(width_px * ph / pw) + 16 + (40 if title else 0)
    if zoom:
        # the zoom's shape comes from the whole page, whatever the page crop
        zw_, zh_ = zoom[2] * wpt, zoom[3] * hpt
        cap_lines = max(1, -(-len(zoom_caption) // max(1, int(zoom_width / 7.2))))
        zh = int(zoom_width * zh_ / zw_) + 8 + 12 + cap_lines * 18 + 16
        h = h + zh + 8 if stack else max(h, zh + 16)
    res = _shoot(doc, out, total_w, h)
    shutil.rmtree(tmp, ignore_errors=True)
    return res


def route(stages: list[tuple[str, str, str]], out: Path, per_row: int = 4) -> Path:
    """The picture of the route a procedure opens with: the screens in order,
    each a box (screen, what happens there, which steps), with an arrow to the
    next. `stages` are (screen, what happens, steps)."""
    css = """
    .route{display:flex;flex-wrap:wrap;gap:12px 0;align-items:stretch;margin:16px;width:1048px}
    .stage{display:flex;align-items:stretch}
    .box{width:206px;background:#fff;border:2px solid #1B2430;border-radius:10px;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.12)}
    .box .scr{font-weight:700;font-size:14px;color:#1F6F8B;letter-spacing:.02em}
    .box .what{font-size:13px;line-height:1.35;margin-top:4px;color:#1B2430}
    .box .steps{font-size:12px;color:#5B6673;margin-top:6px}
    .arrow{width:26px;display:flex;align-items:center;justify-content:center;font-size:22px;color:#E4573D}
    """
    parts = [f"<style>{_CSS}{css}</style><div class='route'>"]
    for i, (screen, what, steps) in enumerate(stages):
        parts.append(f"<div class='stage'><div class='box'><div class='scr'>{html.escape(screen)}</div>"
                     f"<div class='what'>{html.escape(what)}</div><div class='steps'>{html.escape(steps)}</div></div>")
        parts.append("<div class='arrow'>&#8594;</div>" if i + 1 < len(stages) else "<div class='arrow'></div>")
        parts.append("</div>")
    parts.append("</div>")
    rows = -(-len(stages) // per_row)
    return _shoot("".join(parts), out, 1080, 48 + rows * 200)


if __name__ == "__main__":   # a smoke run: python tools/walkshot.py PACK.xlsx OUT.png
    wb = Workbook(Path(sys.argv[1]), Path(tempfile.mkdtemp()))
    print(sheet(wb, 1, Path(sys.argv[2]), ring=(0.05, 0.1, 0.5, 0.1)))
