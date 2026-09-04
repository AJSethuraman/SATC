"""Refused, kept, and never served — the boundary that makes keeping it safe.

The queue exists because a refusal is a finding and the reasoning behind it is
the best evidence of what the record is missing. It is only safe because
`retained is not accepted`: nothing here reaches a caller, and nothing here is
counted as correct. Both halves are asserted rather than described.
"""
from __future__ import annotations

import pytest

import unsupported
from engine import Answer, Outcome, Refusal, Result, Served, grade, serve





# ── nothing leaves without authority ─────────────────────────────────────────

def test_a_cited_answer_is_served_with_its_authority(fixed_assets, problem):
    out = serve(Answer(position=problem.answer, citation=problem.citation), fixed_assets)
    assert isinstance(out, Served)
    assert out.citation == problem.citation
    assert out.tier == "primary"
    assert out.checked, "an answer with no checked date is a claim about the present"


def test_an_uncited_answer_is_never_served_even_when_it_is_right(
        fixed_assets, problem):
    """The rule the whole plugin rests on. Enforced here, not in a prompt."""
    out = serve(Answer(position=problem.answer, citation=""), fixed_assets)
    assert isinstance(out, Refusal)
    assert not out, "a Refusal must be falsy so `if served:` cannot pass by accident"
    assert out.reason == "no_citation"


def test_an_interpretive_source_is_refused_rather_than_served(tmp_path):
    """Tier 2 alone is a position for the firm, not an answer for a client."""
    import record
    d = tmp_path / "guide"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A guide\n\n**Tier:** secondary · **Access:** public_fetch · "
        "**May store:** citation_only · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** G\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** G 1\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "g.md").write_text(
        "## G 1\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n> reading\n",
        encoding="utf-8")
    out = serve(Answer(position="a", citation="G 1"), record.load(d))
    assert isinstance(out, Refusal)
    assert out.reason == "authority_permits_choice"


def test_the_gate_and_the_scoreboard_agree(fixed_assets, problem):
    """They share one verification on purpose. If they drifted, the scoreboard
    would stop measuring what the gate actually does."""
    for citation in ("", "26 CFR 9.9-9", problem.citation):
        a = Answer(position=problem.answer, citation=citation)
        served = not isinstance(serve(a, fixed_assets), Refusal)
        scored_ok = grade(a, problem, fixed_assets).outcome is Outcome.CORRECT
        assert served == scored_ok, (
            f"citation {citation!r}: gate says served={served}, "
            f"scoreboard says correct={scored_ok}"
        )


# ── retained is not accepted ──────────────────────────────────────────────────

def test_a_refusal_becomes_an_entry_carrying_its_reasoning(
        fixed_assets, problem, wrong_position):
    a = Answer(position=wrong_position, citation="26 CFR 9.9-9",
               working="thought it was a repair")
    r = grade(a, problem, fixed_assets)
    entry = unsupported.from_refusal("is storm damage capitalised?", a, r,
                                     model="qwen3:8b", today="2026-09-04")
    assert entry.concluded == "not required to capitalize"
    assert entry.believed_authority == "26 CFR 9.9-9"
    assert entry.failed_because == "authority_absent"
    assert entry.working == "thought it was a repair"


def test_an_entry_round_trips_through_its_own_format(tmp_path, fixed_assets,
                                                     problem):
    a = Answer(position="x", citation="26 CFR 9.9-9")
    r = grade(a, problem, fixed_assets)
    e = unsupported.from_refusal("q?", a, r, today="2026-09-04")
    path = unsupported.append(tmp_path / "UNSUPPORTED.md", e)
    back = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(back) == 1
    assert back[0].id == e.id
    assert back[0].concluded == e.concluded
    assert back[0].failed_because == e.failed_because


def test_recording_the_same_refusal_twice_does_not_duplicate_it(tmp_path):
    e = unsupported.Unsupported(
        id="U1", question="q", concluded="c", believed_authority="a",
        failed_because="no_citation", recorded="2026-09-04")
    p = tmp_path / "UNSUPPORTED.md"
    unsupported.append(p, e)
    unsupported.append(p, e)
    assert len(unsupported.parse(p.read_text(encoding="utf-8"))) == 1, (
        "a queue that grows a row per retry stops being readable, and its count "
        "stops meaning anything"
    )


def test_ids_are_never_reused(tmp_path):
    """A gap with no explanation is an invitation to fill it."""
    existing = [unsupported.Unsupported(
        id=f"U{n}", question="q", concluded="c", believed_authority="a",
        failed_because="no_citation", recorded="2026-09-04") for n in (1, 2, 5)]
    assert unsupported.next_id(existing) == "U6"
    assert unsupported.next_id([]) == "U1"


def test_a_malformed_entry_is_an_error_not_a_default(tmp_path):
    with pytest.raises(Exception):
        unsupported.parse("## U1 · q\n\n**Recorded:** yesterday\n\n"
                          "**Concluded:** c\n\n**Believed authority:** a\n")


def test_the_queue_explains_what_to_do_with_it(tmp_path):
    """A queue nobody knows how to clear is a queue that only grows."""
    p = unsupported.append(tmp_path / "U.md", unsupported.Unsupported(
        id="U1", question="q", concluded="c", believed_authority="a",
        failed_because="no_citation", recorded="2026-09-04"))
    head = p.read_text(encoding="utf-8")
    assert "Retained is not accepted" in head
    assert "source" in head and "position" in head


def test_two_different_refusals_both_reach_the_queue(tmp_path):
    """`from_refusal`'s `existing` defaults to an empty list, so it numbered
    every entry U1; `append` saw the id already present and returned silently.
    The natural one-liner therefore kept the FIRST refusal and threw away every
    one after it -- from the queue whose entire purpose is to keep them."""
    path = tmp_path / "UNSUPPORTED.md"
    for q, cite in [("is a roof a unit of property?", "26 CFR 1"),
                    ("what about an elevator?", "26 CFR 2"),
                    ("and a parking lot?", "")]:
        unsupported.append(path, unsupported.from_refusal(
            q, Answer(position="p", citation=cite),
            Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
            today="2026-09-04"))
    got = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(got) == 3, f"queue kept {len(got)} of 3 refusals"
    assert [u.id for u in got] == ["U1", "U2", "U3"], [u.id for u in got]


def test_the_same_refusal_recorded_twice_is_still_one_row(tmp_path):
    """Renumbering must not turn the idempotency guard off: a queue that grows a
    row per retry stops being readable and its count stops meaning anything."""
    path = tmp_path / "UNSUPPORTED.md"
    make = lambda day: unsupported.from_refusal(
        "is a roof a unit of property?", Answer(position="p", citation="26 CFR 1"),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"), today=day)
    unsupported.append(path, make("2026-09-04"))
    unsupported.append(path, make("2026-09-05"))     # same finding, later day
    assert len(unsupported.parse(path.read_text(encoding="utf-8"))) == 1


def test_a_models_multiline_reasoning_survives_the_round_trip(tmp_path):
    """`_field` read one line, so chain-of-thought was kept as its first sentence
    -- and the reasoning is the whole evidentiary value of a retained refusal.
    Canon had this exact bug in the exact same place, parsing 5 of 24 subjects
    and reporting success."""
    working = ("first, the roof is not the unit of property\n"
               "second, paragraph (e) makes the building the unit\n"
               "so the safe harbour cannot apply")
    path = tmp_path / "UNSUPPORTED.md"
    unsupported.append(path, unsupported.from_refusal(
        "is a roof a unit of property?",
        Answer(position="p", citation="26 CFR 1", working=working),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
        today="2026-09-04"))
    got = unsupported.parse(path.read_text(encoding="utf-8"))[0]
    assert got.working == working, f"kept only {got.working!r}"


def test_the_supported_existing_path_also_deduplicates(tmp_path):
    """The last fix held only on an ID CLASH. Pass the parsed queue as `existing`
    -- the documented way -- and the retry gets a fresh id, so the clash search
    never ran and the same finding was appended twice. Same guarantee, two ways
    in, and only one of them held it."""
    path = tmp_path / "UNSUPPORTED.md"
    make = lambda existing, day: unsupported.from_refusal(
        "is a roof a unit of property?", Answer(position="p", citation="26 CFR 1"),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
        existing=existing, today=day)
    unsupported.append(path, make([], "2026-09-04"))
    current = unsupported.parse(path.read_text(encoding="utf-8"))
    unsupported.append(path, make(current, "2026-09-05"))
    got = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(got) == 1, f"the same refusal was recorded {len(got)} times"


def test_a_models_markdown_reasoning_round_trips_intact(tmp_path):
    """The one free-form field carries prose a model wrote, and prose contains
    Markdown. `**Evidence:**` read as the next record field and truncated
    everything after it; a line opening `## x · y` could be read as a whole new
    ENTRY and make the queue unparsable. Every other field here is structured and
    short — this one is arbitrary, so it is escaped rather than trusted."""
    working = ("First line of reasoning\n"
               "**Evidence:** paragraph (e)(2)(ii) makes the building the unit\n"
               "\n"
               "## Not a heading · and not a new entry\n"
               "- so the safe harbour cannot apply")
    path = tmp_path / "UNSUPPORTED.md"
    unsupported.append(path, unsupported.from_refusal(
        "is a roof a unit of property?",
        Answer(position="p", citation="26 CFR 1", working=working),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
        today="2026-09-04"))
    got = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(got) == 1, f"the queue split into {len(got)} entries"
    assert got[0].working == working, f"kept {got[0].working!r}"
    assert got[0].failed_because == "authority_absent", "a later field was eaten"
