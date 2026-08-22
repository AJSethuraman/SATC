"""The web front door, and the proof it enforces what the CLI enforces.

The constraint: **every process is doable by a human and replicable by
automation, under the same controls.** A browser and a script must not be able
to reach different outcomes from the same answers, and neither may skip a gate.

The way that is guaranteed here is structural rather than aspirational: one
handler answers both, content-negotiated, sharing every line up to rendering.
These tests hold that structure in place -- including one that reads `web.py`'s
own source and fails if a decision is ever written into it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import intake  # noqa: E402
import interview as iv  # noqa: E402
import web  # noqa: E402

SAMPLES = ROOT / "samples"
JSON = {"Accept": "application/json"}
HTML = {"Accept": "text/html"}


@pytest.fixture
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path):
    app = web.create_app(store=tmp_path)
    app.config.update(TESTING=True)
    with app.test_client() as c:
        c.store = tmp_path
        yield c


def drive(client, answers):
    """Run a whole interview through the HTTP API, as automation would."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    while True:
        state = client.get(f"/interview/{sid}", headers=JSON).get_json()
        if state["complete"]:
            return sid
        qid = state["question"]["id"]
        client.post(f"/interview/{sid}", json={"answer": answers.get(qid)},
                    headers=JSON)


# ── the same answers reach the same outcome by either door ────────────────

@pytest.mark.parametrize("mutate,expected", [
    ({}, "created"),
    ({"red_flags": ["assurance_needed"]}, "refused"),
    ({"decision": "no"}, "declined"),
])
def test_the_browser_and_the_core_agree(client, answers, mutate, expected):
    """The claim the whole arrangement rests on."""
    a = dict(answers) | mutate
    sid = drive(client, a)
    got = client.post(f"/interview/{sid}/finish", headers=JSON).get_json()

    direct = intake.finish(a, store=client.store / "direct")
    assert got["status"] == direct.status == expected


def test_a_hard_no_creates_nothing_through_the_web(client, answers):
    sid = drive(client, dict(answers) | {"red_flags": ["assurance_needed"]})
    body = client.post(f"/interview/{sid}/finish", headers=JSON).get_json()
    assert body["status"] == "refused" and body["ref"] is None
    assert not (client.store / "2026-0001").exists(), (
        "the browser must not be able to create what the terminal refuses"
    )


def test_the_web_can_override_a_hard_no_only_deliberately(client, answers):
    sid = drive(client, dict(answers) | {"red_flags": ["assurance_needed"]})
    body = client.post(f"/interview/{sid}/finish", json={"override": True},
                       headers=JSON).get_json()
    assert body["status"] == "created" and body["overridden"] is True


def test_html_and_json_reach_the_same_verdict(client, answers):
    """Same handler, two renderings. The browser is shown the refusal it got."""
    a = dict(answers) | {"red_flags": ["assurance_needed"]}
    sid_json = drive(client, a)
    sid_html = drive(client, a)

    as_json = client.post(f"/interview/{sid_json}/finish", headers=JSON).get_json()
    as_html = client.post(f"/interview/{sid_html}/finish", headers=HTML)

    assert as_json["status"] == "refused"
    assert b"HARD NO" in as_html.data and b"Nothing was written" in as_html.data


# ── the interview itself behaves the same ─────────────────────────────────

def test_branching_works_over_http(client, answers):
    """A question hidden by an answer is never served."""
    sid = drive(client, dict(answers) | {"joint_return": "no"})
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert "spouse_name" not in state["answers"]


def test_a_required_question_is_refused_not_skipped(client):
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    r = client.post(f"/interview/{sid}", json={"answer": ""}, headers=JSON)
    assert r.status_code == 400
    assert "client_full_name" in r.get_json()["question"]


def test_the_claim_is_offered_and_says_whether_it_can_be_taken(client):
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    sid = client.post("/interview", json={"lead": lead},
                      headers=JSON).get_json()["draft"]
    client.post(f"/interview/{sid}", json={"answer": "Mr. and Mrs. Daniel Reyes"},
                headers=JSON)
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert state["question"]["id"] == "client_letter_name"
    assert state["claim"] == "Dan" and state["claim_acceptable"] is True


def test_accepting_the_claim_records_it(client):
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    sid = client.post("/interview", json={"lead": lead},
                      headers=JSON).get_json()["draft"]
    client.post(f"/interview/{sid}", json={"answer": "Mr. and Mrs. Daniel Reyes"},
                headers=JSON)
    client.post(f"/interview/{sid}", json={"accept": True}, headers=JSON)
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert web.load_draft(client.store, sid)["answers"]["client_letter_name"] == "Dan"


def test_an_unacceptable_claim_is_marked_as_such(client):
    """`prior_return_available` gets 'unsure', which is not one of its options."""
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    q = iv.Interview().question("prior_return_available")
    claim = iv.prefill_for(q, lead)
    assert claim == "unsure" and not iv.prefill_is_answerable(q, claim)


# ── drafts: the thing the terminal could not do ───────────────────────────

def test_a_half_finished_interview_survives(client, answers):
    """Closing the laptop mid-call must not lose the consultation."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    client.post(f"/interview/{sid}", json={"answer": "Mr. and Mrs. Daniel Reyes"},
                headers=JSON)
    assert web.load_draft(client.store, sid)["answers"]["client_full_name"]
    assert sid in client.get("/", headers=JSON).get_json()["drafts"]


def test_a_created_engagement_clears_its_draft(client, answers):
    sid = drive(client, answers)
    client.post(f"/interview/{sid}/finish", headers=JSON)
    assert client.get("/", headers=JSON).get_json()["drafts"] == []


def test_a_refusal_keeps_the_draft(client, answers):
    """Refused work is not lost work -- the notes may still be wanted."""
    sid = drive(client, dict(answers) | {"red_flags": ["assurance_needed"]})
    client.post(f"/interview/{sid}/finish", headers=JSON)
    assert sid in client.get("/", headers=JSON).get_json()["drafts"]


def test_a_draft_id_cannot_escape_the_store(client):
    for bad in ("../secret", "a/b", "..%2F..%2Fetc"):
        assert client.get(f"/interview/{bad}", headers=JSON).status_code in (400, 404)


# ── the structural guarantee ──────────────────────────────────────────────

def test_the_web_module_decides_nothing_of_its_own():
    """Read web.py. A rule written here is a rule the CLI does not have.

    `intake.finish` may be called; the decisions inside it may not be
    re-implemented.
    """
    src = (ROOT / "web.py").read_text(encoding="utf-8")
    for smell in ("engagements.create(", "pricing.price(", "iv.compose(",
                  'decision") != ', "RETURN_TYPE"):
        assert smell not in src, (
            f"web.py contains {smell!r} -- that decision belongs in intake, "
            f"or the browser and the CLI will drift apart"
        )
    assert src.count("intake.finish(") == 1, (
        "exactly one delegation to the core, so there is one way through"
    )


def test_every_route_answers_both_a_human_and_a_script(client, answers):
    """Not one JSON API and one HTML app -- one of each route."""
    sid = drive(client, answers)
    ref = client.post(f"/interview/{sid}/finish", headers=JSON).get_json()["ref"]
    for path in ("/", f"/engagement/{ref}"):
        as_html = client.get(path, headers=HTML)
        as_json = client.get(path, headers=JSON)
        assert as_html.status_code == as_json.status_code == 200
        assert as_html.data.startswith(b"<!doctype html")
        assert as_json.is_json
