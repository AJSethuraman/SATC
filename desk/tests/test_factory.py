"""The factory: a desk built by interview, proposed and never written.

The factory's whole claim is that a second desk is cheap because a desk is a
definition rather than code. These tests are what stops that claim from being an
argument: the definition it emits is loaded by `record.load`, gated by
`guards.check` and graded by `engine.grade` -- the same three, called by name,
that the hand-built shipped desk goes through.
"""
from __future__ import annotations

import shutil
from dataclasses import MISSING, fields

import pytest

import engine
import factory
import guards
import record
from conftest import CORPUS

# NOT `S1` AND NOT `26 CFR`. The fixture merges into the SHIPPED corpus, which
# already declares both -- so a draft using them would be refused for colliding
# and every emit test would prove the collision check rather than the merge.
# `test_a_source_the_corpus_already_declares_is_refused` is where that is proved
# on purpose.
SOURCE = factory.SourceDraft(
    id="SW1", title="A public rule", tier="primary", access="public_fetch",
    citation_prefix="Widget Standard", checked="2026-09-04",
    may_store="full_text",
    licence="17 U.S.C. § 105 places a work of the United States Government in "
            "the public domain.",
    url="https://example.invalid/rule",
)

PROBLEMS = (
    factory.ProblemDraft(id="WP1", title="x", citation="Widget Standard 1",
                         answer="must capitalize", facts="a roof was replaced"),
    factory.ProblemDraft(id="WP2", title="y", citation="Widget Standard 2",
                         answer="not required to capitalize",
                         facts="a window was refitted"),
)

# THREE PASSAGES FOR TWO PROBLEMS, DELIBERATELY. A corpus that is exactly the
# keyed citations is a bijection, and citing correctly under one is an assignment
# puzzle rather than retrieval -- measured on fixed-assets, 4 Sep 2026 (#244).
PASSAGES = tuple(
    factory.PassageDraft(citation=c, source_id="SW1", checked="2026-09-04",
                         text=f"the rule at {c}")
    for c in ("Widget Standard 1", "Widget Standard 2", "Widget Standard 3")
)


def draft(**over) -> factory.DeskDraft:
    kw = dict(name="widgets", title="When a widget is a widget",
              answered_from={"SW1": ("widget", "widgets")}, sources=(SOURCE,),
              problems=PROBLEMS, passages=PASSAGES)
    kw.update(over)
    return factory.DeskDraft(**kw)


@pytest.fixture
def checkout(tmp_path):
    """A repository holding THE SHIPPED CORPUS, which is what a proposal merges
    into and the only thing the factory will write to.

    A toy corpus here would make these tests pass over a record that does not
    exist. Until 11 September 2026 there was no corpus in this fixture at all,
    because `emit` wrote a fresh `desk/desks/<name>/` directory -- it passed,
    and what it wrote was unreadable by the answering path. The fixture is the
    real thing so that a merge which cannot land is a red test here.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "desk").mkdir()
    shutil.copytree(CORPUS, tmp_path / "desk" / "corpus")
    return tmp_path


def _untouched(checkout) -> bool:
    """Nothing was written. A refusal that leaves half a subject behind is one a
    later session finds and trusts -- and with one shared corpus the half is not
    in a directory somebody can delete, it is inside the record."""
    live = record.load(checkout / "desk" / "corpus")
    return (not any(s.id == "SW1" for s in live.sources)
            and not any(p.id.startswith("WP") for p in live.problems)
            and not any(q.citation.startswith("Widget Standard")
                        for q in live.passages))


# ── the interview asks for everything the record requires ────────────────────

def test_the_interview_covers_every_field_the_record_requires():
    """Derived from `record.py`, never listed here.

    An interview and a parser are two ways of asking what a desk needs, and two
    ways of asking one question drift -- `guards.every_problem_has_authority`
    already drifted from `engine._check` exactly this way and was the one that
    was wrong. Adding a required field to `Source` or `Problem` turns this red
    until the interview asks about it, instead of producing desks missing it.
    """
    required = {
        f"{kind}.{f.name}"
        for kind, cls in (("source", record.Source), ("problem", record.Problem))
        for f in fields(cls)
        if f.default is MISSING and f.default_factory is MISSING
    } | {"desk.name", "subject.title", "subject.fires_on",
         "subject.answered_from"}

    asked = {r for q in factory.QUESTIONS for r in q.records}
    assert not (required - asked), (
        f"the record requires {sorted(required - asked)} and the interview never "
        f"asks; a desk emitted from it would fail to parse or would carry a "
        f"field nobody supplied"
    )


def test_every_question_carries_what_taught_us_to_ask_it():
    """A question with no provenance is one somebody thought sounded thorough.

    #229: the interview's questions must be traceable to what building the
    fixed-assets desk actually required. An interview authored before anyone had
    built a desk would ask the wrong things confidently, and the firm would have
    to live with the answers.
    """
    for q in factory.QUESTIONS:
        assert q.why.strip(), f"{q.id} asks {q.asks!r} for no recorded reason"
        assert q.asks.strip() and q.records, f"{q.id} is not a question"


# ── a licence is read off the source, or it is not answered ──────────────────

def test_permission_to_store_cannot_be_constructed_without_its_term():
    """Not warned about -- impossible. A guessed licence is the one mistake in
    this module that reaches outside this repository."""
    with pytest.raises(factory.FactoryError, match="no licence term recorded"):
        factory.SourceDraft(id="S1", title="t", tier="primary",
                            access="public_fetch", citation_prefix="26 CFR",
                            checked="2026-09-04", may_store="full_text")


def test_the_default_stores_nothing_and_so_needs_no_term():
    """`license_check` is the answer when the terms could not be established,
    and it is the only one that needs no evidence behind it."""
    s = factory.SourceDraft(id="S1", title="t", tier="primary",
                            access="public_fetch", citation_prefix="26 CFR",
                            checked="2026-09-04")
    assert s.may_store == "license_check"


def test_a_vocabulary_typo_is_a_failure_and_not_a_branch():
    with pytest.raises(factory.FactoryError, match="tier is 'Primary'"):
        factory.SourceDraft(id="S1", title="t", tier="Primary",
                            access="public_fetch", citation_prefix="26 CFR",
                            checked="2026-09-04")


# ── a desk that cannot be scored cannot be proposed ──────────────────────────

def test_a_desk_with_no_problem_set_is_refused():
    """There would be no number to read, so nothing would distinguish it from a
    desk that guesses well."""
    with pytest.raises(factory.FactoryError, match="no problem set"):
        draft(problems=())


def test_a_desk_with_no_sources_is_refused():
    with pytest.raises(factory.FactoryError, match="no sources"):
        draft(sources=())


def test_a_desk_nothing_routes_to_is_refused():
    with pytest.raises(factory.FactoryError, match="no subjects answered"):
        draft(answered_from={})


def test_a_source_that_answers_nothing_is_refused():
    """A named source with an empty subject list declares nothing, and would
    silently make every citation for those subjects uncheckable."""
    with pytest.raises(factory.FactoryError, match="no subjects answered"):
        draft(answered_from={"S1": ()})


# ── what it emits goes into the ONE corpus, and is reachable from there ──────

def test_an_emitted_subject_lands_in_the_corpus_the_answering_path_reads(checkout):
    """THE TEST THAT WOULD HAVE CAUGHT IT. Not "the emitted files are well
    formed" -- they always were. The claim is that a proposal merged this way is
    part of the record a question reaches, and the only way to say that is to
    load the corpus afterwards and find the subject in it.

    Until 11 September 2026 `emit` wrote `desk/desks/<name>/`, which `dec-kill`
    had deleted the day before. Every gate passed. Nothing loaded it.
    """
    before = record.load(checkout / "desk" / "corpus")
    corpus_dir = factory.emit(draft(), checkout, branch="propose-widgets")
    assert corpus_dir == checkout / "desk" / "corpus", (
        "it wrote somewhere other than the one corpus")

    desk = guards.check(corpus_dir)                   # every gate, unchanged
    assert len(desk.problems) == len(before.problems) + 2
    assert len(desk.passages) == len(before.passages) + 3
    assert len(desk.sources) == len(before.sources) + 1

    # and the merge did not cost the corpus anything it already held
    assert {s.id for s in before.sources} < {s.id for s in desk.sources}
    assert {q.citation for q in before.passages} < {q.citation for q in desk.passages}

    p = next(p for p in desk.problems if p.id == "WP1")
    graded = engine.grade(engine.Answer(position=p.answer, citation=p.citation),
                          p, desk)
    assert graded.outcome is engine.Outcome.CORRECT


def test_the_declared_subjects_come_back_out_of_the_merged_file(checkout):
    """`parse_subjects` reads `blocks[0]` AND NOTHING ELSE. A `## widgets`
    heading appended to SUBJECTS.md parses, reviews and merges cleanly, and is
    read by nobody -- the same silent nothing as the wrong directory, one file
    down. So the merge puts the declarations INSIDE the corpus's own block, and
    this is what says it arrived."""
    corpus_dir = factory.emit(draft(), checkout, branch="propose-widgets")
    reg = record.parse_subjects(
        (corpus_dir / "SUBJECTS.md").read_text(encoding="utf-8"), "corpus")
    assert reg.answered_from["SW1"] == ("widget", "widgets")
    assert "widget" in reg.fires_on and "widgets" in reg.fires_on
    # ONE heading, the corpus's own. A second one parses and is never read.
    assert (corpus_dir / "SUBJECTS.md").read_text(
        encoding="utf-8").count("\n## ") == 1, (
        "a second heading was added; everything under it is unread")


def test_the_emitted_record_carries_the_licence_term_into_the_diff(checkout):
    """The evidence lands in `SOURCES.md`, where a reviewer meets it in the pull
    request -- not in whatever session decided it."""
    corpus_dir = factory.emit(draft(), checkout, branch="propose-widgets")
    text = (corpus_dir / "SOURCES.md").read_text(encoding="utf-8")
    assert "17 U.S.C. § 105" in text
    assert next(s for s in record.load(corpus_dir).sources
                if s.id == "SW1").note.startswith("17 U.S.C.")


# ── it proposes; it does not overwrite ───────────────────────────────────────

def test_a_source_the_corpus_already_declares_is_refused(checkout):
    """The interview covered ground already recorded. That is a diff somebody
    reads, not a regeneration -- and picking silently between two texts for one
    citation is exactly what `one_corpus.py` had to REPORT rather than perform."""
    held = record.load(checkout / "desk" / "corpus").sources[0]
    d = draft(sources=(factory.SourceDraft(
        id=held.id, title="mine", tier="primary", access="public_fetch",
        citation_prefix="Widget Standard", checked="2026-09-04",
        may_store="full_text", licence="17 U.S.C. § 105"),),
        answered_from={held.id: ("widget",)})
    with pytest.raises(factory.FactoryError, match="already declared"):
        factory.emit(d, checkout, branch="propose-widgets")


def test_a_citation_the_corpus_already_stores_is_refused(checkout):
    """Two texts under one citation is the six truncations `dec-kill` found, and
    the reason the merge there reported every drop instead of performing it."""
    held = record.load(checkout / "desk" / "corpus").passages[0]
    d = draft(passages=PASSAGES + (factory.PassageDraft(
        citation=held.citation, source_id="SW1", checked="2026-09-04",
        text="a shorter extract of the same rule"),))
    with pytest.raises(factory.FactoryError, match="already stored"):
        factory.emit(d, checkout, branch="propose-widgets")


# ── it writes into a checkout, on a branch, and nowhere else ─────────────────

def test_it_refuses_to_write_anywhere_but_a_checkout(tmp_path):
    """The record is READ from the installed plugin and WRITTEN in the
    repository. A plugin directory is replaced whole on update, so a proposal
    into one is thrown away the next time desk updates -- silently."""
    with pytest.raises(factory.FactoryError, match="not a checkout"):
        factory.emit(draft(), tmp_path, branch="propose-widgets")
    assert not (tmp_path / "desk").exists()


def test_it_refuses_a_checkout_with_no_corpus_rather_than_making_one(tmp_path):
    """A new directory beside the corpus is a record nothing loads, which is the
    defect this whole change is about. It refuses instead of inventing a home."""
    (tmp_path / ".git").mkdir()
    with pytest.raises(factory.FactoryError, match="no corpus at"):
        factory.emit(draft(), tmp_path, branch="propose-widgets")
    assert not (tmp_path / "desk").exists()


@pytest.mark.parametrize("branch", ["main", "master", "  ", ""])
def test_it_refuses_to_land_a_desk_without_a_pull_request(checkout, branch):
    """Writing onto the branch that ships is not a faster route to the same
    place. It is the firm's yes removed."""
    with pytest.raises(factory.FactoryError, match="pull request|branch"):
        factory.emit(draft(), checkout, branch=branch)
    assert _untouched(checkout)


def test_it_refuses_to_propose_the_same_subject_twice(checkout):
    factory.emit(draft(), checkout, branch="propose-widgets")
    with pytest.raises(factory.FactoryError, match="already declared"):
        factory.emit(draft(), checkout, branch="propose-widgets")


# ── a desk that fails a gate does not exist ──────────────────────────────────

def test_the_bijection_guard_still_fires_although_the_corpus_dilutes_it(checkout):
    """THE GUARD THE MERGE WOULD HAVE RETIRED, and the reason `emit` grades
    twice.

    Two problems keyed to exactly the two stored citations is the shape #244
    measured: the authority IS the answer key, so the citation score is an
    assignment puzzle. `authority_is_more_than_the_answer_key` compares two SETS
    -- and merged into 785 other passages that comparison can never be equal
    again, so grading only the merge would have let this through while looking
    like more checking rather than less. The proposal is graded alone as well,
    and this is what proves it.
    """
    d = draft(passages=PASSAGES[:2])
    with pytest.raises(factory.FactoryError,
                       match="gates a hand-built subject"):
        factory.emit(d, checkout, branch="propose-widgets")
    assert _untouched(checkout)


def test_a_problem_citing_authority_the_subject_lacks_is_caught_at_emit(checkout):
    """Every attempt at such a problem would grade `authority_absent`, so the
    denominator would count a row nothing could ever answer."""
    d = draft(problems=PROBLEMS + (
        factory.ProblemDraft(id="WP3", title="z", citation="Widget Standard 99",
                             answer="must capitalize", facts="f"),))
    with pytest.raises(factory.FactoryError, match="did not pass the gates"):
        factory.emit(d, checkout, branch="propose-widgets")
    assert _untouched(checkout)


def test_text_stored_from_a_source_that_forbids_it_is_caught_at_emit(checkout):
    """The factory cannot route around `stored_text_is_permitted` by emitting
    the passages and the permission in one pass."""
    d = draft(sources=(factory.SourceDraft(
        id="SW1", title="A licensed rule", tier="primary",
        access="public_fetch", citation_prefix="Widget Standard",
        checked="2026-09-04"),))                              # license_check
    with pytest.raises(factory.FactoryError, match="did not pass the gates"):
        factory.emit(d, checkout, branch="propose-widgets")
    assert _untouched(checkout)


# ── render writes nothing ────────────────────────────────────────────────────

def test_render_touches_no_disk(checkout):
    """The interview can show the firm exactly what would be written before
    anything is. `canon-mine`'s `Proposal.ask()` draws the same line."""
    files = factory.render(draft())
    assert set(files) == {"SUBJECTS.md", "SOURCES.md", "PROBLEMS.md",
                          "extracted/SW1.md"}
    assert _untouched(checkout)


# ── the skill has to reach other machines to be worth anything ───────────────

def test_the_plugin_version_agrees_with_the_marketplace():
    """A plugin cache is keyed on the MARKETPLACE version, not the plugin's own.

    Bump one and not the other and every machine keeps serving the old copy
    while both files look right in a diff. This session watched that happen to
    canon; the factory ships as a skill, so a desk plugin that never reaches
    another machine is a factory nobody can run.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    mine = json.loads((root / "desk" / ".claude-plugin" / "plugin.json")
                      .read_text(encoding="utf-8"))
    market = json.loads((root / ".claude-plugin" / "marketplace.json")
                        .read_text(encoding="utf-8"))
    listed = next(p for p in market["plugins"] if p["name"] == "desk")
    assert listed["version"] == mine["version"], (
        f"marketplace lists desk {listed['version']}, plugin.json says "
        f"{mine['version']}; installs would keep the cached copy"
    )


def test_the_factory_ships_as_a_skill():
    """`factory.py` with no SKILL.md beside it is a module nobody invokes."""
    from pathlib import Path
    skill = Path(__file__).resolve().parents[1] / "skills" / "desk-factory" / "SKILL.md"
    assert skill.is_file(), "desk-factory/SKILL.md is missing"
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---\nname: desk-factory\n"), "no skill frontmatter"


def test_the_skills_worked_example_names_fields_the_draft_actually_has():
    """A skill IS the interface for an agent following it, so a renamed field is
    a broken interface even with every test green.

    `DeskDraft` lost `fires_on` when a desk started declaring which SOURCE
    answers which subject (#266), and the skill's Phase 2 example went on
    passing it — `TypeError: unexpected keyword argument 'fires_on'` before an
    agent could render a single proposal. Found by Codex on #264.
    """
    import dataclasses
    import re
    from pathlib import Path

    import factory

    text = (Path(__file__).resolve().parents[1] / "skills" / "desk-factory"
            / "SKILL.md").read_text(encoding="utf-8")
    call = re.search(r"factory\.DeskDraft\((.*?)\)\n", text, re.S)
    assert call, "the skill no longer shows a DeskDraft call; show the real one"

    named = set(re.findall(r"(\w+)=", call.group(1)))
    fields = {f.name for f in dataclasses.fields(factory.DeskDraft)}
    assert named <= fields, (
        f"the skill passes {sorted(named - fields)}, which DeskDraft does not "
        f"have; an agent following it gets a TypeError")
    required = {f.name for f in dataclasses.fields(factory.DeskDraft)
                if f.default is dataclasses.MISSING
                and f.default_factory is dataclasses.MISSING}
    assert required <= named, (
        f"the skill omits {sorted(required - named)}, which has no default")
