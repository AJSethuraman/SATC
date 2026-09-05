"""The factory: a desk built by interview, proposed and never written.

The factory's whole claim is that a second desk is cheap because a desk is a
definition rather than code. These tests are what stops that claim from being an
argument: the definition it emits is loaded by `record.load`, gated by
`guards.check` and graded by `engine.grade` -- the same three, called by name,
that the hand-built shipped desk goes through.
"""
from __future__ import annotations

from dataclasses import MISSING, fields

import pytest

import engine
import factory
import guards
import record
import routing


# ── fixtures: the smallest desk that is honestly complete ────────────────────

SOURCE = factory.SourceDraft(
    id="S1", title="A public rule", tier="primary", access="public_fetch",
    citation_prefix="26 CFR", checked="2026-09-04", may_store="full_text",
    licence="17 U.S.C. § 105 places a work of the United States Government in "
            "the public domain.",
    url="https://example.invalid/rule",
)

PROBLEMS = (
    factory.ProblemDraft(id="P1", title="x", citation="26 CFR 1",
                         answer="must capitalize", facts="a roof was replaced"),
    factory.ProblemDraft(id="P2", title="y", citation="26 CFR 2",
                         answer="not required to capitalize",
                         facts="a window was refitted"),
)

# THREE PASSAGES FOR TWO PROBLEMS, DELIBERATELY. A corpus that is exactly the
# keyed citations is a bijection, and citing correctly under one is an assignment
# puzzle rather than retrieval -- measured on fixed-assets, 4 Sep 2026 (#244).
PASSAGES = tuple(
    factory.PassageDraft(citation=c, source_id="S1", checked="2026-09-04",
                         text=f"the rule at {c}")
    for c in ("26 CFR 1", "26 CFR 2", "26 CFR 3")
)


def draft(**over) -> factory.DeskDraft:
    kw = dict(name="widgets", title="When a widget is a widget",
              answered_from={"S1": ("widget", "widgets")}, sources=(SOURCE,),
              problems=PROBLEMS, passages=PASSAGES)
    kw.update(over)
    return factory.DeskDraft(**kw)


@pytest.fixture
def checkout(tmp_path):
    """A repository, which is the only thing the factory will write into."""
    (tmp_path / ".git").mkdir()
    return tmp_path


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


# ── what it emits goes through the shipped desk's own three gates ────────────

def test_an_emitted_desk_loads_gates_and_grades_like_a_hand_built_one(checkout):
    """The claim of the whole module, asserted through the shipped code paths.

    Not a parallel check that generated records are fine: `record.load`,
    `guards.check` and `engine.grade` by name. A generated record held to a
    weaker bar is a second definition of what a desk is, and the two would drift.
    """
    desk_dir = factory.emit(draft(), checkout, branch="propose-widgets")

    desk = guards.check(desk_dir)                     # every gate, unchanged
    assert record.load(desk_dir).name == "widgets"    # and it parses
    assert len(desk.problems) == 2 and len(desk.passages) == 3

    p = desk.problems[0]
    graded = engine.grade(engine.Answer(position=p.answer, citation=p.citation),
                          p, desk)
    assert graded.outcome is engine.Outcome.CORRECT

    reg = routing.parse_subjects(
        (desk_dir / "SUBJECTS.md").read_text(encoding="utf-8"), "widgets")
    assert reg.fires_on == ("widget", "widgets")
    assert reg.answered_from == {"S1": ("widget", "widgets")}


def test_the_emitted_record_carries_the_licence_term_into_the_diff(checkout):
    """The evidence lands in `SOURCES.md`, where a reviewer meets it in the pull
    request -- not in whatever session decided it."""
    desk_dir = factory.emit(draft(), checkout, branch="propose-widgets")
    text = (desk_dir / "SOURCES.md").read_text(encoding="utf-8")
    assert "17 U.S.C. § 105" in text
    assert record.load(desk_dir).sources[0].note.startswith("17 U.S.C.")


# ── it writes into a checkout, on a branch, and nowhere else ─────────────────

def test_it_refuses_to_write_anywhere_but_a_checkout(tmp_path):
    """The record is READ from the installed plugin and WRITTEN in the
    repository. A plugin directory is replaced whole on update, so a proposal
    into one is thrown away the next time desk updates -- silently."""
    with pytest.raises(factory.FactoryError, match="not a checkout"):
        factory.emit(draft(), tmp_path, branch="propose-widgets")
    assert not (tmp_path / "desk").exists()


@pytest.mark.parametrize("branch", ["main", "master", "  ", ""])
def test_it_refuses_to_land_a_desk_without_a_pull_request(checkout, branch):
    """Writing onto the branch that ships is not a faster route to the same
    place. It is the firm's yes removed."""
    with pytest.raises(factory.FactoryError, match="pull request|branch"):
        factory.emit(draft(), checkout, branch=branch)
    assert not (checkout / "desk" / "desks" / "widgets").exists()


def test_it_refuses_to_regenerate_a_desk_that_already_exists(checkout):
    factory.emit(draft(), checkout, branch="propose-widgets")
    with pytest.raises(factory.FactoryError, match="already exists"):
        factory.emit(draft(), checkout, branch="propose-widgets")


# ── a desk that fails a gate does not exist ──────────────────────────────────

def test_a_desk_that_fails_a_gate_is_removed_rather_than_left_half_written(checkout):
    """The bijection case, and the rollback in one test.

    Two problems keyed to exactly the two stored citations is the shape #244
    measured: the corpus IS the answer key, so the citation score measures an
    assignment puzzle. The guard refuses it -- and what matters as much is that
    nothing is left behind, because a half-written desk on disk is one a later
    session finds and trusts.
    """
    d = draft(passages=PASSAGES[:2])
    with pytest.raises(factory.FactoryError, match="did not pass the gates"):
        factory.emit(d, checkout, branch="propose-widgets")
    assert not (checkout / "desk" / "desks" / "widgets").exists()


def test_a_problem_citing_authority_the_desk_lacks_is_caught_at_emit(checkout):
    """Every attempt at such a problem would grade `authority_absent`, so the
    denominator would count a row nothing could ever answer."""
    d = draft(problems=PROBLEMS + (
        factory.ProblemDraft(id="P3", title="z", citation="26 CFR 99",
                             answer="must capitalize", facts="f"),))
    with pytest.raises(factory.FactoryError, match="did not pass the gates"):
        factory.emit(d, checkout, branch="propose-widgets")
    assert not (checkout / "desk" / "desks" / "widgets").exists()


def test_text_stored_from_a_source_that_forbids_it_is_caught_at_emit(checkout):
    """The factory cannot route around `stored_text_is_permitted` by emitting
    the passages and the permission in one pass."""
    d = draft(sources=(factory.SourceDraft(
        id="S1", title="A licensed rule", tier="primary", access="public_fetch",
        citation_prefix="26 CFR", checked="2026-09-04"),))   # license_check
    with pytest.raises(factory.FactoryError, match="did not pass the gates"):
        factory.emit(d, checkout, branch="propose-widgets")


# ── render writes nothing ────────────────────────────────────────────────────

def test_render_touches_no_disk(checkout):
    """The interview can show the firm exactly what would be written before
    anything is. `canon-mine`'s `Proposal.ask()` draws the same line."""
    files = factory.render(draft())
    assert set(files) == {"SUBJECTS.md", "SOURCES.md", "PROBLEMS.md",
                          "extracted/S1.md"}
    assert not (checkout / "desk").exists()


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
