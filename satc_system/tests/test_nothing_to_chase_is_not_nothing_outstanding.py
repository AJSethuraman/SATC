"""The headline agrees with the register underneath it.

D19 FROM THE WALK OF 5 SEPTEMBER 2026.

The chase panel's headline read **"Nothing outstanding."** while the register
directly beneath it read **"Asked for · 5 open"**, every row badged
`outstanding`.

The behaviour underneath is right, and `chasing.waiting` explains itself:

    NOT A CHASE ON THE MORNING YOU ASKED. ... without it, "outstanding" only
    means "asked for and not back yet", which on the day of the ask is noise --
    and a morning list that is mostly noise is a morning list nobody opens.

That is good judgement. The headline is simply the wrong sentence for it: five
things **are** outstanding and none is **due to be chased**, and those are
different reports. *"Nothing to chase yet"* is true; *"Nothing outstanding"* is
not, and it sits three lines above the five rows that contradict it.

`waiting()` was already counting what it held back -- `opened_today`, added for
exactly this reason, with a comment saying "held back rather than hidden: the
count is reported, so the sweep still adds up to the register." **Nothing read
the count.** A denominator computed and never displayed is the same as no
denominator, which is the S2 failure wearing a disguise.

Fixed on BOTH doors. `satc chase` printed the same sentence, and fixing the
browser while leaving the terminal wrong is a fix on the one door that was
walked -- the shape E2 and E4 had both just been.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.intake.chasing import waiting
from satc.models.evidence import RequestedItem
from satc.persistence import SATCStore


@pytest.fixture()
def state(tmp_path):
    """Its own state on its own store.

    These tests write requests, which is durable -- run against the shared store
    they would leave them there for every later test file, which is the
    isolation bug `test_filing` was found to have the day before.

    Built HERE rather than inside the page helper, because constructing an
    `AppState` SEEDS the store with the synthetic fixtures. Building it after
    writing the rows put four fixture chases on a page these tests had just
    emptied, and the failure read as though the fix were broken.
    """
    return AppState(store=SATCStore(tmp_path / "store"))


TODAY = date.today()


def _register(state, *items):
    """Leave the register holding exactly these rows as OPEN debts.

    `save_requested_items` is an upsert, not a replace -- checked, after the
    fixtures it does not touch turned up as four chases on a page these tests
    thought they had emptied. So the seeded rows are closed rather than deleted,
    which also keeps them counted in `requests`: the sweep still has a
    denominator, and `examined_nothing` stays correctly false.
    """
    seeded = [i for i in state.store.load_requested_items()]
    for item in seeded:
        item.status = "satisfied"
    state.store.save_requested_items(seeded + list(items))
    state.reload()


def _asked(request_id, days_ago, status="outstanding", text="Your W-2 from Meridian"):
    return RequestedItem(
        request_id=request_id, client_id="SATC-001000", tax_year=2025,
        doc_type="W-2", request_text=text,
        requested_at=TODAY - timedelta(days=days_ago), status=status)


def _page(state, monkeypatch):
    """The real route, pointed at THIS state.

    `create_app()` takes no state -- the views read the module-level `STATE`.
    """
    monkeypatch.setattr("satc.app.server.STATE", state)
    return create_app().test_client().get("/documents").get_data(as_text=True)


# ── the denominator ───────────────────────────────────────────────────────────

def test_the_sweep_holds_same_day_asks_back(state):
    """The precondition. Without it there is no wrong headline to fix."""
    _register(state, _asked("r1", 0), _asked("r2", 0, text="Interest statements"))
    sweep = waiting(state.store)
    assert not sweep.rows, "a same-day ask reached the chase list"
    assert sweep.opened_today == 2, sweep.opened_today


def test_the_store_was_not_simply_empty(state):
    """`examined_nothing` already owns its own sentence, and this is not it."""
    _register(state, _asked("r1", 0))
    assert not waiting(state.store).examined_nothing


# ── the fix, on the screen ────────────────────────────────────────────────────

def test_the_screen_does_not_claim_nothing_is_outstanding(state, monkeypatch):
    """THE DEFECT."""
    _register(state, _asked("r1", 0), _asked("r2", 0, text="Interest statements"))
    body = _page(state, monkeypatch)
    assert "Nothing outstanding." not in body, (
        "the headline says nothing is outstanding with open requests listed below it")


def test_the_screen_says_what_it_held_back(state, monkeypatch):
    _register(state, _asked("r1", 0), _asked("r2", 0, text="Interest statements"))
    body = _page(state, monkeypatch)
    assert "Nothing to chase yet" in body
    assert "2 asked for today" in body, "the count it already computes is still not shown"


def test_a_genuinely_clear_register_still_says_so(state, monkeypatch):
    """The control. Replacing one wrong sentence with another wrong one is not a
    fix -- when nothing is outstanding, the screen must still say that."""
    _register(state, _asked("r-done", 40, status="satisfied"))
    sweep = waiting(state.store)
    assert not sweep.examined_nothing, "the store is empty; this would prove nothing"
    assert not sweep.rows and not sweep.opened_today, "wrong precondition"

    body = _page(state, monkeypatch)
    assert "Nothing outstanding." in body
    assert "Nothing to chase yet" not in body


def test_an_older_request_still_reaches_the_chase_list(state, monkeypatch):
    """The other control. A request from last week is a chase, not noise."""
    _register(state, _asked("r-old", 9))
    body = _page(state, monkeypatch)
    assert "Nothing outstanding." not in body
    assert "Nothing to chase yet" not in body
    assert "Meridian" in body


def test_a_same_day_ask_does_not_hide_the_chases(state, monkeypatch):
    """A REGRESSION THIS FIX INTRODUCED, caught by writing the controls.

    The first version branched on `chase.opened_today` alone, ahead of the
    branch that renders the table. A store holding one old chase AND one ask
    made this morning therefore printed "Nothing to chase yet" and DROPPED THE
    TABLE -- strictly worse than the wrong headline it replaced, because the
    original at least still listed the rows underneath it.
    """
    _register(state, _asked("r-old", 9), _asked("r-today", 0, text="Interest statements"))
    sweep = waiting(state.store)
    assert sweep.rows and sweep.opened_today, "wrong precondition"

    body = _page(state, monkeypatch)
    assert "Meridian" in body, "the chase table was replaced by a headline"
    assert "Nothing to chase yet" not in body


# ── the fix, in the terminal ──────────────────────────────────────────────────

def test_the_terminal_does_not_contradict_itself(state, capsys):
    """THE TERMINAL'S VERSION IS SMALLER, and I had it wrong at first.

    I assumed `satc chase` carried the identical defect. It does not: it prints
    the held-back count below the headline in BOTH branches, so it never went
    silent the way the screen did. What it printed was

        Nothing outstanding — 2 register row(s) read across 1 client(s) ...
        2 more asked for today — held back, because chasing on the morning
        you asked is noise, not a chase.

    two sentences that cannot both be true, one line apart. So only the headline
    changes here; repeating the count would replace a contradiction with a
    stutter.
    """
    from satc import cli

    _register(state, _asked("r1", 0), _asked("r2", 0, text="Interest statements"))
    cli.main(["chase", "--dir", str(state.store.dir)])
    out = capsys.readouterr().out
    assert "Nothing outstanding" not in out
    assert "Nothing to chase yet" in out
    assert "2 more asked for today" in out, "the line that was already right is gone"
    assert out.count("asked for today") == 1, "the count is now printed twice"


def test_the_terminal_still_reports_its_denominator(state, capsys):
    """S2, and it was already right here -- this must not lose it."""
    from satc import cli

    _register(state, _asked("r1", 0))
    cli.main(["chase", "--dir", str(state.store.dir)])
    out = capsys.readouterr().out
    assert "register row(s) read" in out
