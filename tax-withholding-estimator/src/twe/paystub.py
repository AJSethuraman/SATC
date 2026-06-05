"""Deterministic paystub layout extraction and profile-based field reading.

The estimator core never depends on this module. Paystub import is an optional
feature behind the ``[paystub]`` extra (PyMuPDF for PDFs, plus Tesseract for
image OCR). Everything here is deterministic: the same file and the same saved
profile always produce the same extracted values — no AI, no network.

Workflow:

1. :func:`extract_layout` turns a PDF/image into a rendered page image plus a
   list of words with normalized bounding boxes.
2. The user "teaches" a profile once by clicking which words hold each value;
   :func:`build_rules` converts those clicks into label-anchored rules.
3. :func:`apply_profile` reads any future paystub of the same layout, preferring
   a label anchor and falling back to the saved region.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation


class PaystubError(Exception):
    """Raised when a paystub cannot be read (e.g. missing optional deps)."""


# Fields the form can be auto-filled with. (key, human label, kind)
TARGET_FIELDS: list[tuple[str, str, str]] = [
    ("taxable_wages_per_period", "Taxable wages this period", "currency"),
    ("federal_tax_withheld_per_period", "Federal tax withheld this period", "currency"),
    ("ytd_taxable_wages", "YTD taxable wages", "currency"),
    ("ytd_federal_tax_withheld", "YTD federal tax withheld", "currency"),
    ("last_pay_date", "Pay date", "date"),
]

_FIELD_KIND = {key: kind for key, _, kind in TARGET_FIELDS}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Word:
    """A single token with a bounding box normalized to 0..1 of the page."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def to_dict(self) -> dict:
        return {"text": self.text, "x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}


@dataclass(slots=True)
class Layout:
    """A rendered page plus its words. Image is base64 PNG (no data: prefix)."""

    image_png_b64: str
    img_width: int
    img_height: int
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass(slots=True)
class FieldRule:
    """How to read one field: try the label anchor, else the saved region."""

    field: str
    kind: str
    region: list[float]  # [x0, y0, x1, y1] normalized union of the taught words
    label_text: str = ""

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "kind": self.kind,
            "region": list(self.region),
            "label_text": self.label_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FieldRule:
        return cls(
            field=d["field"],
            kind=d.get("kind", _FIELD_KIND.get(d["field"], "currency")),
            region=[float(v) for v in d["region"]],
            label_text=d.get("label_text", ""),
        )


# ---------------------------------------------------------------------------
# Value parsing (pure, deterministic)
# ---------------------------------------------------------------------------


def parse_currency(token: str) -> Decimal | None:
    """Parse a currency-ish token to a Decimal, or None if it isn't a number.

    Handles ``$``, thousands commas, parentheses-negatives, and trailing ``-``.
    """

    s = token.strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    if s.endswith("-"):
        neg = True
        s = s[:-1]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    s = s.replace("$", "").replace(",", "").replace(" ", "")
    if not s or s == ".":
        return None
    if not re.fullmatch(r"\d*\.?\d+", s):
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if neg else value


_DATE_FORMATS = (
    "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y",
    "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y", "%d-%b-%Y", "%d %b %Y",
)


def parse_date(text: str) -> str | None:
    """Parse a date string to ISO ``YYYY-MM-DD``, or None."""

    s = text.strip().rstrip(".").strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    # Try to locate a date substring like 01/15/2025 anywhere in the text.
    m = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", s)
    if m:
        return parse_date(m.group(0))
    return None


def _parse_value(text: str, kind: str) -> str | None:
    if kind == "date":
        return parse_date(text)
    value = parse_currency(text)
    if value is None:
        return None
    # Paystubs often show withholdings/deductions as negatives (e.g. -951.36).
    # Every field we capture is a magnitude, so normalize to the absolute value.
    return f"{abs(value):.2f}"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _union(words: list[Word]) -> list[float]:
    return [
        min(w.x0 for w in words),
        min(w.y0 for w in words),
        max(w.x1 for w in words),
        max(w.y1 for w in words),
    ]


def _in_region(w: Word, region: list[float], pad: float = 0.005) -> bool:
    x0, y0, x1, y1 = region
    return (x0 - pad) <= w.cx <= (x1 + pad) and (y0 - pad) <= w.cy <= (y1 + pad)


def _same_row(w: Word, y0: float, y1: float) -> bool:
    cy = (y0 + y1) / 2
    return y0 <= w.cy <= y1 or w.y0 <= cy <= w.y1


# ---------------------------------------------------------------------------
# Teaching: clicked words -> rules
# ---------------------------------------------------------------------------


def _nearest_label(words: list[Word], region: list[float]) -> str:
    """Find the text label immediately left of (or above) a value region.

    Returns a short run of non-numeric words on the value's row, to the left.
    """

    x0, y0, x1, y1 = region
    row = [
        w for w in words
        if _same_row(w, y0, y1) and w.x1 <= x0 + 0.01 and parse_currency(w.text) is None
    ]
    row.sort(key=lambda w: w.x0)
    # Keep the trailing contiguous run of label words (closest to the value).
    label_words = [w.text for w in row][-4:]
    return " ".join(label_words).strip(": ").strip()


def build_rules(words: list[Word], assignments: dict[str, list[int]]) -> list[FieldRule]:
    """Turn ``{field: [word indices]}`` into deterministic field rules."""

    rules: list[FieldRule] = []
    for fld, indices in assignments.items():
        chosen = [words[i] for i in indices if 0 <= i < len(words)]
        if not chosen:
            continue
        region = _union(chosen)
        kind = _FIELD_KIND.get(fld, "currency")
        label = _nearest_label(words, region)
        rules.append(FieldRule(field=fld, kind=kind, region=region, label_text=label))
    return rules


# ---------------------------------------------------------------------------
# Applying a profile (pure, deterministic)
# ---------------------------------------------------------------------------


# An orphaned-cents fragment: exactly one or two bare digits, no separators.
_CENTS_FRAGMENT_RE = re.compile(r"\d{1,2}")

# Max horizontal gap (fraction of page width) for two tokens to count as
# "adjacent" — small enough that only same-number fragments qualify.
_ADJACENT_GAP = 0.05


def _is_orphaned_cents(text: str) -> bool:
    """True if a token is a bare 1-2 digit cents fragment (e.g. ``46``, ``36``).

    Such a fragment, when adjacent to a complete dollars value, is the cents
    part of a number whose decimal point glyph the renderer dropped.
    """

    return bool(_CENTS_FRAGMENT_RE.fullmatch(text.strip()))


def _is_orphaned_cents_split(left: str, right: str) -> bool:
    """True when *left* + *right* is a dollars/cents pair split by a dropped ".".

    This is the case the merge step must *refuse* to stitch together: ``left``
    is a complete currency value and ``right`` is a bare 1-2 digit cents
    fragment (e.g. ``"975"`` + ``"36"`` → must stay ``975.36``, never ``97536``;
    ``"5,869"`` + ``"46"`` → must stay ``5869.46``, never ``586946``). Joining
    them here would silently destroy the decimal; instead the readers'
    :func:`_reconstruct_dropped_decimal` splices the "." back in at read time.

    A 3+ digit ``right`` fragment is *not* orphaned cents — it is a thousands
    group whose comma was dropped (e.g. ``"6"`` + ``"653.85"`` → ``6653.85``)
    and is safe to merge — so this returns ``False`` for it.
    """

    if not _is_orphaned_cents(right):
        return False
    # A left token that already ends in a separator is mid-number, not complete.
    if left.endswith((",", ".")):
        return False
    return parse_currency(left) is not None


def _reconstruct_dropped_decimal(dollars: Word, numeric_sorted: list[Word]) -> str | None:
    """Reconstruct ``dollars.cents`` when the decimal-point glyph was not emitted.

    Some PDF renderers omit the "." so a value like ``5,869.46`` arrives as the
    adjacent-but-separate tokens ``5,869`` and ``46``. When the token immediately
    to the right of *dollars* is an orphaned 1-2 digit cents fragment sitting
    very close horizontally, splice a "." between them and parse the result.

    Returns the parsed value string, or ``None`` when no reconstruction applies
    (no right neighbour, too far apart, not a cents fragment, or the join does
    not parse as a single currency value).
    """

    try:
        idx = numeric_sorted.index(dollars)
    except ValueError:
        return None
    if idx + 1 >= len(numeric_sorted):
        return None
    cents = numeric_sorted[idx + 1]
    if cents.x0 - dollars.x1 > _ADJACENT_GAP:
        return None
    if not _is_orphaned_cents(cents.text):
        return None
    merged = dollars.text + "." + cents.text.strip()
    return _parse_value(merged, "currency")


def _read_by_label(words: list[Word], rule: FieldRule) -> str | None:
    """Read a value using the label anchor to find the row and the taught
    region's x-position to pick the column.

    Paystubs commonly repeat one label (e.g. "Gross Pay") across a Current and a
    YTD column. The label fixes the *row* (robust if rows shift vertically); the
    taught region's horizontal position disambiguates *which column*.
    """

    label = rule.label_text.strip().lower()
    if not label:
        return None
    label_tokens = label.split()
    n = len(label_tokens)
    lowered = [w.text.lower().strip(": ") for w in words]
    region_cx = (rule.region[0] + rule.region[2]) / 2

    for i in range(len(words) - n + 1):
        if lowered[i : i + n] == label_tokens:
            run = words[i : i + n]
            ly0 = min(w.y0 for w in run)
            ly1 = max(w.y1 for w in run)
            lx1 = max(w.x1 for w in run)
            cands = [w for w in words if _same_row(w, ly0, ly1) and w.x0 >= lx1 - 0.005]
            if rule.kind == "date":
                cands.sort(key=lambda w: abs(w.cx - region_cx))
                for w in cands:
                    val = _parse_value(w.text, "date")
                    if val:
                        return val
                joined = " ".join(w.text for w in sorted(cands, key=lambda w: w.x0)[:3])
                val = _parse_value(joined, "date")
                if val:
                    return val
            else:
                numeric = [w for w in cands if parse_currency(w.text) is not None]
                if numeric:
                    # Pick the numeric candidate whose column matches what was taught.
                    best = min(numeric, key=lambda w: abs(w.cx - region_cx))
                    # If the decimal period was not emitted, reconstruct it from
                    # an adjacent 1-2 digit cents token (e.g. "5,869" + "46" → 5869.46).
                    numeric_sorted = sorted(numeric, key=lambda w: w.x0)
                    val = _reconstruct_dropped_decimal(best, numeric_sorted)
                    return val if val is not None else _parse_value(best.text, "currency")
    return None


def _read_by_region(words: list[Word], rule: FieldRule) -> str | None:
    inside = [w for w in words if _in_region(w, rule.region)]
    inside.sort(key=lambda w: w.x0)
    if not inside:
        return None
    # For currency: prefer the single numeric token closest to the taught region
    # center rather than joining all tokens.  Joining can corrupt the value when
    # the PDF omitted a separator glyph — e.g. "$5,869" + "46" joined with a
    # space gives "$5,869 46" which strips to 586946 instead of 5869.46.
    if rule.kind != "date":
        region_cx = (rule.region[0] + rule.region[2]) / 2
        numeric = [w for w in inside if parse_currency(w.text) is not None]
        if numeric:
            best = min(numeric, key=lambda w: abs(w.cx - region_cx))
            numeric_sorted = sorted(numeric, key=lambda w: w.x0)
            val = _reconstruct_dropped_decimal(best, numeric_sorted)
            if val is None:
                val = _parse_value(best.text, rule.kind)
            if val is not None:
                return val
    # For dates (or no numeric found): join tokens and parse.
    joined = " ".join(w.text for w in inside)
    val = _parse_value(joined, rule.kind)
    if val is not None:
        return val
    for w in inside:
        val = _parse_value(w.text, rule.kind)
        if val is not None:
            return val
    return None


def apply_rule(words: list[Word], rule: FieldRule) -> str | None:
    """Read one field: label anchor first (robust), then region fallback."""

    return _read_by_label(words, rule) or _read_by_region(words, rule)


def apply_profile(layout: Layout, profile: "Profile") -> dict[str, str]:
    """Extract every field a profile knows how to read from a layout."""

    out: dict[str, str] = {}
    for rule in profile.rules:
        value = apply_rule(layout.words, rule)
        if value is not None:
            out[rule.field] = value
    if profile.pay_frequency:
        out.setdefault("pay_frequency", profile.pay_frequency)
    return out


# ---------------------------------------------------------------------------
# Profile model & matching
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Profile:
    name: str
    pay_frequency: str | None = None
    rules: list[FieldRule] = field(default_factory=list)
    match_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pay_frequency": self.pay_frequency,
            "rules": [r.to_dict() for r in self.rules],
            "match_keywords": list(self.match_keywords),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        return cls(
            name=d["name"],
            pay_frequency=d.get("pay_frequency"),
            rules=[FieldRule.from_dict(r) for r in d.get("rules", [])],
            match_keywords=list(d.get("match_keywords", [])),
        )


def profile_score(layout: Layout, profile: Profile) -> float:
    """Fraction of a profile's label anchors + keywords present in the layout."""

    anchors = [r.label_text for r in profile.rules if r.label_text]
    anchors += list(profile.match_keywords)
    anchors = [a for a in anchors if a]
    if not anchors:
        return 0.0
    text = layout.text.lower()
    hits = sum(1 for a in anchors if a.lower() in text)
    return hits / len(anchors)


def best_profile(layout: Layout, profiles: list[Profile], threshold: float = 0.6) -> Profile | None:
    """Pick the highest-scoring profile at or above ``threshold``, else None."""

    scored = [(profile_score(layout, p), p) for p in profiles]
    scored = [(s, p) for s, p in scored if s >= threshold]
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1]


# ---------------------------------------------------------------------------
# Extraction (depends on the optional PyMuPDF / Tesseract stack)
# ---------------------------------------------------------------------------


def _load_pymupdf():
    try:
        import pymupdf  # type: ignore
        return pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
            return pymupdf
        except ImportError as exc:
            raise PaystubError(
                "Paystub import needs PyMuPDF. Install it with: "
                'pip install "tax-withholding-estimator[paystub]"'
            ) from exc


def _image_filetype(media_type: str) -> str:
    mt = (media_type or "").lower()
    if "png" in mt:
        return "png"
    if "jpeg" in mt or "jpg" in mt:
        return "jpg"
    if "webp" in mt:
        return "webp"
    if "tif" in mt:
        return "tiff"
    return "png"


_NUMERICISH_RE = re.compile(r"^[$(\-]?[\d.,]+[)\-]?$")


def _numericish(text: str) -> bool:
    """True if a token is a digit run possibly wrapped in $ , . ( ) - signs."""

    t = text.strip()
    return bool(t) and bool(_NUMERICISH_RE.match(t)) and any(c.isdigit() for c in t)


def _group_rows(items: list[list]) -> list[list[list]]:
    """Group raw words ``[x0, y0, x1, y1, text]`` into rows by vertical overlap."""

    rows: list[dict] = []
    for w in sorted(items, key=lambda w: (w[1] + w[3]) / 2):
        cy = (w[1] + w[3]) / 2
        height = w[3] - w[1]
        for row in rows:
            if abs(cy - row["cy"]) <= 0.5 * max(height, 1e-6):
                row["items"].append(w)
                break
        else:
            rows.append({"cy": cy, "items": [w]})
    return [r["items"] for r in rows]


def _merge_number_fragments(items: list[list]) -> list[list]:
    """Stitch number tokens that got split apart (e.g. ``6 , 653.85``).

    Some paystubs (notably ADP) emit thousands-separated numbers as several
    text runs, so ``6,653.85`` arrives as ``6`` + ``653.85`` (or with the comma
    as its own glyph). We re-join horizontally-adjacent numeric fragments on the
    same row when the merged text still parses as a single currency value, so a
    value is one clickable token again. Merging two *complete* numbers fails the
    parse check (two decimal points) and is rejected, so distinct columns stay
    separate.
    """

    merged: list[list] = []
    for row in _group_rows(items):
        row = sorted(row, key=lambda w: w[0])
        i = 0
        while i < len(row):
            x0, y0, x1, y1, text = row[i][0], row[i][1], row[i][2], row[i][3], row[i][4]
            j = i + 1
            if _numericish(text):
                height = y1 - y0
                while j < len(row):
                    nxt = row[j]
                    ntext = nxt[4].strip()
                    gap = nxt[0] - x1
                    if gap > 1.5 * max(height, 1e-6) or gap < -0.2 * max(height, 1e-6):
                        break
                    # Absorb numeric fragments and lone separators (a thousands
                    # comma or decimal point emitted as its own glyph).
                    if not (_numericish(ntext) or ntext in (",", ".")):
                        break
                    # Refuse to stitch an orphaned cents fragment onto a value
                    # whose decimal point glyph was dropped: "975" + "36" must
                    # not become "97536", "5,869" + "46" must not become
                    # "586946". The readers' _reconstruct_dropped_decimal splices
                    # the "." back at read time. Thousands groups (3+ digit
                    # fragments, e.g. "6" + "653.85") fall through and DO merge.
                    if _is_orphaned_cents_split(text, ntext):
                        break
                    combined = (text + ntext).replace(" ", "")
                    # Accept while it parses, or while still mid-number (ends in a separator).
                    if parse_currency(combined) is None and combined[-1:] not in (",", "."):
                        break
                    text = text + ntext
                    x1 = nxt[2]
                    y0, y1 = min(y0, nxt[1]), max(y1, nxt[3])
                    j += 1
                text = text.rstrip(",.")  # drop a dangling separator if nothing followed
            merged.append([x0, y0, x1, y1, text])
            i = j if j > i + 1 else i + 1
    return merged


def extract_layout(data: bytes, media_type: str, *, dpi: int = 150) -> Layout:
    """Render the first page and extract words with normalized boxes."""

    import base64

    pdf = _load_pymupdf()
    is_pdf = "pdf" in (media_type or "").lower()
    try:
        if is_pdf:
            doc = pdf.open(stream=data, filetype="pdf")
        else:
            doc = pdf.open(stream=data, filetype=_image_filetype(media_type))
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the UI
        raise PaystubError(f"Could not open file: {exc}") from exc

    if doc.page_count == 0:
        raise PaystubError("The file has no pages.")
    page = doc[0]
    rect = page.rect
    pw, ph = float(rect.width), float(rect.height)
    if pw <= 0 or ph <= 0:
        raise PaystubError("The page has zero size.")

    words_raw = page.get_text("words")
    if not words_raw and not is_pdf:
        words_raw = _ocr_words(page, pdf, dpi=dpi)
    if not words_raw and is_pdf:
        # Scanned PDF with no text layer -> OCR.
        words_raw = _ocr_words(page, pdf, dpi=dpi)

    items = [[w[0], w[1], w[2], w[3], str(w[4])] for w in words_raw if str(w[4]).strip()]
    items = _merge_number_fragments(items)

    words = [
        Word(text=it[4], x0=it[0] / pw, y0=it[1] / ph, x1=it[2] / pw, y1=it[3] / ph)
        for it in items
    ]

    pix = page.get_pixmap(dpi=dpi)
    png = pix.tobytes("png")
    return Layout(
        image_png_b64=base64.b64encode(png).decode("ascii"),
        img_width=pix.width,
        img_height=pix.height,
        words=words,
    )


def _ocr_words(page, pdf, *, dpi: int) -> list:
    """OCR a page that has no text layer. Requires Tesseract."""

    try:
        tp = page.get_textpage_ocr(flags=0, full=True, dpi=dpi)
        return page.get_text("words", textpage=tp)
    except Exception as exc:  # noqa: BLE001
        raise PaystubError(
            "Reading image/scanned paystubs needs the Tesseract OCR engine installed "
            "and on your PATH (set TESSDATA_PREFIX). Install Tesseract, or upload a "
            "text-based PDF instead. Original error: " + str(exc)
        ) from exc
