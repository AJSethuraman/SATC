"""The ninth part cannot be tied to the IRS, so it is marked instead.

The goal was: **every figure the withholding estimator puts on a preparer's
screen can be checked against an IRS document — or is marked, on the screen, as
not checkable.** Eight of the nine are checked. This is the ninth.

THE OBSTACLE, AND IT WAS ATTACKED BEFORE BEING RECORDED. There is no IRS
document describing a paystub. No federal form, no standard layout, no
publication that says what one contains — a stub is whatever the employer's
payroll software prints. Some states legislate the contents (California Labor
Code §226, New York §195.3) and **Ohio does not**, which is where most SATC
clients are. So the verdict is `COULD NOT`, and it is a real verdict rather than
a gap left unmentioned.

WHAT IS MEASURED, WITH ITS DENOMINATOR. The reader scores **126 of 126** on an
eighteen-stub corpus, 0 wrong. That corpus was written in this repository, from
the shapes of failures seen on the firm's own machine — so it measures whether
the reader handles the shapes somebody thought of. It is worth having and it is
not an accuracy figure. The corpus module says so itself, and this test holds it
to that.

WHAT WOULD CLOSE IT: real stubs from the firm's own clients, scored. Those
cannot enter this repository — no client document ever does — so closing it is a
measurement made on the Forge against files that stay there, not a test that can
live here. Naming it is the useful half.
"""
from __future__ import annotations

import pathlib

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput


def _from_a_stub():
    return estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "biweekly", "gross_pay_per_period": 3800,
                    "federal_tax_withheld_per_period": 395, "pay_periods_remaining": 8,
                    "ytd_taxable_wages": 65000, "ytd_federal_tax_withheld": 7110}}))


def _typed_by_hand():
    return estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 80000,
                    "pay_periods_remaining": 1}}))


def test_an_estimate_built_from_a_stub_says_so():
    """The mark. A preparer reading the result has to know which figures came
    off a document nobody can independently verify."""
    said = " ".join(_from_a_stub().notes)
    assert "read by software" in said
    assert "IRS publishes no description of a paystub" in said
    assert "Compare the wages and withholding above against the stub" in said, (
        "the note names no action")


def test_an_estimate_typed_by_hand_does_not_carry_it():
    """A caveat on every estimate is a caveat nobody reads. Typed figures were
    typed by the preparer, who already knows where they came from."""
    assert "read by software" not in " ".join(_typed_by_hand().notes)


def test_the_corpus_is_scored_and_the_denominator_is_real(tmp_path):
    """126 of 126 is only worth stating beside what it counted."""
    from satc.ingest import paystub_corpus as pc

    score = pc.score(tmp_path)
    assert score.total > 100, f"only {score.total} figures scored"
    assert not score.wrong, [o.case for o in score.wrong]
    assert len(score.censuses) >= 18, "the corpus shrank"


def test_the_corpus_says_it_is_not_an_accuracy_figure():
    """Held to its own words. If somebody ever removes that caveat, the score
    starts reading as something it is not."""
    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "src" / "satc" / "ingest" / "paystub_corpus.py").read_text(encoding="utf-8")
    assert "NO CLIENT DOCUMENT IS EVER ADDED HERE" in text
    assert "reconstructing the SHAPE" in text


def test_no_client_document_is_in_the_corpus():
    """The standing constraint, asserted rather than trusted. The corpus is
    shapes in YAML; a real stub would be a binary."""
    root = pathlib.Path(__file__).resolve().parents[1]
    corpus = root / "corpus" / "paystubs"
    strays = [p.name for p in corpus.iterdir()
              if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}]
    assert not strays, f"documents in the paystub corpus: {strays}"
