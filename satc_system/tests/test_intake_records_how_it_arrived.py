"""Intake records that documents arrived, and asks the one thing it cannot know.

D26, and the firm's two answers of 6 September 2026:
**"Ask once per folder"** and **"Warn on the screen."**

THE DEFECT. The Documents screen keeps two registers and says why -- *"what we
ASKED FOR, and what has ARRIVED"* -- and prints under the second:

    How and when a document was obtained, and from whom, is required by
    26 CFR §1.6695-2(b)(4)(i)(C) -- not a nicety.

**Nothing in `src/` had ever written to that register.** Every row in it came
from the synthetic fixtures. `run_intake` read a folder, classified each file and
flipped the matching request to satisfied -- closing the first register without
ever touching the second. The register that cites a regulation had, in the
product's whole history, recorded no real document.

Half was fixed on 5 September: the **Received** button now writes an arrival.
Intake did not, and could not, because of the field below.

WHAT A FOLDER SCAN CANNOT ANSWER. Three of the four things the regulation names
are derivable -- WHEN (now), WHOSE (the client the run was pointed at, which
`run_intake` refuses to run without), WHAT (the classifier's label). **HOW it got
here is not.** A client emailed it, the preparer pulled it off a payroll portal,
it is last year's carry-forward, somebody handed over a thumb drive: the bytes on
disk are identical in every case, and that is exactly what §1.6695-2 asks for.

So it is asked. Once, for the batch, in a preparer's words rather than in the
five machine values of the `ObtainedHow` enum -- and defaulting to an answer that
asserts nothing, so a skipped dropdown produces an honest gap rather than a
plausible-looking record.

AND IT WARNS RATHER THAN BLOCKS. IRS Pub 1345 forbids transmitting before the
W-2s are in hand, so a MISSING document stops a return and should. A document
that is here, whose provenance nobody wrote down, is a record-keeping gap --
about what the practice can show afterwards, not about whether the return is
right. Stopping an April filing over a dropdown skipped in February teaches
people to route around the refusal.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.intake import arrival
from satc.persistence import SATCStore

CLIENT = "SATC-001000"
YEAR = 2025


@pytest.fixture()
def state(tmp_path):
    """Its own store: intake writes, and writes are durable."""
    return AppState(store=SATCStore(tmp_path / "store"))


@pytest.fixture()
def folder(tmp_path):
    """A folder holding one document intake can classify.

    Built from the fixtures' own sample-document maker, so this exercises the
    real classifier rather than a stub -- the point being that the arrival is
    written for whatever actually comes out of a scan.
    """
    from satc.fixtures.sample_docs import create_sample_folder

    out = tmp_path / "drop"
    create_sample_folder(out)
    return str(out)


def _arrivals(state, client_id=CLIENT):
    return [d for d in state.received_documents()
            if d.client_id == client_id and d.document_id.startswith("intake-")]


# ── the vocabulary ────────────────────────────────────────────────────────────

def test_the_default_asserts_nothing():
    """A skipped dropdown must produce an honest gap, not a likely-sounding
    answer. This is the difference between a compliance record and something
    that merely looks like one."""
    assert arrival.DEFAULT.obtained_how == "unknown"
    assert arrival.DEFAULT.channel == ""
    assert not arrival.DEFAULT.is_complete


def test_a_blank_or_unknown_key_resolves_to_the_default():
    """A typo in a form post must not lose a whole intake run."""
    for key in ("", None, "   ", "no-such-option"):
        assert arrival.resolve(key) is arrival.DEFAULT


def test_the_options_are_offered_in_a_preparer_s_words():
    """S35. `furnished_by_client` is how the enum spells it; nobody says that."""
    labels = [label for _, label in arrival.choices()]
    assert labels[0].startswith("Not recorded")
    assert any("emailed" in x for x in labels)
    for label in labels:
        assert "_" not in label, label


def test_the_common_answers_yield_a_complete_record():
    """The whole return on asking: one click and the ordinary case is complete."""
    for key in ("client_email", "client_portal", "client_paper", "preparer_download"):
        assert arrival.resolve(key).is_complete, key


def test_a_third_party_answer_is_honest_about_what_it_does_not_settle():
    """"A broker sent them" says who it was NOT, not by what means it came."""
    third = arrival.resolve("third_party")
    assert third.obtained_how == "furnished_by_third_party"
    assert third.channel == ""
    assert not third.is_complete


# ── intake writes the register ────────────────────────────────────────────────

def test_the_folder_has_documents_to_read(state, folder):
    """The denominator. Everything below is vacuous on an empty folder."""
    summary = state.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    assert summary["files_read"] > 0


def test_intake_writes_an_arrival_for_each_document(state, folder):
    """THE DEFECT. Nothing in `src/` had ever written to this register."""
    assert not _arrivals(state), "the store already has intake arrivals; bad fixture"
    summary = state.run_intake(folder, client_id=CLIENT, tax_year=YEAR,
                               arrival="client_email")
    got = _arrivals(state)
    assert got, "intake read documents and recorded no arrivals"
    assert len(got) == summary["arrivals"]


def test_the_arrival_carries_the_three_things_the_citation_names(state, folder):
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_email")
    for d in _arrivals(state):
        assert d.obtained_how == "furnished_by_client"    # how
        assert d.obtained_at is not None                  # when
        assert d.furnished_by                             # from whom
        assert d.channel == "email"                       # by what means
        assert d.has_known_provenance


def test_the_client_and_year_come_from_the_run_not_a_guess(state, folder):
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_paper")
    for d in _arrivals(state):
        assert d.client_id == CLIENT
        assert d.tax_year == YEAR


def test_an_unanswered_run_records_the_arrival_and_flags_it(state, folder):
    """The gap is a row that SAYS it is a gap -- not a missing row, and not an
    invented answer."""
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    got = _arrivals(state)
    assert got, "skipping the question lost the arrivals altogether"
    for d in got:
        assert d.obtained_how == "unknown"
        assert d.channel == ""
        assert not d.has_known_provenance


def test_re_running_the_same_folder_does_not_duplicate(state, folder):
    """The id is derived from the document, so a second scan updates rather than
    filling the register with copies of one document."""
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_email")
    first = len(_arrivals(state))
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_portal")
    assert len(_arrivals(state)) == first
    assert all(d.channel == "portal" for d in _arrivals(state)), "the re-run did not update"


def test_the_run_says_what_it_recorded(state, folder):
    """On the page it happened on. An `unknown` batch is legitimate and must not
    read as a failure -- but it must not pass silently either."""
    complete = state.run_intake(folder, client_id=CLIENT, tax_year=YEAR,
                                arrival="client_email")
    assert any("complete" in n and "1.6695-2" in n for n in complete["notes"])

    state2 = AppState(store=state.store)
    silent = state2.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    said = " ".join(silent["notes"])
    assert "without complete provenance" in said
    assert "Nothing is blocked" in said


# ── the screen ────────────────────────────────────────────────────────────────

def test_the_intake_screen_asks(state, monkeypatch):
    monkeypatch.setattr("satc.app.server.STATE", state)
    body = create_app().test_client().get("/intake").get_data(as_text=True)
    assert "How did these arrive?" in body
    assert "Not recorded" in body
    assert "1.6695-2" in body
    assert body.find("Not recorded") < body.find("The client emailed"), \
        "the default is not the first option"


def test_the_answer_reaches_the_engine_from_the_route(state, folder, monkeypatch):
    """A dropdown the route drops is a dropdown that does nothing."""
    monkeypatch.setattr("satc.app.server.STATE", state)
    create_app().test_client().post("/intake/run", data={
        "folder": folder, "client": CLIENT, "tax_year": str(YEAR),
        "arrival": "client_portal"})
    got = _arrivals(state)
    assert got, "the run through the route recorded nothing"
    assert all(d.channel == "portal" for d in got)


# ── warn, never block ─────────────────────────────────────────────────────────

def test_the_gaps_are_counted_for_the_screen(state, folder):
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    gaps = state.provenance_gaps()
    assert gaps
    assert all(not d.has_known_provenance for d in gaps)


def test_a_complete_run_reports_no_gaps(state, folder):
    """The control. A warning that fires on a clean file is a warning nobody
    reads on a dirty one."""
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_email")
    assert not [d for d in state.provenance_gaps()
                if d.document_id.startswith("intake-")]


def test_an_incomplete_record_does_not_stop_prep_or_filing(state, folder):
    """THE ANSWER TO THE SECOND QUESTION, asserted as behaviour rather than
    trusted to a comment: nothing about a provenance gap enters the blocking
    calculation."""
    before = len(state.blocking_outstanding())
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    assert state.provenance_gaps(), "wrong precondition — no gap was created"
    assert len(state.blocking_outstanding()) <= before, (
        "an unrecorded provenance started blocking prep")


def test_the_screen_warns_and_says_it_is_not_blocking(state, folder, monkeypatch):
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR)
    monkeypatch.setattr("satc.app.server.STATE", state)
    body = create_app().test_client().get("/documents").get_data(as_text=True)

    assert "incomplete record" in body
    assert "Nothing is blocked by this" in body
    assert "re-running intake" in body, "the warning names no remedy"


def test_the_screen_says_so_when_everything_is_complete(state, folder, monkeypatch):
    state.run_intake(folder, client_id=CLIENT, tax_year=YEAR, arrival="client_email")
    monkeypatch.setattr("satc.app.server.STATE", state)
    body = create_app().test_client().get("/documents").get_data(as_text=True)
    assert "complete" in body
    assert "Nothing is blocked by this" not in body
