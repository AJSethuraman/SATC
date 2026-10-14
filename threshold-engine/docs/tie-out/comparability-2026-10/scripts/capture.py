"""Photograph each independent source: cut the identity header and the rows
out of the real page, enlarge them, and ring the figure in red.

    (from threshold-engine/)
    python docs/tie-out/comparability-2026-10/scripts/capture.py --sources work/sources --out work/images --chrome PATH

PDF pages (Call Reports, instructions, QBP) are rendered with pdftoppm at
200 dpi and located with pdfplumber's word positions, so a ring lands on the
word the PDF itself holds at that place. HTML documents (KeyCorp's filings,
the Fed's H.8) are rendered in Chromium through Playwright and the ring is
drawn on the box the browser reports for the text.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw

DPI = 200
K = DPI / 72.0
RED = (214, 0, 0)


def render(pdf, pageno, tmp):
    out = Path(tmp) / ("p%d" % pageno)
    subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(pageno), "-l", str(pageno), "-png", "-singlefile",
                    str(pdf), str(out)], check=True)
    return Image.open(str(out) + ".png").convert("RGB")


def words_of(page):
    return page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)


def find_page(pdf, must):
    with pdfplumber.open(pdf) as doc:
        for i, p in enumerate(doc.pages):
            text = p.extract_text() or ""
            if all(m in text for m in must):
                return i + 1
    raise SystemExit("no page in %s holds all of %s" % (pdf, must))


def phrase_box(words, phrase, after=None):
    """Bounding box of a run of consecutive words equal to ``phrase``."""
    toks = phrase.split()

    def same(w, t):
        # The forms run dot leaders into the last word: "above......." is "above".
        return w == t or (w.startswith(t) and set(w[len(t):]) <= set(".:,;*"))
    for i in range(len(words) - len(toks) + 1):
        if all(same(words[i + k]["text"], toks[k]) for k in range(len(toks))):
            if after is not None and words[i]["top"] < after:
                continue
            ws = words[i:i + len(toks)]
            return dict(x0=min(w["x0"] for w in ws), x1=max(w["x1"] for w in ws),
                        top=min(w["top"] for w in ws), bottom=max(w["bottom"] for w in ws))
    raise SystemExit("phrase %r not found" % phrase)


def value_after(words, code):
    """The first number to the right of ``code`` on its own line."""
    c = next((w for w in words if w["text"] == code), None)
    if c is None:
        raise SystemExit("code %s not on the page" % code)
    mid = (c["top"] + c["bottom"]) / 2
    cands = [w for w in words if w["x0"] > c["x1"] and abs((w["top"] + w["bottom"]) / 2 - mid) < 4
             and re.fullmatch(r"\(?-?[\d,]+\)?|NR", w["text"])]
    if not cands:
        raise SystemExit("no value after %s" % code)
    v = min(cands, key=lambda w: w["x0"])
    return c, v


def cut(img, top, bottom, x0=0, x1=None):
    x1 = img.width / K if x1 is None else x1
    return img.crop((int(x0 * K), int(top * K), int(x1 * K), int(bottom * K)))


def ring(draw, box, dy, pad=4, width=5):
    x0, y0 = box["x0"] * K - pad * K, (box["top"] - dy) * K - pad * K
    x1, y1 = box["x1"] * K + pad * K, (box["bottom"] - dy) * K + pad * K
    draw.ellipse((x0 - 6, y0 - 2, x1 + 6, y1 + 2), outline=RED, width=width)


def stack(parts, gap=10):
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height + gap
    return out


def pdf_shot(pdf, must, out_dir, name, bands, rings_codes=(), rings_phrases=(), header=True, x0=None, x1=None):
    """``bands`` are (top_anchor, bottom_anchor) pairs of phrases or codes, or
    ('code', CODE, above, below). Each band is cut and the cuts stacked under
    the page's identity header; rings are drawn on the values after
    ``rings_codes`` and on ``rings_phrases``."""
    pageno = find_page(pdf, must)
    with tempfile.TemporaryDirectory() as tmp, pdfplumber.open(pdf) as doc:
        page = doc.pages[pageno - 1]
        ws = words_of(page)
        img = render(pdf, pageno, tmp)
        parts = []
        if header:
            r = phrase_box(ws, "RSSD-ID")
            hdr = cut(img, r["top"] - 13, r["bottom"] + 13)
            parts.append(hdr)
        for b in bands:
            if b[0] == "code":
                c = next(w for w in ws if w["text"] == b[1])
                top, bottom = c["top"] - b[2], c["bottom"] + b[3]
            elif b[0] == "box":
                top, bottom = b[1], b[2]
            else:
                t = phrase_box(ws, b[0])
                btm = phrase_box(ws, b[1], after=t["top"])
                top, bottom = t["top"] - 4, btm["bottom"] + 4
            piece = cut(img, top, bottom, x0 or 0, x1)
            d = ImageDraw.Draw(piece)
            for code in rings_codes:
                c, v = value_after(ws, code)
                if top <= v["top"] and v["bottom"] <= bottom:
                    ring(d, dict(x0=v["x0"] - (x0 or 0), x1=v["x1"] - (x0 or 0), top=v["top"], bottom=v["bottom"]), top)
            for ph in rings_phrases:
                try:
                    bx = phrase_box(ws, ph, after=top - 1)
                except SystemExit:
                    continue
                if bx["bottom"] <= bottom:
                    ring(d, dict(x0=bx["x0"] - (x0 or 0), x1=bx["x1"] - (x0 or 0), top=bx["top"], bottom=bx["bottom"]), top, pad=2, width=4)
            parts.append(piece)
        im = stack(parts)
        path = Path(out_dir) / (name + ".png")
        im.save(path, optimize=True)
        print("wrote", path, "page", pageno, im.size)
        return dict(file=path.name, page=pageno)


_FIND = """([needle, container, height, maxw]) => {
  const it = document.createNodeIterator(document.body, NodeFilter.SHOW_TEXT);
  let n; const norm = s => s.replace(/\\s+/g, ' ');
  while ((n = it.nextNode())) { if (norm(n.textContent).includes(needle)) {
    let el = n.parentElement;
    if (container === 'next-table') {
      // the title, then the first table that follows it in the document
      const t = Array.from(document.querySelectorAll('table')).find(
        tb => el.compareDocumentPosition(tb) & Node.DOCUMENT_POSITION_FOLLOWING);
      t.scrollIntoView(); const a = el.getBoundingClientRect(), b = t.getBoundingClientRect();
      const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
      return {x: x + scrollX, y: y + scrollY, w: Math.max(a.right, b.right) - x, h: Math.max(a.bottom, b.bottom) - y};
    }
    if (container === 'region') {
      el.scrollIntoView(); const a = el.getBoundingClientRect();
      return {x: 0, y: a.y + scrollY - 10, w: document.documentElement.clientWidth, h: height};
    }
    const want = container.toUpperCase();
    while (el && el.tagName !== want && el !== document.body) el = el.parentElement;
    if (!el || el === document.body) el = n.parentElement;
    if (maxw > 0) { el.style.maxWidth = maxw + 'px'; el.style.width = maxw + 'px'; }
    el.scrollIntoView(); const r = el.getBoundingClientRect();
    return {x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height}; } }
  return null; }"""

_RECTS = """([texts, cells, box]) => {
  const out = []; const inside = (x, y) => x >= box.x - 2 && y >= box.y - 2 && x <= box.x + box.w && y <= box.y + box.h;
  const push = (t, node, i, len) => { const rg = document.createRange(); rg.setStart(node, i); rg.setEnd(node, i + len);
    for (const r of rg.getClientRects()) { const x = r.x + scrollX, y = r.y + scrollY;
      if (inside(x, y)) out.push({t, x, y, w: r.width, h: r.height}); } };
  const it = document.createNodeIterator(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = it.nextNode())) { for (const t of texts) {
    if (t.startsWith('=')) { const s = n.textContent.trim(); if (s === t.slice(1)) push(t, n, n.textContent.indexOf(s), s.length); }
    else { const i = n.textContent.indexOf(t); if (i >= 0) push(t, n, i, t.length); } } }
  // cells: [label, k] rings the k-th number in every table row whose first cell starts with label
  for (const [label, k] of cells) { for (const tr of document.querySelectorAll('tr')) {
    const tds = Array.from(tr.querySelectorAll('td')); if (!tds.length) continue;
    if (!tds[0].textContent.replace(/\\s+/g, ' ').trim().startsWith(label)) continue;
    const nums = tds.slice(1).filter(td => /^[(]?[\\d,—–-]+[)]?$/.test(td.textContent.replace(/[\\s$]/g, '')) && td.textContent.trim());
    const td = nums[k]; if (!td) continue; const rg = document.createRange(); rg.selectNodeContents(td);
    const rs = Array.from(rg.getClientRects()).filter(r => r.width > 0); if (!rs.length) continue;
    const x0 = Math.min(...rs.map(r => r.left)), y0 = Math.min(...rs.map(r => r.top));
    const x1 = Math.max(...rs.map(r => r.right)), y1 = Math.max(...rs.map(r => r.bottom));
    const x = x0 + scrollX, y = y0 + scrollY; if (inside(x, y)) out.push({t: label + '#' + k, x, y, w: x1 - x0, h: y1 - y0}); } }
  return out; }"""


def html_shots(path, out_dir, chrome, specs, width=1100):
    """Render ``path`` once in Chromium and take every shot in ``specs``:
    dict(name, find, container, ring=[texts], cells=[(label, k)], height).
    A text starting '=' must be a whole text node (so '6' does not ring '66')."""
    from playwright.sync_api import sync_playwright
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": width, "height": 1400}, device_scale_factor=2)
        target = path if "://" in str(path) else Path(path).resolve().as_uri()
        pg.goto(target, wait_until="load", timeout=300000)
        for sp in specs:
            box = pg.evaluate(_FIND, [sp["find"], sp.get("container", "div"), sp.get("height", 400), sp.get("max_width", 0)])
            if not box:
                raise SystemExit("%s: text %r not found" % (sp["name"], sp["find"]))
            rects = pg.evaluate(_RECTS, [sp.get("ring", []), [list(c) for c in sp.get("cells", [])], box])
            pad = 8
            clip = dict(x=max(0, box["x"] - pad), y=max(0, box["y"] - pad), width=box["w"] + 2 * pad, height=box["h"] + 2 * pad)
            out = Path(out_dir) / (sp["name"] + ".png")
            pg.screenshot(path=str(out), clip=clip, full_page=True)
            im = Image.open(out).convert("RGB")
            d = ImageDraw.Draw(im)
            found = set()
            for r in rects:
                found.add(r["t"])
                x0, y0 = (r["x"] - clip["x"]) * 2 - 10, (r["y"] - clip["y"]) * 2 - 6
                d.ellipse((x0, y0, x0 + r["w"] * 2 + 20, y0 + r["h"] * 2 + 12), outline=RED, width=5)
            want = set(sp.get("ring", [])) | {"%s#%d" % c for c in sp.get("cells", [])}
            if want - found:
                raise SystemExit("%s: could not ring %s" % (sp["name"], sorted(want - found)))
            im.save(out, optimize=True)
            print("wrote", out, im.size)
            made.append(out.name)
        b.close()
    return made


def qbp_shot(pdf, out_dir, name):
    """Table V-A, the label column and 'All Insured Institutions' only, with
    the card, home equity, 1-4 family and other-consumer figures ringed."""
    pageno = find_page(pdf, ["TABLE V-A. Loan Performance, All FDIC-Insured Institutions", "Percent of Loans Charged-Off"])
    with tempfile.TemporaryDirectory() as tmp, pdfplumber.open(pdf) as doc:
        ws = words_of(doc.pages[pageno - 1])
        img = render(pdf, pageno, tmp)
        col = phrase_box(ws, "Institutions")               # the column heading's right edge
        x0, x1 = 32, col["x1"] + 8
        top = phrase_box(ws, "TABLE V-A.")["top"] - 4
        bottom = phrase_box(ws, "Total loans and leases (plus unearned income)")["bottom"] + 4
        piece = cut(img, top, bottom, x0, x1)
        d = ImageDraw.Draw(piece)
        targets = [("Percent of Loans 30-89 Days", "Credit card loans"), ("Percent of Loans Noncurrent", "Credit card loans"),
                   ("Percent of Loans Past-Due and", "Credit card loans"), ("Percent of Loans Charged-Off", "Credit card loans"),
                   ("Loans Outstanding (in billions)", "Home equity loans"), ("Loans Outstanding (in billions)", "Other 1-4 family residential"),
                   ("Loans Outstanding (in billions)", "Credit card loans"), ("Loans Outstanding (in billions)", "Other loans to individuals")]
        for section, label in targets:
            s_ = phrase_box(ws, section)
            lb = phrase_box(ws, label, after=s_["top"])
            mid = (lb["top"] + lb["bottom"]) / 2
            v = min((w for w in ws if abs((w["top"] + w["bottom"]) / 2 - mid) < 3 and w["x0"] > lb["x1"]),
                    key=lambda w: w["x0"])
            ring(d, dict(x0=v["x0"] - x0, x1=v["x1"] - x0, top=v["top"], bottom=v["bottom"]), top, pad=2, width=4)
        path = Path(out_dir) / (name + ".png")
        piece.save(path, optimize=True)
        print("wrote", path, "page", pageno, piece.size)


COL = ("(Column A) Past due 30", "Dollar amounts in thousands")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chrome", required=True, help="Chromium/Chrome executable for the HTML shots")
    a = ap.parse_args()
    S, O = Path(a.sources), Path(a.out)
    O.mkdir(parents=True, exist_ok=True)
    call = lambda c, d: S / ("call-%s-%s.pdf" % (c, d))
    gl = S / "instr-glossary-2026-09.pdf"

    # Gap 1: RC-N item 11 against the first-lien line
    for c, nm in (("17534", "keybank"), ("6548", "usbank")):
        pdf_shot(call(c, "06302026"), ["RCFDK037", "RCONC237"], O, "g1-%s-rcn-11" % nm,
                 [COL, ("2. Closed-end loans secured by 1-4 family", "a. Secured by first liens"),
                  ("11. Loans and leases reported in items 1 through 8", "for repurchase included in item 11 above")],
                 rings_codes=["RCONC237", "RCFDK037", "RCFDK040", "RCFDK043"])
    pdf_shot(call("17534", "12312025"), ["RCFDK043", "RCONC237"], O, "g1-keybank-rcn-11-dec25",
             [COL, ("11. Loans and leases reported in items 1 through 8", "for repurchase included in item 11 above")],
             rings_codes=["RCFDK043"])
    # Gap 2: card nonaccrual policy, as filed; the glossary's exception
    for c, d, nm in (("17534", "06302026", "keybank"), ("57957", "06302026", "citizens"), ("3511", "06302026", "wellsfargo"),
                     ("57957", "12312015", "citizens-2015")):
        pdf_shot(call(c, d), ["RCFDB577", "RCFDB576"], O, "g2-%s-rcn-5a" % nm,
                 [COL, ("5. Loans to individuals for household", "a. Credit cards")], rings_codes=["RCFDB576", "RCFDB577"])
    pdf_shot(gl, ["Exceptions to the general rule", "need not be placed in nonaccrual"], O, "g2-glossary-nonaccrual",
             [("Nonaccrual Status: This entry covers", "both well secured and in the process of collection."),
              ("Exceptions to the general rule", "loan (as defined for Schedule RC-C, Part I, item 6,")],
             rings_phrases=["need not be placed in nonaccrual", "is a consumer"], header=False)
    pdf_shot(gl, ["Nonaccrual Status (cont.):", "Nevertheless, such loans should be subject"], O, "g2-glossary-nonaccrual-cont",
             [("Nonaccrual Status (cont.):", "nonaccrual in Schedule RC-N, column C.")],
             rings_phrases=["must be reported as nonaccrual in Schedule RC-N, column C."], header=False)
    # Gap 3: the Fed's note on the 2010 consolidation
    html_shots(S / "fed-h8-2010-04-16.html", O, a.chrome, [
        dict(name="g3-fed-h8-release", find="Release Date: April 16, 2010", container="region", height=170, ring=["Release Date: April 16, 2010"]),
        dict(name="g3-fed-h8-notes", find="Some of the data reported in the", container="div",
             ring=["$322.3 (instead of $323.9)", "$378.1 (instead of $377.8)"])], width=900)
    # Gap 4: QBP Table V-A
    qbp_shot(S / "qbp-2026q2.pdf", O, "g4-qbp-table-va")
    # Gap 5: the double count, from the filings
    for c, d, nm in (("7213", "06302011", "citi-jun11"), ("7213", "09302011", "citi-sep11"), ("23360", "06302011", "csd-jun11")):
        pdf_shot(call(c, d), ["RIADB514", "RIADB515"], O, "g5-%s-rib-5a" % nm,
                 [("(Column A) Charge-offs", "Calendar year-to-date"), ("5. Loans to individuals for household", "a. Credit cards")],
                 rings_codes=["RIADB514"])
    pdf_shot(gl, ["Transactions between entities under common control", "as though the entities had combined"], O,
             "g5-glossary-common-control",
             [("Transactions between entities under common control", "transactions is similar to the pooling-of-interests method."),
              ("If there has been a change in reporting entity", "Schedule RI, Income Statement, as though the entities had combined at the beginning of the year.")],
             rings_phrases=["as though the entities had combined at the beginning of the year."], header=False)
    # Gap 6: KeyBank RC-C consumer lines; KeyCorp's own tables
    for d in ("12312025", "06302026"):
        pdf_shot(call("17534", d), ["RCFDB538", "RCFDK207", "RCFD1797"], O, "g6-keybank-rcc-%s" % d,
                 [("(Column A) Consolidated Bank", "(Column B) Domestic Offices"),
                  ("c. Secured by 1-4 family residential properties:", "b. Secured by junior liens"),
                  ("6. Loans to individuals for household", "automobile loans, and all student loans)")],
                 rings_codes=["RCFD1797", "RCFD5367", "RCFD5368", "RCFDB538", "RCFDB539", "RCFDK137", "RCFDK207"])
    k10, q10 = S / "keycorp-10k-2025.htm", S / "keycorp-10q-2026q2.htm"
    html_shots(k10, O, a.chrome, [
        dict(name="g6-10k-cover", find="SECURITIES AND EXCHANGE COMMISSION", container="region", height=250,
             ring=["=10-K", "=December 31", "=KeyCorp"]),
        dict(name="g6-10k-figure9", find="Figure 9. Composition of Loans", container="next-table",
             ring=["18,732", "5,703", "4,644", "953"]),
        dict(name="g6-10k-figure9-note-c", find="Total loans exclude loans of", container="div", max_width=420, ring=["$205 million"]),
        dict(name="g6-10k-hfs-note", find="residential mortgage loans held for sale at fair value of", container="div", max_width=420, ring=["=149"]),
        dict(name="g6-10k-figure32", find="Figure 32. Summary of Loan and Lease Loss Experience", container="next-table",
             cells=[("Real estate — residential mortgage", 0), ("Home equity loans", 0), ("Other consumer loans", 0), ("Credit cards", 0)]),
        dict(name="g1-10k-gnma-note", find="associated with loans sold to GNMA", container="div", max_width=420, ring=["=66", "=6"]),
        dict(name="g7-10k-collateral", find="consumer loans have collateral that includes", container="div", max_width=420,
             ring=["automobiles, boats, and RVs"]),
    ])
    html_shots(q10, O, a.chrome, [
        dict(name="g6-10q-cover", find="SECURITIES AND EXCHANGE COMMISSION", container="region", height=300,
             ring=["=10-Q", "=June 30, 2026", "=KeyCorp"]),
        dict(name="g6-10q-figure8", find="Figure 8. Composition of Loans at June 30, 2026", container="next-table",
             ring=["18,178", "5,408", "4,349", "927"]),
        dict(name="g6-10q-figure8-note-b", find="Total loans exclude loans of", container="div", max_width=420, ring=["$182 million"]),
        dict(name="g6-10q-hfs-note", find="residential mortgage loans held for sale at fair value of", container="div", max_width=420, ring=["=204"]),
        dict(name="g6-10q-figure29", find="Figure 29. Summary of Loan and Lease Loss Experience", container="next-table",
             cells=[("Real estate — residential mortgage", 2), ("Home equity loans", 2), ("Other consumer loans", 2), ("Credit cards", 2)]),
        dict(name="g1-10q-gnma-note", find="associated with loans sold to GNMA", container="div", max_width=420, ring=["=54", "=5"]),
    ])
    # Gap 7: auto and consumer leases; the 2021 securitisation; the instruction
    for c, nm in (("17534", "keybank"), ("6548", "usbank")):
        pdf_shot(call(c, "06302026"), ["RCFDK137", "RCFDF162"], O, "g7-%s-rcc-6c-10a" % nm,
                 [("(Column A) Consolidated Bank", "(Column B) Domestic Offices"), ("c. Automobile loans", "c. Automobile loans"),
                  ("10. Lease financing receivables", "b. All other leases")], rings_codes=["RCFDK137", "RCFDF162"])
    pdf_shot(call("17534", "09302021"), ["RCFDB846"], O, "g7-keybank-rcb-m5c-sep21",
             [("(Column A) (Column B) (Column C) (Column D)", "Dollar amounts in thousands"),
              ("5. Asset-backed securities (ABS)", "c. Automobile loans")], rings_codes=["RCFDB846"])
    for d, nm in (("06302021", "jun21"), ("09302021", "sep21")):
        pdf_shot(call("17534", d), ["RCFDK137", "RCFDK207"], O, "g7-keybank-rcc-6c-%s" % nm,
                 [("(Column A) Consolidated Bank", "(Column B) Domestic Offices"), ("c. Automobile loans", "c. Automobile loans")],
                 rings_codes=["RCFDK137"])
    pdf_shot(S / "instr-rc-c-part1.pdf", ["Automobile loans. Report", "Personal cash loans secured by automobiles"], O,
             "g7-instr-rcc-6c", [("6.c Automobile loans. Report", "part I, item 6.d).")],
             rings_phrases=["Include both direct and indirect consumer automobile loans as well as retail installment sales paper",
                            "motorcycles, recreational", "Personal cash loans secured by automobiles already paid for (report in Schedule RC-C,"],
             header=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
