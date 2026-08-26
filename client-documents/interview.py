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

    # One lead value can answer more than one question: the intake form collects
    # location as a single "Solon, OH", and the letter needs city and state in
    # separate lines of the address block. `prefill_index` says which comma-
    # separated piece this question wants.
    #
    # Without it both questions offered the whole string, and once enter began
    # accepting a prefill that produced "Solon, OH, Solon, OH 44139" on a client
    # letter. A claim that cannot be accepted as shown is not a usable claim.
    idx = question.get("prefill_index")
    if idx is not None and isinstance(node, str):
        pieces = [p.strip() for p in node.split(",")]
        return pieces[idx] if idx < len(pieces) and pieces[idx] else None

    # The website and this schema do not share a vocabulary. The intake form
    # collects "rental"; the letter needs "Schedule E page 1". `prefill_map`
    # translates, and a lead value with no entry is dropped rather than carried
    # through -- "w2" is a real thing to tell us and not a schedule.
    mapping = question.get("prefill_map")
    if mapping:
        if isinstance(node, list):
            out = []
            for v in node:
                got = mapping.get(v)
                for one in (got if isinstance(got, list) else [got]):
                    if one is not None and one not in out:
                        out.append(one)
            return out or None
        return mapping.get(node)
    return node


def prefill_is_answerable(question: dict, value) -> bool:
    """Could this claim be accepted as it stands?

    The interview offers a prefill as a default you accept with enter, so it has
    to be a legal answer to the question being asked. A value the question would
    reject is still worth SHOWING -- it is what the client told us -- but it
    must not be one keystroke from landing in a document.
    """
    if value in (None, "", []):
        return False
    options = [o["value"] for o in question.get("options", [])]
    if not options:
        return True
    values = value if isinstance(value, list) else [value]
    return all(v in options for v in values)


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
        return hard_no(self.answers, self.schema)


def hard_no(answers: dict, schema: dict | None = None) -> list[str]:
    """Options the schema marks HARD NO that were actually ticked.

    Takes answers rather than a session so it can be run against a saved
    interview.json, a web form's posted body, or a live sitting -- all three
    have to hit the same gate.
    """
    hit = []
    for _, q in all_questions(schema or load_schema()):
        picked = answers.get(q["id"]) or []
        picked = [picked] if isinstance(picked, str) else picked
        for opt in q.get("options") or []:
            if opt.get("hard_no") and opt["value"] in picked:
                hit.append(opt["label"])
    return hit


def review_flags(answers: dict) -> list[str]:
    """Things a human should look at. NEVER things the software decides.

    A flag is not a blocker and it is not a derivation. It is the third thing:
    an answer that is probably fine and is worth a preparer's eye before the
    return is priced or prepared.

    The distinction is the firm's, made on 25 August 2026 about the municipal
    case, and it is the right one. A client with four rentals and one locality
    may genuinely owe one local return -- Ohio townships have no income tax,
    an out-of-state rental has nothing to do with an Ohio municipality, and
    plenty of jurisdictions do not tax rental income at all. Deriving the
    count from the rentals would quietly bill for returns nobody has to file.
    Saying nothing lets a client who simply did not think about it under-file.
    So: ask a human, and let the answer stay the client's.

    These are preparer-facing. They never reach a client document, and they
    never change a price.

    Written in Python rather than as a registry rule on purpose. It is one
    comparison; a gate language invented to hold one rule is a language nobody
    decided on. When there is a third flag with a different shape, that is the
    moment to look again.
    """
    flags: list[str] = []

    rentals = _as_count(answers.get("count_rentals"))
    localities = _as_count(answers.get("count_localities"))
    if rentals > localities:
        noun = "property" if rentals == 1 else "properties"
        flags.append(
            f"{rentals} rental {noun} but {localities} local return"
            f"{'' if localities == 1 else 's'}. Rental income is often taxed "
            f"by the municipality it sits in. Check whether a local return is "
            f"owed for each one before the estimate goes out -- do not assume "
            f"either way: townships levy no income tax, an out-of-state "
            f"rental owes nothing to an Ohio city, and some jurisdictions do "
            f"not tax rents at all."
        )

    # The brokerage keying line, and the one flag here that is about our own
    # process rather than the client's year. `count_brokerages_keyed` is
    # usually unanswerable when the estimate is written -- nobody knows
    # whether a statement can be summarised until it arrives -- so a blank is
    # the normal case and must not be read as "none". Zero, typed by a human
    # who checked, is an answer and raises nothing.
    if (_as_count(answers.get("count_brokerages")) > 0
            and answers.get("count_brokerages_keyed") in (None, "")):
        flags.append(
            "A 1099-B is coming and nobody has said yet whether it can be "
            "summarised. Nothing is billed for keying until that is answered, "
            "so check it when the file is reviewed -- each statement that has "
            "to be entered by hand is a line on the invoice, and a line added "
            "after the estimate went out is a conversation."
        )
    return flags


def _as_count(value) -> int:
    """A count for comparison only, never for money.

    `pricing._count` refuses a bool or a fraction because billing one of those
    is a wrong invoice. Here a bad answer should not stop a review flag being
    raised, so anything unreadable counts as nothing and the flag falls out of
    the comparison on its own.
    """
    if isinstance(value, bool) or value in (None, ""):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


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


_STRUCTURE = {
    "llc": "limited liability company",
    "corporation": "corporation",
    "lp": "limited partnership",
    "llp": "limited liability partnership",
    "gp": "general partnership",
}

# What the chosen federal return says about how the entity is TAXED, which is
# a different fact from how it is organised. An LLC taxed as an S corporation
# is the ordinary case and the letter has to be able to say so.
_TREATMENT = {"1120S": "S corporation", "1065": "partnership", "1120": "C corporation"}


def _entity_type(answers: dict) -> str:
    """"an Ohio limited liability company taxed as an S corporation".

    Built rather than typed. A preparer asked to type this at speed writes
    "an OH LLC" on one letter and "an Ohio Limited Liability Co." on the next,
    and the phrase is the letter's description of what it is binding.
    """
    structure = _STRUCTURE.get(answers["entity_structure"], answers["entity_structure"])
    state = str(answers["entity_state"]).strip()
    phrase = f"{_article(state)} {state} {structure}"

    treatment = _TREATMENT.get(answers.get("federal_form"))
    if treatment and not _treatment_is_redundant(answers):
        phrase += f" taxed as {_article(treatment)} {treatment}"
    return phrase


# "an S corporation", but "a C corporation". The rule is about SOUND, not
# spelling: a single letter takes "an" when its name begins with a vowel sound
# -- ess, eff, em -- which is why the naive vowel test got "a S corporation".
_AN_LETTERS = set("AEFHILMNORSX")


def _article(word: str) -> str:
    word = word.strip()
    if not word:
        return "a"
    first = word.split()[0]
    if len(first) == 1:
        return "an" if first.upper() in _AN_LETTERS else "a"
    return "an" if first[:1].upper() in "AEIOU" else "a"


def _treatment_is_redundant(answers: dict) -> bool:
    """Is "taxed as ..." saying what the structure already said?

    A corporation filing an 1120 is a C corporation; a limited partnership
    filing a 1065 is a partnership. Spelling it out reads as though something
    unusual had been elected, which is the opposite of what it means.
    """
    structure, form = answers["entity_structure"], answers.get("federal_form")
    return ((structure == "corporation" and form == "1120")
            or (structure in {"lp", "llp", "gp"} and form == "1065"))


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
                         "AdditionalForms", "JointReturn", "PriorFirm",
                         "EntityType", "OwnerReturnsPrepared",
                         "OwnerReturnsElsewhere"}:
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

    # ── the entity half ───────────────────────────────────────────────────
    #
    # EntityType is a PHRASE, not a code: it drops into the letter's opening
    # sentence after a comma, and the letter is the firm's statement of what it
    # believes the entity is, put where the client can correct it. Assembled
    # the same way FederalReturns is -- from structured answers, so nothing is
    # typed twice and nothing is invented.
    if answers.get("entity_structure") and answers.get("entity_state"):
        out["EntityType"] = _entity_type(answers)

    # Exact inverses, from one answer. Two questions could disagree; one
    # cannot, and the letter would contradict itself if they did.
    if "owner_returns" in answers and answers["owner_returns"]:
        prepared = answers["owner_returns"] == "yes"
        out["OwnerReturnsPrepared"] = prepared
        out["OwnerReturnsElsewhere"] = not prepared

    # Derived, never asked. The election is what the chosen return MEANS, so
    # asking would invite an answer that contradicts the form.
    if answers.get("federal_form"):
        out["SCorpElection"] = answers["federal_form"] == "1120S"

    # Does this engagement prepare RETURNS? True for every engagement the
    # interview covers, and the estimate's scope block turns on it: it repeats
    # the engagement letter's four scope lines, and those four fields only
    # exist where a return is being filed. A bookkeeping engagement has a
    # scope too -- ScopeItems, a list -- but no interview yet, so the block
    # stays off there rather than rendering four blanks. See
    # docs/pricing-open-threads.md.
    if answers.get("federal_form"):
        out["ReturnScope"] = True

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
