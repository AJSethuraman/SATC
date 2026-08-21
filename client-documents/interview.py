"""Run `registry/interview.yaml` — the consultation call, as a question flow.

The schema has always described the interview: seven sections, thirty
questions, branching, prefill from the website intake, and a mapping from every
answer to a registry field. Nothing asked them, so a record was filled by hand
in a text editor and the pipeline went unused.

This is the engine, deliberately with no front end in it. `next_question` and
`answer` drive a flow; `compose` turns answers into merge fields. A terminal
front end lives in `cli.py`; a web one could reuse every line of this.

Two things are done here rather than left to the caller, because getting either
wrong is silent:

1. **`showIf` is parsed, not `eval`-ed.** These conditions decide whether a
   spouse signs and whether a predecessor is contacted. A condition that
   mis-evaluates is worse than one that raises, so anything the grammar does
   not cover is an error rather than a guess.
2. **Composition is explicit.** Several questions feed one field --
   `FederalReturns` is the form plus its schedules -- and an empty list is
   "None" rather than blank, because with foreign reporting in scope those are
   different statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "registry" / "interview.yaml"


class InterviewError(RuntimeError):
    pass


# ── the schema ─────────────────────────────────────────────────────────────

def load_schema(path: Path | str = SCHEMA) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def all_questions(schema: dict):
    """(section, question) in asking order."""
    for section in schema["sections"]:
        for q in section["questions"]:
            yield section, q


# ── showIf ─────────────────────────────────────────────────────────────────

_EQ = re.compile(r"^\s*(\w+)\s*(==|!=)\s*'([^']*)'\s*$")
_IN = re.compile(r"^\s*'([^']*)'\s+in\s+(\w+)\s*$")


def _clause(text: str, answers: dict) -> bool:
    m = _EQ.match(text)
    if m:
        qid, op, literal = m.groups()
        value = answers.get(qid)
        return (value == literal) if op == "==" else (value != literal)

    m = _IN.match(text)
    if m:
        literal, qid = m.groups()
        value = answers.get(qid) or []
        if isinstance(value, str):          # a single answer, not a multi
            return value == literal
        return literal in value

    raise InterviewError(
        f"showIf condition this engine cannot parse: {text!r}. "
        f"Supported: \"id == 'x'\", \"id != 'x'\", \"'x' in id\", joined by "
        f"and/or. Extend the grammar rather than reaching for eval -- these "
        f"conditions decide whether a spouse signs."
    )


def visible(question: dict, answers: dict) -> bool:
    """Is this question asked, given what has been answered so far?"""
    cond = question.get("showIf")
    if not cond:
        return True
    if " or " in cond:
        return any(_clause(part, answers) for part in cond.split(" or "))
    if " and " in cond:
        return all(_clause(part, answers) for part in cond.split(" and "))
    return _clause(cond, answers)


# ── prefill ────────────────────────────────────────────────────────────────

def prefill_for(question: dict, lead: dict | None) -> object:
    """What the website said, if anything, for this question.

    A claim, not a fact: the schema is explicit that every prefilled question is
    still asked. This offers the claim as a default; it never answers for you.
    """
    if not lead or not question.get("prefill"):
        return None
    node = lead
    for part in question["prefill"].split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


# ── the flow ───────────────────────────────────────────────────────────────

@dataclass
class Interview:
    schema: dict = dc_field(default_factory=load_schema)
    lead: dict | None = None
    answers: dict = dc_field(default_factory=dict)

    def pending(self):
        """Every question still to ask, in order, given current answers."""
        for section, q in all_questions(self.schema):
            if q["id"] in self.answers:
                continue
            if visible(q, self.answers):
                yield section, q

    def next_question(self):
        return next(iter(self.pending()), None)

    def answer(self, qid: str, value) -> None:
        q = self.question(qid)
        if q.get("required") and value in (None, "", []):
            raise InterviewError(f"{qid} is required")
        self.answers[qid] = value
        # An answer can hide a question that was already answered -- change
        # joint_return to "no" and the spouse name must go, or it reaches a
        # document that no longer has a place for it.
        for _, other in all_questions(self.schema):
            if other["id"] in self.answers and not visible(other, self.answers):
                del self.answers[other["id"]]

    def question(self, qid: str) -> dict:
        for _, q in all_questions(self.schema):
            if q["id"] == qid:
                return q
        raise InterviewError(f"no question {qid!r} in the schema")

    def missing_required(self) -> list[str]:
        return [q["id"] for _, q in all_questions(self.schema)
                if q.get("required") and visible(q, self.answers)
                and self.answers.get(q["id"]) in (None, "", [])]

    def hard_no(self) -> list[str]:
        """Options the schema marks HARD NO that were actually ticked."""
        hit = []
        for _, q in all_questions(self.schema):
            picked = self.answers.get(q["id"]) or []
            picked = [picked] if isinstance(picked, str) else picked
            for opt in q.get("options") or []:
                if opt.get("hard_no") and opt["value"] in picked:
                    hit.append(opt["label"])
        return hit


# ── answers -> merge fields ────────────────────────────────────────────────

_FORM_LABEL = {"1040": "Form 1040", "1120S": "Form 1120-S",
               "1065": "Form 1065", "1120": "Form 1120"}

_SCHEDULE_LABEL = {"A": "A", "B": "B", "C": "C", "D": "D",
                   "E1": "E", "E2": "E", "F": "F", "SE": "SE"}


def _oxford(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _federal_returns(answers: dict) -> str:
    form = _FORM_LABEL.get(answers.get("federal_form"), answers.get("federal_form") or "")
    picked = answers.get("federal_schedules") or []
    # E1 and E2 are both Schedule E; naming it twice reads as a mistake.
    seen, labels = set(), []
    for value in picked:
        label = _SCHEDULE_LABEL.get(value, value)
        if label not in seen:
            seen.add(label)
            labels.append(label)
    if not labels:
        return form
    word = "Schedule" if len(labels) == 1 else "Schedules"
    return f"{form} with {word} {_oxford(labels)}"


def _listed(answers: dict, qid: str, *, none: bool) -> str:
    """A list answer as a sentence. `none=True` emits the literal "None"."""
    items = answers.get(qid) or []
    if isinstance(items, str):
        items = [items]
    items = [str(i).strip() for i in items if str(i).strip()]
    if items:
        return "; ".join(items)
    return "None" if none else ""


def compose(answers: dict) -> dict:
    """Interview answers -> the merge fields they supply.

    Only fields the interview owns. The firm's settings and anything computed
    are folded in later by `cli.build_record`.
    """
    out: dict = {}

    for _, q in all_questions(load_schema()):
        if q.get("internal") or not q.get("supplies"):
            continue
        value = answers.get(q["id"])
        if value in (None, "", []):
            continue
        for field in q["supplies"]:
            # Composed fields are built below; a raw answer must not clobber one.
            if field in {"FederalReturns", "StateReturns", "LocalReturns",
                         "AdditionalForms", "JointReturn", "PriorFirm"}:
                continue
            out[field] = value

    if answers.get("federal_form"):
        out["FederalReturns"] = _federal_returns(answers)
    if "states" in answers:
        out["StateReturns"] = _listed(answers, "states", none=False)
    if "localities" in answers:
        out["LocalReturns"] = _listed(answers, "localities", none=True)
    if "additional_forms" in answers:
        out["AdditionalForms"] = _listed(answers, "additional_forms", none=True)

    if "joint_return" in answers:
        out["JointReturn"] = answers["joint_return"] == "yes"
    if "prior_firm" in answers:
        out["PriorFirm"] = answers["prior_firm"] == "yes"

    if answers.get("tax_year"):
        # PeriodLabel is self-describing and is what the document set uses.
        # TaxYear survives only because two templates still ask for it; the
        # authoring contract says it should not exist. See the run log.
        out["PeriodLabel"] = f"{answers['tax_year']} tax year"

    return out


def billable_counts(answers: dict) -> dict:
    """Everything tagged `feeds:`, by the list it feeds.

    Counted, not priced -- there is no fee schedule yet. Kept with the
    engagement so the estimate can be built the moment there is one.
    """
    out: dict = {}
    for _, q in all_questions(load_schema()):
        feeds = q.get("feeds")
        if not feeds:
            continue
        value = answers.get(q["id"])
        if value not in (None, "", []):
            out.setdefault(feeds, {})[q["id"]] = value
    return out
