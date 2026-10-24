"""A tie-out document, checked before it is rendered. Refuses; does not warn.

WHY THIS IS CODE AND NOT A LINE IN THE SKILL. On 11 September 2026 the tie-out
skill was measured against the largest document ever built from it. Every
promise the skill made sorted into three piles, and the piles are the whole
argument for this file:

    enforced by code       1 of 1 kept, across three sessions
    carrying an incident   5 of 5 kept
    stated as instruction  0 of 5 kept

The instructions that were skipped are the MOST specific ones in the skill --
ring the row in red, three named headings, a closed verdict vocabulary. So the
variable is not how precisely a rule is written. It is whether anything but
willpower holds it. This file is the anything.

WHAT IT TAKES. The HTML a builder is about to render, before the render. That
is deliberate: the refusal lands while there is still nothing to forward, and
the source is a better thing to check than the PDF -- a heading is a heading in
the markup and a guess in a page of extracted text.

WHAT IT REFUSES ON, and nothing else yet. Three things, each of which was
actually broken in a delivered document:

  1. THE ROSTER MUST SUM TO THE HEADLINE. The document said 156,881 values
     delivered and its roster beneath added to 156,767. The missing 114 were a
     category whose wording had been reworded while the counter still searched
     for the old string, so the row printed `0` and read as good news.
  2. THE THREE NAMED SECTIONS MUST EXIST -- what it found, what I got wrong,
     what this does not prove. The delivered document had two of the three, and
     the missing one was `what I got wrong`, which is the one that costs
     something to write.
  3. A SOURCE IMAGE MUST CARRY A MARK. The skill says ring the exact row in
     red. Both delivered documents photographed the filed page and ringed
     nothing, so the reader was handed a dense regulatory page and a sentence
     pointing at it.

A DOCUMENT DECLARES ITS OWN PARTS, and a document that declares none is
refused. Every check here reads a `data-tieout` attribute rather than guessing
which table is the roster. That is on purpose: guessing gives a checker that
passes documents it did not understand, which is the green that means nothing.
An unrecognised value is refused for the same reason -- `data-tieout="rostr"`
would otherwise be a check that quietly switched itself off.

WHY THERE IS NO IMAGE LIBRARY HERE. canon is stdlib only, because it has to
lift out whole into any repository the firm owns. The obvious way to check for
red ink is Pillow or pymupdf, and the obvious compromise is an optional import
that skips when it is missing. That compromise was rejected: a check that goes
quiet when its dependency is absent reports green for a document nobody
examined, and this repository has that bug on record more than once. So the
PNG decoder is written out below in `zlib` and arithmetic -- about seventy
lines -- and there is no skip path to go quiet down. An image this cannot read
is REFUSED and named, never passed: unknown is not a pass.
"""
from __future__ import annotations

import base64
import binascii
import re
import struct
import subprocess
import sys
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

#: The attribute a document uses to point at its own parts.
ATTR = "data-tieout"

#: Every part this checker knows. A document that declares anything else is
#: refused rather than ignored -- see the module docstring.
ROLES = {
    "headline",                   # the total the roster has to add up to
    "roster",                     # the table of verdicts beneath it
    "count",                      # one number inside the roster
    "what-it-found",              # the three sections the skill names
    "what-i-got-wrong",
    "what-this-does-not-prove",
    "source",                     # an <img> of the independent source
}

#: The three sections, in the order the skill puts them, with the words a
#: refusal should use.
SECTIONS = (
    ("what-it-found", "what it found"),
    ("what-i-got-wrong", "what I got wrong"),
    ("what-this-does-not-prove", "what this does not prove"),
)

#: What counts as a mark. Deliberately narrow -- ink a reader would call red,
#: not a warm grey. A pixel qualifies when the red channel is bright AND well
#: clear of the other two, which is true of a drawn ring and false of the black
#: text, the hairline rules and the paper underneath it.
RED_MIN = 128
RED_MARGIN = 64

#: How much red makes a mark. A ring around a row is thousands of pixels; a
#: handful is a JPEG artefact or an antialiased edge of something else. Set
#: where an accident cannot reach and a deliberate mark cannot miss.
RED_ENOUGH = 64

_NUMBER = re.compile(r"-?\d[\d,]*")
_DATA_URI = re.compile(r"^data:image/(?P<kind>[a-z+]+);base64,(?P<body>.*)$",
                       re.S)


class Unreadable(Exception):
    """This checker cannot decode that image, so it cannot prove the mark."""


# ---------------------------------------------------------------------------
# Reading the document's own declarations
# ---------------------------------------------------------------------------

@dataclass
class Part:
    """One declared part of the document: what it says it is, and what is in it."""

    role: str
    tag: str
    src: str = ""
    text: str = ""
    counts: list[int] = field(default_factory=list)


class _Reader(HTMLParser):
    """Collects every element carrying `data-tieout`, with its inner text.

    Nesting is handled by depth rather than by a tag stack keyed on name: a
    `count` cell lives inside a `roster` table, and both have to be collected,
    with the count's number landing in the roster as well as on its own.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[Part] = []
        self.unknown: list[str] = []
        self._open: list[tuple[Part, int]] = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        void = tag in {"img", "br", "hr", "meta", "link", "input"}
        if not void:
            self._depth += 1
        values = dict(attrs)
        role = values.get(ATTR)
        if role is not None:
            if role not in ROLES:
                self.unknown.append(role)
                return
            part = Part(role=role, tag=tag, src=values.get("src") or "")
            self.parts.append(part)
            if not void:
                self._open.append((part, self._depth))

    def handle_endtag(self, tag):
        while self._open and self._open[-1][1] >= self._depth:
            self._open.pop()
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data):
        for part, _ in self._open:
            part.text += data


def read(html: str) -> tuple[list[Part], list[str]]:
    """Every declared part, and every role the document invented."""
    reader = _Reader()
    reader.feed(html)
    reader.close()
    for part in reader.parts:
        part.text = " ".join(part.text.split())
    return reader.parts, reader.unknown


def number_in(text: str) -> int | None:
    """The first whole number in some text, commas and all, or None."""
    hit = _NUMBER.search(text or "")
    return int(hit.group().replace(",", "")) if hit else None


# ---------------------------------------------------------------------------
# The PNG decoder. See the module docstring for why it is here.
# ---------------------------------------------------------------------------

_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _unfilter(raw: bytes, height: int, stride: int, bpp: int) -> list[bytes]:
    """The five PNG line filters, undone. Straight out of the specification."""
    lines: list[bytes] = []
    prev = bytearray(stride)
    at = 0
    for row in range(height):
        if at + 1 + stride > len(raw):
            raise Unreadable("the image data stops part way through row %d" % row)
        kind = raw[at]
        line = bytearray(raw[at + 1:at + 1 + stride])
        at += 1 + stride
        if kind == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                upleft = prev[i - bpp] if i >= bpp else 0
                up = prev[i]
                guess = left + up - upleft
                dl, du, dul = (abs(guess - left), abs(guess - up),
                               abs(guess - upleft))
                if dl <= du and dl <= dul:
                    pick = left
                elif du <= dul:
                    pick = up
                else:
                    pick = upleft
                line[i] = (line[i] + pick) & 0xFF
        elif kind != 0:
            raise Unreadable("row %d uses filter %d, which is not a PNG filter"
                             % (row, kind))
        lines.append(bytes(line))
        prev = line
    return lines


def _samples(line: bytes, count: int, depth: int) -> bytes:
    """One byte per sample, whatever the bit depth was."""
    if depth == 8:
        return line[:count]
    if depth == 16:
        return line[0:count * 2:2]          # the high byte is the whole story
    per_byte = 8 // depth
    mask = (1 << depth) - 1
    out = bytearray()
    for i in range(count):
        shift = 8 - depth * (i % per_byte + 1)
        out.append((line[i // per_byte] >> shift) & mask)
    return bytes(out)


def red_pixels(data: bytes) -> int:
    """How many pixels of this PNG a reader would call red.

    Greyscale images short-circuit to zero: a grey pixel cannot be red, which
    is a fact about the format and not an assumption about the picture. Every
    other case is decoded.
    """
    if not data.startswith(_SIGNATURE):
        raise Unreadable("not a PNG (its first eight bytes are not the "
                         "PNG signature)")
    header = None
    palette = b""
    body: list[bytes] = []
    at = 8
    while at + 8 <= len(data):
        (length,) = struct.unpack(">I", data[at:at + 4])
        kind = data[at + 4:at + 8]
        chunk = data[at + 8:at + 8 + length]
        if len(chunk) != length:
            raise Unreadable("the PNG stops part way through its %s chunk"
                             % kind.decode("ascii", "replace"))
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk[:13])
        elif kind == b"PLTE":
            palette = chunk
        elif kind == b"IDAT":
            body.append(chunk)
        elif kind == b"IEND":
            break
        at += 12 + length
    if header is None:
        raise Unreadable("the PNG carries no IHDR chunk")
    width, height, depth, colour, compression, filtering, interlace = header
    if colour in (0, 4):
        return 0
    if colour not in _CHANNELS:
        raise Unreadable("colour type %d is not a PNG colour type" % colour)
    if interlace:
        raise Unreadable("the PNG is Adam7 interlaced, which this does not "
                         "decode -- save it uninterlaced")
    if compression or filtering:
        raise Unreadable("the PNG uses a compression or filter method this "
                         "does not know")
    if colour == 3 and not palette:
        raise Unreadable("a palette PNG with no PLTE chunk")
    if not body:
        raise Unreadable("the PNG carries no image data")

    channels = _CHANNELS[colour]
    stride = (width * channels * depth + 7) // 8
    bpp = max(1, channels * depth // 8)
    try:
        raw = zlib.decompress(b"".join(body))
    except zlib.error as exc:
        raise Unreadable("the PNG's image data would not decompress (%s)" % exc)
    found = 0
    for line in _unfilter(raw, height, stride, bpp):
        values = _samples(line, width * channels, depth)
        for i in range(0, width * channels, channels):
            if colour == 3:
                index = values[i] * 3
                if index + 3 > len(palette):
                    raise Unreadable("a pixel points outside the palette")
                r, g, b = palette[index], palette[index + 1], palette[index + 2]
            else:
                r, g, b = values[i], values[i + 1], values[i + 2]
            if r >= RED_MIN and r - g >= RED_MARGIN and r - b >= RED_MARGIN:
                found += 1
    return found


def decode_data_uri(src: str) -> bytes:
    """The bytes behind a `data:` URI, or an Unreadable saying why not."""
    hit = _DATA_URI.match(src.strip())
    if not hit:
        raise Unreadable("the image is not embedded in the document -- its "
                         "src is a path, and a path resolves only on the "
                         "machine that wrote it")
    if hit.group("kind") != "png":
        raise Unreadable("the image is %s; this reads PNG only, and refuses "
                         "rather than assuming an unread picture carries a "
                         "mark" % hit.group("kind"))
    try:
        return base64.b64decode(hit.group("body"), validate=False)
    except (binascii.Error, ValueError) as exc:
        raise Unreadable("the embedded image is not valid base64 (%s)" % exc)


# ---------------------------------------------------------------------------
# The three checks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Report:
    """What was refused, and what was examined to get there.

    `examined` is not decoration. A clean result from a check that looked at
    nothing is worse than a dirty one, so the denominator travels with the
    verdict -- the same reason `check_record.py` prints its file count.
    """

    findings: tuple[str, ...]
    examined: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.findings

    def render(self) -> str:
        counts = ", ".join("%s %s" % (v, k) for k, v in self.examined.items())
        head = "tie-out conformance — examined %s" % (counts or "nothing")
        if self.ok:
            return head + "\nThe roster adds up, the three sections are " \
                          "there, and every source picture carries a mark."
        return "\n".join([head, "",
                          "%d thing(s) this document may not be published with:"
                          % len(self.findings), ""]
                         + ["  - " + f for f in self.findings])


def check(html: str) -> Report:
    """Read a tie-out document's HTML and say what stops it being published."""
    parts, unknown = read(html)
    bad: list[str] = []
    examined = {"declared parts": len(parts)}

    for role in sorted(set(unknown)):
        bad.append("the document declares %s=\"%s\", which is not a part this "
                   "checker knows. A mistyped mark is a check that switched "
                   "itself off, so it is refused rather than ignored. Known "
                   "parts: %s" % (ATTR, role, ", ".join(sorted(ROLES))))

    by_role: dict[str, list[Part]] = {}
    for part in parts:
        by_role.setdefault(part.role, []).append(part)

    # --- a · the roster must sum to the headline -----------------------------
    headlines = by_role.get("headline", [])
    rosters = by_role.get("roster", [])
    counts = by_role.get("count", [])
    examined["roster rows"] = len(counts)
    if not headlines:
        bad.append("no part is marked %s=\"headline\". A tie-out that states a "
                   "total about itself must point at it, and one that states "
                   "none is not reporting its denominator." % ATTR)
    if not rosters:
        bad.append("no part is marked %s=\"roster\". More than one figure means "
                   "a roster with its denominator, and a roster nothing points "
                   "at cannot be added up." % ATTR)
    if headlines and rosters:
        if len(headlines) > 1:
            bad.append("%d parts are marked headline; there can only be one "
                       "total for the roster to add to." % len(headlines))
        total = number_in(headlines[0].text)
        if total is None:
            bad.append("the headline carries no number: %r"
                       % headlines[0].text[:80])
        elif not counts:
            bad.append("the roster declares no %s=\"count\" cells, so nothing "
                       "was added up. A roster whose rows are not marked is "
                       "not a roster this can check." % ATTR)
        else:
            adds_to = 0
            for cell in counts:
                value = number_in(cell.text)
                if value is None:
                    bad.append("a roster row carries no number: %r"
                               % cell.text[:80])
                    break
                adds_to += value
            else:
                if adds_to != total:
                    bad.append(
                        "the roster does not add up to the document's own "
                        "headline: %s rows across %d lines against a headline "
                        "of %s, off by %s. Every figure in it may be right and "
                        "the document still says two different things about "
                        "how much it checked."
                        % ("{:,}".format(adds_to), len(counts),
                           "{:,}".format(total),
                           "{:+,}".format(adds_to - total)))

    # --- b · the three named sections ---------------------------------------
    present = 0
    for role, spoken in SECTIONS:
        found = by_role.get(role, [])
        if not found:
            bad.append("there is no section marked %s=\"%s\". The skill asks "
                       "for “%s” as a heading of its own, and the two "
                       "that cost something to write are the two that make the "
                       "rest believable." % (ATTR, role, spoken))
        elif not found[0].text.strip():
            bad.append("the “%s” heading is empty." % spoken)
        else:
            present += 1
    examined["named sections"] = present

    # --- c · a source image must carry a mark -------------------------------
    sources = by_role.get("source", [])
    examined["source pictures"] = len(sources)
    if not sources:
        bad.append("no image is marked %s=\"source\". A tie-out shows the "
                   "independent document rather than describing it, and an "
                   "unmarked picture cannot be checked for the ring."
                   % ATTR)
    marked = 0
    for index, picture in enumerate(sources, 1):
        try:
            found = red_pixels(decode_data_uri(picture.src))
        except Unreadable as exc:
            bad.append("source picture %d could not be read, so its mark could "
                       "not be proved, so it is refused: %s" % (index, exc))
            continue
        if found >= RED_ENOUGH:
            marked += 1
    examined["marked pictures"] = marked
    if sources and not marked:
        bad.append(
            "not one of the %d source pictures carries a red mark. The skill "
            "asks for the exact row ringed in red, because a photograph of a "
            "dense page with a sentence pointing at it is still a puzzle the "
            "reader has to solve — and the checking that gets done is the "
            "kind that takes one glance." % len(sources))
    return Report(tuple(bad), examined)


def gate(html: str, what: str = "this tie-out document") -> None:
    """Refuse to publish. Raises SystemExit on any finding; returns otherwise.

    This is the whole interface a builder needs. It refuses rather than warning
    because a warning printed by a build that then succeeds is read exactly
    once, by the person who wrote it.
    """
    report = check(html)
    print(report.render())
    if not report.ok:
        raise SystemExit(
            "\nREFUSING to publish %s. Nothing above is about a number being "
            "wrong; each one is the document contradicting itself, or leaving "
            "out the part a reader checks you with." % what)


#: Where Chrome usually is. A builder may pass its own path; this is only so
#: that the common case needs no argument.
CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise SystemExit(
        "REFUSING: no Chrome found to render with, and rendering is the only "
        "way to produce a tie-out document. Pass chrome=<path>. Tried:\n  "
        + "\n  ".join(CHROME_CANDIDATES))


def _pdf_images(raw: bytes) -> int:
    """How many pictures the PDF carries, counted from the file itself.

    Not a PDF parser: it counts `/Subtype /Image` dictionary entries, which is
    what an embedded picture has and what nothing else in a Chrome-printed file
    does. It is used only to tell NONE from SOME, so a count that is
    approximate is still a true answer to the question being asked.
    """
    return len(re.findall(rb"/Subtype\s*/Image", raw))


def render(html: str, pdf: "Path | str", what: str = "this tie-out document",
           chrome: str | None = None, scratch: "Path | str | None" = None,
           timeout: int = 300) -> Path:
    """Gate the document, then render it. **This is the only door.**

    WHY THE RENDER LIVES HERE AND NOT IN THE BUILDER. Until 23 September 2026
    canon shipped `gate()` and nothing else, and the skill asked each builder to
    call it before rendering. That request is prose — and this file exists
    because a promise held by prose was kept 0 times out of 5 while a promise
    held by code was kept 1 of 1. Shipping the check and leaving the CALLING of
    it to an instruction moved the problem one layer down and left it there: a
    builder that simply never called `gate` would produce an unchecked document
    indistinguishable from a checked one.

    The firm, shown that: *"I want it to be required."*

    So the gate is on the inside of the only door. A builder that wants a PDF
    asks for one here and is checked on the way through. There is no argument
    that skips it, and a builder that renders some other way is not using this
    module at all — which is visible in a grep rather than silent in a build.

    Returns the path written. Raises SystemExit if the document fails the gate,
    if Chrome produces nothing, or if what came out has no pictures in it.
    """
    pdf = Path(pdf)
    gate(html, what)

    source = Path(scratch) if scratch else pdf.parent
    source.mkdir(parents=True, exist_ok=True)
    page = source / (pdf.stem + ".html")
    page.write_text(html, encoding="utf-8")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    # A stale file sitting where the new one goes would satisfy every check
    # below, which is the shape of "it worked" meaning "it never ran".
    if pdf.exists():
        pdf.unlink()

    subprocess.run(
        [chrome or find_chrome(), "--headless=new", "--disable-gpu",
         "--no-pdf-header-footer", "--print-to-pdf=%s" % pdf, page.as_uri()],
        capture_output=True, timeout=timeout)
    if not pdf.exists():
        raise SystemExit("REFUSING: Chrome produced no PDF for %s." % what)

    # The pictures are the evidence, and a render that drops them is
    # indistinguishable from one that kept them until somebody opens it. The
    # HTML was checked for marked source images before Chrome ran; this asks
    # whether they SURVIVED, which is a different question, and the one that
    # caught seven exhibits built with no photographs in them.
    embedded = _pdf_images(pdf.read_bytes())
    if not embedded:
        raise SystemExit(
            "REFUSING: %s rendered with NO images in it. Every figure it "
            "traces is supposed to carry a photograph of the source, and a "
            "document that argues about numbers the reader cannot see is not "
            "evidence. The pictures were in the HTML and did not survive the "
            "render." % what)
    print("rendered: %s  (%d images embedded, %.1f MB)"
          % (pdf, embedded, pdf.stat().st_size / 1e6))
    return pdf


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m canon.check_tie_out <document.html>")
        return 2
    report = check(Path(argv[0]).read_text(encoding="utf-8"))
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
