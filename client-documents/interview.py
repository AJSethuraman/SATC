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

import schedules as sched

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
        return _collapse(question, _mapped(question, mapping, node))

    # No map, because the question shares the website's vocabulary on purpose
    # -- `return_features` does. Anything the question does not OFFER is still
    # dropped: the intake form collects "w2" and "retirement" alongside
    # "rentals", and those are real things to tell us that imply no schedule.
    #
    # Filtering here rather than leaving it to `prefill_is_answerable` matters:
    # that helper rejects the WHOLE list when one value is unknown, so a lead
    # saying "W-2 employment, Rental property" would have offered a claim
    # nobody could accept with a keystroke -- which is how the old mapping's
    # five dead keys stayed invisible for as long as they did.
    options = [o["value"] for o in question.get("options") or []]
    if options and isinstance(node, list):
        kept = [v for v in node if v in options]
        return kept or None
    return node


def _mapped(question: dict, mapping: dict, node):
    """The lead's vocabulary translated through the question's own map.

    THREE OUTCOMES PER VALUE, not two:

      absent from the map   the lead said something this question does not
                            care about -- "W-2 employment" is not a schedule.
                            Dropped, quietly, and the rest still stands.
      mapped to a value     translated.
      mapped to NULL        the lead said something this question DOES care
                            about and that does not resolve to one answer.
                            The whole prefill is dropped.

    The third case was missing and it guessed. `services: [individual_tax,
    business_tax]` offered "1040", because business_tax mapped to nothing and
    disappeared -- so a prospect who asked for both an individual and a
    business return was quietly offered the individual one. Which entity form
    a business needs depends on how it is set up; there is no answer to give,
    and no answer is the right one to give.
    """
    values = node if isinstance(node, list) else [node]
    out = []
    for v in values:
        if v not in mapping:
            continue
        got = mapping[v]
        if got is None:
            return None
        for one in (got if isinstance(got, list) else [got]):
            if one not in out:
                out.append(one)
    if not out:
        return None
    return out if isinstance(node, list) else out[0]


def _collapse(question: dict, value):
    """A one-of question cannot be answered with a list.

    A lead's `services` is a multi-select and `federal_form` is not, so the
    mapping can produce ["1040"] for a single-choice question -- one keystroke
    from putting a list where a string belongs. One value collapses; TWO is a
    real ambiguity and is dropped rather than resolved: a prospect who ticked
    individual tax AND business tax is telling us something, and picking one
    for them is exactly the guess this whole mechanism is built to avoid.
    """
    if question.get("type") == "single" and isinstance(value, list):
        distinct = list(dict.fromkeys(value))
        return distinct[0] if len(distinct) == 1 else None
    return value


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

# ── the returning client ───────────────────────────────────────────────────
#
# The firm chose this over building an organizer, and their reasoning is the
# whole design: "we are not copying out of drake - drake is only system of
# record for info. but our interview and such is system of record until proven
# wrong." A returning client does not need last year's FIGURES typed back at
# them. They need last year's ANSWERS shown back for confirmation, plus the
# handful of events that move a return.
#
# CARRIED IS NOT ASSUMED. Every carried answer is still asked, offered as last
# year's claim exactly the way a website lead's answer is offered -- this
# schema has said from the beginning that "the website answer is a claim, not
# a fact", and last year's answer is a weaker claim than that one, because a
# year has passed.

# Answers that describe something stable about the client rather than about
# one year's return. Anything not on this list is simply asked fresh, which is
# the safe default: a question asked twice costs a minute, and an answer
# carried wrongly costs a wrong return.
CARRIES: tuple[str, ...] = (
    # who they are
    "client_full_name", "client_address1", "client_city", "client_state",
    "client_zip", "client_email",
    # what they file
    "federal_form",
    # the entity, which does not change shape year to year
    "entity_structure", "entity_state", "signer_name", "signer_title",
    "count_owners", "owner_returns",
    # where they file. A move changes this -- which is precisely what the
    # change questions ask about, and why this is offered rather than assumed.
    "states", "localities",
)

# Named rather than merely absent, because "why was I asked this again?" is a
# fair question and the answer should be written down.
DOES_NOT_CARRY: dict[str, str] = {
    "tax_year":              "it is a new year",
    "return_basis":          "whether this year is an original or an amendment is this year's fact",
    "amendment_reason":      "belongs to the amendment it explains, and this year may not be one",
    "joint_return":          "a marriage or a divorce is exactly what the change questions ask about",
    "taxpayer_name":         "follows the filing status, which is asked again",
    "spouse_name":           "follows the filing status, which is asked again",
    "k1_target":             "a date, and last year's date is wrong by definition",
    "first_deliverable_target": "a date, and last year's date is wrong by definition",
    "prior_firm":            "we are the prior firm now",
    "prior_firm_name":       "there is no predecessor to name once we are it",
    "prior_return_available": "we hold it",
    "unfiled_years":         "a year that was unfiled may not be any more",
    "decision":              "taking the work is decided again every year",
    "red_flags":             "a flag is about a year, not about a person",
    "returning_client":      "set by the command, not carried",
    "life_changes":          "the question is what changed SINCE last year",
    "life_changes_detail":   "the specifics belong to the change being asked about",
}


def carry_forward(prior: dict) -> tuple[dict, list[str]]:
    """(what carries into a new year, what was deliberately dropped).

    Everything about the return itself -- what is on it, how many of each,
    which extra forms -- is left out without being listed: a count is a fact
    about one year and carrying it would be inventing this year's return out
    of last year's.
    """
    carried = {k: prior[k] for k in CARRIES
               if k in prior and prior[k] not in (None, "", [])}
    dropped = sorted(k for k in prior if k in DOES_NOT_CARRY)
    return carried, dropped


@dataclass
class Interview:
    schema: dict = dc_field(default_factory=load_schema)
    lead: dict | None = None
    answers: dict = dc_field(default_factory=dict)
    # Last year's answers, offered as claims. Never merged into `answers`:
    # a carried answer that answered itself would be an assumption wearing a
    # confirmation's clothes.
    carried: dict = dc_field(default_factory=dict)

    def pending(self):
        """Every question still to ask, in order, given current answers.

        A `derived: true` question is never asked. It holds a value the
        software works out -- `federal_schedules` from `return_features` --
        and putting it in front of a person would be asking them to confirm
        arithmetic they did not do.
        """
        for section, q in all_questions(self.schema):
            if q["id"] in self.answers or q.get("derived"):
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
        # DERIVE BEFORE PRUNING. `federal_schedules` is worked out from the
        # facts, and half the fee questions below are gated on it -- change
        # `return_features` and `count_rentals` has to appear or disappear on
        # the same keystroke. Deriving after the prune would leave the session
        # one answer behind itself.
        sched.apply(self.answers, self.schema)
        # An answer can hide a question that was already answered -- change
        # joint_return to "no" and the spouse name must go, or it reaches a
        # document that no longer has a place for it.
        for _, other in all_questions(self.schema):
            if other["id"] in self.answers and not visible(other, self.answers):
                del self.answers[other["id"]]

    def asked(self) -> list[str]:
        """The questions a person actually answered, in the order they did.

        Not `answers.keys()`: `sched.apply` writes derived values into the same
        dict, and a derived value was never put to anybody -- offering to step
        back to one would be offering to edit arithmetic. Dict order is answer
        order, and re-answering a question keeps its original place, so this
        stays the sitting's own history rather than the schema's running order.
        """
        real, derived = set(), set()
        for _, q in all_questions(self.schema):
            real.add(q["id"])
            if q.get("derived"):
                derived.add(q["id"])
        return [k for k in self.answers if k in real and k not in derived]

    def question(self, qid: str) -> dict:
        for _, q in all_questions(self.schema):
            if q["id"] == qid:
                return q
        raise InterviewError(f"no question {qid!r} in the schema")

    def missing_required(self) -> list[str]:
        return missing_required(self.answers, self.schema)

    def hard_no(self) -> list[str]:
        """Options the schema marks HARD NO that were actually ticked."""
        return hard_no(self.answers, self.schema)


def coerce(q: dict, raw) -> object:
    """A typed-in answer -> the value the schema expects.

    A browser sends strings; so does `--set count_rentals=2`. Both need the
    same conversion, and it lived in `web.py` where only the browser could
    reach it. The re-quote is the second front door onto changing an answer,
    and a second converter is how "2" becomes the integer 2 in one door and
    the string "2" in the other -- which prices differently and looks
    identical in a log.

    An unknown option value is passed through untouched, so `Interview.answer`
    rejects it. Inventing one that is not offered would be the converter
    deciding what the client said.
    """
    t = q["type"]
    if t in ("multi", "list"):
        values = raw if isinstance(raw, list) else \
            [p.strip() for p in (raw or "").split(",") if p.strip()]
        return values
    if t == "number":
        raw = (raw or "").strip() if isinstance(raw, str) else raw
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if isinstance(raw, str):
        raw = raw.strip()
    return raw or None


def same_answer(question: dict, before, after) -> bool:
    """Are these two the same answer to this question?

    ORDER IS MEANINGFUL IN ONE OF THE TWO LIST TYPES AND NOT THE OTHER.
    A `multi` is a set of ticked boxes: the schedules on a return are the same
    schedules whichever order the boxes were read in, and a browser reads them
    in the order they are drawn, which is not the order they were stored in.
    A `list` is typed prose -- the states, the additional forms -- and it
    prints in the order it was given, so reordering it is a real change.

    Found by looking at a re-quote's before-and-after, which reported
    "C, SE, E1, E2, A -> A, C, E1, E2, SE" as something the client had
    changed, and reported the engagement letter's scope line as moving with
    it. Nothing had changed but the reading order.
    """
    if question.get("type") == "multi":
        one = before if isinstance(before, list) else []
        two = after if isinstance(after, list) else []
        return sorted(str(x) for x in one) == sorted(str(x) for x in two)
    return before == after


def missing_required(answers: dict, schema: dict | None = None) -> list[str]:
    """Required questions this interview should have answered and did not.

    A free function over ANSWERS, for the same reason `hard_no` is one: a live
    sitting, a saved interview.json and a posted web body all have to hit the
    same gate. `intake.finish` is the back door, and it was not hitting it --
    a set of answers with `owner_returns` simply absent produced an entity
    engagement whose business letter carried an empty section where the
    paragraph about the owners' returns belongs. The schema has said
    `required: true` on that question the whole time.

    Derivation runs first, on a copy: half the schedule questions are gated on
    facts worked out from other answers, so checking the raw set reports
    questions that would never have been asked.
    """
    schema = schema if schema is not None else load_schema()
    seen = dict(answers)
    try:
        sched.apply(seen, schema)
    except Exception:                                        # noqa: BLE001
        pass          # a schedule that will not derive is reported elsewhere
    return [q["id"] for _, q in all_questions(schema)
            if q.get("required") and not q.get("derived")
            and visible(q, seen)
            and seen.get(q["id"]) in (None, "", [])]


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

# Every schedule the scope sentence is capable of naming. Public because
# `consistency` compares what a document BILLS against what the scope SAYS,
# and a name the scope sentence can never produce -- "Schedule K-1",
# "Schedule L" -- is not a federal schedule that could be inside or outside
# it. Derived from the map above so the two cannot drift.
SCOPE_SCHEDULES = frozenset(_SCHEDULE_LABEL.values())


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
    # AN AMENDMENT SAYS SO ON THE SIGNED LETTER. Three amendment engagements go
    # through the harness and every one of them produced an engagement letter
    # byte-identical to a first-time preparation: "What we will prepare —
    # Federal: Form 1040", when the work is amending a 1040 somebody has
    # already filed. The word "amend" appeared nowhere in the letter, though
    # `return_basis` and `amendment_reason` were both recorded and priced, and
    # the fee estimate beside it said "Amending a return prepared elsewhere".
    # Found by opening the pack.
    #
    # This names the RETURN, not the firm's policy. "Amended Form 1040" is what
    # the thing is; what the firm has to say ABOUT amendments is the firm's
    # sentence to write, and it is still unwritten -- see the open questions.
    if answers.get("return_basis") == "amended" and form:
        form = f"Amended {form}"
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


# Merge fields this module BUILDS rather than reads straight off an answer.
#
# Two callers need the same list and it existed as a set literal inside
# `compose`, where only `compose` could see it. The other caller is `requote`:
# re-pricing an engagement recomposes the record from the amended answers, and
# a field the new answers no longer supply has to be REMOVED from the record
# rather than left standing. A client who drops their second state and keeps
# `StateReturns: "Ohio and Michigan"` on the engagement letter is the same
# stale-claim failure as any other -- the scope says one thing, the price says
# another, and nothing compares them.
COMPOSED = frozenset({
    "FederalReturns", "StateReturns", "LocalReturns", "AdditionalForms",
    "JointReturn", "PriorFirm", "EntityType", "OwnerReturnsPrepared",
    "OwnerReturnsElsewhere", "EntityIssuesK1s",
    # Built below and supplied by no question today. Listed anyway: the point
    # of the list is what compose CAN emit, and a question that starts
    # supplying one of these should not silently win over the derivation.
    "SCorpElection", "ReturnScope", "PeriodLabel",
})


def composable_fields() -> frozenset[str]:
    """Every merge field the interview's answers can put on a record.

    What `compose` builds, plus everything any question declares it
    `supplies:`. Read from the schema rather than listed here, so a new
    question is covered the day it is added.
    """
    out = set(COMPOSED)
    for _, q in all_questions(load_schema()):
        out.update(q.get("supplies") or [])
    return frozenset(out)


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
            if field in COMPOSED:
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
        # A C CORPORATION ISSUES NO K-1s. `count_owners` already knows it --
        # the question is asked of 1120-S and 1065 only -- but the letter did
        # not, so the K-1 scope line has to be gated on the same fact rather
        # than on a count that is simply absent for a 1120.
        #
        # This is only half a fix. See docs/review-queue.md: the whole of the
        # letter's section 02 is about K-1s and is UNGATED, so a C corporation
        # is currently sent a target date for K-1s it will never receive. What
        # that section should say instead is the firm's to write, not an
        # agent's to invent.
        out["EntityIssuesK1s"] = answers["federal_form"] in ("1120S", "1065")

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
