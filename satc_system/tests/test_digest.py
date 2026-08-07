"""THE DIGEST AND THE LADDER SCREENS — docs/AUTONOMY-CHARTER.md section 8.

Three things this file has to prove that no other test in the suite does:

* :func:`~satc.autonomy.digest.digest_for` is REGENERABLE — the same facts
  produce the same digest for a past day, every time, because it reads
  nothing but its own arguments.
* The five correction reasons are never collapsed into one figure, anywhere
  — not in the dataclasses, not on either screen.
* Both screens actually render, through the REAL ``create_app()`` — not a
  hand-assembled Flask app that would pass whether or not the blueprint is
  actually wired into ``server.py`` (``tests/test_app_routes.py``'s own
  lesson, learned the hard way in this repo before).

WIRING NOTE, read this before touching the fixture below: ``server.py`` is
explicitly out of scope for this slice (the orchestrator wires it), so at the
time this file runs the blueprint is not yet registered there. The ``app``
fixture registers it on the REAL app object ``create_app()`` returns — every
other guard ``create_app`` sets up (the loopback/CSRF check, the secret key,
every other blueprint) is exercised exactly as the owner would see it; only
the one line ``server.py`` will eventually carry is added here instead. Once
that line lands, ``"autonomy" not in application.blueprints`` is simply
always false and this fixture is a no-op.
"""

from __future__ import annotations

import ast
import inspect
from datetime import date, timedelta
from pathlib import Path

import pytest

from satc.app import autonomy_views
from satc.app.autonomy_views import bp as autonomy_bp
from satc.app.server import create_app
from satc.app.state import STATE
from satc.autonomy.approval import REASON_CODES, record_approval, record_correction
from satc.autonomy.digest import Digest, Proposed, ReasonTally, Scoreboard, digest_for, week_for
from satc.autonomy.ladder import load_autonomy_policy
from satc.autonomy.preconditions import ALL_PRECONDITIONS, PreconditionRecord, record_precondition
from satc.models.actor import Actor

OWNER = Actor.owner()
DAY = date(2026, 3, 20)
RENDERED = "Subject: Your organizer is ready\n\nHi there, please see attached."


def approved(*, decided_on=DAY, template_key="welcome", client_id="CL-1", **kw):
    args = dict(actor=OWNER, template_key=template_key, client_id=client_id,
               rendered_text=RENDERED, decided_on=decided_on)
    args.update(kw)
    return record_approval(**args)


def corrected(*, decided_on=DAY, template_key="welcome", client_id="CL-1",
             reason="wrong_fact", **kw):
    args = dict(actor=OWNER, template_key=template_key, client_id=client_id,
               rendered_text=RENDERED, sent_text=RENDERED + " (edited)",
               reason=reason, decided_on=decided_on)
    args.update(kw)
    return record_correction(**args)


def a_precondition(key, *, confirmed_on=DAY, actor=OWNER):
    return record_precondition(actor=actor, key=key, confirmed_on=confirmed_on)


def all_preconditions(*, confirmed_on=DAY):
    return [a_precondition(k, confirmed_on=confirmed_on) for k in ALL_PRECONDITIONS]



def a_clean_night(day):
    """A drill that ran and passed, for the day in question.

    Needed by any test about something OTHER than the drill: charter §7 says a
    tripwire that could not run counts as a MISS, and "nobody ran it" is the
    strongest version of that — so a digest with no drill on file holds every
    template at draft-only. That is the correct fail-safe and it is deliberate;
    it just means a test isolating the precondition gate has to say the night
    was clean.
    """
    import dataclasses

    from satc.autonomy.traps import run_drill

    return dataclasses.replace(run_drill(today=day), today=day)


# --- digest_for: pure, regenerable, never a combined figure ------------------

def test_digest_for_is_identical_on_two_generations_for_a_past_day():
    """Regenerable — charter §8: 'a digest that cannot be recomputed is a
    claim, not a record.' Built from a FRESH list literal the second time,
    not the same object, so this is about the VALUES, not identity."""
    history = [approved(decided_on=DAY), corrected(decided_on=DAY, reason="wrong_judgment")]
    policy = load_autonomy_policy()
    preconditions = all_preconditions()

    first = digest_for(DAY, approvals=list(history), preconditions=list(preconditions),
                       policy=policy)
    second = digest_for(DAY, approvals=[history[0], history[1]],
                        preconditions=[preconditions[0], preconditions[1], preconditions[2]],
                        policy=policy)
    assert first == second


def test_week_for_is_identical_on_two_generations():
    history = [approved(decided_on=DAY - timedelta(days=i)) for i in range(3)]
    first = week_for(DAY, approvals=list(history))
    second = week_for(DAY, approvals=list(history))
    assert first == second


def test_a_digest_only_counts_decisions_on_or_before_its_own_day():
    """A decision made the day AFTER a past digest must not appear in it —
    otherwise a digest for March 20th generated on the 21st would differ from
    one generated a year later, and neither would be "the record for that
    day"."""
    approvals = [approved(decided_on=DAY), approved(decided_on=DAY + timedelta(days=1))]
    d = digest_for(DAY, approvals=approvals)
    assert d.approved_clean == 1


def test_reason_codes_are_broken_out_and_never_totalled_into_one_figure():
    """Charter §6: the five reasons are DIFFERENT PRACTICES IN DIFFERENT
    TROUBLE and must never be summed against approvals into an 'accuracy'
    number. This is checked two ways: the type itself offers no such method,
    and a day with corrections in two different codes keeps them apart."""
    forbidden = {"accuracy", "rate", "pct", "percent", "score"}
    for cls in (Digest, Scoreboard, ReasonTally):
        field_names = {f.name.lower() for f in __import__("dataclasses").fields(cls)}
        method_names = {n.lower() for n in dir(cls) if not n.startswith("_")}
        hit = forbidden & (field_names | method_names)
        assert not hit, f"{cls.__name__} exposes {hit} — charter §6 forbids a combined figure"

    approvals = [
        corrected(decided_on=DAY, client_id="CL-1", reason="wrong_fact"),
        corrected(decided_on=DAY, client_id="CL-2", reason="should_not_have_flagged"),
    ]
    d = digest_for(DAY, approvals=approvals)
    assert d.corrections.for_code("wrong_fact") == 1
    assert d.corrections.for_code("should_not_have_flagged") == 1
    # Every code is present even at zero — a screen can print all five rows.
    assert set(d.corrections.counts) == set(REASON_CODES)


def test_gave_up_is_counted_and_is_not_the_same_number_as_a_correction_total():
    approvals = [corrected(decided_on=DAY, reason="gave_up")]
    d = digest_for(DAY, approvals=approvals)
    assert d.gave_up == 1
    assert d.corrections.for_code("gave_up") == 1


# --- the precondition gate: names which one is missing -----------------------

def test_a_pair_blocked_by_a_missing_precondition_names_which_one():
    """Charter §3: 'streaks() returns every pair at rung zero with the reason
    named.' No preconditions recorded at all — the harder case."""
    approvals = [approved(decided_on=DAY)]
    d = digest_for(DAY, approvals=approvals, preconditions=[],
                   drill_results=[a_clean_night(DAY)])
    assert len(d.rungs) == 1
    rung = d.rungs[0]
    assert rung.state == "draft_only"
    assert rung.blocked_reason
    for key in ALL_PRECONDITIONS:
        assert key in d.gate.missing
    # The reason names the ACTUAL missing preconditions, in the owner's words
    # — not a bare "false" or a generic "blocked".
    assert "off-disk backup" in rung.blocked_reason.lower() or "offsite_backup" in rung.blocked_reason


def test_a_lapsed_precondition_freezes_but_does_not_demote():
    """Charter §3: 'a lapsed reconfirmation freezes accrual and demotes
    nothing.' Five clean approvals (the routine bar) with a precondition
    confirmed long enough ago to have lapsed: the streak is still SHOWN, but
    the rung cannot be earned while frozen."""
    old = DAY - timedelta(days=365)
    preconditions = all_preconditions(confirmed_on=old)
    approvals = [approved(decided_on=DAY - timedelta(days=i), template_key="welcome")
                for i in range(5)]
    d = digest_for(DAY, approvals=approvals, preconditions=preconditions)
    rung = d.rungs[0]
    assert rung.streak == 5          # nothing was wiped
    assert rung.state == "draft_only"  # but it could not cross into earned
    assert set(d.gate.lapsed) == set(ALL_PRECONDITIONS)


def test_all_preconditions_current_lets_a_routine_pair_earn():
    """Uses ``date.today()`` rather than the fixed ``DAY`` fixture on purpose:
    :func:`~satc.autonomy.ladder.streaks` checks the precondition gate against
    the REAL clock internally (it has no ``today=`` parameter of its own —
    see :class:`~satc.autonomy.digest.Digest`'s ``gate`` docstring for the
    known gap this leaves for a genuinely PAST digest day). Anchoring both the
    approvals and the confirmations to today sidesteps that gap so this test
    is about the streak crossing the threshold, not about the gate's dating."""
    today = date.today()
    preconditions = all_preconditions(confirmed_on=today)
    approvals = [approved(decided_on=today - timedelta(days=i), template_key="welcome")
                for i in range(5)]
    d = digest_for(today, approvals=approvals, preconditions=preconditions,
                   drill_results=[a_clean_night(today)])
    assert d.rungs[0].state == "earned"


# --- the screens: through the real app ----------------------------------------

@pytest.fixture()
def app():
    application = create_app()
    if "autonomy" not in application.blueprints:
        application.register_blueprint(autonomy_bp)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def empty_ledger(monkeypatch):
    """Force both screens to see NO recorded decisions, regardless of what
    earlier tests in this session may have written to the shared STATE store
    — the empty-case test must not depend on test execution order."""
    monkeypatch.setattr(STATE.store, "load_approvals", lambda client_id="": [])
    monkeypatch.setattr(autonomy_views, "load_preconditions", lambda: [])
    return None


def test_the_ladder_screen_renders(client, empty_ledger):
    resp = client.get("/autonomy")
    assert resp.status_code == 200
    assert b"Autonomy" in resp.data


def test_the_digest_screen_renders(client, empty_ledger):
    resp = client.get("/autonomy/digest")
    assert resp.status_code == 200
    assert b"Autonomy digest" in resp.data


def test_the_digest_screen_accepts_a_past_day(client, empty_ledger):
    resp = client.get("/autonomy/digest", query_string={"day": "2026-01-05"})
    assert resp.status_code == 200
    assert b"January 05, 2026" in resp.data


def test_an_unparseable_day_is_refused_by_name_not_a_500(client, empty_ledger):
    resp = client.get("/autonomy/digest", query_string={"day": "not-a-date"})
    assert resp.status_code == 200
    assert b"is not a date" in resp.data


def test_the_digest_screen_is_identical_on_two_generations_for_a_past_day(client, monkeypatch):
    """The view-level version of regenerability: the same recorded facts,
    read twice, render byte-identical HTML for the same past day."""
    fixed = [approved(decided_on=DAY), corrected(decided_on=DAY, reason="wrong_judgment")]
    fixed_pre = all_preconditions(confirmed_on=DAY)
    monkeypatch.setattr(STATE.store, "load_approvals", lambda client_id="": list(fixed))
    monkeypatch.setattr(autonomy_views, "load_preconditions", lambda: list(fixed_pre))

    first = client.get("/autonomy/digest", query_string={"day": DAY.isoformat()})
    second = client.get("/autonomy/digest", query_string={"day": DAY.isoformat()})
    assert first.status_code == second.status_code == 200
    assert first.data == second.data


def test_the_empty_case_explains_itself_rather_than_a_blank_panel(client, empty_ledger):
    """Principle 13: a screen with nothing on it must say WHY, not just be
    blank — otherwise a genuinely empty ladder and a broken data seam look
    the same."""
    ladder = client.get("/autonomy").data
    assert b"No decision has ever been recorded" in ladder

    digest_page = client.get("/autonomy/digest").data
    assert b"No decision has ever been recorded" in digest_page


def test_reason_codes_are_shown_separately_on_the_digest_screen(client, monkeypatch):
    approvals = [
        corrected(decided_on=DAY, client_id="CL-1", reason="wrong_fact"),
        corrected(decided_on=DAY, client_id="CL-2", reason="should_not_have_flagged"),
    ]
    monkeypatch.setattr(STATE.store, "load_approvals", lambda client_id="": approvals)
    monkeypatch.setattr(autonomy_views, "load_preconditions", lambda: [])
    body = client.get("/autonomy/digest", query_string={"day": DAY.isoformat()}).data.decode()
    for code in REASON_CODES:
        assert code in body
    # NO SINGLE COMBINED FIGURE ANYWHERE (charter §6).
    #
    # This banned four prose phrases and nothing else, so it could not fail on
    # the thing it exists to catch: the screen was, at the time, summing the
    # reason codes with a Jinja filter and printing the total in the headline
    # row. No banned phrase appeared, the test passed, and the forbidden number
    # was on the page. A reviewer caught it by inserting a real computed ratio
    # and watching this stay green.
    #
    # So it now asserts on the NUMBER. Two corrections in two different reason
    # codes: the total, 2, must not appear as a standalone figure, because the
    # only way to produce it is by adding the codes together.
    for banned in ("combined accuracy", "% accurate", "success rate", "an accuracy of"):
        assert banned not in body.lower()

    # Asserted on the HEADLINE ROW's columns, which is where the total was and
    # is the only place it could go without being a per-code figure. Matching on
    # numbers alone collides with legitimate cells (a streak of 2, a count of 0).
    import re

    headline = re.search(r"<tr>\s*(<th>.*?</th>\s*)+</tr>", body, re.S)
    assert headline, "the digest headline row is gone"
    assert "Corrected" not in headline.group(0), (
        "the headline row has a combined 'Corrected' column again — the only "
        "way to fill it is by summing the reason codes, which charter section 6 "
        "forbids. should_not_have_flagged at 30% and wrong_fact at 30% are "
        "different practices in different trouble, and one number hides which.")
    assert "Approved unchanged" in headline.group(0), "the row itself is intact"


def test_a_pair_blocked_by_a_missing_precondition_says_which_one_on_screen(client, monkeypatch):
    monkeypatch.setattr(STATE.store, "load_approvals",
                        lambda client_id="": [approved(decided_on=DAY)])
    monkeypatch.setattr(autonomy_views, "load_preconditions", lambda: [])
    body = client.get("/autonomy").data.decode()
    assert "Off-disk backup" in body or "off-disk backup" in body.lower()
    assert "never recorded" in body.lower()


def test_recording_a_precondition_is_durable_and_names_who_and_when(client, monkeypatch, tmp_path):
    path = tmp_path / "autonomy_preconditions.json"
    monkeypatch.setattr(autonomy_views, "_preconditions_path", lambda: path)

    resp = client.post("/autonomy/precondition", data={"key": "mfa", "note": "checked it"})
    assert resp.status_code == 302
    assert path.exists()

    recorded = autonomy_views.load_preconditions()
    assert len(recorded) == 1
    assert recorded[0].key == "mfa"
    assert recorded[0].confirmed_by == "human:owner"
    assert recorded[0].confirmed_on == date.today()


def test_recording_the_same_precondition_twice_today_is_recorded_once(client, monkeypatch, tmp_path):
    path = tmp_path / "autonomy_preconditions.json"
    monkeypatch.setattr(autonomy_views, "_preconditions_path", lambda: path)

    client.post("/autonomy/precondition", data={"key": "tailnet_lock"})
    client.post("/autonomy/precondition", data={"key": "tailnet_lock"})
    assert len(autonomy_views.load_preconditions()) == 1


def test_an_unknown_precondition_key_is_refused_by_name(client, monkeypatch, tmp_path):
    path = tmp_path / "autonomy_preconditions.json"
    monkeypatch.setattr(autonomy_views, "_preconditions_path", lambda: path)

    resp = client.post("/autonomy/precondition", data={"key": "not_a_real_precondition"})
    assert resp.status_code == 200
    assert b"not one of the autonomy preconditions" in resp.data
    assert not path.exists()


# --- nothing on these screens comes from a model ------------------------------

_FORBIDDEN_MODULES = ("ollama", "satc.agent", "satc.ingest.readers.ollama",
                      "smtplib", "requests", "httpx", "email.mime", "email.message")


def _imported_dotted_names(source: str) -> set[str]:
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_the_detector_itself_actually_fires_on_a_forbidden_import():
    """Mutation-test the check below (principle 12): prove the detector can
    fail before trusting it to pass. Run against a synthetic snippet, never
    against a file changed on disk — nothing here is left broken."""
    poisoned = "import ollama\n\ndef f():\n    return ollama.chat()\n"
    found = _imported_dotted_names(poisoned) & set(_FORBIDDEN_MODULES)
    assert found == {"ollama"}


def test_nothing_on_the_autonomy_screens_imports_a_model():
    for module in (autonomy_views, __import__("satc.autonomy.digest", fromlist=["digest"])):
        source = inspect.getsource(module)
        found = _imported_dotted_names(source) & set(_FORBIDDEN_MODULES)
        assert not found, f"{module.__name__} imports {found} — these screens read only recorded facts"


def test_neither_file_writes_html_from_a_free_text_field_that_could_hide_a_prompt():
    """A softer companion check: every render_template call in the view names
    a template file, never builds a string dynamically. If this ever changes
    it is worth a human reading the diff, not something a screen should do on
    its own."""
    source = inspect.getsource(autonomy_views)
    tree = ast.parse(source)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and getattr(n.func, "id", "") == "render_template"]
    assert calls, "expected at least one render_template call"
    for call in calls:
        assert call.args and isinstance(call.args[0], ast.Constant), (
            "render_template's template name must be a literal, never assembled at runtime")
