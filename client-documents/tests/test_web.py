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
    """Any answer this question will accept AND that does not end the sitting.

    These tests care about reaching a later question, not about what the
    earlier ones said. So a HARD NO option is never picked: the refusal
    question moved to the front of the interview on 2 September 2026 and now
    falls inside the walk, its first option is "Needs assurance work", and
    ticking that correctly ends the sitting -- leaving these tests reading a
    `question` key that is not there. Skipping the blockers keeps the helper
    doing the one job it says it does."""
    options = [o for o in (q.get("options") or []) if not o.get("hard_no")]
    if options:
        return [options[0]["value"]] if q["type"] == "multi" \
            else options[0]["value"]
    if q.get("options"):
        # Every option is a blocker: answering nothing is the only way past.
        return [] if q["type"] == "multi" else ""
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
    """A HARD NO now ends the sitting where it is ticked, so the review screen
    the override is pressed from is showing four answers out of thirty. The
    override means "the list is wrong" — so the questions RESUME, and only then
    can the engagement be created. Creating from the four would refuse anyway,
    and tell the preparer the wrong reason."""
    a = dict(answers) | {"red_flags": ["assurance_needed"]}
    sid = drive(client, a)
    resumed = client.post(f"/interview/{sid}/finish", json={"override": True},
                          headers=JSON).get_json()
    assert resumed.get("resumed") is True, (
        "overriding an unfinished sitting must resume it, not create from it")

    # The rest of the interview, now that the block has been waved through.
    while True:
        state = client.get(f"/interview/{sid}", headers=JSON).get_json()
        if state["complete"]:
            break
        client.post(f"/interview/{sid}",
                    json={"answer": a.get(state["question"]["id"])}, headers=JSON)

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


# ── packaging: the last mile, without a terminal ──────────────────────────
#
# "every process is doable by a human and replicable by automation, under the
# same controls." Packaging was the half of that sentence that was not true: a
# preparer could interview, price and edit the wording in a browser, and then
# had to type a command to get the pack the client actually signs -- which is
# the one step with a BLOCKING gate on it.

import engagements  # noqa: E402
import presend  # noqa: E402


def _an_engagement(client, answers):
    """A real created engagement, through the browser, as a preparer would."""
    sid = drive(client, answers)
    got = client.post(f"/interview/{sid}/finish", headers=JSON).get_json()
    assert got["status"] == "created", got
    return got["ref"]


def _gate_that_blocks(monkeypatch, detail="a sentence the firm deleted is back"):
    """The gate, failing, without pretending to know how to fail it.

    What is under test here is the DOOR -- whether a browser can get past a
    blocked gate -- not the checks, which `test_presend` owns. `sending` and
    `web` both reach the gate through the same module object, so one patch
    covers both doors and neither can quietly use a different one.
    """
    def fake(pack, record, **kw):
        res = presend.Result()
        res.checked.append("no sentence the firm has deleted has come back")
        res.findings.append(presend.Finding(
            check="no sentence the firm has deleted has come back",
            document="SATC Engagement Letter.html", detail=detail))
        return res
    monkeypatch.setattr(presend, "gate", fake)


@pytest.mark.renders
def test_the_browser_can_build_the_pack_the_terminal_builds(client, answers):
    ref = _an_engagement(client, answers)
    got = client.post(f"/engagement/{ref}/package", json={}, headers=JSON)
    assert got.status_code == 200
    body = got.get_json()
    assert body["status"] == "written", body

    import cli
    import packaging
    record = cli.build_record(engagements.load(ref, client.store))
    assert body["documents"] == packaging.documents_for(record), (
        "the browser decided for itself which documents go in the pack"
    )
    pack = client.store / ref / "pack"
    assert (pack / "MANIFEST.json").is_file()
    assert body["written"], "a pack with no files in it reported success"


@pytest.mark.renders
def test_the_browser_cannot_skip_the_gate(client, answers, monkeypatch):
    """The one claim the whole arrangement rests on, at the one step that
    blocks."""
    ref = _an_engagement(client, answers)
    _gate_that_blocks(monkeypatch)

    got = client.post(f"/engagement/{ref}/package", json={}, headers=JSON)
    assert got.status_code == 409
    body = got.get_json()
    assert body["status"] == "refused-gate"
    assert body["blocking"], "it refused without saying what failed"
    assert not (client.store / ref / "pack").exists(), (
        "a blocked gate still wrote a pack"
    )


@pytest.mark.renders
def test_an_override_through_the_browser_is_recorded(client, answers,
                                                     monkeypatch):
    """The firm chose blocking-with-a-logged-override. A gate a browser cannot
    override is a gate a preparer works around by opening a terminal, which is
    the one place nobody is watching -- so the browser has it, and it costs the
    same sentence the terminal charges."""
    ref = _an_engagement(client, answers)
    _gate_that_blocks(monkeypatch)

    nothing = client.post(f"/engagement/{ref}/package",
                          json={"force": True, "reason": "   "}, headers=JSON)
    assert nothing.get_json()["status"] == "no-reason"
    assert not (client.store / ref / "pack").exists()

    said = "client is at the desk; the deleted line is in a quoted excerpt"
    got = client.post(f"/engagement/{ref}/package",
                      json={"force": True, "reason": said}, headers=JSON)
    assert got.get_json()["status"] == "written"
    assert (client.store / ref / "pack" / "MANIFEST.json").is_file()

    logged = engagements.overrides(ref, client.store)
    assert [e for e in logged if e["reason"] == said], logged
    assert logged[-1]["failed"], "the override recorded no failed check"


def test_the_browser_will_not_write_into_somebody_elses_folder(client, answers):
    ref = _an_engagement(client, answers)
    theirs = client.store / ref / "pack"
    theirs.mkdir(parents=True)
    (theirs / "their-notes.txt").write_text("mine", encoding="utf-8")

    got = client.post(f"/engagement/{ref}/package", json={}, headers=JSON)
    assert got.get_json()["status"] == "not-ours"
    assert (theirs / "their-notes.txt").read_text(encoding="utf-8") == "mine"


@pytest.mark.renders
def test_the_failed_checks_come_before_the_green_ones_on_the_page(
        client, answers, monkeypatch):
    """The terminal prints the check list and then the refusal under it. On a
    page that ordering puts the thing you have to act on below a wall of
    green.

    ANCHORED ON STRUCTURE, NOT ON COPY. This looked for the literal string
    `check(s) failed`, and the headline became `2 checks stopped it` when the
    bracket-s plurals went -- so a wording change broke a test about ORDERING,
    which is not what it is here to hold. The refusal block and the table of
    every check are the two things whose order matters; their labels are free
    to improve.
    """
    ref = _an_engagement(client, answers)
    _gate_that_blocks(monkeypatch)
    page = client.post(f"/engagement/{ref}/package",
                       data={}).get_data(as_text=True)
    assert "class=hardno" in page, "nothing on the page says it was refused"
    assert "plain checks" in page, "the table of every check is missing"
    assert page.index("class=hardno") < page.index("plain checks"), \
        "the wall of green came before the thing you have to act on"
    assert "name=reason" in page, "no way to override, and no way to ask why"


def test_web_decides_nothing_about_packaging(client):
    """Same rule the interview lives under: `sending.build` may be called from
    here; the decisions inside it may not be copied out."""
    import inspect
    import web
    src = inspect.getsource(web)
    for smell in ("presend.gate(", "PACK_ASSETS", "record_override(",
                  "MANIFEST.json\").write_text", "tempfile.mkdtemp"):
        assert smell not in src, (
            f"web.py contains {smell!r} -- that decision belongs in sending, "
            f"where the terminal reaches it too"
        )


def test_the_check_table_and_the_failures_above_it_cannot_disagree():
    """Found by rendering the blocked page and looking at it: two checks were
    named as failures at the top and both read `ok` in the table underneath.

    Which checks failed is `Result.blocking` -- one list, authoritative however
    a finding got there. Deciding it a second time from each check's own bucket
    is two functions that must agree about the same fact, which is the pattern
    that produced the disagreement.
    """
    import web
    res = presend.Result()
    res.add("no sentence the firm has deleted has come back",
            presend.Counted([], 76, "sentence-in-document pair"))
    res.add("every promised enclosure is in the pack",
            presend.Counted([], 3, "declared enclosure claim"))
    # A finding that reached the result without going through its own check.
    res.findings.append(presend.Finding(
        check="no sentence the firm has deleted has come back",
        document="SAT-C Engagement Letter.html", detail="it is back on page 2"))

    table = web._checks_block(res)
    rows = table.split("<tr>")
    deleted = next(r for r in rows if "has deleted has come back" in r)
    enclosure = next(r for r in rows if "promised enclosure" in r)
    # THE PROPERTY IS THE DISAGREEMENT, NOT THE WORDS. `ok`/`FAIL` became
    # `fine`/`stops it` on 2 September 2026, because the mark should say what
    # happens to the person reading rather than what the check did. The example
    # moved and the rule did not (S25).
    assert "mk stop" in deleted and "stops it" in deleted, deleted
    assert "mk pass" in enclosure and ">fine<" in enclosure, enclosure


# ── quoting a live engagement again ───────────────────────────────────────
#
# The screens are the second front door onto the money, and the first one has
# gates. These hold the ones that are not obvious from looking at the page.

import engagements  # noqa: E402
import requote  # noqa: E402

# BOTH ANSWERS THAT STATE ONE FACT. The count is what the K-1 line is billed
# from; the additional forms line is the same fact in the preparer's own words,
# two inches above it on the estimate. Moving one without the other is refused,
# so a form post that moves one is exercising the refusal.
K1S_6 = {"_asked": ["count_k1s", "additional_forms"],
         "count_k1s": "6", "additional_forms": "6 K-1s as reported"}


@pytest.fixture
def priced(client, answers):
    """One live engagement, created through the browser like any other."""
    sid = drive(client, answers)
    ref = client.post(f"/interview/{sid}/finish", headers=JSON).get_json()["ref"]
    return ref


def test_the_engagement_page_offers_the_door(client, priced):
    """A door nothing links to is a door nobody finds. Packaging was reachable
    only by typing a command until this page linked it; re-quoting was not
    reachable at all."""
    body = client.get(f"/engagement/{priced}").data.decode()
    assert f"/engagement/{priced}/requote" in body
    assert "Update the quote" in body


def test_the_form_shows_what_is_on_file_and_writes_nothing(client, priced):
    before = engagements.load(priced, client.store)
    page = client.get(f"/engagement/{priced}/requote").data.decode()
    assert "count_k1s" in page
    assert "count_owners" not in page, (
        "an individual filer is offered a question the schedule ignores here"
    )
    assert engagements.load(priced, client.store) == before


def test_a_preview_shows_every_line_that_moves_and_records_nothing(client,
                                                                   priced):
    before = engagements.load(priced, client.store)
    page = client.post(f"/engagement/{priced}/requote",
                       data=K1S_6).data.decode()
    assert "What this changes" in page
    assert before["EstimateTotal"] in page
    assert "Record the new quote" in page
    assert engagements.load(priced, client.store) == before
    assert not requote.revisions(priced, client.store)


def test_the_reason_is_what_writes_it(client, priced):
    """Two posts, one route. Without a reason it is a look; with one it is a
    record -- and there is no third state where something is half written."""
    posted = {**K1S_6,
              "reason": "the estate issued four more K-1s in June"}
    page = client.post(f"/engagement/{priced}/requote", data=posted).data.decode()
    assert "The new quote is recorded" in page
    log = requote.revisions(priced, client.store)
    assert len(log) == 1
    assert log[0]["reason"] == posted["reason"]
    assert engagements.load(priced, client.store)["EstimateTotal"] == log[0]["now"]


def test_the_page_that_records_it_offers_the_pack_again(client, priced):
    """The scope or the figure has moved, so the documents the client holds
    are out of date. The next step is on the page that knows it."""
    page = client.post(f"/engagement/{priced}/requote",
                       data={**K1S_6, "reason": "four more K-1s in June"}).data.decode()
    assert f"/engagement/{priced}/package" in page


def test_the_price_history_is_on_the_engagement_page(client, priced):
    """`revisions.json` is append-only and nobody would have found it. A price
    that moved and can only be explained by opening a file in the store is a
    price nobody can defend on the phone."""
    client.post(f"/engagement/{priced}/requote",
                data={**K1S_6, "reason": "four more K-1s in June"})
    body = client.get(f"/engagement/{priced}").data.decode()
    assert "This quote has moved" in body
    assert "four more K-1s in June" in body


def test_emptying_a_multi_select_is_a_change_the_form_can_express(client,
                                                                  priced):
    """FOUND BY DRIVING IT. Unticking every box sends no field at all, which
    is indistinguishable from the question not being on the page -- so
    clearing the schedules silently did nothing, on a screen that had just
    shown the boxes being unticked. `_asked` is posted once per question and
    says what the preparer was looking at."""
    page = client.post(f"/engagement/{priced}/requote",
                       data={"_asked": "federal_schedules"}).data.decode()
    assert "federal_schedules" in page
    assert "(nothing)" in page
    assert "engagement letter says something else" in page.lower(), (
        "dropping every schedule changes the scope and the page did not say so"
    )


def test_posting_nothing_different_is_refused_rather_than_logged(client,
                                                                 priced):
    on_file = requote._answers(priced, client.store)["count_k1s"]
    res = client.post(f"/engagement/{priced}/requote",
                      data={"_asked": "count_k1s", "count_k1s": str(on_file)})
    assert res.status_code == 400
    assert b"nothing to re-quote" in res.data
    assert not requote.revisions(priced, client.store)


def test_both_doors_reach_the_same_verdict(client, priced):
    """One of each route, like everything else here -- and the JSON has to
    carry the blockers, not just the happy total."""
    got = client.post(f"/engagement/{priced}/requote", headers=JSON,
                      json={"changes": {
                          "count_k1s": 6,
                          "additional_forms": ["6 K-1s as reported"]}}
                      ).get_json()
    assert got["status"] == "planned"
    assert got["difference"].endswith("more")
    assert any(m["service"] == "Schedule K-1 received" for m in got["moved"])
    assert not requote.revisions(priced, client.store)
