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


def _plausible(q):
    """Any answer this question will accept -- the tests below care about
    reaching a later question, not about what the earlier ones said."""
    if q.get("options"):
        return [q["options"][0]["value"]] if q["type"] == "multi" \
            else q["options"][0]["value"]
    return 1 if q["type"] == "number" else "x"


def answer_next(client, sid, value):
    """Answer whichever question is actually next, and return its id.

    The tests used to hard-code `client_full_name` as the first question. That
    coupled them to the schema's ORDER rather than its behaviour, so moving
    `federal_form` to the front -- which is what makes the branching work at
    all -- broke four tests that were not testing ordering.
    """
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    qid = state["question"]["id"]
    client.post(f"/interview/{sid}", json={"answer": value}, headers=JSON)
    return qid


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
    first = client.get(f"/interview/{sid}", headers=JSON).get_json()["question"]
    assert first["required"], "this test needs a required question to refuse"
    r = client.post(f"/interview/{sid}", json={"answer": ""}, headers=JSON)
    assert r.status_code == 400
    assert r.get_json()["question"] == first["id"]


def test_the_claim_is_offered_and_says_whether_it_can_be_taken(client):
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    sid = client.post("/interview", json={"lead": lead},
                      headers=JSON).get_json()["draft"]
    # Walk to the first question the website actually made a claim about.
    for _ in range(12):
        state = client.get(f"/interview/{sid}", headers=JSON).get_json()
        if state["question"]["id"] == "client_email":
            break
        answer_next(client, sid, _plausible(state["question"]))
    assert state["question"]["id"] == "client_email"
    assert state["claim"] == "dreyes@example.com" and state["claim_acceptable"] is True


def test_accepting_the_claim_records_it(client):
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    sid = client.post("/interview", json={"lead": lead},
                      headers=JSON).get_json()["draft"]
    for _ in range(12):
        state = client.get(f"/interview/{sid}", headers=JSON).get_json()
        if state["question"]["id"] == "client_email":
            break
        answer_next(client, sid, _plausible(state["question"]))
    client.post(f"/interview/{sid}", json={"accept": True}, headers=JSON)
    assert web.load_draft(client.store, sid)["answers"]["client_email"] == "dreyes@example.com"


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
    qid = answer_next(client, sid, "1040")
    assert web.load_draft(client.store, sid)["answers"][qid]
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


# ── the two doors a sitting starts from ───────────────────────────────────

import leads  # noqa: E402


def _workbook(tmp_path):
    """A one-row workbook, written the way the firm's export writes one."""
    openpyxl = pytest.importorskip("openpyxl")
    from tests.test_leads import HEADER, ROW
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    ws.append(ROW)
    path = tmp_path / "leads.xlsx"
    wb.save(path)
    return path


def test_the_leads_page_shows_what_a_prospect_said(tmp_path):
    import web
    app = web.create_app(store=tmp_path / "store",
                         leads_workbook=_workbook(tmp_path))
    body = app.test_client().get("/leads").get_data(as_text=True)
    assert "Marcus Ellwood" in body
    # In the words the client saw, not the codes the form posts.
    assert "Rental property" in body and "individual_tax" not in body


def test_a_sitting_can_start_from_a_workbook_row(tmp_path):
    import web
    app = web.create_app(store=tmp_path / "store",
                         leads_workbook=_workbook(tmp_path))
    c = app.test_client()
    r = c.post("/interview", data={"lead_index": "0"})
    assert r.status_code == 302
    page = c.get(r.headers["Location"]).get_data(as_text=True)
    # THE BUTTON NAMES THE ANSWER IT WILL GIVE. It used to read "Accept the
    # claim", which is our word for it rather than a preparer's, and which
    # this test could satisfy without the lead's actual answer ever reaching
    # the page. Asserting on the VALUE proves the prefill arrived, which is
    # what the test was always for.
    assert "1040" in page, (
        "the sitting started blank; the lead's answer did not reach it"
    )
    assert "Use &ldquo;1040&rdquo;" in page, (
        "the prefill is on the page but there is no one-press way to take it"
    )
    assert "Accept the claim" not in page, (
        "our vocabulary is back on a screen a preparer reads"
    )


def test_a_sitting_can_start_from_a_phone_call(tmp_path):
    """"they may just give us contact info" — that is a whole lead."""
    import web
    app = web.create_app(store=tmp_path / "store")
    r = app.test_client().post("/interview",
                               data={"by_hand": "1", "name": "Priya Raman"})
    assert r.status_code == 302 and "/interview/" in r.headers["Location"]


def test_a_manual_lead_with_nothing_in_it_is_refused(tmp_path):
    """It used to fall through and start a blank sitting, which looks like it
    worked."""
    import web
    app = web.create_app(store=tmp_path / "store")
    r = app.test_client().post("/interview",
                               data={"by_hand": "1", "name": "", "email": ""})
    assert "/leads" in r.headers["Location"]
    assert "nobody+to+come+back+to" in r.headers["Location"]


def test_a_missing_workbook_is_not_an_error(tmp_path):
    """The firm may not have exported one yet, and the manual door still
    works."""
    import web
    app = web.create_app(store=tmp_path / "store",
                         leads_workbook=tmp_path / "nope.xlsx")
    body = app.test_client().get("/leads").get_data(as_text=True)
    # The fact, not the wording: the by-hand form is on the page and posts.
    assert "name=by_hand" in body
    assert "by phone" in body


# ── the price editor ──────────────────────────────────────────────────────

def test_the_price_list_shows_every_price_and_says_which_are_public(client):
    """The list is the schedule's, and it says which figures a stranger reads.

    Published-vs-withheld is the difference between changing a number and
    changing satcllp.com, and it belongs before the click rather than after.
    """
    body = client.get("/prices").get_data(as_text=True)
    assert "The hourly rate" in body
    assert "Published" in body and "Withheld" in body
    assert "base.1040.tiers.standard" in body


def test_a_preview_shows_what_moves_and_writes_nothing(client, tmp_path, monkeypatch):
    """The reason a form beats editing YAML: the file cannot show you what a
    number moves. And a preview that writes is not a preview."""
    import registry_editor
    before = registry_editor.SCHEDULE.read_text(encoding="utf-8")
    r = client.post("/prices/base.1040.tiers.business",
                    data={"amount": "560", "preview": "1"},
                    headers={"Accept": "application/json"})
    assert r.status_code == 200
    report = r.get_json()
    assert report["saved"] is False
    assert report["from"] == 500 and report["to"] == 560
    assert report["sample_total_before"] != report["sample_total_after"]
    assert registry_editor.SCHEDULE.read_text(encoding="utf-8") == before


def test_a_price_that_is_not_a_number_is_refused_by_the_form(client):
    """A browser must not be able to save something a script could not."""
    r = client.post("/prices/basis.rate", data={"amount": "banana"},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400
    assert "whole number" in r.get_json()["error"]


def test_a_price_that_does_not_exist_is_a_404_not_a_guess(client):
    assert client.get("/prices/per_unit.moon_landing").status_code == 404


# ── going back ────────────────────────────────────────────────────────────
#
# The one thing a preparer sitting with a client will need in the first hour
# and the browser had no route for: the client corrects themselves. Nothing
# below deletes an answer to make room -- the cursor moves, the old answer is
# shown as it stands, and re-answering runs the same `Interview.answer` the
# forward path runs.

def test_back_returns_to_the_previous_question_with_the_answer_shown(client):
    """What was typed comes back with it. A blank form asks a preparer to
    remember what they said, in front of the person who said it."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    first = client.get(f"/interview/{sid}", headers=JSON).get_json()["question"]
    client.post(f"/interview/{sid}", json={"answer": _plausible(first)},
                headers=JSON)
    second = client.get(f"/interview/{sid}", headers=JSON).get_json()["question"]
    assert second["id"] != first["id"]

    client.post(f"/interview/{sid}/back", headers=JSON)
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert state["question"]["id"] == first["id"]
    assert state["revising"] is True

    page = client.get(f"/interview/{sid}", headers=HTML).get_data(as_text=True)
    assert str(_plausible(first)) in page
    assert "Save the change" in page


def test_back_on_the_first_question_is_a_no_op_not_a_crash(client):
    """There is nowhere behind question one, and the control is not offered."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    page = client.get(f"/interview/{sid}", headers=HTML).get_data(as_text=True)
    assert "&larr; Back" not in page

    r = client.post(f"/interview/{sid}/back", headers=JSON)
    assert r.status_code == 200
    assert client.get(f"/interview/{sid}", headers=JSON).get_json()["revising"] \
        is False


def test_changing_an_answer_keeps_everything_asked_after_it(client, answers):
    """Correcting one thing must not throw away the rest of the sitting."""
    sid = drive(client, answers)
    before = client.get(f"/interview/{sid}", headers=JSON).get_json()["answers"]

    client.post(f"/interview/{sid}/back", json={"to": "client_city"},
                headers=JSON)
    client.post(f"/interview/{sid}", json={"answer": "Twinsburg"}, headers=JSON)

    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert state["complete"] is True, "the sitting should resume where it was"
    assert state["answers"]["client_city"] == "Twinsburg"
    assert set(state["answers"]) == set(before)


def test_changing_an_answer_prunes_what_it_hides(client, answers):
    """The same pruning the forward path does. `spouse_name` has no place on a
    return that is no longer joint, and leaving it would carry a name into a
    document with nowhere to put it."""
    sid = drive(client, answers)
    assert client.get(f"/interview/{sid}", headers=JSON) \
        .get_json()["answers"]["spouse_name"] == "Maria Reyes"

    client.post(f"/interview/{sid}/back", json={"to": "joint_return"},
                headers=JSON)
    client.post(f"/interview/{sid}", json={"answer": "no"}, headers=JSON)

    now = client.get(f"/interview/{sid}", headers=JSON).get_json()["answers"]
    assert now["joint_return"] == "no"
    assert "spouse_name" not in now


def test_a_stale_cursor_hands_the_sitting_back_rather_than_failing(client,
                                                                   answers):
    """A cursor can go stale in one keystroke. Pointing at a question that has
    since been pruned must not strand the sitting on a 500."""
    sid = drive(client, answers)
    client.post(f"/interview/{sid}/back", json={"to": "spouse_name"},
                headers=JSON)
    # Reach into the draft and pull `spouse_name` out from under the cursor,
    # exactly as answering `joint_return: no` would.
    path = web.draft_path(client.store, sid)
    draft = json.loads(path.read_text(encoding="utf-8"))
    assert draft["at"] == "spouse_name"
    draft["answers"] = {k: v for k, v in draft["answers"].items()
                        if k != "spouse_name"}
    draft["answers"]["joint_return"] = "no"
    path.write_text(json.dumps(draft), encoding="utf-8")

    state = client.get(f"/interview/{sid}", headers=JSON)
    assert state.status_code == 200
    got = state.get_json()
    assert got.get("question", {}).get("id") != "spouse_name", (
        "a cursor on a pruned question must not hold the sitting there"
    )
    assert "spouse_name" not in got["answers"]


def test_the_review_offers_a_way_back_to_every_answer(client, answers):
    """The review was the one page that showed a preparer a wrong answer and
    gave them nothing to do about it."""
    sid = drive(client, answers)
    page = client.get(f"/interview/{sid}", headers=HTML).get_data(as_text=True)
    given = client.get(f"/interview/{sid}", headers=JSON).get_json()["answers"]
    # Everything a person said, and nothing the software worked out for them:
    # `federal_schedules` is derived, and offering to edit it would be
    # offering to edit arithmetic.
    derived = {q["id"] for _, q in iv.all_questions(iv.load_schema())
               if q.get("derived")}
    assert derived & set(given), "the sample should exercise a derived answer"
    assert page.count("Change</button>") == len(set(given) - derived), (
        "every answer a person gave should be reachable from the review"
    )
    assert f"/interview/{sid}/back" in page


def test_back_will_not_jump_to_a_question_nobody_answered(client, answers):
    """`to` comes off a form in a browser. It gets checked against the
    sitting's own history, not trusted."""
    sid = drive(client, answers)
    r = client.post(f"/interview/{sid}/back", json={"to": "not_a_question"},
                    headers=JSON)
    assert r.get_json()["at"] in set(answers)


def test_never_mind_puts_the_sitting_back_where_it_was(client):
    """Stepping back and finding nothing wrong is the common case, and the way
    out of it must not be pressing Back until something happens."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    first = client.get(f"/interview/{sid}", headers=JSON).get_json()["question"]
    client.post(f"/interview/{sid}", json={"answer": _plausible(first)},
                headers=JSON)
    second = client.get(f"/interview/{sid}", headers=JSON).get_json()["question"]

    client.post(f"/interview/{sid}/back", headers=JSON)
    page = client.get(f"/interview/{sid}", headers=HTML).get_data(as_text=True)
    assert "Never mind" in page

    client.post(f"/interview/{sid}/back", json={"resume": True}, headers=JSON)
    state = client.get(f"/interview/{sid}", headers=JSON).get_json()
    assert state["question"]["id"] == second["id"]
    assert state["revising"] is False
    kept = json.loads(web.draft_path(client.store, sid)
                      .read_text(encoding="utf-8"))["answers"]
    assert kept[first["id"]] == _plausible(first), (
        "backing out of a correction must not change the answer"
    )


def _controls_by_form(html_text):
    """{form action: [control names]} -- which form each control actually
    posts to, rather than which one it looks like it sits under."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.here = None
            self.forms = {}

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "form":
                self.here = a.get("action", "")
                self.forms.setdefault(self.here, [])
            elif tag in ("input", "button", "textarea", "select") \
                    and self.here is not None:
                self.forms[self.here].append(a.get("name") or f"<{tag}>")

        def handle_endtag(self, tag):
            if tag == "form":
                self.here = None

    p = P()
    p.feed(html_text)
    return p.forms


def test_the_way_out_of_a_correction_carries_nothing_with_it(tmp_path):
    """Forms do not nest. `Never mind` sits under the answer's own buttons, and
    the first cut of it swallowed them -- the one-press `Use "1040"` ended up
    inside the back form, where `accept=1` would have stepped the sitting
    somewhere nobody asked for. Driven from a lead so the claim is on the page:
    without one there is no accept button to swallow, and the test would pass
    over the bug it exists for."""
    import web
    app = web.create_app(store=tmp_path / "store",
                         leads_workbook=_workbook(tmp_path))
    c = app.test_client()
    sid = c.post("/interview", data={"lead_index": "0"}) \
        .headers["Location"].rsplit("/", 1)[-1]
    c.post(f"/interview/{sid}", data={"accept": "1"})
    c.post(f"/interview/{sid}/back")

    page = c.get(f"/interview/{sid}").get_data(as_text=True)
    assert "Use &ldquo;1040&rdquo;" in page, "the claim is not on the page"
    forms = _controls_by_form(page)
    back = forms[f"/interview/{sid}/back"]
    assert set(back) == {"resume", "<button>"}, back
    assert "answer" in forms[f"/interview/{sid}"]
    assert "accept" in forms[f"/interview/{sid}"]


def test_the_review_reads_in_the_words_on_the_screen(client, answers):
    """The last page anybody checks before a client is billed was printing the
    software's key for an option -- `missing_records` -- rather than the label
    a preparer ticked, and showing an answered-with-nothing question as an
    empty cell, which reads as nobody having answered it."""
    sid = drive(client, dict(answers) | {"red_flags": ["missing_records"]})
    page = client.get(f"/interview/{sid}", headers=HTML).get_data(as_text=True)

    want = next(o["label"] for _, q in iv.all_questions(iv.load_schema())
                if q["id"] == "red_flags"
                for o in q["options"] if o["value"] == "missing_records")
    assert want in page and "missing_records" not in page

    given = client.get(f"/interview/{sid}", headers=JSON).get_json()["answers"]
    empty = sum(1 for v in given.values() if v in (None, "", []))
    assert empty, "the sample should leave something blank"
    assert page.count("left blank") == empty
