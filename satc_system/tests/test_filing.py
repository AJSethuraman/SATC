"""Filings: transmitted is not filed, and filed is not accepted.

``PipelineStatus`` called transmission ``"Filed"``. IRS Pub 1345 says an
electronically filed return *"isn't considered filed until the IRS acknowledges
acceptance"* — so a client told "filed" on the day of transmission has been told
something untrue, and the gap is exactly the window a rejection lives in.

The other thing one status column could never do: represent two attempts.
"""

from __future__ import annotations

from datetime import date, datetime

from satc.models.actor import Actor
from satc.models.filing import Filing, Return


def _filing(ack="", attempt=1, **kw):
    return Filing(filing_id=f"F{attempt}", return_key="RK", client_id="C",
                  transmitted_at=datetime(2026, 3, 1, 9, 0),
                  transmitted_by=Actor.owner(), ack_code=ack, attempt=attempt, **kw)


# --- the three events one column collapsed ------------------------------------

def test_transmitted_is_not_filed():
    """THE correction. Pub 1345."""
    f = _filing(ack="P")
    assert f.transmitted_at is not None
    assert f.is_pending
    assert not f.is_filed


def test_only_acceptance_counts_as_filed():
    assert _filing(ack="A").is_filed
    assert _filing(ack="a").is_filed          # extension accepted
    for not_filed in ("P", "T", "R", "B", "D", "E", "S", "X", ""):
        assert not _filing(ack=not_filed).is_filed, not_filed


def test_a_return_reports_an_honest_status_line():
    ret = Return(return_key="RK", client_id="C", tax_year=2025,
                 return_type="1040", jurisdiction="US")
    assert ret.filing_status_line() == "Not transmitted."

    ret.filings.append(_filing(ack="P"))
    assert "awaiting IRS acknowledgement" in ret.filing_status_line()
    assert not ret.is_filed
    assert ret.is_transmitted

    ret.filings.append(_filing(ack="A", attempt=2, ack_date=date(2026, 3, 3)))
    assert "Accepted by the IRS on Mar 03, 2026" in ret.filing_status_line()
    assert ret.is_filed


# --- a transport failure is not a rejection -----------------------------------

def test_a_transport_failure_never_reached_the_irs():
    """B and X are Drake/transport problems. Treating them as IRS rejections
    would start a 24-hour taxpayer-notification clock over nothing."""
    for code in ("B", "X"):
        f = _filing(ack=code)
        assert f.is_transport_failure
        assert not f.is_rejected
        assert f.notify_taxpayer_by() is None


def test_a_real_rejection_starts_the_24_hour_clock():
    """Pub 1345: the taxpayer must be told within 24 hours."""
    f = _filing(ack="R", ack_date=date(2026, 3, 2))
    assert f.is_rejected
    deadline = f.notify_taxpayer_by()
    assert deadline == datetime(2026, 3, 3, 0, 0)


def test_a_duplicate_hard_blocks_a_resend():
    f = _filing(ack="D")
    assert f.is_duplicate
    ret = Return(return_key="RK", client_id="C", tax_year=2025,
                 return_type="1040", jurisdiction="US", filings=[f])
    assert "Do not resend" in ret.filing_status_line()


# --- the reject detail the client notice must quote ---------------------------

def test_the_reject_rule_and_element_are_kept_verbatim():
    f = _filing(ack="R", reject_rule_id="IND-031-04",
                reject_element="PriorYearAGIAmt",
                reject_message="The prior year AGI does not match IRS records.")
    notice = f.client_notice_text()
    assert "IND-031-04" in notice
    assert "PriorYearAGIAmt" in notice
    assert "does not match IRS records" in notice


def test_an_accepted_filing_produces_no_client_notice():
    assert _filing(ack="A").client_notice_text() == ""


# --- many filings per return --------------------------------------------------

def test_a_return_can_have_several_attempts():
    """The thing one status column could not represent."""
    ret = Return(return_key="RK", client_id="C", tax_year=2025,
                 return_type="1040", jurisdiction="US",
                 filings=[_filing(ack="R", attempt=1),
                          _filing(ack="A", attempt=2)])
    assert len(ret.filings) == 2
    assert ret.latest_filing.attempt == 2
    assert ret.is_filed
    assert not ret.needs_attention


def test_a_return_rejected_and_not_yet_fixed_needs_attention():
    ret = Return(return_key="RK", client_id="C", tax_year=2025,
                 return_type="1040", jurisdiction="US",
                 filings=[_filing(ack="R")])
    assert ret.needs_attention


# --- an amended return is a different document --------------------------------

def test_an_amendment_is_a_new_return_not_a_status():
    original = Return(return_key="RK-1", client_id="C", tax_year=2025,
                      return_type="1040", jurisdiction="US")
    amended = Return(return_key="RK-2", client_id="C", tax_year=2025,
                     return_type="1040", jurisdiction="US",
                     version="amended", amends_return_key="RK-1")
    assert amended.version == "amended"
    assert amended.amends_return_key == original.return_key
    assert amended.filings is not original.filings


# --- round trip ---------------------------------------------------------------

def test_a_filing_survives_persistence_with_its_reject_detail():
    import tempfile

    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        store.save_filings([_filing(ack="R", ack_date=date(2026, 3, 2),
                                    submission_id="12345",
                                    reject_rule_id="IND-031-04",
                                    reject_element="PriorYearAGIAmt")])
        f = store.load_filings("RK")[0]
        assert f.ack_code == "R"
        assert f.submission_id == "12345"        # Pub 1345 ties this to the 8879
        assert f.reject_rule_id == "IND-031-04"
        assert f.transmitted_by.is_human
        assert not f.is_filed


def test_filings_are_removed_with_their_client():
    import tempfile

    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        store.save_filings([_filing(ack="A")])
        store.delete_client("C")
        assert store.load_filings("RK") == []


def test_return_status_does_not_shadow_client_filing_status():
    """Two different things both want the word "filing".

    ``filing_status`` is the client's TAX filing status (married filing
    jointly). ``return_status`` is whether the IRS has the return. A shadowing
    definition silently broke the interview screen, and only a test that
    asserted on the real value caught it.
    """
    from satc.app.state import STATE

    client_id = STATE.client_choices()[0][0]
    tax_status = STATE.filing_status(client_id)
    assert tax_status in ("", "Single", "Married filing jointly",
                          "Married filing separately", "Head of household",
                          "Qualifying surviving spouse")

    ret = STATE.returns()[0]
    assert STATE.return_status(ret.return_key) in (
        "Not transmitted", "Awaiting IRS", "Accepted", "Rejected",
        "Duplicate", "Transmission failed")


def test_a_return_no_longer_carries_a_status_of_its_own():
    """Derived, never stored — a second copy is how a dashboard ends up saying
    "Filed" about a return the IRS rejected."""
    from satc.models.mart import ReturnRecord

    fields = {f for f in ReturnRecord.__dataclass_fields__}
    assert "status" not in fields
    assert "is_extended" not in fields
    assert "filed_date" not in fields
