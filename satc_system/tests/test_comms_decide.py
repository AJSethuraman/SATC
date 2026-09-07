"""The click the autonomy ladder was waiting for.

Everything under ``satc/autonomy`` — streaks, rungs, the digest, the traps —
derives from :class:`~satc.autonomy.approval.Approval` records, and until this
route existed nothing in the app created one. The scoreboard was complete and
permanently empty (charter §11).

What is guarded here is narrow and specific: that the comparison is made against
what the ENGINE rendered rather than what the page claims it rendered, that the
five reason codes reach the screen from the record that enforces them, and that
recording a decision is not sending one.
"""

from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.autonomy.approval import REASON_CODES

CLIENT = "SATC-001000"
TEMPLATE = "welcome"


@pytest.fixture()
def web():
    return create_app().test_client()


@pytest.fixture()
def ledger(monkeypatch):
    """An approval ledger this test owns, so a real practice is never written to."""
    rows: list = []
    monkeypatch.setattr(STATE.store, "load_approvals", lambda client_id="": list(rows))
    monkeypatch.setattr(STATE.store, "save_approvals", lambda added: rows.extend(added))
    return rows


def decide(web, **extra):
    data = {"client": CLIENT, "template": TEMPLATE, "tax_year": "2025"}
    data.update(extra)
    return web.post("/comms/decide", data=data)


def body(resp) -> str:
    assert resp.status_code == 200, resp.status_code
    return resp.data.decode("utf-8")


# --- the form is actually on the screen ---------------------------------------

def test_the_draft_screen_offers_both_answers(web):
    page = body(web.get(f"/comms?client={CLIENT}&template={TEMPLATE}&tax_year=2025"))
    assert "I sent this as written" in page
    assert "Record the correction" in page


def test_every_reason_code_reaches_the_screen_from_the_engine(web):
    """Never a list retyped in a template — the screen and the record would then
    be free to offer different sets (principle 6a)."""
    page = body(web.get(f"/comms?client={CLIENT}&template={TEMPLATE}&tax_year=2025"))
    for code in REASON_CODES:
        assert code in page


# --- what gets recorded --------------------------------------------------------

def test_sending_as_written_records_an_approval(web, ledger):
    decide(web, outcome="as_written")
    assert len(ledger) == 1
    assert ledger[0].outcome == "approval"
    assert ledger[0].decided_by.startswith("human:")
    assert ledger[0].recorded_at is not None, "same-day order needs a clock"


def test_the_same_click_twice_is_recorded_once(web, ledger):
    decide(web, outcome="as_written")
    resp = decide(web, outcome="as_written")
    assert len(ledger) == 1
    assert "counted twice" in body(resp)


def test_a_correction_carries_its_reason(web, ledger):
    decide(web, outcome="changed", reason="wrong_fact", sent_text="I rewrote it.")
    assert len(ledger) == 1
    assert ledger[0].is_correction
    assert ledger[0].reason == "wrong_fact"


def test_nothing_sent_is_a_real_answer_not_a_blank(web, ledger):
    """"Should not have flagged" means nothing went out, and an empty sent text
    is the truth about that rather than a missing value (principle 1)."""
    decide(web, outcome="changed", reason="should_not_have_flagged", sent_text="")
    assert len(ledger) == 1
    assert ledger[0].is_correction
    assert ledger[0].reason == "should_not_have_flagged"


def test_a_reason_outside_the_five_is_refused_on_the_page(web, ledger):
    resp = decide(web, outcome="changed", reason="because_i_felt_like_it",
                  sent_text="x")
    assert "not one of the five" in body(resp)
    assert not ledger, "a refused decision must not be recorded"


# --- the comparison is against the ENGINE, not the page ------------------------

def test_the_rendered_side_is_re_derived_and_not_taken_off_the_form(web, ledger):
    """A hidden field saying "this is what you rendered" is a claim the BROWSER
    makes about the engine. Taking it on trust would let an edit to the page
    launder itself into an approval — the hashes would match because both sides
    came from the same tampered value."""
    import ast
    import inspect

    from satc.app import comms_views

    source = inspect.getsource(comms_views.comms_decide)
    tree = ast.parse(source.lstrip())
    names = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
             for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "render" in names, "the route must render the draft itself"
    assert "_draft_text" in names, "and hash the engine's own output"

    # And the form does not carry the rendered text at all, so there is nothing
    # to take on trust in the first place.
    page = body(web.get(f"/comms?client={CLIENT}&template={TEMPLATE}&tax_year=2025"))
    assert 'name="rendered_text"' not in page
    assert 'name="rendered_hash"' not in page


def test_recording_a_decision_does_not_send_anything(web, ledger):
    """Charter §10. The codebase-wide AST scan covers this too; asserted here
    as well because THIS is the route somebody would be tempted to extend."""
    import ast
    import inspect

    from satc.app import comms_views

    tree = ast.parse(inspect.getsource(comms_views.comms_decide).lstrip())
    names = {getattr(n.func, "attr", None) or getattr(n.func, "id", None)
             for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for banned in ("sendmail", "send_message", "SMTP", "open_outlook_draft"):
        assert banned not in names
