"""Refused, kept, and never served — the boundary that makes keeping it safe.

The queue exists because a refusal is a finding and the reasoning behind it is
the best evidence of what the record is missing. It is only safe because
`retained is not accepted`: nothing here reaches a caller, and nothing here is
counted as correct. Both halves are asserted rather than described.
"""
from __future__ import annotations

import pytest

import unsupported
from record import RecordError
from engine import Answer, Outcome, Refusal, Result, Served, grade, serve





# ── nothing leaves without authority ─────────────────────────────────────────

def test_a_cited_answer_is_served_with_its_authority(fixed_assets, problem):
    out = serve(Answer(position=problem.answer, citation=problem.citation),
                fixed_assets, question=problem.facts)
    assert isinstance(out, Served)
    assert out.citation == problem.citation
    assert out.tier == "primary"
    assert out.checked, "an answer with no checked date is a claim about the present"


def test_an_uncited_answer_is_never_served_even_when_it_is_right(
        fixed_assets, problem):
    """The rule the whole plugin rests on. Enforced here, not in a prompt."""
    out = serve(Answer(position=problem.answer, citation=""), fixed_assets,
                question=problem.facts)
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
    out = serve(Answer(position="a", citation="G 1"), record.load(d),
                question="a question")
    assert isinstance(out, Refusal)
    assert out.reason == "authority_permits_choice"


def test_the_gate_and_the_scoreboard_agree(fixed_assets, problem):
    """They share one verification on purpose. If they drifted, the scoreboard
    would stop measuring what the gate actually does."""
    for citation in ("", "26 CFR 9.9-9", problem.citation):
        a = Answer(position=problem.answer, citation=citation)
        served = not isinstance(serve(a, fixed_assets, question=problem.facts),
                                Refusal)
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


def test_every_field_that_comes_from_outside_survives_markdown(tmp_path):
    """`working` was quoted first, on the reasoning that it was "the one
    free-form field". It was not: the question is the caller's, and the
    conclusion and citation are the MODEL's. All three are arbitrary text, and
    all three were written straight into Markdown structure.

    The escape had been applied to an instance instead of to the category."""
    hostile = ("line one\n"
               "**Evidence:** this used to end the field\n"
               "## U99 · and this used to start a whole new entry\n"
               "- trailing")
    path = tmp_path / "UNSUPPORTED.md"
    unsupported.append(path, unsupported.from_refusal(
        hostile,
        Answer(position=hostile, citation=hostile, working=hostile),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
        today="2026-09-04"))
    got = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(got) == 1, f"the queue split into {len(got)} entries"
    u = got[0]
    assert u.question == hostile, f"question kept {u.question!r}"
    assert u.concluded == hostile, f"concluded kept {u.concluded!r}"
    assert u.believed_authority == hostile, f"citation kept {u.believed_authority!r}"
    assert u.working == hostile, f"working kept {u.working!r}"
    assert u.failed_because == "authority_absent", "a later field was eaten"
    assert u.recorded == "2026-09-04"


def test_the_heading_stays_one_line_and_scannable(tmp_path):
    """A heading is a LABEL a person scans; the quoted field below it is the
    value. Letting a multiline question into the heading broke the format."""
    path = tmp_path / "UNSUPPORTED.md"
    unsupported.append(path, unsupported.from_refusal(
        "is a roof\na unit\nof property?",
        Answer(position="p", citation="26 CFR 1"),
        Result("P1", Outcome.WRONG_CAUGHT, reason="authority_absent"),
        today="2026-09-04"))
    text = path.read_text(encoding="utf-8")
    assert "## U1 · is a roof a unit of property?" in text, text
    assert unsupported.parse(text)[0].question == "is a roof\na unit\nof property?"


# ── which kind of refusal this is, so the queue can be read ──────────────────

def _desk_holding(*citations):
    """A desk whose authority is exactly these citations. Nothing else is used
    by `from_refusal`, so nothing else is built."""
    from record import Desk, Passage
    return Desk(name="d", passages=tuple(
        Passage(citation=c, source_id="S1", checked="2026-09-04", text="rule")
        for c in citations))


def _refusal(citation, desk=None):
    from engine import Answer, Outcome, Result
    return unsupported.from_refusal(
        "some facts",
        Answer(position="must capitalize", citation=citation),
        Result(problem_id="P1", outcome=Outcome.WRONG_CAUGHT,
               reason="citation_does_not_support"),
        desk=desk, today="2026-09-05")


def test_a_finer_path_inside_the_desks_authority_is_filed_as_a_near_miss():
    """Measured on the second scoreboard, 4 September 2026: the frontier row
    cited the governing rule in 16 of 16 and named the paragraph the regulation
    itself names in 4, so 12 answers landed here as undifferentiated refusals.
    The queue exists to say what authority is MISSING, and 12 of its 16 entries
    were not missing authority at all."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)")
    u = _refusal("26 CFR 1.263(a)-3(j)(1)(iii)", desk)
    assert u.near_miss
    assert u.falls_under == "26 CFR 1.263(a)-3(j)"


def test_a_citation_outside_the_desks_authority_is_not_a_near_miss():
    """The control. Without it the label could be unconditional and every test
    above would still pass."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)")
    assert not _refusal("26 CFR 1.263(a)-3(k)(1)(vi)", desk).near_miss
    assert not _refusal("26 CFR 1.263(a)-3(k)(1)(vi)", desk).falls_under


def test_the_nearest_containing_rule_is_the_one_kept():
    """A desk holding both `(j)` and `(j)(1)` contains the answer twice. The
    nearest ancestor says more about where the desk actually got to."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)", "26 CFR 1.263(a)-3(j)(1)")
    assert _refusal("26 CFR 1.263(a)-3(j)(1)(iii)", desk).falls_under \
        == "26 CFR 1.263(a)-3(j)(1)"


def test_the_exact_citation_is_not_a_near_miss_because_it_is_not_a_miss():
    """`under` is strict. An answer citing what the desk holds exactly was
    refused for some other reason, and labelling it a near miss would say the
    citation was the problem when it was not."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)")
    assert not _refusal("26 CFR 1.263(a)-3(j)", desk).near_miss


def test_a_ratified_position_counts_as_authority_held():
    """`Desk.authority_for` treats a stored passage and a ratified position
    alike -- they differ in who wrote them, not in whether the desk holds the
    rule -- and this must not disagree with it."""
    from record import Desk
    from positions import Position
    desk = Desk(name="d", positions=(
        Position(id="POS1", title="t", citation="26 CFR 1.263(a)-3(j)",
                 recorded="2026-09-04", position="we capitalise",
                 ratified="PR #999"),))
    assert _refusal("26 CFR 1.263(a)-3(j)(1)", desk).falls_under \
        == "26 CFR 1.263(a)-3(j)"


def test_an_unratified_position_is_not_authority_held():
    """A proposal sitting in a pull request is not yet the firm's word, and
    `Desk.position()` already ignores it. The queue must agree."""
    from record import Desk
    from positions import Position
    desk = Desk(name="d", positions=(
        Position(id="POS1", title="t", citation="26 CFR 1.263(a)-3(j)",
                 recorded="2026-09-04", position="we capitalise"),))
    assert not _refusal("26 CFR 1.263(a)-3(j)(1)", desk).falls_under


def test_without_a_desk_nothing_is_claimed_either_way():
    """`from_refusal` is called from places that have no desk to hand. An empty
    label there means "not asked", and it must not read as "not a near miss"."""
    assert not _refusal("26 CFR 1.263(a)-3(j)(1)").falls_under


def test_the_label_survives_the_round_trip(tmp_path):
    """It is written into the file a person reads, so it has to come back out."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)")
    path = tmp_path / "UNSUPPORTED.md"
    unsupported.append(path, _refusal("26 CFR 1.263(a)-3(j)(1)(iii)", desk))
    back = unsupported.parse(path.read_text(encoding="utf-8"))
    assert len(back) == 1
    assert back[0].falls_under == "26 CFR 1.263(a)-3(j)"
    assert back[0].near_miss


def test_a_near_miss_is_still_refused_and_still_kept():
    """The firm declined loosening the citation check, and the reason stands:
    `_check` is shared by `serve()` and `grade()`, so anything that forgives a
    near miss on a scoreboard hands one to a client. This is a label on a
    retained refusal, never a pass."""
    desk = _desk_holding("26 CFR 1.263(a)-3(j)")
    u = _refusal("26 CFR 1.263(a)-3(j)(1)(iii)", desk)
    assert u.failed_because == "citation_does_not_support"
    assert u.concluded == "must capitalize"     # kept, not served


# ── the front door for a question nobody has answered yet ────────────────────

def test_a_stuck_agents_question_lands_in_the_queue(tmp_path):
    """The firm, 5 September 2026, on an agent failing to close a set of books:
    "i am going to stop it from working and instead have it come up with
    questions to ask and see what we can do from there."

    That is what this is for. `from_refusal` needs an answer and a grade because
    it records a desk that TRIED; this records one that could not start.
    """
    path = tmp_path / "UNSUPPORTED.md"
    u = unsupported.from_question(
        "Client paid a supplier in December for goods delivered in January. "
        "Which period does the expense belong to?",
        why="the close agent stopped here; no desk holds a cutoff rule",
        model="occam", today="2026-09-05")
    unsupported.append(path, u)

    back = unsupported.parse(path.read_text(encoding="utf-8"))[0]
    assert back == u, "what was written is not what comes back"
    assert back.failed_because == "authority_absent"
    assert "close agent stopped here" in back.working
    assert "question, not an answer" in back.concluded


def test_a_question_may_be_filed_as_a_missing_fact_instead(tmp_path):
    """`authority_absent` resolves by loading authority; `facts_not_established`
    resolves by ASKING. Which one it is changes what somebody does next, so it
    is recorded rather than assumed."""
    u = unsupported.from_question(
        "Were the J.Crew purchases work clothing or personal?",
        because="facts_not_established", today="2026-09-05")
    assert u.failed_because == "facts_not_established"


def test_a_question_is_never_an_answer(tmp_path):
    """Retained is not accepted — the queue's own rule, and it must hold for
    entries that never carried an answer at all."""
    u = unsupported.from_question("anything", today="2026-09-05")
    assert u.believed_authority == ""
    assert not u.near_miss


def test_the_same_question_filed_twice_is_one_entry(tmp_path):
    """A stuck agent re-runs. A queue that grows a row per attempt stops being
    readable, which is what `_same_refusal` exists to prevent."""
    path = tmp_path / "UNSUPPORTED.md"
    for _ in range(3):
        current = (unsupported.parse(path.read_text(encoding="utf-8"))
                   if path.exists() else [])
        unsupported.append(path, unsupported.from_question(
            "the same question", existing=current, today="2026-09-05"))
    assert len(unsupported.parse(path.read_text(encoding="utf-8"))) == 1


def test_an_entry_with_no_citation_survives_the_round_trip(tmp_path):
    """THE BUG THIS FOUND, and it was already there.

    `render` wrote "(none offered)" for an empty citation and `parse` did not
    know the word, so an entry came back carrying that phrase AS its citation.
    `_same_refusal` compares that field — so the idempotency guard stopped
    recognising the entry it had just written, and the same finding would be
    filed again on every run. A question has no citation by definition, so this
    would have bitten every single one.
    """
    u = unsupported.Unsupported(
        id="U1", question="q", concluded="c", believed_authority="",
        failed_because="authority_absent", recorded="2026-09-05")
    back = unsupported.parse(u.render())[0]
    assert back.believed_authority == "", "the display sentinel came back as data"
    assert back == u

    real = unsupported.Unsupported(
        id="U2", question="q", concluded="c", believed_authority="26 CFR 1",
        failed_because="authority_absent", recorded="2026-09-05")
    assert unsupported.parse(real.render())[0].believed_authority == "26 CFR 1"


# ── the closed vocabulary the escape rule rests on ───────────────────────────

def test_a_question_reason_outside_the_set_is_refused():
    """`failed_because` is one of only two fields written into the queue's
    Markdown UNESCAPED, on the stated grounds that it is a closed vocabulary.
    `from_question` took it from a caller with a default and no check, so a
    heading in it writes a queue `parse()` then refuses to read — and an
    ordinary typo files the entry under a category nothing counts."""
    with pytest.raises(RecordError, match="closed vocabulary"):
        unsupported.from_question("what is this charge",
                                  because="authority_absent\n## U99 · injected")
    with pytest.raises(RecordError, match="authority_absent"):
        unsupported.from_question("what is this charge", because="autority_absent")


def test_the_question_reasons_are_the_engines_reasons():
    """Two sets, one vocabulary. Written apart, a reason could be renamed in the
    engine and go on being accepted here, or accepted here and rejected the
    moment the same entry reached `serve()`."""
    import engine
    extra = set(unsupported.QUESTION_REASONS) - set(engine.REASONS)
    assert not extra, f"{sorted(extra)} is not an escalation reason the engine knows"


def test_both_question_reasons_round_trip_through_the_queue(tmp_path):
    """The two a question can honestly be in, written and read back. A reason
    the parser cannot recover is a queue entry nobody can sort."""
    path = tmp_path / "q.md"
    for reason in unsupported.QUESTION_REASONS:
        unsupported.append(path, unsupported.from_question(
            f"a question failing for {reason}", why="asked by the close",
            because=reason, existing=unsupported.parse(
                path.read_text(encoding="utf-8")) if path.exists() else []))
    back = unsupported.parse(path.read_text(encoding="utf-8"))
    assert [u.failed_because for u in back] == list(unsupported.QUESTION_REASONS)
