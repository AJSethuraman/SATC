"""Score a paystub reader against the synthetic corpus. The denominator.

WHY THIS EXISTS, and it is the same reason `satc.ingest.corpus` exists for the
classifier: the paystub reader had unit tests and no measurement. Every test it
had ran against ONE hand-written sample string in
`tests/test_paystub_reader.py`, laid out exactly the way the reader assumes.
That is a check tested on the case it cannot fail (S18), and the number it
produced -- seven fields, all green -- said nothing about a stub anybody sent.

WHAT A CASE HERE IS. `corpus/paystubs/cases.yaml` describes a SHAPE: where each
word sits on the page. This module renders it onto a real page and reads it back
through the same word-box extraction an upload goes through, so a case exercises
the geometry, which is where the failure lives. A case written as a paragraph of
text would prove nothing, for the reason `corpus/manifest.yaml` already gives
about the classifier corpus: a block of text with the right words in it is not
the document.

NO CLIENT DOCUMENT IS EVER ADDED HERE. Nothing in this repository holds one, and
the corpus grows by reconstructing the SHAPE of a failure seen on the firm's own
machine -- never the stub.

THREE NUMBERS, NOT ONE, and the middle one is the only one that can hurt a
client:

    RIGHT     the figure matched what the stub says.
    REFUSED   the reader stopped and said why. On a case whose right answer is
              to refuse, this counts as right; elsewhere it is a gap, not a harm.
    WRONG     a figure came back and it was not the figure on the stub.

`WRONG` is the number that becomes a tax return. A reader that refuses half the
corpus and is wrong on none of it is doing its job; a reader that answers
everything and is wrong on a tenth of it is the thing this replaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from satc.config import read_yaml

CASES = Path(__file__).resolve().parents[3] / "corpus" / "paystubs" / "cases.yaml"

REFUSE = "REFUSE"
FONT = "helv"
FONT_SIZE = 9.0
TOP = 60.0
LINE = 17.0

# The corpus key -> the label the reader emits. One place, so a renamed label
# cannot leave the corpus silently scoring a field nobody produces.
FIELD_LABELS: dict[str, str] = {}


def _labels() -> dict[str, str]:
    global FIELD_LABELS
    if FIELD_LABELS:
        return FIELD_LABELS
    from satc.ingest.readers.paystub import (
        LABEL_FED_WH_CURRENT, LABEL_FED_WH_YTD, LABEL_GROSS_CURRENT,
        LABEL_GROSS_YTD, LABEL_PAY_FREQUENCY, LABEL_RETIREMENT_CURRENT,
    )
    from satc.ingest.readers.paystub_columns import LABEL_RETIREMENT_YTD

    FIELD_LABELS = {
        "gross_current": LABEL_GROSS_CURRENT,
        "gross_ytd": LABEL_GROSS_YTD,
        "fed_current": LABEL_FED_WH_CURRENT,
        "fed_ytd": LABEL_FED_WH_YTD,
        "retirement_current": LABEL_RETIREMENT_CURRENT,
        "retirement_ytd": LABEL_RETIREMENT_YTD,
        "pay_frequency": LABEL_PAY_FREQUENCY,
    }
    return FIELD_LABELS


def load_cases(path: Path | None = None) -> list[dict]:
    data = read_yaml(path or CASES) or {}
    return list(data.get("cases") or [])


# --------------------------------------------------------------------------
# Rendering a case onto a real page
# --------------------------------------------------------------------------

def render(case: dict, out_dir: Path) -> Path:
    """Render one case to a PDF and return its path.

    Money columns are RIGHT-ALIGNED, as every payroll provider sets them, and
    a cell prefixed ``r:`` is right-aligned at its x. Getting this wrong would
    make the corpus easier than reality in exactly the place that matters.
    """
    import pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{case['id']}.pdf"
    doc = pymupdf.open()
    for page_spec in case.get("pages") or []:
        page = doc.new_page()
        y = TOP
        for row in page_spec.get("rows") or []:
            for cell in row or []:
                x, text = float(cell[0]), str(cell[1])
                if text.startswith("r:"):
                    text = text[2:]
                    x -= pymupdf.get_text_length(text, fontname=FONT, fontsize=FONT_SIZE)
                page.insert_text((x, y), text, fontname=FONT, fontsize=FONT_SIZE)
            y += LINE
    doc.save(str(path))
    doc.close()
    return path


def build(out_dir: Path, path: Path | None = None) -> list[tuple[dict, Path]]:
    """Render every case. Returns ``[(case, pdf path)]``."""
    return [(c, render(c, out_dir)) for c in load_cases(path)]


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

@dataclass
class Outcome:
    case: str
    field: str
    expected: str | None      # None = the stub does not carry it
    got: str | None
    reason: str = ""          # why the reader stopped, when it stopped
    want_reason: str = ""     # the reason the case says it must stop FOR

    @property
    def verdict(self) -> str:
        if self.expected == REFUSE:
            if self.got is not None:
                return "wrong"
            # AN EMPTY BOX IS NOT A REFUSAL. S11: absence leaves no token, so a
            # case whose right answer is "stop and say so" has to name WHICH
            # stop. Without this, a reader that found nothing at all — because
            # its labels drifted, say — would score full marks on every refusal
            # case in the corpus and the corpus would report it as working.
            if self.want_reason and self.reason != self.want_reason:
                return "wrong"
            return "right"
        if self.expected is None:
            # Nothing to find. Producing a figure anyway is an invention.
            return "wrong" if self.got is not None else "right"
        if self.got is None:
            return "refused"
        return "right" if self.got == self.expected else "wrong"


@dataclass
class Score:
    outcomes: list[Outcome] = field(default_factory=list)
    censuses: dict[str, dict] = field(default_factory=dict)

    def counted(self, verdict: str) -> int:
        return sum(1 for o in self.outcomes if o.verdict == verdict)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def wrong(self) -> list[Outcome]:
        return [o for o in self.outcomes if o.verdict == "wrong"]

    def report(self) -> str:
        if not self.outcomes:
            return ("NOTHING TO SCORE — the corpus rendered no cases. That is not "
                    "a pass.")
        lines = [
            f"paystub corpus: {len(self.censuses)} stubs, {self.total} figures asked for",
            f"  right   {self.counted('right')}/{self.total}",
            f"  refused {self.counted('refused')}/{self.total}   (a gap, not a harm)",
            f"  WRONG   {self.counted('wrong')}/{self.total}   (this is the one that "
            f"becomes a return)",
        ]
        for o in self.wrong:
            if o.expected == REFUSE and o.got is None:
                lines.append(f"    {o.case} · {o.field}: had to stop for "
                             f"{o.want_reason!r}, stopped for {o.reason!r}")
            else:
                lines.append(f"    {o.case} · {o.field}: expected {o.expected!r}, "
                             f"got {o.got!r}")
        return "\n".join(lines)


def _read_with_column_reader(pdf: Path):
    from satc.ingest.readers.paystub_columns import PaystubColumnReader

    read = PaystubColumnReader().read(str(pdf))
    got, why = {}, {}
    for key, label in _labels().items():
        fig = read.figures.get(label)
        got[key] = fig.value if fig else None
        why[key] = "" if (fig is None or fig.read) else fig.reason_code
    return got, why, read.census()


def _read_with_line_reader(pdf: Path):
    """The reader this replaces, scored on the same corpus, for comparison.

    It has no reason codes, because it has no refusals: a field it cannot read
    is simply missing, which is the difference the corpus is measuring.
    """
    from satc.ingest.readers.paystub import PaystubReader, _page_text

    fields = PaystubReader().read_text(_page_text(pdf)).labeled_fields
    got = {key: fields.get(label) for key, label in _labels().items()}
    return got, {key: "" for key in got}, {
        "pages_examined": 0, "tables_found": 0, "rows_examined": 0,
        "money_seen": 0, "fields_asked": len(_labels()),
        "fields_read": sum(1 for v in got.values() if v),
        "fields_refused": sum(1 for v in got.values() if not v)}


READERS = {"columns": _read_with_column_reader, "lines": _read_with_line_reader}


def score(out_dir: Path, *, reader: str = "columns", path: Path | None = None) -> Score:
    read_one = READERS[reader]
    result = Score()
    for case, pdf in build(out_dir, path):
        got, why, census = read_one(pdf)
        result.censuses[case["id"]] = census
        truth = case.get("truth") or {}
        wanted = case.get("reasons") or {}
        for key in _labels():
            result.outcomes.append(Outcome(
                case=case["id"], field=key, expected=truth.get(key, None),
                got=got.get(key), reason=why.get(key, ""),
                want_reason=wanted.get(key, "")))
    return result
