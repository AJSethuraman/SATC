"""Exactly one nav item is lit, on every screen.

D7, FROM THE WALK OF 5 SEPTEMBER 2026. On `/intake`, `/intake/new` and
`/intake/plan`, **both Intake and Engagements** carried the active background and
the gold left bar. A person cannot tell from the nav which screen they are on.

The cause: the nav decided from the page's `title`.

    class="{{ 'active' if title=='Intake' }}"                        Intake
    class="{{ 'active' if title in ['Engagements','New client','Intake'] }}"

and `title="Intake"` belongs to FOUR screens across two nav items -- the
document-reading Intake screen in `server.py`, plus `/intake/new`,
`/intake/plan` and `/intake/organizer` in `intake_views.py`. A title is a
heading for a person to read. It was never an identifier, and asking it to be
one produced two answers to a question that has one.

The same guesswork was visible elsewhere in that nav: `'nvoice' in title`, spelt
without its leading letter so it would catch both "Invoices" and "Invoice
2026-0001". It works. It is a substring search over prose.

A route knows exactly which screen it is, and cannot be two things at once.

THIS FILE'S REAL JOB IS THE SWEEP: every GET route in the app, asserted to light
exactly one item. The walk found this on three screens by looking at three
screens; the same defect on a fourth would have needed a fourth pair of eyes.
"""
from __future__ import annotations

import re

import pytest

from satc.app import navigation
from satc.app.server import create_app


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def _get_routes(app):
    """Every GET route with no URL parameters -- the ones a nav can be checked on.

    Parameterised routes (`/clients/<client_id>`) are exercised through
    `navigation.active` below instead, by endpoint, so they are not skipped.
    """
    out = []
    for rule in app.url_map.iter_rules():
        if "static" in rule.endpoint or rule.arguments:
            continue
        if "GET" not in (rule.methods or set()):
            continue
        out.append((rule.endpoint, str(rule)))
    return sorted(out, key=lambda p: p[1])


def _lit(body):
    """The nav links carrying `active`, by their visible text."""
    nav = re.search(r"<nav class=\"nav\">(.*?)</nav>", body, re.S)
    if not nav:
        return None
    return [re.sub(r"<[^>]+>", "", a).strip()
            for a in re.findall(r"<a [^>]*class=\"active\"[^>]*>.*?</a>", nav.group(1), re.S)]


# ── the denominator ───────────────────────────────────────────────────────────

def test_there_are_routes_to_sweep(app):
    routes = _get_routes(app)
    assert len(routes) > 12, f"only {len(routes)} routes; the sweep proves little"


def test_the_intake_screens_are_among_them(app):
    """The three the walk actually found. Named, so a refactor that drops them
    from the sweep is visible rather than silent."""
    paths = {path for _, path in _get_routes(app)}
    assert {"/intake", "/intake/new", "/intake/plan"} <= paths


# ── the defect, on the screens it was found on ────────────────────────────────

@pytest.mark.parametrize("path", ["/intake", "/intake/new", "/intake/plan"])
def test_the_intake_screens_light_exactly_one_item(client, path):
    """THE DEFECT. Both Intake and Engagements were lit on all three."""
    body = client.get(path).get_data(as_text=True)
    lit = _lit(body)
    assert lit is not None, "no nav on the page at all"
    assert len(lit) == 1, f"{path} lights {lit}"


def test_intake_lights_intake_and_the_others_light_engagements(client):
    """Not just "one" -- the RIGHT one. A nav that lights a single wrong item
    passes the count and still lies."""
    assert _lit(client.get("/intake").get_data(as_text=True)) == ["⤓ Intake"]
    for path in ("/intake/new", "/intake/plan"):
        assert _lit(client.get(path).get_data(as_text=True)) == ["☑ Engagements"], path


# ── the sweep ─────────────────────────────────────────────────────────────────

def test_every_screen_lights_exactly_one_item(app, client):
    """What the walk could not do by looking: all of them, at once."""
    wrong = []
    for endpoint, path in _get_routes(app):
        response = client.get(path)
        if response.status_code >= 400:
            continue          # a route that refuses is not a nav question
        if "html" not in (response.mimetype or ""):
            continue          # a PDF or a spreadsheet has no nav to check
        lit = _lit(response.get_data(as_text=True))
        if lit is None:
            continue          # a print view or a download has no nav
        if len(lit) != 1:
            wrong.append(f"{path} ({endpoint}) lights {lit}")
    assert not wrong, "\n".join(wrong)


# ── the table itself ──────────────────────────────────────────────────────────

def test_every_endpoint_in_the_app_is_placed(app):
    """A route nobody placed lights nothing, which is honest -- but it should be
    a decision, not an oversight. This names the ones that fell through."""
    unplaced = sorted(
        rule.endpoint for rule in app.url_map.iter_rules()
        if "static" not in rule.endpoint and not navigation.active(rule.endpoint))
    assert not unplaced, f"endpoints belonging to no nav item: {unplaced}"


def test_a_route_that_does_not_exist_lights_nothing():
    """The control. Guessing would put us back where D7 started."""
    assert navigation.active("nonesuch.route") == ""
    assert navigation.active(None) == ""


def test_the_client_screens_are_not_swallowed_by_the_intake_blueprint():
    """ORDER IS LOAD-BEARING, and this is the entry that makes it so.

    Several client screens live on the `intake.` blueprint, so the `clients`
    row has to sit above the `engagements` prefix. Moving it below turns
    "New client" into an Engagements screen with nothing to say so.
    """
    for endpoint in ("intake.new_client", "intake.client_start",
                     "intake.quick_add_client", "intake.import_clients"):
        assert navigation.active(endpoint) == "clients", endpoint
    assert navigation.active("intake.engagements") == "engagements"


def test_the_bare_intake_screen_is_not_the_intake_blueprint():
    """The endpoint `intake` and the blueprint `intake.` are different things,
    and reading one as the other is the whole defect."""
    assert navigation.active("intake") == "intake"
    assert navigation.active("intake.new_engagement") == "engagements"
