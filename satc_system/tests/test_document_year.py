"""A document from another year must not close this year's request.

Measured 30 August 2026: a 2019 W-2 from a job the client left classified as
``W-2`` at HIGH confidence and filed as ``W-2 (2).pdf`` beside the current one.
``Classification`` carried no year at all -- its fields were label, key, code,
confidence, method, evidence -- so nothing downstream could tell a current W-2
from a seven-year-old one. ``reconcile_received`` would happily mark this year's
W-2 request Received on the strength of it.

THE RULE THIS ESTABLISHES, and it is deliberately asymmetric:

  * A year we could not read is **unknown**, never a guess, and unknown blocks
    nothing -- most documents will read fine, and a pipeline that refused
    everything it was unsure about would be returned to the preparer wholesale.
  * A year we DID read, which differs from the engagement's, refuses. That is the
    only case where we know enough to be sure something is wrong.

Guessing in either direction is worse than the gap it fills: guess the year and a
stale W-2 closes a live request; refuse on unknown and the preparer does the
sorting by hand, which is the job the software exists to remove.
"""

from __future__ import annotations

import pytest

from satc.ingest.classify import document_year


# -- reading the year off the document ----------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Form W-2  Wage and Tax Statement\n2026\n1 Wages 64,500.00", 2026),
    ("Form W-2 (2019)  Department of the Treasury", 2019),
    ("2026 CONSOLIDATED FORMS 1099\nCharles Schwab & Co.", 2026),
    ("SSA-1099  SOCIAL SECURITY BENEFIT STATEMENT\n2025\nBox 5.", 2025),
])
def test_reads_the_year_a_form_prints(text, expected):
    assert document_year(text) == expected


def test_a_year_inside_a_longer_number_is_not_a_year():
    """An EIN, an account number or a ZIP+4 can contain four digits that look
    like a year. Only a standalone run counts."""
    assert document_year("Account 3120260045  EIN 34-2026112") is None


def test_no_year_at_all_is_unknown_not_a_guess():
    assert document_year("Wages, tips, other compensation  64,500.00") is None


def test_a_year_outside_the_plausible_range_is_ignored():
    assert document_year("Established 1887. Interest income 412.55") is None


def test_the_most_repeated_year_wins_when_a_form_names_several():
    """Real forms reprint their year in the header, the footer and the boxes;
    a stray reference to another year appears once."""
    text = ("Form W-2 (2026)  Wage and Tax Statement 2026\n"
            "Corrected from your 2025 filing\n"
            "Form W-2 (2026)")
    assert document_year(text) == 2026


def test_a_genuine_tie_is_unknown_rather_than_the_first_one_seen():
    assert document_year("2024 statement\n2025 statement") is None


# -- and what the classifier does with it -------------------------------------

def test_a_classification_carries_the_year(tmp_path):
    from satc.ingest.classify import load_classifier
    c = load_classifier()
    got = c.classify_text("Form W-2  Wage and Tax Statement\n2019\n"
                          "1 Wages, tips, other compensation  31,000.00")
    assert got.label == "W-2"
    assert got.tax_year == 2019


def test_a_document_with_no_readable_year_says_unknown():
    from satc.ingest.classify import load_classifier
    c = load_classifier()
    got = c.classify_text("Form 1099-INT\nInterest Income\n1 Interest income 412.55")
    assert got is not None and got.tax_year is None


# -- the reason it matters ----------------------------------------------------

def test_a_prior_year_document_does_not_close_this_years_request():
    from satc.ingest import classify as cl
    assert cl.wrong_year(2019, 2026) is True


def test_the_right_year_passes():
    from satc.ingest import classify as cl
    assert cl.wrong_year(2026, 2026) is False


def test_an_unknown_year_is_not_treated_as_wrong():
    """The asymmetry, asserted. Unknown must not block."""
    from satc.ingest import classify as cl
    assert cl.wrong_year(None, 2026) is False
    assert cl.wrong_year(2026, None) is False


# -- end to end, through the real store ---------------------------------------

def test_a_2019_w2_does_not_close_the_2026_request(tmp_path, monkeypatch):
    """The measured failure, asserted against the actual reconcile path.

    Not a unit test of wrong_year -- that is above. This walks the seam a real
    document walks: an open Requested row for tax year 2026, and a W-2 whose
    printed year is 2019.
    """
    from satc.intake.service import reconcile_received
    from satc.models.mart import DocumentRecord

    class FakeMart:
        def __init__(self, docs): self.documents = docs

    class FakeStore:
        def __init__(self, docs):
            self._docs = docs
            self.set_calls = []
        def load_mart(self): return FakeMart(self._docs)
        def set_document_status(self, doc_id, status): self.set_calls.append((doc_id, status))
        def load_intake_engagements(self): return []
        def save_task(self, task): pass

    def a_request():
        return DocumentRecord(document_id="D1", client_id="C1", tax_year=2026,
                              doc_type="W-2", status="Requested",
                              note="Upload your W-2s")

    stale = FakeStore([a_request()])
    assert reconcile_received(stale, client_id="C1", doc_type="W-2",
                              doc_year=2019) is None
    assert stale.set_calls == [], "a 2019 W-2 closed the 2026 request"

    current = FakeStore([a_request()])
    assert reconcile_received(current, client_id="C1", doc_type="W-2",
                              doc_year=2026) is not None
    assert current.set_calls == [("D1", "Received")]

    unknown = FakeStore([a_request()])
    assert reconcile_received(unknown, client_id="C1", doc_type="W-2",
                              doc_year=None) is not None, \
        "an unreadable year must not block -- unknown is not wrong"
