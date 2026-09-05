"""Build the rewards-and-information-returns desk's `extracted/` store.

WHY A SCRIPT AND NOT A TRANSCRIPTION. Every passage this writes is a literal
slice of a file that was fetched, located by two anchors that must both be
found and, where an anchor occurs more than once, by a stated occurrence count.
Nothing is retyped, so the store cannot drift from the source by a keystroke --
which is the failure mode that matters most here, because a stored threshold or
ruling number is what a return gets built on.

WHAT IT REFUSES TO DO. It does not fetch, it does not summarise, and it does not
repair prose. An anchor that is missing, or that occurs a different number of
times than declared, RAISES -- because a slice that silently began somewhere
else would move a stored passage without changing a line of this file.

IT DOES REPAIR TWO THINGS, BOTH OF THEM ARTEFACTS OF READING A PDF RATHER THAN
FEATURES OF THE TEXT: a soft hyphen (U+00AD) left at a typeset line break, which
is by definition not part of the word; and the fact that a TJ array renders an
inter-word gap as a numeric offset rather than a space character. The second is
measured rather than guessed: on the 2005-19 Bulletin, kerning offsets cluster
between -50 and 0 and word gaps between -200 and -950, so a cut at -150 is
exact. Read `_spaces_from_kerning` before changing it.

THE SOURCES, AND HOW THEY WERE FETCHED (5 September 2026):

    curl -sS --compressed -o reg-1.61-1.xml \\
      "https://www.ecfr.gov/api/versioner/v1/full/2026-09-03/title-26.xml?part=1&section=1.61-1"
    ... likewise 1.6041-1, 1.6041-3, 1.6041-6, 1.6050W-1
    curl -sSL --compressed -o usc-6041.html \\
      "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section6041&num=0&edition=prelim"
    ... likewise 6041A, 6050W, 6071
    curl -sSL --compressed -o rr-2005-28.pdf  "https://www.irs.gov/pub/irs-drop/rr-05-28.pdf"
    curl -sSL --compressed -o ann-2002-18.pdf "https://www.irs.gov/pub/irs-drop/a-02-18.pdf"
    curl -sSL --compressed -o plr-201027015.pdf "https://www.irs.gov/pub/irs-wd/1027015.pdf"
    curl -sSL --compressed -o instr-1099-misc-nec.pdf "https://www.irs.gov/pub/irs-pdf/i1099mec.pdf"
    curl -sSL --compressed -o pub525.html "https://www.irs.gov/publications/p525"
    curl -sSL --compressed -o pub334.html "https://www.irs.gov/publications/p334"

    python tools/build_rewards_desk.py <fetched-dir> <desk-dir> <YYYY-MM-DD>

The eCFR endpoint REQUIRES compression -- without `--compressed` it answers 406,
which reads like a bad URL. A date later than the title's most recent issue date
answers 404 with the date it will accept, which is how 2026-09-03 was chosen.
"""
from __future__ import annotations

import html as _html
import re
import sys
import zlib
from pathlib import Path

# ── PDF text, because no PDF library is installable here ──────────────────────

class _PDF:
    def __init__(self, data: bytes):
        self.objs: dict[int, bytes] = {}
        for m in re.finditer(rb'(\d+)\s+(\d+)\s+obj\b', data):
            end = data.find(b'endobj', m.end())
            self.objs[int(m.group(1))] = data[m.end(): end if end > 0 else len(data)]
        for num, body in list(self.objs.items()):
            if b'/ObjStm' not in body:
                continue
            s = self.stream(body)
            if not s:
                continue
            n = int(re.search(rb'/N\s+(\d+)', body).group(1))
            first = int(re.search(rb'/First\s+(\d+)', body).group(1))
            hdr = s[:first].split()
            for i in range(n):
                onum, off = int(hdr[2 * i]), int(hdr[2 * i + 1])
                nxt = int(hdr[2 * i + 3]) + first if i + 1 < n else len(s)
                self.objs.setdefault(onum, s[first + off:nxt])

    def stream(self, body: bytes):
        m = re.search(rb'stream\r?\n', body)
        if not m:
            return None
        e = body.rfind(b'endstream')
        raw = body[m.end(): e if e > 0 else len(body)]
        if b'/FlateDecode' not in body[:m.start()]:
            return raw
        try:
            return zlib.decompress(raw)
        except Exception:
            try:
                return zlib.decompressobj().decompress(raw)
            except Exception:
                return None


def _tounicode(cmap: bytes) -> dict[int, str]:
    out: dict[int, str] = {}
    for blk in re.findall(rb'beginbfchar(.*?)endbfchar', cmap, re.S):
        for a, b in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', blk):
            out[int(a, 16)] = ''.join(
                chr(int(b[i:i + 4], 16)) for i in range(0, len(b), 4))
    for blk in re.findall(rb'beginbfrange(.*?)endbfrange', cmap, re.S):
        for m in re.finditer(
                rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[(.*?)\])',
                blk, re.S):
            lo, hi = int(m.group(1), 16), int(m.group(2), 16)
            if m.group(3):
                base = int(m.group(3)[-4:], 16)
                for i in range(hi - lo + 1):
                    out[lo + i] = chr(base + i)
            elif m.group(4):
                for i, it in enumerate(re.findall(rb'<([0-9A-Fa-f]*)>', m.group(4))):
                    out[lo + i] = ''.join(
                        chr(int(it[j:j + 4], 16)) for j in range(0, len(it), 4))
    return out


_ESC = {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f',
        b'(': b'(', b')': b')', b'\\': b'\\'}


def _unescape(s: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i:i + 1]
        if c != b'\\':
            out += c
            i += 1
            continue
        nxt = s[i + 1:i + 2]
        if nxt in _ESC:
            out += _ESC[nxt]
            i += 2
        elif nxt.isdigit():
            j, oct_ = i + 1, b''
            while j < len(s) and len(oct_) < 3 and s[j:j + 1].isdigit():
                oct_ += s[j:j + 1]
                j += 1
            out.append(int(oct_, 8) & 0xFF)
            i = j
        else:
            i += 2
    return bytes(out)


_TOK = re.compile(
    rb"(\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\))"       # 1 literal string
    rb"|<([0-9A-Fa-f\s]*)>"                                # 2 hex string
    rb"|/([#\w.,+-]+)\s+[\d.]+\s+Tf"                       # 3 font select
    rb"|((?:[-\d.]+\s+){5}([-\d.]+)\s+Tm)"                 # 4,5 text matrix
    rb"|(([-\d.]+)\s+([-\d.]+)\s+T[dD])"                   # 6,7,8 relative move
    rb"|(T\*|ET|BT)"                                       # 9 line/end
)
_TJ_GAP = re.compile(rb'(?<=[)>])\s*(-\d+(?:\.\d+)?)\s*(?=[(<])')


def _spaces_from_kerning(content: bytes, threshold: float = -150.0) -> bytes:
    """A TJ array renders an inter-word gap as a number, not a space character.

    MEASURED on Internal Revenue Bulletin 2005-19: kerning offsets cluster
    between -50 and 0 (1,740 of them) and word gaps between -200 and -950
    (1,400 of them), with four offsets in between. Without this every word in
    that bulletin ran together; with the threshold set at -200 instead,
    justified lines lost their spaces the other way ("dressesthe taxtreatmentof
    rebatespaidby"). -150 is the gap between the two clusters.
    """
    return _TJ_GAP.sub(
        lambda m: b'( )' if float(m.group(1)) <= threshold else m.group(0),
        content)


def _decode(raw: bytes, cmap: dict, two_byte: bool) -> str:
    if not cmap:
        return raw.decode('cp1252', 'replace')
    if two_byte:
        return ''.join(cmap.get((raw[i] << 8) | raw[i + 1], '')
                       for i in range(0, len(raw) - 1, 2))
    return ''.join(cmap.get(b, chr(b) if 32 <= b < 127 else '') for b in raw)


def pdf_text(path: Path) -> str:
    """Page-aware, per-font extraction.

    THE FONT MAP IS READ FROM THE PAGE'S OWN /Resources, NOT THE DOCUMENT'S.
    Keyed document-wide by the resource name, two pages using `/F1` for
    different subset fonts decode each other's glyphs: on the 1099 instructions
    that produced whole paragraphs of "¸·ÀÀ" where "1099" belonged,
    and it looked like a corrupt download rather than a bug here.

    A Td/TD that moves only in x DOES NOT MEAN A SPACE. It sets a new line
    start relative to the previous one, so on a justified line its x is the
    whole advance so far -- reading it as a gap inserted spaces inside words
    ("phar maceutical", "det ermining"). Word spacing comes from the strings
    themselves and from `_spaces_from_kerning`.
    """
    data = path.read_bytes()
    pdf = _PDF(data)
    out = []
    for _, body in pdf.objs.items():
        if not re.search(rb'/Type\s*/Page\b', body):
            continue
        rm = re.search(rb'/Resources\s+(\d+)\s+0\s+R', body)
        res = pdf.objs.get(int(rm.group(1)), b'') if rm else (
            re.search(rb'/Resources\s*<<(.*)', body, re.S).group(1)
            if re.search(rb'/Resources', body) else b'')
        fm = re.search(rb'/Font\s*(\d+)\s+0\s+R', res)
        fd = pdf.objs.get(int(fm.group(1)), b'') if fm else (
            (re.search(rb'/Font\s*<<(.*?)>>', res, re.S) or [None, b''])[1]
            if re.search(rb'/Font', res) else b'')
        fonts = {}
        for fname, ref in re.findall(rb'/([^\s/<>\[\]]+)\s+(\d+)\s+0\s+R', fd):
            fobj = pdf.objs.get(int(ref))
            if not fobj:
                continue
            tu = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', fobj)
            cm = {}
            if tu:
                s = pdf.stream(pdf.objs.get(int(tu.group(1)), b'') or b'')
                if s:
                    cm = _tounicode(s)
            fonts[fname.decode('latin-1')] = (
                cm, b'/Type0' in fobj or b'/Identity-H' in fobj)
        cm_ref = re.search(rb'/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)', body)
        if not cm_ref:
            continue
        chunks = [pdf.stream(pdf.objs.get(int(r), b'') or b'')
                  for r in re.findall(rb'(\d+)\s+0\s+R', cm_ref.group(1))]
        content = b'\n'.join(c for c in chunks if c)
        if not content:
            continue
        content = _spaces_from_kerning(content)
        buf, y, cur = [], None, ({}, False)
        for m in _TOK.finditer(content):
            lit, hexs, font, _tm, tmy, td, _tdx, tdy, op = m.groups()
            if font is not None:
                cur = fonts.get(font.decode('latin-1'), ({}, False))
            elif lit is not None:
                buf.append(_decode(_unescape(lit[1:-1]), *cur))
            elif hexs is not None:
                h = re.sub(rb'\s', b'', hexs)
                if len(h) % 2:
                    h += b'0'
                try:
                    buf.append(_decode(bytes.fromhex(h.decode()), *cur))
                except ValueError:
                    pass
            elif tmy is not None:
                ny = float(tmy)
                if y is None or abs(ny - y) > 0.6:
                    buf.append('\n')
                y = ny
            elif td is not None:
                dy = float(tdy)
                if abs(dy) > 0.6:
                    buf.append('\n')
                if y is not None:
                    y += dy
            elif op == b'T*':
                buf.append('\n')
            elif op == b'ET':
                buf.append('\n')
                y = None
        out.append(''.join(buf))
    txt = '\n'.join(out).replace('\r', '\n')
    return re.sub(r'\n{2,}', '\n', re.sub(r'[ \t]+', ' ', txt))


def xml_text(path: Path) -> str:
    t = re.sub(r'<[^>]+>', '\n', path.read_text(encoding='utf-8'))
    t = _html.unescape(t)
    return re.sub(r'\n\s*\n+', '\n', re.sub(r'[ \t]+', ' ', t))


def html_text(path: Path) -> str:
    t = path.read_text(encoding='utf-8', errors='replace')
    t = re.sub(r'(?s)<(script|style).*?</\1>', '', t)
    t = _html.unescape(re.sub(r'<[^>]+>', '\n', t))
    return re.sub(r'\n\s*\n+', '\n', re.sub(r'[ \t\xa0]+', ' ', t))


# ── the record ────────────────────────────────────────────────────────────────

#: `(source_id, citation, file, start, end, nth, occurrences)`.
#: `occurrences` is how many times `start` appears in the file. Stated rather
#: than defaulted: an anchor that quietly begins matching a second place moves a
#: stored passage without changing this file. "Cash rebates." occurs twice in
#: Publication 525 -- once in its table of contents -- and "Payments to
#: corporations for legal services." twice in the 1099 instructions, once in
#: each form's half.
SPEC = [
    ("S1", "26 CFR 1.61-1(a)", "reg-1.61-1",
     "(a) \nGeneral definition.", "(b) \nCross references.", 1, 1),

    ("S2", "26 USC 6041(a)", "usc-6041",
     "(a) Payments exceeding threshold", "\n(b) Collection of foreign items", 1, 1),
    ("S2", "26 USC 6041(d)", "usc-6041",
     "(d) Statements to be furnished to persons with respect to whom information is required",
     "\n(e) Section does not apply to certain tips", 1, 1),
    ("S2", "26 USC 6041(h)", "usc-6041",
     "(h) Inflation adjustment", "\nIf any increase under the preceding sentence", 1, 1),
    ("S2", "26 USC 6041A(a)", "usc-6041A",
     "(a) Returns regarding remuneration for services",
     "\n(b) Direct sales of $5,000 or more", 1, 1),
    ("S2", "26 USC 6050W(e)", "usc-6050W",
     "(e) Exception for de minimis payments by third party settlement organizations",
     "\n(f) Statements to be furnished", 1, 1),
    ("S2", "26 USC 6071(c)", "usc-6071",
     "(c) Returns and statements relating to employee wage information and nonemployee compensation",
     "\n(d) ", 1, 1),

    ("S3", "26 CFR 1.6041-1(a)(1)(i)", "reg-1.6041-1",
     "Payments required to be reported.",
     "\n(ii) \nInformation returns required under other provisions", 1, 1),
    ("S3", "26 CFR 1.6041-1(a)(1)(iv)", "reg-1.6041-1",
     "(iv) \nInformation returns required under section 6050W", "\n(v) \nExamples.", 1, 1),
    ("S3", "26 CFR 1.6041-1(a)(1)(v), Example 1", "reg-1.6041-1",
     "Example 1.\nRestaurant owner A", "\nExample 2.", 1, 1),
    ("S3", "26 CFR 1.6041-1(a)(1)(v), Example 2", "reg-1.6041-1",
     "Example 2.\nRestaurant owner A", "\n(2) \nPrescribed form.", 1, 1),
    ("S3", "26 CFR 1.6041-1(b)(1)", "reg-1.6041-1",
     "(b) \nPersons engaged in trade or business", "\n(2) \nSpecial rule for REMICs.", 1, 1),
    ("S3", "26 CFR 1.6041-1(d)(2)", "reg-1.6041-1",
     "(2) \nProfessional fees.", "\n(3) \nPrizes and awards.", 1, 1),

    ("S4", "26 CFR 1.6041-3 (introductory text)", "reg-1.6041-3",
     "Returns of information are not required under section 6041",
     "\n(a) Payments of income required", 1, 1),
    ("S4", "26 CFR 1.6041-3(c)", "reg-1.6041-3",
     "(c) Payments of bills for merchandise", "\n(d) Payments of rent", 1, 1),
    ("S4", "26 CFR 1.6041-3(p)", "reg-1.6041-3",
     "(p) Payments made to the following persons:",
     "\n(2) An organization exempt from taxation", 1, 1),

    ("S5", "26 CFR 1.6041-6(a)", "reg-1.6041-6",
     "(a) \nIn general.", "\n(b) \nException.", 1, 1),
    ("S5", "26 CFR 1.6041-6(b)", "reg-1.6041-6",
     "(b) \nException.", "\n(c) \nApplicability date.", 1, 1),

    ("S6", "26 CFR 1.6050W-1(a)(3)", "reg-1.6050W-1",
     "(3) \nReportable payment transaction.", "\n(4) \nPayment settlement entity", 1, 1),
    ("S6", "26 CFR 1.6050W-1(a)(5)(i)", "reg-1.6050W-1",
     "(5) \nParticipating payee", "\n(ii) \nForeign payees", 1, 1),
    ("S6", "26 CFR 1.6050W-1(c)(2)", "reg-1.6050W-1",
     "(2) \nThird party settlement organization.",
     "\n(3) \nThird party payment network.", 1, 1),
    ("S6", "26 CFR 1.6050W-1(c)(3)", "reg-1.6050W-1",
     "(3) \nThird party payment network.",
     "\n(4) \nException for de minimis payments.", 1, 1),
    ("S6", "26 CFR 1.6050W-1(c)(4)", "reg-1.6050W-1",
     "(4) \nException for de minimis payments.",
     "\n(5) \nCoordination with information returns", 1, 1),

    ("S7", "Rev. Rul. 2005-28, ISSUE", "rr-2005-28",
     "ISSUE \nAre Medicaid Rebates", "\nFACTS ", 1, 1),
    ("S7", "Rev. Rul. 2005-28, Pittsburgh Milk", "rr-2005-28",
     "In Pittsburgh Milk Co. v. Commissioner", "\nIn contrast, in United Draperies", 1, 1),
    ("S7", "Rev. Rul. 2005-28, United Draperies", "rr-2005-28",
     "In contrast, in United Draperies",
     "\nRev. Rul. 76-96, 1976-1 C.B. 23, addresses", 1, 1),
    ("S7", "Rev. Rul. 2005-28, Rev. Rul. 76-96", "rr-2005-28",
     "Rev. Rul. 76-96, 1976-1 C.B. 23, addresses",
     "\nThe Medicaid Rebate is paid by M to S", 1, 1),
    ("S7", "Rev. Rul. 2005-28, HOLDING", "rr-2005-28",
     "HOLDING \nMedicaid Rebates", "\nEFFECT ON OTHER DOCUMENTS", 1, 1),
    ("S7", "Rev. Rul. 2005-28, EFFECT ON OTHER DOCUMENTS", "rr-2005-28",
     "EFFECT ON OTHER DOCUMENTS \nRev. Rul. 76-96 is suspended in part.",
     "\nDRAFTING INFORMATION", 1, 1),

    ("S8", "Announcement 2002-18, the unresolved issues", "ann-2002-18",
     "Questions have been raised", "\nConsistent with prior practice", 1, 1),
    ("S8", "Announcement 2002-18, the relief", "ann-2002-18",
     "Consistent with prior practice", "\nThis relief does not apply", 1, 1),
    ("S8", "Announcement 2002-18, what the relief does not cover", "ann-2002-18",
     "This relief does not apply", "\nFor information regarding this announcement", 1, 1),

    ("S9", 'IRS Pub. 525 (2025), "Cash rebates"', "pub525",
     "Cash rebates.\nA cash rebate", "\nCasualty insurance", 1, 1),
    ("S9", 'IRS Pub. 525 (2025), "Rewards"', "pub525",
     "Rewards.\nIf you receive a reward for providing information",
     "\nSale of home.", 1, 1),

    ("S10", 'IRS Pub. 334 (2025), "Trade discounts"', "pub334",
     "Trade discounts.\nThe differences", "\nCash discounts.", 1, 1),
    ("S10", 'IRS Pub. 334 (2025), "Cash discounts"', "pub334",
     "Cash discounts.\nCash discounts are amounts",
     "\nPurchase returns and allowances.", 1, 1),

    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Increase in threshold"',
     "instr-1099-misc-nec",
     "Increase in threshold", "\nNew boxes 1b and 13a.", 1, 1),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Filing dates"',
     "instr-1099-misc-nec", "Filing dates. \n", "\nForm 1099-K. \n", 1, 1),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Form 1099-K"',
     "instr-1099-misc-nec",
     "Form 1099-K. \nPayments made with a credit card", "\nForm 1099-NEC, box 1a.", 1, 1),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), Specific Instructions for Form 1099-NEC',
     "instr-1099-misc-nec",
     "File Form 1099-NEC, Nonemployee Compensation, for each",
     "\nCaution: \nBe sure to report each payment", 1, 1),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Reportable payments to corporations"',
     "instr-1099-misc-nec", "Reportable payments to corporations. \n",
     "\nCaution: \nFederal executive agencies may also", 2, 2),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Payments to corporations for legal services"',
     "instr-1099-misc-nec", "Payments to corporations for legal services. \n",
     "\nTaxpayer identification numbers (TINs).", 2, 2),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Exceptions"',
     "instr-1099-misc-nec",
     "Exceptions\nSome payments do not have to be reported on Form \n1099-NEC",
     "\nState or local sales taxes.", 1, 1),
    ("S11", 'Instr. 1099-MISC/NEC (Rev. 12-2026), "Statements to Recipients"',
     "instr-1099-misc-nec",
     "Statements to Recipients\nIf you are required to file Form 1099-NEC",
     "\nTruncating recipient", 1, 1),

    ("S12", "PLR 201027015, LAW AND ANALYSIS", "plr-201027015",
     "Section 61 provides that gross income means all income from whatever source derived.",
     "\nA deduction for contributions and gifts", 1, 1),
    ("S12", "PLR 201027015, Ruling request (1)", "plr-201027015",
     "A rebate received from the party to whom the buyer directly or indirectly paid the",
     "\nRuling request (2)", 1, 1),
    ("S12", "PLR 201027015, precedential value", "plr-201027015",
     "This ruling is directed only to the taxpayers requesting it.",
     "\nIn accordance with the Power of Attorney", 1, 1),
]

PREAMBLE = """# Authority — someone else's words, checkable line by line

Every line here is verifiable against the source named on it, which is why an
agent may write this file and why a large diff can be skimmed. **Judgement does
not live here.** What the firm decided goes in `positions/`, where the diff is
read — `guards.no_positions_in_extracted` fails the build rather than trusting
anyone to notice a position that rode along inside an extraction.

Written by `tools/build_rewards_desk.py`, which slices each passage out of a
fetched file between two anchors and refuses when either is missing. Nothing
below was retyped.

---

"""


def read(dirpath: Path, stem: str) -> str:
    """Whichever form of this source was fetched. A soft hyphen is dropped.

    U+00AD at a typeset line break is a hint about where a word MAY be broken,
    not a character in the word; the 1099 instructions carry hundreds of them
    and leaving them in would store words the IRS did not print.
    """
    for suffix, reader in ((".xml", xml_text), (".html", html_text), (".pdf", pdf_text)):
        p = dirpath / (stem + suffix)
        if p.is_file():
            return reader(p).replace("­\n", "").replace("­", "")
    raise SystemExit(f"no fetched file for {stem} in {dirpath}")


def slice_out(text: str, stem: str, start: str, end: str, nth: int, occurrences: int) -> str:
    hits = [m.start() for m in re.finditer(re.escape(start), text)]
    if len(hits) != occurrences:
        raise SystemExit(
            f"{stem}: anchor {start!r} occurs {len(hits)}x, the record says "
            f"{occurrences}x. The source moved under the record; re-read it.")
    i = hits[nth - 1]
    j = text.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"{stem}: end anchor {end!r} not found after {start!r}")
    return " ".join(text[i:j].split())


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    fetched, desk, checked = Path(argv[1]), Path(argv[2]), argv[3]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
        raise SystemExit("the date is the day the sources were FETCHED, YYYY-MM-DD")
    out = desk / "extracted"
    out.mkdir(parents=True, exist_ok=True)
    texts: dict[str, str] = {}
    by_source: dict[str, list[str]] = {}
    for sid, citation, stem, start, end, nth, occ in SPEC:
        if stem not in texts:
            texts[stem] = read(fetched, stem)
        body = slice_out(texts[stem], stem, start, end, nth, occ)
        by_source.setdefault(sid, []).append(
            f"## {citation}\n\n**Source:** {sid} · **Checked:** {checked}\n\n> {body}\n")
    for sid, blocks in by_source.items():
        (out / f"{sid}.md").write_text(PREAMBLE + "\n".join(blocks), encoding="utf-8")
        print(f"{sid}.md  {len(blocks)} passages")
    print(f"{sum(len(b) for b in by_source.values())} passages in "
          f"{len(by_source)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
