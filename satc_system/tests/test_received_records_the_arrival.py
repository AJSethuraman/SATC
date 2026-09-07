"""The button marked "Received" records that something was received.

THE DEFECT, found by walking the product on 5 September 2026.

The Documents screen keeps **two** registers and says why:

    "Two registers, because they are two different things: what we ASKED FOR,
     and what has ARRIVED."

and the second carries its own justification, printed under the table:

    "How and when a document was obtained, and from whom, is required by
     26 CFR §1.6695-2(b)(4)(i)(C) — not a nicety."

Pressing **Received** closed the first register and wrote nothing to the second.
The ask flipped to `satisfied`, the nav badge counted down 4 → 3, and **Arrived**
still read *"Nothing has arrived yet."* The one button on the screen that means
"it came in" left no record of any of the three things the citation names.

WHAT IS DERIVED AND WHAT IS NOT, because the difference is the whole design:

  furnished_by_client   DERIVED. The request was made TO this client; closing it
                        as received is the statement that they answered it.
  the client            DERIVED, from the request.
  the date              NOW — when the preparer recorded it.
  the channel           NOT derived. Email, portal or paper is unknowable from
                        here, so it stays empty and the row flags itself
                        `provenance incomplete` rather than inventing one.

An arrival honest about its gap is worth more than a complete-looking record
nobody can rely on — which is the same rule the N/A button already follows by
refusing a blank reason.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.persistence import SATCStore


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.fixture()
def state(tmp_path):
    """A state of its own, on its own store.

    These tests CLOSE requests, and closing one is durable. Run against the
    shared store they consume the fixture's open requests one by one, so the
    last test in the file finds none left -- and every later test file inherits
    a store that has been quietly worked through. That is the same shape as the
    `test_filing` isolation bug found the day before, and writing it a second
    time is not an accident worth repeating.
    """
    return AppState(store=SATCStore(tmp_path / "store"))


def _an_open_request(state):
    return next((i for i in state.mart.requested_items if i.is_open), None)


def _arrival_for(state, request_id):
    return next((d for d in state.mart.received_documents
                 if getattr(d, "satisfies_request_id", "") == request_id), None)


def test_there_is_an_open_request_to_close(state):
    """The denominator. Everything below is vacuous without one."""
    assert _an_open_request(state) is not None


def test_marking_received_writes_an_arrival(state):
    """THE DEFECT. `satisfied` was written; the arrivals register was not."""
    item = _an_open_request(state)
    assert _arrival_for(state, item.request_id) is None, "already arrived; bad fixture"

    state.close_request(item.request_id, how="received")

    got = _arrival_for(state, item.request_id)
    assert got is not None, "the ask closed and nothing was recorded as arriving"


def test_the_arrival_carries_the_three_things_the_citation_names(state):
    """§1.6695-2(b)(4)(i)(C): how, when, and from whom."""
    item = _an_open_request(state)
    state.close_request(item.request_id, how="received", channel="email")

    got = _arrival_for(state, item.request_id)
    assert got.obtained_how == "furnished_by_client"      # how
    assert got.obtained_at is not None                    # when
    assert got.furnished_by                               # from whom
    assert got.channel == "email"
    assert got.has_known_provenance


def test_an_unrecorded_channel_leaves_the_row_flagged_rather_than_invented(state):
    """The channel is the one thing that cannot be derived from here.

    Leaving it empty is correct; filling it in would be the confident wrong
    answer. What matters is that the row then SAYS it is incomplete.
    """
    item = _an_open_request(state)
    state.close_request(item.request_id, how="received")

    got = _arrival_for(state, item.request_id)
    assert got.channel == "", "a channel was invented for a document nobody described"
    assert got.obtained_how != "unknown", (
        "who furnished it IS derivable and should not be thrown away with the channel")
    assert not got.has_known_provenance, (
        "a row with no channel reports a complete §1.6695-2 record")


def test_the_completeness_flag_counts_all_three_things_the_reg_names():
    """`has_known_provenance` checked how and when, and ignored from-whom and by-what-means.

    It went unnoticed because nothing in `src/` had ever written to this register:
    every row came from the fixtures, and those fill in every field. A check whose
    only inputs are fixtures has never been asked a real question.
    """
    from datetime import datetime

    from satc.models.evidence import ReceivedDocument

    def doc(**kw):
        base = dict(document_id="d", client_id="C", tax_year=2025, doc_type="W-2",
                    obtained_how="furnished_by_client",
                    obtained_at=datetime(2026, 2, 3, 9, 0),
                    furnished_by="A Client", channel="email")
        return ReceivedDocument(**{**base, **kw})

    assert doc().has_known_provenance                       # all three present
    assert not doc(obtained_how="unknown").has_known_provenance
    assert not doc(obtained_at=None).has_known_provenance
    assert not doc(furnished_by="").has_known_provenance    # was reported complete
    assert not doc(channel="").has_known_provenance         # was reported complete


def test_pressing_received_twice_records_one_arrival(state):
    """The id is derived from the request, so the button is idempotent."""
    item = _an_open_request(state)
    state.close_request(item.request_id, how="received")
    state.close_request(item.request_id, how="received", channel="portal")

    hits = [d for d in state.mart.received_documents
            if getattr(d, "satisfies_request_id", "") == item.request_id]
    assert len(hits) == 1, f"pressing Received twice made {len(hits)} arrivals"
    assert hits[0].channel == "portal", "the second press did not update the record"


def test_the_screen_asks_how_it_arrived(client):
    """A register that cites a regulation has to collect what the regulation names."""
    body = client.get("/documents").get_data(as_text=True)
    assert 'name="channel"' in body
    assert "how it arrived" in body


def test_n_a_still_records_no_arrival(state):
    """The control. Not applicable means it never came, so nothing arrived."""
    item = _an_open_request(state)
    state.close_request(item.request_id, how="not_applicable",
                        reason="they closed that account in March")

    assert _arrival_for(state, item.request_id) is None, (
        "a document that was never sent was recorded as having arrived")
