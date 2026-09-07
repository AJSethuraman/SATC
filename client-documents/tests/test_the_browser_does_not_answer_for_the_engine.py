"""A refused answer says so on the page, in the firm's words.

E2 FROM THE WALK OF 5 SEPTEMBER 2026 -- and the walk got the diagnosis wrong.

What the walk recorded: *"An out-of-range tax year is refused in complete
silence."* I typed `1` into **Which tax year?**, pressed **Next**, and the page
sat there with `1` still in the box and nothing to read.

WHAT IS ACTUALLY HAPPENING IS WORSE THAN SILENCE: THERE WAS NO REFUSAL. No
request was made at all. The year box carried `min=2023 max=2027`, so Chrome's
own constraint validation cancelled the submit before it left the machine. The
engine refuses an out-of-range year correctly, and has all along, with a
sentence naming the bounds -- it was simply never reached. Confirmed in a real
browser, not inferred: after typing `1` and clicking Next,
`performance.getEntriesByType("navigation")` still showed the ORIGINAL
navigation, and `input.validationMessage` read *"Value must be greater than or
equal to 2023."*

So a preparer sitting with a client sees a button that does nothing. Chrome does
raise a bubble, but it is transient, it hangs off the field rather than living in
the page, and it is written in the browser's words and the browser's language --
not the firm's. Press Next a second time and even that is gone.

The comment above that input read:

    `min`/`max` are a convenience, never the control -- `Interview.answer` is
    the control, and the JSON door has no HTML to obey.

**In a browser they ARE the control.** They are the only check that runs, and
they run INSTEAD of the real one. That is the same mistake as guarding the view
rather than the engine, wearing the opposite face: here the view's guard is what
stops the engine's guard from ever being heard.

`novalidate` on the form. The attributes stay -- the spinner arrows stay bounded
and the range is discoverable -- and every refusal now comes from
`Interview.answer`, which is the door the JSON API and `cli.py --set` also meet.

AND THE FOUR REFUSALS E3 LEFT BEHIND. E3 fixed the required message to name the
question instead of `federal_form`. It fixed one raise. The four beside it still
read `tax_year needs a tax year between 2023 and 2027` -- the field id, on
screen, under the question it belongs to. With `novalidate` those messages stop
being theoretical, because they are now the ones people actually see.
"""
from __future__ import annotations

import re

import pytest

import interview as iv
import web


@pytest.fixture()
def c(tmp_path):
    return web.create_app(store=str(tmp_path / "engagements")).test_client()


def _walk_to(c, target):
    """Answer questions until `target` is the current one. Returns the sid."""
    sid = c.post("/interview", data={"lead": ""}).headers["Location"].rstrip("/").split("/")[-1]
    for _ in range(12):
        body = c.get(f"/interview/{sid}").get_data(as_text=True)
        qid = re.search(r"name=question value='([^']+)'", body).group(1)
        if qid == target:
            return sid, body
        opts = re.findall(r"name=answer value='([^']+)'", body)
        c.post(f"/interview/{sid}", data={"question": qid, "answer": opts[0] if opts else "X"})
    raise AssertionError(f"never reached {target}")


# ── E2: the browser must not answer for the engine ────────────────────────────

def _answer_form_tag(body):
    """The opening tag of the form that CARRIES the answer.

    Not the first `<form action='/interview/...'>` on the page -- that is the
    Back button, whose action differs only by a trailing `/back`. Matching on
    the prefix found Back and passed this test against the unfixed code for the
    wrong reason. The answer form is the one holding the question's id.
    """
    for m in re.finditer(r"<form[^>]*>", body):
        rest = body[m.end():body.find("</form>", m.end())]
        if "name=question" in rest:
            return m.group(0)
    raise AssertionError("no form on the page carries the question")


def test_the_question_form_does_not_let_the_browser_cancel_the_submit(c):
    """THE DEFECT. Without `novalidate` the POST never happens."""
    _, body = _walk_to(c, "tax_year")
    form = _answer_form_tag(body)
    assert "novalidate" in form, (
        "the browser's own validation can cancel the submit, so the engine's "
        "refusal is never reached and Next reads as a dead button")


def test_the_bounds_are_still_on_the_box(c):
    """The control. Stripping `min`/`max` would fix the silence by removing a
    real convenience -- bounded spinner arrows, and a range you can see."""
    _, body = _walk_to(c, "tax_year")
    assert re.search(r"<input type=number name=answer autofocus min=\d{4} max=\d{4}", body)


def test_the_range_is_offered_before_it_is_needed(c):
    """A refusal read mid-sitting is one the preparer had to earn."""
    _, body = _walk_to(c, "tax_year")
    assert re.search(r"\d{4} to \d{4}\. A year outside that", body), (
        "the bounds are enforced and never stated")


def test_an_out_of_range_year_is_refused_on_the_page(c):
    """What the preparer must end up seeing: a sentence, in the page, that stays."""
    sid, _ = _walk_to(c, "tax_year")
    r = c.post(f"/interview/{sid}", data={"question": "tax_year", "answer": "1"})
    page = r.get_data(as_text=True)

    assert r.status_code == 400
    assert "class=err" in page, "the refusal is not rendered where errors go"
    assert "between" in page and "Which tax year?" in page


def test_a_year_in_range_still_goes_through(c):
    """The control. A form that refuses everything is not a fix."""
    sid, _ = _walk_to(c, "tax_year")
    from datetime import date
    r = c.post(f"/interview/{sid}", data={"question": "tax_year",
                                          "answer": str(date.today().year - 1)})
    assert r.status_code == 302, r.get_data(as_text=True)[:300]


# ── the four refusals E3 left behind ──────────────────────────────────────────

def _refusal(qid, value):
    s = iv.Interview()
    with pytest.raises(iv.InterviewError) as exc:
        s.answer(qid, value)
    return str(exc.value)


def test_an_out_of_range_year_names_the_question_not_the_field(c):
    """It read `tax_year needs a tax year between 2023 and 2027`."""
    sid, _ = _walk_to(c, "tax_year")
    page = c.post(f"/interview/{sid}",
                  data={"question": "tax_year", "answer": "1"}).get_data(as_text=True)
    err = re.search(r"<p class=err>(.*?)</p>", page, re.S).group(1)
    assert "Which tax year?" in err, f"still names only the field id: {err!r}"
    assert "tax_year" in err, "the id is gone, and `--set` and the logs take it"


def test_a_refused_option_names_the_question_too():
    message = _refusal("federal_form", "1040-EZ")
    assert "Which federal return?" in message
    assert "federal_form" in message


def test_a_non_number_names_the_question_too():
    """`type: number` questions exist further down the schema."""
    schema = iv.Interview().schema
    numeric = next((q for _, q in iv.all_questions(schema)
                    if q.get("type") == "number"), None)
    assert numeric is not None, "no numeric question in the schema; test is vacuous"
    message = _refusal(numeric["id"], "seven")
    assert numeric["question"] in message
    assert numeric["id"] in message


def test_a_required_question_still_names_its_question():
    """E3's fix, which this must not undo."""
    message = _refusal("federal_form", "")
    assert "Which federal return?" in message
    assert "federal_form" in message
