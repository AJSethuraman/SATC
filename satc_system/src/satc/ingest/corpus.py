"""Score the classifier against the real IRS blanks. The denominator.

WHY THIS EXISTS. The classifier had 83% line coverage and thirty-five unit tests,
and not one of them answered the only question that matters: over documents that
look like what clients actually send, how often is it right? The synthetic corpus
scored 10 of 12 with zero wrong. The real blanks, the same day, scored 8 of 14
with four confidently wrong. The firm predicted exactly this:

    "the synthetic tests weren't doing it -- it was miscategorising W-2s and
     stuff, and maybe that would've been fixed had it been actually looked at"

THE DISTINCTION THIS REPORTS THAT NOTHING ELSE DOES. A verdict reached by the
FILENAME rung is not a win. `fw2.pdf` classifies as a W-2 because it is called
`fw2.pdf`; a client's upload is called `IMG_4471.pdf`. On the first run three of
the eight "right" answers were filename saves, so content-only accuracy was five
of thirteen, not eight. Any score that does not separate those two is flattering
itself, so this one separates them and leads with the content number.

Empty folder is not a pass. `corpus/blanks/` ships empty -- irs.gov is blocked
from the build environment -- so a run with nothing in it reports NOTHING TO
SCORE rather than a clean sheet, per S2: a green check that examined nothing is
worse than a red one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from satc.ingest.classify import DocumentClassifier, load_classifier

BLANKS = Path(__file__).resolve().parents[3] / "corpus" / "blanks"

# A verdict reached this way tells us nothing about a real upload, whose name is
# whatever the client's phone called it.
BY_NAME = "filename"


@dataclass
class Verdict:
    stem: str
    expected: str | None
    got: str
    method: str
    confidence: str

    @property
    def not_configured(self) -> bool:
        return self.expected is None

    @property
    def correct(self) -> bool:
        return self.got == self.expected

    @property
    def by_name_only(self) -> bool:
        """Right, but only because the file was helpfully named."""
        return self.correct and self.method == BY_NAME

    @property
    def wrong(self) -> bool:
        """Confidently the wrong form -- the worst outcome, worse than unknown.

        A wrong answer files the document under another form and, downstream,
        closes the request that form satisfies. Unclassified leaves it open.
        """
        return (not self.not_configured and not self.correct
                and self.got != "Unclassified")


@dataclass
class Score:
    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def scored(self) -> list[Verdict]:
        return [v for v in self.verdicts if not v.not_configured]

    @property
    def by_content(self) -> int:
        return sum(1 for v in self.scored if v.correct and not v.by_name_only)

    @property
    def by_name(self) -> int:
        return sum(1 for v in self.scored if v.by_name_only)

    @property
    def wrong(self) -> int:
        return sum(1 for v in self.scored if v.wrong)

    @property
    def unknown(self) -> int:
        return sum(1 for v in self.scored if v.got == "Unclassified")

    @property
    def total(self) -> int:
        return len(self.scored)

    @property
    def claimed(self) -> list[Verdict]:
        """Unconfigured types that came back named anyway.

        AN UNSCORED FILE IS NOT AN UNSEEN ONE. `expect: null` means the type is
        not configured, so Unclassified is the honest answer and no miss is
        counted -- but the classifier answering "Prior-year 1040" for a Schedule
        C is a claim about a client's document, and leaving it out of the report
        entirely is how a score flatters itself. It is shown, and it is shown
        separately, because it is not the same failure as getting a configured
        type wrong.
        """
        return [v for v in self.verdicts
                if v.not_configured and v.got != "Unclassified"]


def score(folder: Path | None = None,
          classifier: DocumentClassifier | None = None) -> Score:
    """Classify every blank in the folder against its recorded expectation."""
    folder = Path(folder or BLANKS)
    spec = folder / "expected.yaml"
    if not spec.exists():
        return Score()
    expected = (yaml.safe_load(spec.read_text(encoding="utf-8")) or {}).get("expect") or {}
    if classifier is None:
        classifier = load_classifier()
        # OCR IS OFF HERE, AND THE REPORT SAYS SO. Every blank in this corpus
        # carries a real text layer, so the OCR rung is not what decides any of
        # them -- but it is reached on a file the text rung declines, and one
        # page of Tesseract at 300 dpi costs seconds. Leaving it on turned a
        # sub-second check into minutes and nobody would run it.
        #
        # This narrows what the number covers, so the number must say what it
        # covers: `report` prints the rungs that were exercised.
        classifier.ocr_text_provider = None
        classifier.ocr_page_text_provider = None

    out = Score()
    for stem, want in expected.items():
        pdf = folder / f"{stem}.pdf"
        if not pdf.exists():
            continue                  # not fetched; absent is not a failure
        got = classifier.classify_path(pdf)
        out.verdicts.append(Verdict(stem=stem, expected=want, got=got.label,
                                    method=got.method, confidence=got.confidence))
    return out


def report(s: Score) -> str:
    """The score as a preparer reads it, denominator first."""
    if not s.verdicts:
        return ("  NOTHING TO SCORE. corpus/blanks/ holds no forms -- see its\n"
                "  README for the one-line fetch. An empty run is not a pass.")
    lines = ["  rungs exercised: form fields, text layer, filename. NOT OCR --",
             "  every blank here has a text layer, and OCR is priced in seconds.",
             "",
             f"  {'form':12} {'expected':22} {'got':26} how", "  " + "-" * 74]
    for v in sorted(s.verdicts, key=lambda v: (not v.wrong, v.correct, v.stem)):
        mark = ("!!" if v.wrong else "· " if v.not_configured
                else "~ " if v.by_name_only else "ok" if v.correct else "? ")
        lines.append(f"{mark} {v.stem:12} {str(v.expected):22} {v.got:26} "
                     f"[{v.method}/{v.confidence}]")
    lines += ["  " + "-" * 74,
              f"  {s.by_content} of {s.total} by content"
              + (f"   (+{s.by_name} by filename only -- not a win)" if s.by_name else ""),
              f"  {s.wrong} WRONG   {s.unknown} unclassified"]
    for v in s.claimed:
        lines.append(f"  NOTE  {v.stem} is not a configured type, so the honest "
                     f"answer is Unclassified;\n        it came back "
                     f"{v.got!r} [{v.method}/{v.confidence}]. Not counted above.")
    if s.wrong:
        lines.append("  A wrong answer is worse than unknown: it files the document"
                     " under another\n  form and closes that form's request.")
    return "\n".join(lines)
