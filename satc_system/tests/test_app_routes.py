"""A net under the whole app: walk every GET route and assert it renders.

Written BEFORE the schema reset, on purpose. The existing suite exercises about
five of ~35 routes, so the two failure modes a rename actually causes are
invisible to it:

  * ``url_for`` BuildError when an endpoint moves — a hard 500 nothing catches;
  * Jinja ``Undefined`` when an attribute is renamed — which is *silently falsy*,
    so a template renders 200 with the wrong answer rather than failing.

``engagements.html`` and ``engagement_detail.html`` are the sharp cases: neither
is rendered by any existing test, and both count completed tasks with
``selectattr('completed')``. Against a status string that is any non-empty value,
``selectattr`` counts everything as done — a 200 with a wrong number, which is
the worst kind of failure.

This file does not assert correctness. It asserts the app is not on fire, which
is the thing a reset needs and did not have.
"""

from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def _sample_values() -> dict[str, str]:
    """Real ids from the seeded store, so routes hit their populated path."""
    clients = STATE.client_choices()
    client_id = clients[0][0] if clients else "SATC-001000"
    requested = STATE.requested_items()
    engagements = STATE.intake_engagements()
    workflows = STATE.all_workflows()
    fields = STATE.gate.all_fields()
    return {
        "client_id": client_id,
        "request_id": requested[0].request_id if requested else "REQ-0001",
        "engagement_id": engagements[0].engagement_id if engagements else "ENG-1",
        "task_id": "TASK-1",
        "key": workflows[0].key if workflows else "personal_1040_core",
        "field_id": fields[0].field_id if fields else "f1",
        "status": "Received",
        "action": "confirm",
    }


def _get_routes(app) -> list[tuple[str, str]]:
    """Every GET-able rule, with its converters filled from live state."""
    values = _sample_values()
    out: list[tuple[str, str]] = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or "GET" not in rule.methods:
            continue
        try:
            filled = {arg: values[arg] for arg in rule.arguments}
        except KeyError:                      # a converter this test doesn't know
            continue
        out.append((rule.endpoint, rule.rule.format(**{k: v for k, v in filled.items()})
                    if not rule.arguments else _build(rule, filled)))
    return out


def _build(rule, filled: dict[str, str]) -> str:
    path = rule.rule
    for arg, value in filled.items():
        for converter in (f"<{arg}>", f"<path:{arg}>", f"<string:{arg}>", f"<int:{arg}>"):
            path = path.replace(converter, str(value))
    return path


def test_the_walk_actually_covers_the_app(app):
    """A net that silently covers nothing is worse than no net (doctrine rule 10)."""
    routes = _get_routes(app)
    assert len(routes) >= 20, f"only {len(routes)} GET routes resolved — the walk is broken"
    endpoints = {e for e, _ in routes}
    # The two templates no other test renders — the whole reason this file exists.
    assert "intake.engagements" in endpoints
    assert "intake.engagement_detail" in endpoints


@pytest.mark.parametrize("endpoint,path", _get_routes(create_app()))
def test_every_get_route_renders(client, endpoint, path):
    """No 500. Redirects and 400s are legitimate answers; a stack trace is not."""
    resp = client.get(path, follow_redirects=True)
    assert resp.status_code < 500, (
        f"{endpoint} ({path}) returned {resp.status_code}\n"
        f"{resp.data[:600].decode('utf-8', 'replace')}")


# --- the silent sites the reset will move ------------------------------------

def test_pipeline_counts_returns_the_keys_the_dashboard_reads():
    """dashboard.html does pipeline.get('In prep', 0) — a rename yields a silent 0."""
    counts = STATE.pipeline_counts()
    assert isinstance(counts, dict)
    assert counts, "the seeded store should produce at least one pipeline bucket"
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in counts.items())


def test_outstanding_rows_expose_what_every_page_reads():
    """AppState.outstanding() is injected into EVERY page by a context processor,
    and dashboard.html reads .client_id / .doc_type straight off it in Jinja."""
    for row in STATE.outstanding():
        assert hasattr(row, "client_id")
        assert hasattr(row, "doc_type")
        assert hasattr(row, "request_text")
        assert row.is_open


def test_both_evidence_registers_are_populated_in_the_seeded_practice():
    """An empty register silently produces a chase with nothing in it."""
    assert STATE.requested_items(), "seeded fixtures should hold open requests"
    assert STATE.received_documents(), "seeded fixtures should hold arrivals"


def test_comms_still_finds_outstanding_and_received_for_the_demo_client():
    """The end-to-end guard on the evidence split: whatever DocStatus becomes,
    the chase email must still distinguish what is outstanding from what arrived."""
    from satc.comms import build_context

    client_id = STATE.client_choices()[0][0]
    values = build_context(
        client_id=client_id,
        requested=[r for r in STATE.requested_items() if r.client_id == client_id],
        received=[d for d in STATE.received_documents() if d.client_id == client_id],
        tax_year=2024)
    assert values.get("missing_items") or values.get("received_items"), \
        "neither outstanding nor received items survived — the register lost its split"
