"""Photograph the source for the figure traced end to end: the filed 10-Q's
cover (who, what form, which quarter) and the filed table holding the figure,
with its row ringed.

    python photograph.py FILED.htm OUT_DIR "Education" "8,044"

FILED.htm is the 10-Q's primary document as SEC serves it (fetched with the
contact SEC requires), with its images beside it. The cover is Chrome's
rendering of that document as it is. The table is the filing's own <table>
element, cut out with its own inline styling and rendered alone; the only
thing added is a red outline on the one row. Of the rows that read the label
and then the figure, the last is used: in a 10-Q the notes to the financial
statements, where the class disclosure sits, come after any MD&A table that
repeats it. The zoom is the same table at twice the scale, cut around the
red outline."""
import re
import subprocess
import sys
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def shoot(html: Path, png: Path, width=1300, height=900, scale=1):
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--virtual-time-budget=8000",
                    "--window-size=%d,%d" % (width, height), "--force-device-scale-factor=%s" % scale,
                    "--screenshot=%s" % png.resolve(), html.resolve().as_uri()], check=True, capture_output=True)


def text(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s).replace("&#160;", " ").replace("&nbsp;", " "))


def trim(png: Path, around_red=False, margin=24):
    """Cut a render down to what is drawn, or to the red outline and a margin."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    if around_red:
        ys = [y for y in range(h) for x in range(0, w, 3) if px[x, y][0] > 180 and px[x, y][1] < 40 and px[x, y][2] < 40]
        top, bottom = min(ys) - margin * 3, max(ys) + margin * 3
        im.crop((0, max(0, top), w, min(h, bottom))).save(png)
        return
    rows = [y for y in range(h) if any(sum(px[x, y]) < 700 for x in range(0, w, 4))]
    cols = [x for x in range(w) if any(sum(px[x, y]) < 700 for y in range(0, h, 4))]
    im.crop((max(0, min(cols) - margin), max(0, min(rows) - margin), min(w, max(cols) + margin),
             min(h, max(rows) + margin))).save(png)


def main(filed, out_dir, label, figure):
    filed, out = Path(filed).resolve(), Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    html = filed.read_text(encoding="utf-8", errors="replace")
    shoot(filed, out / "source-cover.png", height=1000)
    rows = [m for m in re.finditer(r"<tr\b[^>]*>.*?</tr>", html, flags=re.S | re.I)
            if re.search(r"^\s*%s\s" % re.escape(label), text(m.group(0)))
            and re.search(r"(?<![\d,])%s(?![\d,])" % re.escape(figure), text(m.group(0)))]
    if not rows:
        sys.exit("no row reads %r then %r" % (label, figure))
    hit = rows[-1]
    start = html.rfind("<table", 0, hit.start())
    end = html.find("</table>", hit.end()) + len("</table>")
    marked = re.sub(r"^<tr\b", '<tr style="outline:4px solid #CC0000;outline-offset:1px"', hit.group(0), flags=re.I)
    table = html[start:hit.start()] + marked + html[hit.end():end]
    page = out / "table.htm"
    page.write_text('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:20px;'
                    'background:#fff;font-family:Arial">%s</body></html>' % table, encoding="utf-8")
    shoot(page, out / "source-table.png", height=1600)
    trim(out / "source-table.png")
    shoot(page, out / "source-row-zoom.png", height=1600, scale=2)
    trim(out / "source-row-zoom.png", around_red=True)
    page.unlink()
    print("%d rows read %r then %r; photographed the last: %s" % (len(rows), label, figure, text(hit.group(0))[:160]))
    print("table starts:", text(table)[:300])


if __name__ == "__main__":
    main(*sys.argv[1:5])
