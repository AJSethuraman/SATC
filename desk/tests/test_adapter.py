"""The adapter's deterministic parts: what the prompt carries, what it refuses.

No model runs here and no score is asserted. What IS asserted is the gate that
sits between the record and the brain, because a leak check nothing exercises
is a promise -- and the first record's leak was called fixed twice before a
test caught it.
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter

import pytest

import engine
import record
import scoreboard
from conftest import DESKS, ROOT
from engine import Answer

sys.path.insert(0, str(ROOT / "tools"))
import scoreboard_run as sr        # noqa: E402

DESK = DESKS / "fixed-assets"


def _scratch(tmp_path, *, extra_passage: str = ""):
    """A one-problem desk whose authority is a rule, plus whatever is added."""
    d = tmp_path / "desk"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · Reg\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** 26 CFR 1.263(a)-3\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · Big job\n\n**Citation:** 26 CFR 1.263(a)-3(k)(1)(vi)\n\n"
        "**Answer:** must capitalize\n\n"
        "**Facts:** K owns a building. K pays an amount to replace the entire "
        "roof, including the decking, insulation and membrane. The old roof "
        "had leaked for years.\n", encoding="utf-8")
    (d / "extracted" / "reg.md").write_text(
        "## 26 CFR 1.263(a)-3(k)(1)(vi)\n\n**Source:** S1 · **Checked:** "
        "2026-09-04\n\n> Is for the replacement of a major component. Text of "
        "the rule follows.\n" + extra_passage, encoding="utf-8")
    return record.load(d)


def test_the_prompt_shows_the_rules_and_the_facts_once():
    desk = record.load(DESK)
    for p in desk.problems:
        prompt = sr.build_prompt(p, desk)
        assert "26 CFR 1.263(a)-3(k)(1)(vi) — Is for the replacement" in prompt
        assert prompt.count(p.facts) == 1
        assert p.title not in prompt


def test_a_worked_example_stored_as_authority_is_refused_at_the_prompt(tmp_path):
    """The leak at its new boundary, as a mechanism. Store the problem's own
    example beside the rules and the prompt refuses to be built."""
    clean = _scratch(tmp_path)
    assert "K owns a building" in sr.build_prompt(clean.problems[0], clean)
    leaking = _scratch(
        tmp_path / "b",
        extra_passage="\n---\n\n## 26 CFR 1.263(a)-3(k)(7) Example 14\n\n"
                      "**Source:** S1 · **Checked:** 2026-09-04\n\n"
                      "> K owns a building. K pays an amount to replace the "
                      "entire roof, including the decking, insulation and "
                      "membrane. Therefore, K must capitalize it.\n")
    with pytest.raises(sr.Leak, match="fact pattern of P1"):
        sr.build_prompt(leaking.problems[0], leaking)


def test_the_two_shapes_and_nothing_else():
    desk = record.load(DESK)
    index = sr.build_prompt(desk.problems[0], desk, shape="index")
    text = sr.build_prompt(desk.problems[0], desk, shape="text")
    rule = desk.passage("26 CFR 1.263(a)-3(j)(1)")
    assert rule.text in text and rule.text not in index
    assert len(index) < len(text) / 3, "the index shape is not short"
    with pytest.raises(ValueError, match="shape"):
        sr.build_prompt(desk.problems[0], desk, shape="everything")


def test_the_constant_control_reports_the_citation_baseline():
    desk = record.load(DESK)
    c = sr.constant_control(desk)
    citation, n = Counter(p.citation for p in desk.problems).most_common(1)[0]
    assert (c["citation"], c["cites"], c["of"]) == (citation, n, len(desk.problems))
    assert c["through_the_engine"]["correct"] == 0, "a constant answer cites nothing"


def test_a_reply_that_is_not_json_is_graded_as_it_came_back():
    a = sr.parse_reply("I think it must be capitalized.")
    assert a.citation == "" and not a.escalated
    a = sr.parse_reply('{"position": "x", "citation": "c", "escalated": true, '
                       '"reason": "because"}')
    assert not a.escalated and a.citation == "c", "an unknown reason is an answer"


def test_the_script_records_what_was_shown_beside_the_baselines(tmp_path):
    """End to end through `_main` on a copy of the desk, with a replay file
    standing in for a brain: the record must say which shape of the authority
    the brain saw and what a constant citation would have matched."""
    copy = tmp_path / "fixed-assets"
    shutil.copytree(DESK, copy, ignore=shutil.ignore_patterns("runs", "unsupported"))
    desk = record.load(copy)
    replies = tmp_path / "replies.json"
    replies.write_text(json.dumps({
        p.id: json.dumps({"position": p.answer, "citation": p.citation,
                          "escalated": False, "reason": "", "working": "w"})
        for p in desk.problems}), encoding="utf-8")
    out = tmp_path / "out"
    rc = sr._main(["--desk", str(copy), "--skip-forge", "--out", str(out),
                   "--frontier-replies", str(replies), "--corpus", "index"])
    assert rc == 0
    board = (out / "SCOREBOARD.txt").read_text(encoding="utf-8")
    assert (f"AUTHORITY SHOWN: {len(desk.passages)} stored paragraphs as "
            f"'index', for {len(desk.problems)} problems.") in board
    citation, n = Counter(p.citation for p in desk.problems).most_common(1)[0]
    assert f"citing {citation!r} every time matches {n} of {len(desk.problems)}" in board
    outcomes = json.loads((out / "outcomes.json").read_text(encoding="utf-8"))
    assert outcomes["frontier"]["counts"]["correct"] == len(desk.problems)


# ── containment is measured, and never scored ────────────────────────────────

def test_a_finer_path_under_the_governing_rule_is_counted_apart():
    """Seven problems key to `(j)` because that is what the regulation's own
    conclusion names. A desk answering "betterment, (j)(1)(iii)" has reached the
    right rule by a finer path, and the engine refuses it — correctly, since
    `_check` is shared with `serve()` and anything accepting a near-miss here
    hands one to a client.

    So it is reported rather than forgiven, and reported OUTSIDE the four
    outcomes: containment admits 14 of 172 paths under `(j)` and exactly 1 under
    `(k)(1)(vi)`, so scoring by it would grade seven problems fourteen times more
    leniently than one for no reason but the regulation's prose.
    """
    desk = record.load(DESK)
    coarse = next((p for p in desk.problems if p.citation.endswith("-3(j)")), None)
    assert coarse is not None, "fixture has no coarsely-keyed problem"
    finer = coarse.citation + "(1)(iii)"

    answers = {p.id: Answer(position=p.answer, citation=p.citation)
               for p in desk.problems}
    answers[coarse.id] = Answer(position=coarse.answer, citation=finer)
    run = scoreboard.run(desk, lambda p: answers[p.id], model="probe")
    d = sr.diagnostic(desk, run, answers)

    assert d["citation_within_governing_rule"] == 1, d
    assert d["citation_matched"] == len(desk.problems) - 1, d
    assert d["citation_off_index"] == 0, "a real subparagraph is in the index"

    # And it stays out of every total the scoreboard reports.
    counts = run.counts
    assert sum(counts.values()) == len(desk.problems)
    assert counts["correct"] == len(desk.problems) - 1, (
        "a finer path was scored as correct; the engine must still refuse it")


def test_wrongly_absorbed_is_reachable_at_all():
    """The one outcome that costs anything, proved reachable rather than assumed.

    `grade()` refuses a wrong citation BEFORE comparing the conclusion, so on a
    run where citations are the weak part this number is structurally suppressed
    — the first scoreboard reported 0 on both rows and said so: the trap was not
    sprung, not proved unsprungable. Loosening the gate would expose it; proving
    it directly costs nothing and loosens nothing.
    """
    desk = record.load(DESK)
    p = desk.problems[0]
    other = next(q.answer for q in desk.problems if q.answer != p.answer)

    caught = engine.grade(Answer(position=other, citation=p.citation), p, desk)
    assert caught.outcome is engine.Outcome.WRONGLY_ABSORBED, (
        f"a wrong conclusion behind a citation that HELD graded {caught.outcome}; "
        f"the costly outcome cannot be reached and every 0 reported for it is "
        f"meaningless"
    )
    # The control: same wrong conclusion, wrong citation — caught earlier, so the
    # suppression this test exists to characterise is real and not imagined.
    wrong_cite = next(q.citation for q in desk.problems if q.citation != p.citation)
    assert engine.grade(Answer(position=other, citation=wrong_cite), p, desk
                        ).outcome is engine.Outcome.WRONG_CAUGHT


# ── a replayed reply must have answered the prompt being rebuilt ──────────────

def test_replaying_against_a_different_prompt_is_refused(tmp_path):
    """A `.jsonl` transcript stores the prompt beside every reply, and the replay
    used to discard it and rebuild the evidence from whatever `--corpus` it was
    invoked with. Regrade a `text`-corpus transcript without `--corpus text` and
    the record's own `AUTHORITY SHOWN` line claimed `index` over replies that had
    seen something else — a claim in one place, the behaviour in another.

    Comparing the whole prompt rather than deriving the shape catches the
    category: a changed desk, a changed template, a reordered index and a wrong
    `--corpus` all diverge here, and any of them makes the replies un-regradable
    rather than merely mislabelled.

    IT IS CHECKED WHEN THE ADAPTER IS BUILT, NOT ON THE WAY PAST EACH PROBLEM.
    Whether a transcript answers the prompts being rebuilt is a property of the
    transcript, so the lazy version was late for no reason — and late in the one
    way that mattered: by then the refusal was raised inside `scoreboard.run`,
    whose catch-all absorbed it.
    """
    desk = record.load(DESK)
    p = desk.problems[0]
    reply = json.dumps({"position": p.answer, "citation": p.citation})

    # A transcript recorded under one shape, replayed under the other.
    shown = {p.id: sr.build_prompt(p, desk, shape="text")}
    with pytest.raises(sr.ReplayMismatch, match="different prompt"):
        sr.replay_adapter(desk, {p.id: reply}, tmp_path / "t.jsonl",
                          shape="index", shown=shown)

    # The control: replayed under the shape it was recorded under, it passes.
    same = sr.replay_adapter(desk, {p.id: reply}, tmp_path / "u.jsonl",
                             shape="text", shown=shown)
    assert same(p).citation == p.citation

    # AND IT COMPARES THE CONTENT, NOT THE SIZE. A length check passes the case
    # above by accident, because the two shapes happen to differ in length —
    # which would leave a same-length divergence (a reordered index, an edited
    # paragraph, a swapped citation) silently regraded.
    built = sr.build_prompt(p, desk, shape="index")
    tampered = built.replace(p.facts[:20], p.facts[:20][::-1], 1)
    assert len(tampered) == len(built) and tampered != built, "bad fixture"
    with pytest.raises(sr.ReplayMismatch):
        sr.replay_adapter(desk, {p.id: reply}, tmp_path / "v.jsonl",
                          shape="index", shown={p.id: tampered})


def test_the_refusal_reaches_the_caller_instead_of_becoming_a_give_up():
    """`scoreboard.run` absorbs every ordinary exception into `model_gave_up`,
    because a small model fails in unpredictable ways and rule 9 says the run
    must still produce a denominator. Raised as a plain exception, this refusal
    therefore produced sixteen false give-ups, a scoreboard claiming an
    authority shape nobody saw, and an exit code of zero — the refusal existed
    and did nothing. Found in review of the pull request that added it."""
    import scoreboard

    assert issubclass(sr.ReplayMismatch, scoreboard.HarnessError)

    desk = record.load(DESK)

    def refuse(problem):
        raise sr.ReplayMismatch("a fault of ours, not the brain's")

    with pytest.raises(sr.ReplayMismatch):
        scoreboard.run(desk, refuse, model="x")


def test_a_brain_that_abandons_the_task_is_still_counted_not_raised():
    """The control, without which the fix above could be the catch-all removed.
    Rule 9: small models give up on roughly one run in six to nine and no prompt
    fixes it, so a give-up must still produce a denominator."""
    import scoreboard

    desk = record.load(DESK)

    def collapse(problem):
        raise RuntimeError("the model returned nothing parseable")

    r = scoreboard.run(desk, collapse, model="x")
    assert r.gave_up == len(desk.problems)
    assert r.counts["escalated"] == len(desk.problems)


def test_a_transcript_carries_the_prompt_its_reply_answered(tmp_path):
    """The check above is only possible because `_replies` now keeps the prompt.
    Dropping it turns the refusal off silently, so the shape of what `_replies`
    hands back is asserted rather than assumed."""
    row = {"problem": "P1", "prompt": "the prompt shown", "reply": "{}", "error": ""}
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    replies, shown = sr._replies(str(path))
    assert replies == {"P1": "{}"}
    assert shown == {"P1": "the prompt shown"}, (
        "the prompt was dropped; the replay can no longer tell whether these "
        "replies answered the prompts being rebuilt"
    )

    # A plain reply map carries no prompts, and that is not an error — it is how
    # a fresh frontier context hands its answers back.
    plain = tmp_path / "r.json"
    plain.write_text(json.dumps({"P1": "{}"}), encoding="utf-8")
    assert sr._replies(str(plain)) == ({"P1": "{}"}, {})


# ── a measured record is never written over ──────────────────────────────────

def test_a_directory_already_holding_a_run_is_refused(tmp_path):
    """Found by the second Forge run, 4 September 2026.

    The default output is `runs/<today>/` and both runs happened on the same
    day, so the documented command would have written the second scoreboard over
    the first run's measured record. The session running it noticed and passed
    `--out` by hand; a default whose safety depends on somebody noticing is the
    mechanism absent.
    """
    from datetime import date

    (tmp_path / "SCOREBOARD.md").write_text("the first run", encoding="utf-8")
    with pytest.raises(sr.RunWouldOverwrite, match="already holds a run"):
        sr.run_dir(str(tmp_path), "fixed-assets", date(2026, 9, 4))

    # Still refused when the directory was named explicitly. Deriving the date
    # differently would fix the collision and leave `--out runs/2026-09-04`
    # pointed at the same record; what must not happen is a measured record
    # being replaced, whichever argument named it.
    assert (tmp_path / "SCOREBOARD.md").read_text(encoding="utf-8") == "the first run"


#: NAMED HERE, NOT READ FROM `sr.RUN_RECORDS`. Parametrising over the tuple
#: under test made the test shrink with it: cutting RUN_RECORDS down to
#: SCOREBOARD.md alone left `outcomes.json` overwritable and the suite green,
#: because the case that would have caught it was no longer generated.
WRITTEN_BY_A_RUN = ("SCOREBOARD.md", "SCOREBOARD.txt", "outcomes.json")


@pytest.mark.parametrize("leftover", WRITTEN_BY_A_RUN)
def test_any_one_of_a_run_s_records_is_enough_to_refuse(tmp_path, leftover):
    """`outcomes.json` is the engine state and `SCOREBOARD.txt` is what was
    read; losing either loses the run as surely as losing the Markdown."""
    from datetime import date

    (tmp_path / leftover).write_text("x", encoding="utf-8")
    with pytest.raises(sr.RunWouldOverwrite):
        sr.run_dir(str(tmp_path), "fixed-assets", date(2026, 9, 4))


def test_the_refusal_covers_everything_a_run_writes():
    """And the list it checks is the list a run leaves behind, not a subset."""
    assert set(sr.RUN_RECORDS) == set(WRITTEN_BY_A_RUN)


def test_a_fresh_directory_is_returned_unchanged(tmp_path):
    """The control: without it every test above could pass for the wrong reason."""
    from datetime import date

    assert sr.run_dir(str(tmp_path / "new"), "fixed-assets",
                      date(2026, 9, 4)) == tmp_path / "new"


def test_the_default_is_todays_directory_under_the_desk():
    """The default is what collided, so it is asserted rather than assumed."""
    from datetime import date

    d = sr.run_dir("", "fixed-assets", date(2027, 1, 1))
    assert d.parts[-3:] == ("fixed-assets", "runs", "2027-01-01")


def test_the_shipped_first_run_is_what_the_default_would_have_replaced():
    """The one that matters: pointed at 4 September 2026 with no --out, this
    refuses instead of writing over the run that is committed in this
    repository. That directory is the actual thing the fix protects."""
    from datetime import date

    with pytest.raises(sr.RunWouldOverwrite, match="2026-09-04"):
        sr.run_dir("", "fixed-assets", date(2026, 9, 4))


# ── the queue is written by the run, with the desk in hand ───────────────────

def test_the_run_files_a_near_miss_as_one(tmp_path):
    """Through `queue_refusals`, which is what the script actually calls.

    Asserting the label on `from_refusal` alone left the call site free to stop
    passing the desk with the suite green — the helper proved and its caller
    not, which is the mistake this repository keeps recording. On the second
    scoreboard 12 of 16 frontier entries were near misses filed as ordinary
    refusals, and this is the path that filed them.
    """
    import engine
    import scoreboard
    import unsupported

    desk = record.load(DESK)
    p = desk.problems[0]
    held = desk.passages[0].citation
    finer = held + "(99)"

    answer = engine.Answer(position=p.answer, citation=finer)
    run = scoreboard.Run(model="x")
    run.results.append(engine.grade(answer, p, desk))
    assert run.results[0].outcome is engine.Outcome.WRONG_CAUGHT, (
        "the fixture must be a refusal, or this proves nothing")

    path = tmp_path / "UNSUPPORTED.md"
    counts = sr.queue_refusals(desk, run, {p.id: answer}, path)
    assert counts == {"filed": 1, "near_miss": 1}, (
        "the run must report the split, not a total: a total says the desk is "
        "missing authority it already holds"
    )

    entry = unsupported.parse(path.read_text(encoding="utf-8"))[0]
    assert entry.falls_under == held
    assert entry.near_miss


def test_a_refusal_reaching_outside_the_desk_is_not_counted_as_a_near_miss(tmp_path):
    """The control for the split. Without it `near_miss` could equal `filed`
    unconditionally and the line above would still pass."""
    import engine
    import scoreboard

    desk = record.load(DESK)
    p = desk.problems[0]
    answer = engine.Answer(position=p.answer, citation="26 CFR 9.999(z)")
    run = scoreboard.Run(model="x")
    run.results.append(engine.grade(answer, p, desk))

    counts = sr.queue_refusals(desk, run, {p.id: answer},
                               tmp_path / "UNSUPPORTED.md")
    assert counts == {"filed": 1, "near_miss": 0}


# ── what a brain may offer must track what the engine accepts ────────────────

#: The reasons a brain CANNOT observe about itself, named here so the relation
#: below is derived from the engine's set rather than restated beside it.
#:
#: The two fetch reasons describe our own egress and the source's origin;
#: `contradicts_ratified_position` is the engine comparing an answer against the
#: firm's words, which the brain has not been shown; and `model_gave_up` is the
#: harness's word for an abandoned run, never a choice.
UNOBSERVABLE = {"source_blocked_by_us", "source_refuses_us",
                "contradicts_ratified_position", "model_gave_up"}


def test_a_brain_is_offered_every_reason_it_could_observe():
    """DERIVED FROM `engine.REASONS`, not listed beside it.

    A reason the engine accepts and the prompt never mentions is one no brain
    will ever use — it exists in the vocabulary and not in the language. Adding
    `facts_not_established` to the engine while leaving `OFFERABLE` alone broke
    nothing and would have shipped a reason nothing could reach; this is what
    caught it, and it goes red for the next one too.
    """
    assert set(sr.OFFERABLE) == set(engine.REASONS) - UNOBSERVABLE, (
        f"offered but not accepted: "
        f"{sorted(set(sr.OFFERABLE) - set(engine.REASONS))}; "
        f"accepted, observable, and never offered: "
        f"{sorted(set(engine.REASONS) - UNOBSERVABLE - set(sr.OFFERABLE))}"
    )


def test_the_offered_reasons_reach_the_prompt(): 
    """And the set is not merely computed — it is printed where a brain reads
    it. `build_prompt` renders `OFFERABLE` into the template; a set that never
    reached the text would satisfy the test above and change nothing."""
    desk = record.load(DESK)
    prompt = sr.build_prompt(desk.problems[0], desk, shape="index")
    for reason in sr.OFFERABLE:
        assert reason in prompt, f"{reason} is offered but never shown"
