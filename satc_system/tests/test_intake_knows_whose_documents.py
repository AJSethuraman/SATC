"""Intake will not read a folder without being told whose it is.

THE DEFECT, found by walking the product in a browser on 5 September 2026 with
3,247 tests passing and none of them red. `AppState.run_intake` was declared

    def run_intake(self, folder, *, client_id="SATC-001000", tax_year=2024)

and the `/intake` screen carried the client as a HIDDEN field, so the nav's own
Intake link supplied none. Every document any preparer ever scanned through that
screen was staged and posted to a hardcoded demo client id, in the prior tax
year, whoever they meant and whatever year the form said.

It was found by doing it: a folder holding two invented W-2s (92,400 and 58,150)
was scanned and posted, and the figures landed as `Wages 150,550.00` on a third
party's 1040 workpaper -- 2025 forms, filed into 2024.

Several tests in this suite *passed the default in*, which is why a green suite
was compatible with the defect. They now name their client, and so does everyone
else.

WHAT EACH TEST HERE WOULD CATCH. The first two pin the refusal at the engine. The
third is the defect itself -- one client's documents reaching another client's
return -- and is the one that would have failed before the fix. The fourth pins
the same refusal at the screen, in words a preparer can act on. The fifth is the
missing-folder half of the same screen, which used to answer with somebody else's
six demo documents for any string at all.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.fixtures import create_sample_folder


@pytest.fixture()
def client():
    return create_app().test_client()


def _folder(tmp_path, name="2025"):
    return str(create_sample_folder(tmp_path / name))


def test_run_intake_refuses_without_a_client(tmp_path):
    """No client is not a default. It is a refusal."""
    state = AppState()
    with pytest.raises(ValueError, match="needs a client"):
        state.run_intake(_folder(tmp_path), client_id="", tax_year=2025)


def test_run_intake_refuses_without_a_tax_year(tmp_path):
    """A year decides which return the figures land on; last year's is not a guess
    worth making."""
    state = AppState()
    with pytest.raises(ValueError, match="needs a tax year"):
        state.run_intake(_folder(tmp_path), client_id="SATC-001000", tax_year=0)


def test_documents_do_not_land_on_a_client_nobody_chose(client, tmp_path):
    """THE DEFECT ITSELF, driven the way the walk drove it -- through the screens.

    THIS TEST WAS DECORATIVE ON ITS FIRST DRAFT, and the mutation run caught it.
    It called `run_intake(folder, client_id=them, ...)` directly and asserted the
    figures reached `them`. That passes against the OLD code too, because a caller
    who names a client was always honoured -- the default only fired for a caller
    who named none. The defect was never "the engine ignores a client you gave
    it"; it was "the screen gave it none, and the engine invented one."

    So the test has to arrive the way a preparer does: press the buttons with the
    client box empty, then press Post, and prove nothing was written onto anyone.
    Against the old code the first press posts to `SATC-001000` in 2024.
    """
    from satc.app.state import STATE

    folder = _folder(tmp_path)

    # Compare the CONTENT of the ledger, not its length, and not the set of
    # returns. Two earlier drafts of this assertion stayed green under mutation:
    #   - "did a new return appear?" -- no. SATC-001000 already has a 2024 return
    #     in the shipped store and `post_confirmed` reuses it.
    #   - "did the line-item count change?" -- no. `post_confirmed` is idempotent:
    #     it drops the prior intake-sourced lines for that return and adds the
    #     current set, so a wholesale REPLACEMENT nets to the same count.
    # What the defect actually does is overwrite one client's figures with
    # another's, which only a value-by-value comparison can see.
    def ledger():
        return sorted((li.return_key, li.schedule, li.line_code, str(li.amount))
                      for li in STATE.mart.line_items)

    before = ledger()

    # The screen as it was: a folder, and no answer to "whose is this?"
    client.post("/intake/run", data={"folder": folder, "client": "", "tax_year": ""})
    client.post("/staging/auto")
    client.post("/staging/post")

    after = ledger()
    assert after == before, (
        "staging with no client chosen changed the ledger. Went in: "
        f"{sorted(set(after) - set(before))[:4]} -- documents were posted onto a "
        "client nobody picked")


def test_post_confirmed_refuses_when_nothing_recorded_a_client(tmp_path):
    """The same defect one step downstream: `post_confirmed` used to end
    `or "SATC-001000"` / `or 2024` on its own account."""
    state = AppState()
    state.intake_context = {}
    with pytest.raises(ValueError, match="needs a client and a tax year"):
        state.post_confirmed()


def test_the_screen_refuses_and_says_what_is_missing(client, tmp_path):
    """A preparer must be told which of the two is missing, not just stopped."""
    r = client.post("/intake/run", data={"folder": _folder(tmp_path),
                                         "client": "", "tax_year": ""})
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Choose a client and a tax year" in body
    assert "not something SATC will assume" in body
    assert "Read &amp; stage" not in body, "it offered to stage anyway"


def test_a_folder_that_is_not_there_says_so(client):
    """The demo fallback answered a question it never asked the disk.

    Any string at all came back as "Found 6 documents in ..." -- the synthetic
    demo set, with detected types, confidence badges and a live staging button --
    while the very next screen honestly reported "Read 0 fields from 0 documents".
    """
    r = client.post("/intake", data={"folder": "/this/path/is/invented/nowhere"})
    body = r.get_data(as_text=True)
    assert "There is no folder at" in body
    assert "Found 6 documents" not in body
    assert "Read &amp; stage" not in body, "it offered to stage a folder that is not there"
