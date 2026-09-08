"""What a person is shown does not depend on the SKILL.md a session loaded.

THE DEFECT THIS IS THE ANSWER TO, and it has bitten every Forge run. The Skill
tool served `desk:ask-desk` from a plugin cache that was three releases stale,
then four -- a file with no mention of `unchecked`, none of `passage`, and an
opening snippet that raises. A session following it correctly produces the old
output and has no way to know.

0.7.3 answered that by adding a version check and a `/reload-plugins` note TO
THAT FILE. The tester found the flaw in one sentence: *"the warning you added
lives in the file that does not load [...] Anything that depends on the loaded
SKILL.md being current cannot fix a stale SKILL.md."*

So the layout moves onto the object. `print(out)` is the whole instruction, and
every release that adds a field adds it to what a two-release-old skill prints.

WHAT `__repr__` KEEPS. The counters -- `showed`, `showed_by_source` -- exist to
falsify a model's claim that the desk held nothing. They are for the queue. The
same tester found them printed beside a sentence written for a preparer:
*"pure instrumentation next to a sentence meant for a person."*
"""
import ask
import conftest
import engine

BOOKS = ('IRS Pub. 583 (12/2024), "Reconciling the checking account" '
         '— what the books are updated for')


def _served():
    return conftest.answer_judged("the bank statement shows a $10 service charge and "
                      "nothing for it is in the books", "cash-and-bank",
                      position="an entry in the books", citation=BOOKS,
                      keep=False)


def _escalation():
    return conftest.answer_judged("how do I know if a lease should be booked as an asset",
                      "fixed-assets", escalate="authority_absent",
                      working="Whether a lease puts a right-of-use asset on the "
                              "balance sheet is US GAAP under ASC 842. No desk "
                              "here holds the Codification.",
                      keep=False)


# --------------------------------------------------------------- what serves

def test_printing_a_served_answer_shows_every_field_a_reader_needs():
    out = _served()
    assert isinstance(out, engine.Served)
    shown = str(out)
    for part in (out.position, out.citation, out.tier, out.unchecked, out.passage):
        assert part and part in shown, part[:60]


def test_the_unchecked_sentence_cannot_be_left_off_by_printing():
    """The field existed in 0.7.2 and a stale skill still never printed it.

    Asserted on the FIELD, not on a form of words. The two branches say
    different things by design, and from 0.7.5 the ratified branch is shorter
    again where `alongside` carries the rest — so a test pinned to one phrase
    goes red on a wording change that broke nothing."""
    out = _served()
    assert out.unchecked and out.unchecked in str(out)


def test_the_passage_is_shown_in_full_not_truncated():
    out = _served()
    assert out.passage[-40:] in str(out)


# ------------------------------------------------------------ what refuses

def test_an_escalation_carries_the_working_that_read_the_question():
    """REVERSED 8 SEPTEMBER 2026, AND THE OLD ASSERTION IS KEPT AS A NOTE.

    This used to read `assert str(out).startswith(out.working)` — the working
    LEADS. That was right for 0.7.5, where `working` had just stopped being
    dropped and was the only part worth reading. It is wrong now, and the thing
    that made it wrong is the fix succeeding: the skill pushes for long working,
    got a 900-character paragraph, and a reader meeting that first has started
    forming an answer before reaching "THE DESK DID NOT ANSWER".

    What survives is the part that was always the point: the reasoning written
    by something that read the question comes BACK. Where it sits is asserted
    below, by the tests that reversed it."""
    out = _escalation()
    assert isinstance(out, engine.Refusal)
    assert out.working and out.working in str(out)


def test_the_reason_and_detail_still_reach_the_reader():
    out = _escalation()
    assert out.reason in str(out) and out.detail in str(out)


def test_the_counters_do_not_reach_the_reader():
    """`showed_by_source` is for the queue. THE CONTROL IS THE NEXT TEST."""
    out = _escalation()
    assert out.showed_by_source, "premise: this escalation carries counters"
    shown = str(out)
    assert "showed" not in shown
    assert "showed_by_source" not in shown
    assert str(out.showed) not in shown.split(out.working, 1)[-1]


def test_the_counters_are_still_on_the_repr():
    """They were not deleted -- they moved to where the log reads them."""
    out = _escalation()
    assert "showed_by_source" in repr(out)


# ----------------------------------------------- the skill's own instruction

def test_the_skill_tells_the_agent_to_print_the_object():
    """If this ever goes back to a field list, the stale-file defect returns."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parent.parent
             / "skills" / "be-the-desk" / "SKILL.md").read_text(encoding="utf-8")
    assert "print(out)" in skill
    assert "print(out.position)" not in skill


# ------------------------------------- a refusal leads with its verdict

def test_a_printed_refusal_opens_with_the_verdict_not_the_reasoning():
    """THIS REVERSES 0.7.5, AND BOTH FINDINGS WERE RIGHT.

    0.7.5 put `working` first, because a tester found the escalation "hands the
    caller the least" — true then: `working` was not on the object at all. What
    that fix did not anticipate is that the skill pushes for LONG working, and
    it worked. The next run produced a 900-character paragraph opening *"The
    rule is clear and it is conditional"*.

    The desk session that wrote it, 8 September 2026: *"a reader skimming a
    refusal meets a long paragraph whose opening words here are 'The rule is
    clear and it is conditional' — which reads like the beginning of an answer —
    and only reaches 'THE DESK DID NOT ANSWER' once they have already started
    forming one. The verdict is the one line that must not be missed and it is
    the last thing rendered."*

    So: `working` must come back, and it must not come back FIRST. `Served`
    puts its conclusion at the top; a refusal that inverts that teaches a reader
    the shape means nothing."""
    out = _escalation()
    first = str(out).splitlines()[0]
    assert first.startswith("THE DESK DID NOT ANSWER"), first
    assert out.reason in first


def test_but_the_working_still_comes_back_in_full():
    """THE CONTROL for the reversal. Leading with the verdict must not become
    dropping the reasoning — that was the 0.7.4 defect this replaced."""
    out = _escalation()
    assert out.working and out.working in str(out)


def test_the_verdict_is_above_the_working_and_not_merely_present():
    out = _escalation()
    shown = str(out)
    assert shown.index("THE DESK DID NOT ANSWER") < shown.index(out.working)


# --------------------------------------------- and it says which desk

def test_a_printed_refusal_names_the_desk_that_made_it():
    """A QUESTION REACHES MORE THAN ONE DESK. The forklift question routed to
    two on 8 September and came back as two refusals for two DIFFERENT reasons
    — one a hole in our own file, one a fact about the transaction nobody had
    stated. The desk session: *"Both refusals above are distinguishable only
    because I typed the headings myself. Print two in a row without them and
    you have two anonymous paragraphs."*

    `Served` never had this problem: its citation identifies where it came from.
    A refusal cites nothing — that is what makes it a refusal."""
    out = _escalation()
    assert out.desk == "fixed-assets"
    assert "fixed-assets" in str(out).splitlines()[0]


def test_two_refusals_to_one_question_are_told_apart():
    """THE CASE IT EXISTS FOR, and it is the real one from the live run."""
    seen = {}
    for name, reason in (("fixed-assets", "facts_not_established"),
                         ("capitalization-and-de-minimis", "context_not_on_file")):
        out = conftest.answer_judged("we bought a forklift, deducted or capitalized", name,
                         escalate=reason, working="the rule is conditional and "
                         "the condition is not on file",
                         ask="What was the invoice amount?", keep=False)
        seen[name] = str(out).splitlines()[0]
    assert len(set(seen.values())) == 2, seen
    for name, line in seen.items():
        assert name in line


def test_the_desk_is_stamped_at_one_place_not_at_each_refusal():
    """`serve` refuses at three points today and a fourth will be added. The
    stamp is a wrapper so a new `return Refusal(...)` inherits it rather than
    quietly shipping an anonymous one."""
    import inspect
    assert "_serve" in inspect.getsource(engine.serve)
    assert inspect.getsource(engine.serve).count("Refusal") <= 3


def test_the_asking_skill_tells_the_doer_not_to_read_the_desks():
    """IT USED TO ASSERT THEY COULD NOT, AND THEY COULD.

    `ask-desk` opened with *"You do not hold the desks and you cannot read
    them."* A doer on 8 September read five files out of `desk/desks/` before
    sending anything — it is in the same checkout — and named the defect
    exactly: *"a check that runs on the honour system, because the skill does
    not ask the doer to refrain, it asserts they are unable. A doer who reads
    that sentence, notices the files, and infers the skill is describing some
    other deployment has been given no rule to follow."*

    A rule can be followed. A false statement about capability cannot."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "the rule is do not read them" in skill, "no rule, only a claim"
    # NARROWED, AND FOR THE REASON THIS FILE KEEPS RE-LEARNING: a guard that
    # forbids the STRING forbids the skill from quoting the defect it records,
    # which makes the record unwritable. What must not come back is the ASSERTION
    # — the sentence stated as fact rather than quoted as the thing that was
    # wrong. So the old wording is allowed only on a line that says it is old.
    live = [ln for ln in skill.splitlines()
            if "cannot read them" in ln and "used to say" not in ln]
    assert not live, (
        f"the skill asserts an inability the doer does not have: {live}")


def test_the_asking_skill_does_not_pass_python_into_a_tool_call():
    """`prompt=relay.as_prompt(a)` cannot be done: one is a Python expression,
    the other a harness tool in a different execution context. A doer had to
    invent the copy step — *"an invented step and a transcription risk on a
    multi-hundred-word string"* — so the skill says print, then copy."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "paste the printed envelope here" in skill
    # IN A FENCED BLOCK ONLY. The prose quotes the broken form while explaining
    # it; what must not survive is a block a doer would copy.
    import re
    fenced = "\n".join(re.findall(r"```[a-z]*\n(.*?)```", skill, re.S))
    assert "relay.as_prompt(a)" not in fenced.split("print(relay.as_prompt(a))")[-1], (
        "a copyable block still passes a Python expression into a tool call")


def test_the_asking_skill_describes_a_refusal_as_well_as_an_answer():
    """The single "what comes back" table listed `unchecked`, `passage` and
    `alongside` and read as universal. A refusal carries none of them."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "If it REFUSED" in skill
    assert "| `working` |" in skill and "| `ask` |" in skill


def test_the_asking_skill_says_what_to_do_if_no_answer_comes():
    """It forbade chasing and never said what to do when the answer genuinely
    is not coming. A doer invented a fallback: *"doer ends turn, nothing ever
    wakes it, task dies without a word — is worse than the chasing the skill
    correctly prohibits."*"""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    # ASSERTED ON THE INSTRUCTION, NOT ON A PHRASE THE QUOTATION ALSO CONTAINS.
    # The first version checked for "fallback reminder", which survives in the
    # doer's quoted words below — so deleting the actual instruction left this
    # green. Caught by mutation M31, 8 September.
    instruction = [ln for ln in skill.splitlines()
                   if ln.startswith("**2 · Do not chase")]
    assert instruction, "the rule is no longer a rule"
    assert "set ONE fallback reminder" in "".join(
        skill.split("**2 · Do not chase")[1].split(">")[0]), (
        "the section warns about dying silently and no longer says what to do")
    assert "One reminder is" in skill and "a loop is" in skill


def test_the_asking_skill_routes_a_gap_to_the_research_session():
    """THE FIRM ASKED FOR THIS EXPLICITLY, 8 September 2026: *"the skill also has
    to direct questions to this container when they need research, obviously."*

    `run-down-a-question` had existed since 5 September and nothing connected it:
    a doer got `authority_absent` and the trail stopped there."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "authority_absent` is not a dead end" in skill
    assert "relay.research(" in skill
    assert "research_prompt(" in skill


def _flat(name):
    """A skill as one line. ASSERTING ON RAW MARKDOWN ASSERTS ON ITS LINE WRAPS:
    two of these tests failed on 8 September because the phrase they looked for
    was split across a newline in prose that said exactly the right thing."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "skills" / name
            / "SKILL.md").read_text(encoding="utf-8")
    return " ".join(text.split())


def test_and_says_a_fruitless_search_is_still_a_result():
    flat = _flat("ask-desk")
    assert "is a real result" in flat
    assert "the difference between a queue and a pile" in flat


def test_and_says_a_find_is_not_authority_until_the_firm_admits_it():
    assert "the firm admits a source" in _flat("ask-desk").lower()
