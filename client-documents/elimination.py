"""Does a form eliminate work, or only claim to?

THE FIRM'S TENET, 2 September 2026, in their words:

    "a tenet of any checklist or interview-like form we make ... no matter if
    for clients or internal use, should be it directionally eliminates work
    where possible. for instance, if something is not applicable why would you
    want to answer questions around it"

WHY THIS IS A MODULE AND NOT A SENTENCE. The tenet was already true in
intention: the interview's questions carry `showIf`, the close-out's carry
`applies_to`, and both were written to skip what does not apply. Then
`sorting_amount` -- "How much for the sorting? ($175 minimum)" -- was gated on
`count_sorting != ''` and asked of EVERY client on EVERY return type, because a
blank number is stored as None and `None != ''`. The condition existed, read
correctly, and never once said no.

That is this repository's oldest bug shape: a claim in one place, the behaviour
in another, and nothing comparing them (S31). A condition is a CLAIM that a
question can be eliminated. This module is the thing that compares the claim to
what actually happens, by running the form and watching.

WHAT IT DOES NOT DO. It does not judge whether a form asks too much -- nothing
here knows what a practice needs. It answers one question per condition: is
there any reachable set of answers under which this question is not asked? A
condition that is never false is not eliminating anything, and the person who
wrote it believes it is.

And it reports its denominator (S2). "No dead conditions" is only good news
when it says how many it examined.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

import interview as iv

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Dead:
    """One condition that cannot eliminate its question."""

    form: str
    question: str
    condition: str
    why: str

    def line(self) -> str:
        return f"  {self.form}/{self.question}: {self.condition!r} — {self.why}"


@dataclass
class Sweep:
    """What was examined, and what was found. Both halves are the report."""

    examined: int = 0
    conditional: int = 0
    always: list[str] = field(default_factory=list)
    dead: list[Dead] = field(default_factory=list)

    @property
    def examined_nothing(self) -> bool:
        return self.examined == 0


# The values a question's answer can take, for the purpose of asking whether a
# condition can be false. Not a fixture of real answers: the point is to try the
# shapes a real sitting produces, INCLUDING the ones that caused the bug -- an
# absent answer, and a blank number, which `coerce` turns into None.
def _candidates(question: dict) -> list:
    """Only values a real answer to this question can actually hold.

    THIS FUNCTION IS WHY THE FIRST VERSION OF THIS CHECK WAS USELESS. It
    offered "" as a candidate for every question, found that `count_sorting`
    set to "" hides `sorting_amount`, and pronounced the condition alive --
    while the live bug was that a blank number is coerced to None and the
    question was asked of everybody. A checker that invents values the system
    cannot produce proves the code agrees with the checker (S32). So every
    candidate goes through `coerce`, exactly as both front doors do, and what
    comes out is what a real sitting can hold.
    """
    options = [o["value"] for o in question.get("options") or []]
    raw: list = ["", None]
    raw += options
    if options:
        raw += [[o] for o in options]
        raw.append(list(options))
    if question.get("type") == "number":
        raw += ["0", "1", "7"]

    out: list = []
    for value in raw:
        try:
            coerced = iv.coerce(question, value) if question else value
        except Exception:
            continue
        if coerced not in out:
            out.append(coerced)
    return out


def _referenced(condition: str) -> set[str]:
    """Which question ids a condition reads. Parsed, never evaluated."""
    out: set[str] = set()
    for part in condition.replace(" and ", "|").replace(" or ", "|").split("|"):
        part = part.strip()
        for token in ("==", "!="):
            if token in part:
                out.add(part.split(token)[0].strip())
                break
        else:
            if " in " in part:
                out.add(part.split(" in ")[-1].strip())
    return {o for o in out if o}


def interview_sweep(schema: dict | None = None) -> Sweep:
    """Every `showIf` in the interview, and whether it can ever say no."""
    schema = schema or iv.load_schema()
    questions = {q["id"]: q for _, q in iv.all_questions(schema)}
    sweep = Sweep()

    for qid, q in questions.items():
        sweep.examined += 1
        cond = q.get("showIf")
        if not cond:
            sweep.always.append(qid)
            continue
        sweep.conditional += 1
        reads = _referenced(cond)
        if not reads:
            sweep.dead.append(Dead("interview", qid, cond,
                                   "reads no answer, so nothing can change it"))
            continue

        # Try one referenced question at a time, then all of them together.
        # Exhaustive would be combinatorial; this finds a hiding answer set for
        # every condition this schema actually writes, and says so when it
        # cannot rather than passing quietly.
        hidden = False
        for target in reads:
            other = questions.get(target)
            for value in _candidates(other or {}):
                if not iv.visible(q, {target: value}):
                    hidden = True
                    break
            if hidden:
                break
        if not hidden:
            for value in _candidates(questions.get(sorted(reads)[0]) or {}):
                trial = {t: value for t in reads}
                if not iv.visible(q, trial):
                    hidden = True
                    break
        if not hidden:
            sweep.dead.append(Dead(
                "interview", qid, cond,
                f"no answer to {', '.join(sorted(reads))} hides it, so it is "
                f"asked of everybody"))
    return sweep


def closeout_sweep(path: Path | str | None = None) -> Sweep:
    """Every `applies_to` in the close-out, and whether it can ever say no.

    The close-out is an internal checklist, and the firm's tenet says plainly
    that internal ones are held to the same rule as the ones a client sees.
    """
    path = Path(path or ROOT / "registry" / "closeout.yaml")
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    kinds = {k for q in spec.get("questions", [])
             for k in (q.get("applies_to") or [])}
    sweep = Sweep()

    for q in spec.get("questions", []):
        sweep.examined += 1
        applies = q.get("applies_to")
        if not applies:
            sweep.always.append(q["id"])
            continue
        sweep.conditional += 1
        if kinds and set(applies) >= kinds:
            sweep.dead.append(Dead(
                "closeout", q["id"], f"applies_to: {applies}",
                "names every return type this file knows, so it is asked of "
                "everybody and the list only looks like a filter"))
    return sweep


def report(sweeps: dict[str, Sweep]) -> list[str]:
    """The whole sweep as lines, denominator first."""
    out: list[str] = []
    for name, s in sweeps.items():
        if s.examined_nothing:
            out.append(f"  {name}: NOTHING EXAMINED — this form has no questions "
                       f"to read, which is not the same as a form that eliminates "
                       f"well")
            continue
        out.append(f"  {name}: {s.conditional} conditional of {s.examined} "
                   f"question(s) examined; {len(s.always)} asked of everybody")
        for d in s.dead:
            out.append(d.line())
    return out


def sweep_all() -> dict[str, Sweep]:
    return {"interview": interview_sweep(), "closeout": closeout_sweep()}
