"""Build a desk by interview: propose the definition, never write the record.

A DESK IS A DEFINITION, NOT CODE. Subjects, sources with their tiers and storage
rules, a problem set, and the two record stores. That is what makes a second desk
cheap: this module fills in a form, it compiles nothing, and the engine that
grades a hand-built desk is the engine that grades this one.

WHAT THIS MODULE REFUSES TO DO, AND WHY EACH REFUSAL IS CODE RATHER THAN PROSE.
Canon's mining skill draws the same line one level up: it surfaces passages, a
person decides, and there is no fourth step where something gets written on its
own. Here:

  - A source whose storage permission was not read off the source's own terms
    cannot be constructed at all. Not warned about -- `SourceDraft` raises. A
    guessed licence is the one mistake in this file that reaches outside it.
  - A desk with no problem set cannot be constructed. A desk that cannot be
    scored is a claim.
  - `emit` writes into a git checkout and nowhere else, so the installed plugin
    -- which is replaced whole on update -- can never be the thing that changed.
  - `emit` runs `guards.check` over what it just wrote and DELETES IT on failure.
    A factory-built desk passes exactly the gates a hand-built one does, or it
    does not exist. There is deliberately no weaker path for generated records.

The pull request is the firm's yes. Nothing here is a substitute for it.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import guards
import record


class FactoryError(Exception):
    """A desk that could not be proposed. Never downgraded to a warning."""


#: Branches a proposal may not land on. The record changes by pull request, so
#: writing straight onto the branch that ships is not a shortcut, it is the
#: mechanism removed.
PROTECTED = ("main", "master")


# ── the interview ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Question:
    """One thing the interview must ask, and the thing that taught us to ask it.

    `records` names the record fields the answer fills, and a test compares that
    set against the fields `record.py` requires -- so a new required field turns
    the interview red until it asks about it. An interview and a parser are two
    ways of asking what a desk needs, and two ways of asking one question drift.
    `guards.every_problem_has_authority` already drifted from `engine._check`
    exactly this way and was the one that was wrong.

    `why` is the provenance: what building the fixed-assets desk by hand actually
    required. A question with no provenance is one somebody thought sounded
    thorough, and the firm has to live with the answer.
    """
    id: str
    asks: str
    records: tuple[str, ...]
    why: str


QUESTIONS: tuple[Question, ...] = (
    Question(
        id="Q1",
        asks="What does this desk answer on -- one line, and the folder name it "
             "lives under?",
        records=("desk.name", "subject.title"),
        why="`routing.parse_subjects` refuses a heading that disagrees with the "
            "directory. A stale name still matched on the way in, so the refusal "
            "that names a desk sent the caller to one that does not exist -- the "
            "deterministic recovery path pointing away from the record that "
            "produced it.",
    ),
    Question(
        id="Q2",
        asks="Which words in a question mean it belongs to this desk? List the "
             "inflections you actually expect, not the stems.",
        records=("subject.fires_on",),
        why="Routing matches whole words only, so it under-fires on purpose: "
            "`defer` does not fire on `deferring`, and substring matching once "
            "made *extension* fire on *extensive*. fixed-assets lists capitalize, "
            "capitalise, capitalized, capitalised and capitalization separately "
            "for that reason. Loosening the rule is what teaches somebody to stop "
            "reading the output.",
    ),
    Question(
        id="Q3",
        asks="Where is the authority? Name each body of it and give its URL.",
        records=("source.id", "source.title", "source.url"),
        why="`parse_sources` raises rather than loading a desk with none: a desk "
            "with no authority cannot answer, and an empty source list is the "
            "shape that would otherwise reach the engine as a desk that escalates "
            "everything and looks disciplined doing it.",
    ),
    Question(
        id="Q4",
        asks="Does this source settle a question on its own, or is it somebody's "
             "reading of one that does? (primary / secondary / tertiary)",
        records=("source.tier",),
        why="Tier is what decides whether this desk can escalate at all: "
            "`authority_permits_choice` fires only on secondary or tertiary "
            "authority. Every fixed-assets problem rested on one binding primary "
            "source, so across 42 measured answers the escalation half of the "
            "design could not trigger once and went untested from both sides "
            "(#245). A desk built entirely on primary authority is answering the "
            "questions the software already settles.",
    ),
    Question(
        id="Q5",
        asks="How is this source reached -- an ordinary fetch, a browser, a "
             "signed-in browser, or not by a machine at all?",
        records=("source.access",),
        why="Declared, never discovered by failing. If a failed fetch were what "
            "reached for a heavier client, a site refusing automated access would "
            "be the thing that triggered one. `human_only` is not a stricter "
            "fetch, it is the absence of one -- FASB ASC's licence forbids the "
            "content reaching a model by any route, so nothing rescues it.",
    ),
    Question(
        id="Q6",
        asks="What do this source's OWN terms say may be copied into the "
             "repository? Quote the term you read it from.",
        records=("source.may_store", "source.licence"),
        why="§ 1.263(a)-3 is storable in full because 17 U.S.C. § 105 places a "
            "work of the United States Government in the public domain -- a term "
            "read off the source, not an assumption about government documents. "
            "Where no term can be produced the answer is `license_check`, which "
            "stores nothing. A licence the firm holds may permit an internal "
            "copy, which is why this is a fact recorded per source rather than "
            "one policy over all of them.",
    ),
    Question(
        id="Q7",
        asks="What does a citation into this source look like? Give the prefix "
             "every one of them starts with.",
        records=("source.citation_prefix",),
        why="Positions are matched to their source by citation prefix rather than "
            "by an id. A prefix matching zero sources produced a desk that loaded "
            "clean and raised the first time anybody asked that exact question; "
            "two sources whose prefixes both match is the same defect wearing the "
            "other face, with file order deciding the tier served.",
    ),
    Question(
        id="Q8",
        asks="What day did a person last confirm this entry against the source "
             "itself?",
        records=("source.checked",),
        why="A citation with no date is a claim about the present that nobody "
            "re-examines, and `staleness` reports off this field. It is checked "
            "against the calendar and not only against the digit layout, because "
            "2026-02-31 parsed as a date-shaped string and then crashed the "
            "report instead of failing the load.",
    ),
    Question(
        id="Q9",
        asks="What are the worked problems, and where does each answer come "
             "from? Whose conclusion is it?",
        records=("problem.id", "problem.title", "problem.citation",
                 "problem.answer", "problem.facts"),
        why="The answers must not be ours. fixed-assets scores against the "
            "regulation's own worked examples, which is what makes the "
            "denominator mean anything: a score against answers we wrote measures "
            "agreement, not correctness. Note that several of its titles name the "
            "outcome, so a title is withheld from the model along with the answer.",
    ),
    Question(
        id="Q10",
        asks="Is the authority you would store the same text the answers are read "
             "from? If it is, what would you store instead?",
        records=("desk.corpus_is_not_the_key",),
        why="Measured on fixed-assets, 4 September 2026: 21 problems, 21 stored "
            "passages, one citation each and a bijection between them. The "
            "authority corpus WAS the answer key, so citing correctly was an "
            "assignment puzzle and the citation number was uninterpretable "
            "(#244). The corpus is now the section's 172 operative rule "
            "paragraphs and the answers are read from the analysis withheld from "
            "the facts. `guards.authority_is_more_than_the_answer_key` fails the "
            "build on the bijection rather than trusting this question to be "
            "asked.",
    ),
)


# ── the draft ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SourceDraft:
    """One proposed source. Refuses to exist if its licence was guessed at.

    `licence` is the term the storage answer was read from, and it renders into
    the record's `Why` field, where a reviewer meets it in the pull request diff
    rather than having to take the factory's word for it.
    """
    id: str
    title: str
    tier: str
    access: str
    citation_prefix: str
    checked: str
    may_store: str = "license_check"
    licence: str = ""
    url: str = ""

    def __post_init__(self) -> None:
        where = f"source {self.id}"
        for value, allowed, label in ((self.tier, record.TIERS, "tier"),
                                      (self.access, record.ACCESS, "access"),
                                      (self.may_store, record.MAY_STORE,
                                       "may_store")):
            if value not in allowed:
                raise FactoryError(
                    f"{where}: {label} is {value!r}; must be one of "
                    f"{', '.join(allowed)}")
        if self.may_store != "license_check" and not self.licence.strip():
            raise FactoryError(
                f"{where}: may_store={self.may_store!r} with no licence term "
                f"recorded. The storage answer is read off the source's own "
                f"terms or it is not made: quote the term, or leave this at "
                f"license_check, which stores nothing."
            )
        if not self.citation_prefix.strip():
            raise FactoryError(
                f"{where}: no citation prefix. Positions resolve to their source "
                f"by prefix, so a source without one can hold no position.")


@dataclass(frozen=True)
class ProblemDraft:
    """One proposed problem. The answer is somebody else's conclusion."""
    id: str
    title: str
    citation: str
    answer: str
    facts: str

    def __post_init__(self) -> None:
        for name in ("title", "citation", "answer", "facts"):
            if not getattr(self, name).strip():
                raise FactoryError(f"problem {self.id}: no {name}")


@dataclass(frozen=True)
class PassageDraft:
    """One piece of authority text the interview gathered.

    THE DESK IS NOT COMPLETE WITHOUT THESE, AND THAT IS THE POINT. A definition
    whose problems cite authority the desk does not hold fails
    `guards.every_problem_has_authority`, so `emit` refuses it -- every attempt
    at such a problem would grade `authority_absent` and the denominator would
    count rows nothing could ever answer.

    It has a second consequence worth stating rather than discovering: a desk
    whose authority is entirely RATIFIED POSITIONS -- a `human_only` source, say
    -- cannot be emitted at all, because an agent never writes a ratified
    position. Such a desk is proposed in two steps, and the firm's ratification
    is the first of them, not a formality after the fact.
    """
    citation: str
    source_id: str
    checked: str
    text: str

    def __post_init__(self) -> None:
        for name in ("citation", "source_id", "checked", "text"):
            if not getattr(self, name).strip():
                raise FactoryError(f"passage {self.citation!r}: no {name}")


@dataclass(frozen=True)
class DeskDraft:
    """A whole proposed desk. Refuses to exist incomplete."""
    name: str
    title: str
    fires_on: tuple[str, ...]
    sources: tuple[SourceDraft, ...] = field(default_factory=tuple)
    problems: tuple[ProblemDraft, ...] = field(default_factory=tuple)
    passages: tuple[PassageDraft, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name.strip() or "/" in self.name or " " in self.name:
            raise FactoryError(
                f"desk name {self.name!r} is not a directory name; the directory "
                f"is the desk's identity and a refusal hands it back to a caller")
        if not self.title.strip():
            raise FactoryError(f"{self.name}: no one-line subject")
        if not self.fires_on:
            raise FactoryError(
                f"{self.name}: no subjects to fire on. A desk nothing routes to "
                f"is a desk nobody asks.")
        if not self.sources:
            raise FactoryError(
                f"{self.name}: no sources. A desk with no authority cannot "
                f"answer; it can only escalate, and look disciplined doing it.")
        if not self.problems:
            raise FactoryError(
                f"{self.name}: no problem set. A desk that cannot be scored "
                f"cannot be trusted -- there is no number to read, so nothing "
                f"distinguishes it from one that guesses well.")


# ── rendering ─────────────────────────────────────────────────────────────────

_SUBJECTS_PREAMBLE = """# Subjects — what brings this desk into play

`Fires on` is what makes routing deterministic: the subjects that bring a desk
into play. It matches **whole words only** — substring matching once made
*"extension"* fire on *"extensive"*.

**It under-fires, and that is worth knowing.** The list matches a question's
subject, not its shape, so an inflected form is missed: `defer` does not fire on
`deferring`. Add the inflections that matter rather than loosening the rule.

---

"""

_SOURCES_PREAMBLE = """# Sources — what this desk is allowed to rely on

Each entry records **what the source is**, how binding it is, how it may be
reached, and what may be copied here from it. `Checked` is the date a person last
confirmed the entry against the source; a citation with no date is a claim about
the present that nobody re-examines.

**Nothing here is a default.** A source missing any field is a parse error rather
than a guess, because a field that was never read and a field that was empty look
identical downstream. Where a source permits storing, `Why` carries the term that
was read to establish it — not a summary of it.

---

"""

_PROBLEMS_PREAMBLE = """# Problems — the denominator

**The answers are not ours.** Each problem carries a conclusion its own authority
states, which is what makes the denominator mean anything: a score against
answers we wrote measures agreement, not correctness.

**Withhold the conclusion from the facts.** A fact pattern that announces its own
outcome, or that names the paragraph governing it, is answered by copying rather
than by knowing — and a problem set that leaks scores well while proving nothing.

---

"""


_EXTRACTED_PREAMBLE = """# Authority — someone else's words, checkable line by line

Every line here is verifiable against the source named on it, which is why an
agent may write this file and why a large diff can be skimmed. **Judgement does
not live here.** What the firm decided goes in `positions/`, where the diff is
read — `guards.no_positions_in_extracted` fails the build rather than trusting
anyone to notice a position that rode along inside an extraction.

---

"""


def render(draft: DeskDraft) -> dict[str, str]:
    """The files this proposal would add, keyed by name. Writes nothing."""
    subjects = _SUBJECTS_PREAMBLE + (
        f"## {draft.name} · {draft.title}\n\n"
        f"**Fires on:** {', '.join(draft.fires_on)}\n"
    )

    sources = _SOURCES_PREAMBLE + "\n---\n\n".join(
        f"## {s.id} · {s.title}\n\n"
        f"**Tier:** {s.tier} · **Access:** {s.access} · "
        f"**May store:** {s.may_store} · **Checked:** {s.checked}\n\n"
        f"**Citation prefix:** {s.citation_prefix}\n"
        + (f"\n**Url:** {s.url}\n" if s.url else "")
        + (f"\n**Why:** {s.licence}\n" if s.licence else "")
        for s in draft.sources
    )

    problems = _PROBLEMS_PREAMBLE + "\n---\n\n".join(
        f"## {p.id} · {p.title}\n\n"
        f"**Citation:** {p.citation}\n\n"
        f"**Answer:** {p.answer}\n\n"
        f"**Facts:** {p.facts}\n"
        for p in draft.problems
    )

    files = {"SUBJECTS.md": subjects,
             "SOURCES.md": sources,
             "PROBLEMS.md": problems}

    # One file per source, so an extraction diff is read against the source it
    # came from. `guards.no_positions_in_extracted` reads this directory: nothing
    # carrying a Position or Ratified field may be written into it, which is why
    # `PassageDraft` has no field that could become one.
    by_source: dict[str, list[PassageDraft]] = {}
    for q in draft.passages:
        by_source.setdefault(q.source_id, []).append(q)
    for source_id, group in sorted(by_source.items()):
        files[f"extracted/{source_id}.md"] = _EXTRACTED_PREAMBLE + "\n".join(
            f"## {q.citation}\n\n"
            f"**Source:** {q.source_id} · **Checked:** {q.checked}\n\n"
            f"> {q.text}\n"
            for q in group
        )
    return files


# ── emitting ──────────────────────────────────────────────────────────────────

def emit(draft: DeskDraft, repo_root: Path, *, branch: str) -> Path:
    """Write the proposal into a checkout, or write nothing at all.

    Returns the desk directory. The caller commits it and opens a pull request;
    that pull request is the firm's yes, and there is no argument to this
    function that stands in for one.

    IT VALIDATES WHAT IT WROTE THROUGH `guards.check` AND ROLLS BACK ON FAILURE.
    Not through a copy of those rules, and not through a subset of them: a desk
    this emits either passes every gate the shipped desk passes, or it is
    removed and this raises. A generated record held to a weaker bar is a second
    definition of what a desk is, and the two would drift.
    """
    repo_root = Path(repo_root)
    if not (repo_root / ".git").exists():
        raise FactoryError(
            f"{repo_root} is not a checkout. The record is READ from the "
            f"installed plugin and WRITTEN only in the repository -- a plugin "
            f"directory is replaced whole on update, so anything proposed into "
            f"one is thrown away the next time desk updates."
        )
    if branch.strip() in PROTECTED or not branch.strip():
        raise FactoryError(
            f"branch {branch!r}: a desk enters the record by pull request. "
            f"Writing onto {branch!r} is not a faster route to the same place, "
            f"it is the firm's yes removed."
        )

    desk_dir = repo_root / "desk" / "desks" / draft.name
    if desk_dir.exists():
        raise FactoryError(
            f"{desk_dir} already exists. The factory proposes a new desk; "
            f"changing an existing one is a diff somebody reads, not a "
            f"regeneration.")

    desk_dir.mkdir(parents=True)
    (desk_dir / "extracted").mkdir()
    try:
        for name, text in render(draft).items():
            (desk_dir / name).write_text(text, encoding="utf-8")
        guards.check(desk_dir)
    except Exception as exc:
        shutil.rmtree(desk_dir, ignore_errors=True)
        raise FactoryError(
            f"{draft.name} did not pass the gates a hand-built desk passes, so "
            f"nothing was left on disk: {exc}"
        ) from exc
    return desk_dir
