"""Re-quoting a live engagement: the answers changed, so the money did.

WHAT WAS MISSING, AND FOR HOW LONG. An engagement was priced exactly once --
in `intake.finish`, at the moment it was created -- and nothing anywhere could
price it again. Nineteen commands, and not one of them could add a chargeable
line to work that already existed. A client who rang in March to say they had
bought a rental could be re-interviewed from scratch as a second engagement, or
have a number typed onto an invoice by hand. Both are wrong, and the second is
wrong in the way this whole pipeline exists to prevent: two documents stating
the same money from two sources, and the one the client keeps is the one that
says the larger number.

THE ANSWERS MOVE, THE PRICE FOLLOWS. Nobody types a figure here. A re-quote
changes what we were TOLD -- three K-1s instead of two, a second state, a
Schedule C that turned out to be a real business -- and the engine prices it
again from those answers, the same engine that priced it the first time. That
is not a stylistic preference: `pricing.py` exists so that no human arithmetic
reaches a client, and a re-quote that let a preparer type $80 would be a second
front door onto the money with none of the schedule's rules behind it.

THE PRICE IS NOT THE ONLY THING THAT MOVES. The estimate repeats the
engagement letter's scope -- the same four fields, on purpose, so a client
holding both sheets cannot find them disagreeing. Change the answer that adds a
state and the SCOPE changes too, on a letter that has already been signed. So a
plan reports that separately and in the preparer's face: the price is the
headline, and the sentence on the letter is the thing that gets missed.

NOTHING IS WRITTEN BY `plan`. It is a report, and it is the same report the CLI
prints, the browser renders and the tests assert on. Only `apply` touches disk,
and only with a reason, which lands in an append-only log beside the record --
the same shape as a waved-through gate failure, for the same reason. A price
that moved and cannot be explained a year later is a price nobody can defend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import engagements
import intake
import interview as iv
import invoicing
import money as m
import pricing


class RequoteError(RuntimeError):
    """Something that would put a wrong number on a client's engagement."""


# Merge fields a re-quote must never move, whatever the new answers say.
#
# `EngagementRef` is the join key: changing it orphans every document already
# carrying it. `LetterDate` is the date on the SIGNED engagement letter --
# recomposing the record sets it to today, which would silently re-date an
# instrument the client has already put their name to.
FROZEN = ("EngagementRef", "LetterDate")

# ANSWERS THAT STATE ONE FACT TWICE: the number, and the names. Both print --
# the count decides what the estimate bills, the list becomes the scope line on
# the estimate AND on the engagement letter -- and nothing joined them.
#
# Found by running a re-quote across all 29 scenarios and reading the sheet
# that came out: `count_states` had been moved from one to three, the estimate
# billed three, and two inches above it the scope line still read
# "State: Ohio". The K-1 pair is the same shape and is checked the same way,
# except that its list is prose and needs reading rather than counting --
# `consistency.k1_claim` does that.
#
# MEASURED BEFORE IT WAS ALLOWED TO BLOCK ANYTHING: every one of the 29
# scenarios and the shipped sample answers agree on both pairs today, so this
# refuses nothing that already works.
COUNTED_AND_NAMED = (
    ("count_states", "states", ("state return", "state returns")),
    ("count_localities", "localities", ("local return", "local returns")),
)

# The scope lines the estimate and the engagement letter both carry, in the
# order they read on the page. Named here because these are the ones worth
# saying out loud when they move -- the letter is already signed.
SCOPE = ("FederalReturns", "StateReturns", "LocalReturns", "AdditionalForms",
         "EntityType", "PeriodLabel")


@dataclass(frozen=True)
class Change:
    """One answer, before and after."""
    question: str
    before: object
    after: object

    def line(self) -> str:
        return f"{self.question}: {_shown(self.before)} → {_shown(self.after)}"


@dataclass(frozen=True)
class Moved:
    """One line of the estimate, before and after.

    `before` and `after` are the amount as the client reads it, or `None` for
    a line that was not there. A line whose Service is unchanged and whose
    amount moved is the common case -- two states become three and the same
    line costs more -- so the service name is the identity, not the row.
    """
    service: str
    detail: str
    before: str | None
    after: str | None

    @property
    def kind(self) -> str:
        if self.before is None:
            return "added"
        if self.after is None:
            return "gone"
        return "changed"


@dataclass
class Quote:
    """What re-quoting this engagement would do. Nothing has been written."""
    ref: str
    changed: list[Change] = field(default_factory=list)
    moved: list[Moved] = field(default_factory=list)
    scope_moved: list[Change] = field(default_factory=list)
    before_total: str = ""
    after_total: str = ""
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    answers: dict = field(default_factory=dict)
    record: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.blockers

    @property
    def moves_money(self) -> bool:
        return bool(self.moved) or self.before_total != self.after_total

    @property
    def changes_anything(self) -> bool:
        return bool(self.moved or self.scope_moved)

    @property
    def difference(self) -> str:
        """The headline, as a sentence a preparer reads out loud."""
        was, now = m.parse(self.before_total), m.parse(self.after_total)
        if was is None or now is None:
            return "the totals cannot be compared"
        cents = round(now * 100) - round(was * 100)
        if cents == 0:
            return "the total does not change"
        size = m.money(abs(cents) / 100)
        return f"{size} {'more' if cents > 0 else 'less'}"


def _shown(value) -> str:
    if value in (None, "", []):
        return "(nothing)"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(x) for x in value)
    return str(value)


def questions(answers: dict | None = None,
              schedule: dict | None = None) -> list[dict]:
    """The interview questions whose answers move money, in schema order.

    Schema order rather than alphabetical, because this is what a preparer
    reads down: the sitting asked them in this order and the client answered
    them in this order. `pricing.answers_that_move_money` decides WHICH; the
    interview decides the order and supplies the wording, so neither is typed
    twice.

    AND THE ONES THAT PRINT THE SCOPE, which move no money at all. The
    estimate carries four scope lines and so does the engagement letter, from
    the same fields, so that a client holding both cannot find them
    disagreeing. `additional_forms` is the one that matters: a preparer types
    "Two K-1s as reported" in their own words while `count_k1s` is the number
    the K-1 line is billed from, and a re-quote that moved the count and not
    the sentence would print four billed K-1s two inches under a line saying
    two. Offering the count without the sentence is offering half of one fact.

    GIVEN `answers`, ONLY THE ONES THIS CLIENT WAS ASKED. Nineteen answers move
    money across the whole schedule and no client is asked all nineteen -- an
    individual filer is never asked how many owners receive a K-1. Listing the
    other twelve does not merely add noise: it invites a preparer to set
    `count_owners` on a 1040, where the schedule reads it for two entity forms
    and silently ignores it for this one. A control that appears to do
    something and does nothing is worse than one that is not there.

    A change can reveal a question -- ticking Schedule E1 is what makes "how
    many rental properties?" appear -- so this is re-read after every change
    rather than fixed at the start.
    """
    moving = set(pricing.answers_that_move_money(schedule))
    out = [q for _, q in iv.all_questions(iv.load_schema())
           if q["id"] in moving or scope_fields(q)]
    seen = {q["id"] for q in out}
    missing = sorted(moving - seen)
    if missing:
        raise RequoteError(
            f"the fee schedule prices on {missing}, which the interview does "
            f"not ask. A price that turns on an answer nobody is asked for is "
            f"a price nobody can change."
        )
    if answers is None:
        return out
    return [q for q in out if iv.visible(q, answers)]


def scope_fields(question: dict) -> list[str]:
    """The scope lines this question writes, if any.

    Read off the question's own `supplies:`, not listed here. Every scope
    field except `PeriodLabel` is declared by the question that fills it, and
    a map in this file would go stale the first time one was renamed --
    silently, because the re-quote would simply stop offering the question.

    `PeriodLabel` is deliberately not reachable: changing which tax year an
    engagement is for is not a re-quote, it is a different engagement.
    """
    return sorted(set(question.get("supplies") or []) & set(SCOPE)
                  - {"PeriodLabel"})


def plan(ref: str, changes: dict, *, store: Path | None = None,
         schedule=None, today: date | None = None) -> Quote:
    """What re-quoting `ref` with these answers would do. Writes nothing.

    `changes` is answer id -> new value, already coerced to the type the
    schema expects. An id the interview does not ask raises rather than being
    ignored: a typo in `--set count_state=3` that silently changed nothing
    would report "the total does not change" and be believed.
    """
    store = store or engagements.STORE
    record = engagements.load(ref, store)
    answers = _answers(ref, store)

    unknown = sorted(set(changes)
                     - {q["id"] for _, q in iv.all_questions(iv.load_schema())})
    if unknown:
        raise RequoteError(
            f"the interview asks no question called {', '.join(unknown)}. "
            f"`python cli.py requote --engagement {ref}` lists the ones that "
            f"move money."
        )

    asked = {q["id"]: q for _, q in iv.all_questions(iv.load_schema())}
    new_answers = dict(answers)
    for qid, value in changes.items():
        # A `multi` given back in a different order is the same answer, and
        # the stored order is kept -- the schedules print on the engagement
        # letter in the order they are held, so taking the new order would
        # reword a scope line on a signed letter to say the same thing.
        if iv.same_answer(asked[qid], answers.get(qid), value):
            continue
        new_answers[qid] = value

    quote = Quote(ref=ref, answers=new_answers,
                  before_total=str(record.get("EstimateTotal", "")))
    quote.changed = [Change(qid, answers.get(qid), new_answers[qid])
                     for qid in changes
                     if not iv.same_answer(asked[qid], answers.get(qid),
                                           new_answers[qid])]

    # THE SAME GATES THE INTERVIEW KEEPS. A re-quote is a second way to change
    # the answers an engagement rests on, and a second way in with fewer rules
    # is how the first one stops being worth having.
    blocked = iv.hard_no(new_answers)
    if blocked:
        quote.blockers.append(
            "these answers now flag work the firm does not take: "
            + "; ".join(blocked)
            + ". A quote is not the document for this — the engagement is "
              "already live, so what is needed is the disengagement letter "
              "(`python cli.py event --kind disengagement`), not a new price."
        )
    short = iv.missing_required(new_answers)
    if short:
        quote.blockers.append(
            "still unanswered: " + ", ".join(short)
            + ". A re-quote reprices the whole engagement, not one line, so "
              "it needs the same complete interview the first price did."
        )

    if quote.blockers:
        return quote

    try:
        composed = intake.compose_record(new_answers, today=today)
        priced = pricing.price(new_answers, pricing.load(schedule)
                               if isinstance(schedule, (str, Path))
                               else schedule)
    except (pricing.PricingError, iv.InterviewError) as exc:
        quote.blockers.append(f"the fee schedule cannot price this: {exc}")
        return quote

    quote.record = _recompose(record, composed, priced, today=today)
    quote.after_total = str(quote.record.get("EstimateTotal", ""))
    quote.moved = _moved(record.get("LineItems") or [],
                         quote.record.get("LineItems") or [])
    quote.scope_moved = [
        Change(name, record.get(name), quote.record.get(name))
        for name in SCOPE
        if record.get(name) != quote.record.get(name)
    ]
    quote.notes = _notes(ref, store, quote)
    _contradictions(record, quote)
    return quote


def _k1_gap(record: dict):
    """(what the scope line claims, what is counted) where they disagree."""
    import consistency

    claimed = consistency.k1_claim(record.get("AdditionalForms"))
    counted = consistency._counted_k1s(record)
    if claimed is None or counted is None or claimed[1] == counted:
        return None
    return claimed[0], counted


def _list_gaps(answers: dict) -> list[tuple[str, int, int, str]]:
    """(which list, how many named, how many counted, what they are)."""
    out = []
    for count_id, list_id, what in COUNTED_AND_NAMED:
        named = answers.get(list_id)
        count = answers.get(count_id)
        if not isinstance(named, (list, tuple)) or not named:
            continue
        try:
            count = int(count)
        except (TypeError, ValueError):
            continue
        if count and len(named) != count:
            out.append((list_id, len(named), count, what))
    return out


def _contradictions(before: dict, quote: Quote) -> None:
    """Where the new record would print two numbers for one fact.

    THE SHEET MAY NOT ARGUE WITH ITSELF. `count_k1s` is billed on the estimate
    and `additional_forms` is printed two inches above it in the preparer's own
    words, and nothing joined them until `consistency` did -- seen live on an
    engagement billing four K-1s under a scope line reading "Two K-1s as
    reported". A re-quote is the moment that gap opens, because the count is
    exactly what a re-quote moves.

    BLOCKED ONLY WHERE THIS RE-QUOTE OPENS IT. The first cut blocked on the
    gap however it got there, which trapped a preparer: an engagement that
    already disagreed with itself refused every re-quote, including the one
    changing something else entirely, and including the one that would have
    fixed it. A gap that was already there is still said out loud -- it is on
    the sheet either way -- but it stops nothing.
    """
    _list_contradictions(quote)

    gap = _k1_gap(quote.record)
    if not gap:
        return
    claimed, counted = gap
    fix = (f"Change {_question_text('additional_forms')!r} in this same "
           f"re-quote so both say the number the client gave you.")
    if _k1_gap(before):
        quote.notes.append(
            f"the scope line already said {claimed} K-1s while {counted} are "
            f"billed — that was true before this re-quote and is not its "
            f"doing, but it is on the sheet. {fix}")
        return
    quote.blockers.append(
        f"the scope line would say {claimed} K-1s while {counted} are billed, "
        f"on the same sheet, two inches apart. {fix}")


def _list_contradictions(quote: Quote) -> None:
    """The number and the names, for the pairs where both are answered.

    Same rule as the K-1 pair and for the same reason: blocked where this
    re-quote opens the gap, said out loud where it was already there. The
    remedy is on the same screen, because both answers are offered.
    """
    was = {gap[0] for gap in _list_gaps(quote.answers)} - {
        gap[0] for gap in _list_gaps(_before_answers(quote))}
    for list_id, named, counted, what in _list_gaps(quote.answers):
        one, many = what
        said = (f"the letter would name {named} {one if named == 1 else many} "
                f"while {counted} are billed. Change "
                f"{_question_text(list_id)!r} in this same re-quote so both "
                f"say what the client told you.")
        if list_id in was:
            quote.blockers.append(said)
        else:
            quote.notes.append(
                f"the letter already named {named} "
                f"{one if named == 1 else many} while {counted} are billed — "
                f"that was true before this re-quote. {said}")


def _before_answers(quote: Quote) -> dict:
    """The answers as they were, reconstructed from what this quote changed.

    `plan` holds the amended set; the originals are one step back through
    `quote.changed`, which is already the record of what moved. Kept as a
    function rather than a second stored dict so there is one answer to
    "what changed" and it cannot go out of step with itself.
    """
    return {**quote.answers, **{c.question: c.before for c in quote.changed}}


def _question_text(qid: str) -> str:
    """One question in its own words, so no wording is typed twice."""
    for _, q in iv.all_questions(iv.load_schema()):
        if q["id"] == qid:
            return q["question"]
    return qid


def _answers(ref: str, store: Path) -> dict:
    import json
    path = engagements._dir(store, ref) / "interview.json"
    if not path.exists():
        raise RequoteError(
            f"{ref} has no saved interview, so there are no answers to change "
            f"and nothing to re-price from. An engagement created before the "
            f"interview was kept can only be quoted again by running one."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _recompose(record: dict, composed: dict, priced: dict, *,
               today: date | None = None) -> dict:
    """The engagement's record, rebuilt from the amended answers.

    A MERGE IS NOT ENOUGH, and this is the whole care in this function. Layering
    the new fields over the old leaves behind every field the new answers no
    longer supply: drop a state and `StateReturns` still reads "Ohio and
    Michigan" on a letter whose price now covers one. So everything the
    interview COULD supply is cleared first, and only what it supplies now is
    put back. Anything else on the record -- fields a lifecycle event or a
    close-out added, fields a future version writes -- is left exactly alone,
    because this function does not know what they are and guessing is how a
    record loses something.
    """
    universe = iv.composable_fields()
    kept = {k: v for k, v in record.items() if k not in universe}
    out = {**kept, **composed, **priced}
    for name in FROZEN:
        if name in record:
            out[name] = record[name]
    # THE ESTIMATE GETS ITS OWN DATE, AND THE LETTER KEEPS ITS ONE. Two sheets
    # in a drawer showing different totals under the same date is a question
    # nobody can answer next February.
    out["EstimateDate"] = (today or date.today()).strftime("%B %-d, %Y")
    return out


def _moved(before: list[dict], after: list[dict]) -> list[Moved]:
    """Every line that changed, in the order the new estimate reads.

    Keyed on `Service`, which is the line as a client reads it: two states
    becoming three is the SAME line costing more, not one line gone and
    another arrived, and a diff that said otherwise would be read as a
    re-quote that rebuilt the estimate from nothing.
    """
    was = _by_service(before)
    now = _by_service(after)
    out = []
    for service, line in now.items():
        old = was.get(service)
        if old is None:
            out.append(Moved(service, str(line.get("Detail", "")),
                             None, str(line.get("Amount", ""))))
        elif str(old.get("Amount", "")) != str(line.get("Amount", "")):
            out.append(Moved(service, str(line.get("Detail", "")),
                             str(old.get("Amount", "")),
                             str(line.get("Amount", ""))))
    for service, line in was.items():
        if service not in now:
            out.append(Moved(service, str(line.get("Detail", "")),
                             str(line.get("Amount", "")), None))
    return out


def _by_service(lines: list[dict]) -> dict:
    out: dict = {}
    for line in lines:
        service = str(line.get("Service", ""))
        if service in out:
            raise RequoteError(
                f"this estimate has two lines both called {service!r}, so a "
                f"before-and-after cannot say which one moved. Price them as "
                f"one line or name them apart."
            )
        out[service] = line
    return out


def _notes(ref: str, store: Path, quote: Quote) -> list[str]:
    """Things a preparer should know before pressing it, which stop nothing."""
    out = []
    raised = invoicing.issued_for(store, ref)
    if raised:
        out.append(
            f"{len(raised)} invoice(s) have already been raised on this "
            f"engagement. Those are written and are not touched — a bill that "
            f"changed after it was sent is not a bill. The new figure applies "
            f"to what is billed next."
        )
    if quote.scope_moved:
        # WHAT IS TRUE, NOT WHAT TO TYPE. This ended with `python cli.py
        # package --engagement <ref>` and the browser printed it under a
        # button that does exactly that -- telling somebody standing in front
        # of the control to open a terminal instead. A note says what
        # happened; each front door says how, in its own terms.
        out.append(
            "the engagement letter's scope changes too, so the signed pack no "
            "longer describes the work. It has to be built again."
        )
    if quote.moved and not quote.scope_moved:
        out.append(
            "the scope lines are unchanged, so the engagement letter still "
            "reads correctly. Only the estimate needs to go out again."
        )
    return out


def apply(quote: Quote, reason: str, *, store: Path | None = None,
          today: date | None = None) -> Path:
    """Write the new price, the amended answers, and why.

    Refuses three things, each of which has left a mess somewhere before:

    * a quote with a blocker on it -- the caller has been told and is asking
      anyway;
    * a quote that changes nothing -- a revision log full of no-ops is a log
      nobody reads, and a second estimate identical to the first is a document
      that confuses a client for no reason;
    * a re-quote with no reason -- the number moved and in a year nobody will
      remember why. The gate's override log takes a reason for the same
      reason, and this is the money.
    """
    store = store or engagements.STORE
    if not quote.ok:
        raise RequoteError(
            "this quote was not written: " + " ".join(quote.blockers))
    if not quote.changes_anything:
        raise RequoteError(
            "nothing about this engagement changes, so nothing was written. "
            "The answers you gave price to the same lines and the same total.")
    if not reason.strip():
        raise RequoteError(
            "a re-quote needs a reason, in one sentence, for whoever reads "
            "this engagement next year. A reason names the thing: \"client "
            "bought a second rental in April\". \"Updated\" is not a reason.")

    # The answers first: `save_answers` refuses a TIN before it reaches disk,
    # and a record whose price came from answers that were then refused is a
    # price with no interview behind it.
    engagements.save_answers(quote.answers, quote.ref, store)
    engagements.save(quote.record, quote.ref, store)
    return record_revision(quote.ref, {
        "when": (today or date.today()).isoformat(),
        "reason": reason.strip(),
        "was": quote.before_total,
        "now": quote.after_total,
        "answers": [{"question": c.question,
                     "from": _shown(c.before), "to": _shown(c.after)}
                    for c in quote.changed],
        "lines": [{"service": mv.service, "was": mv.before, "now": mv.after}
                  for mv in quote.moved],
        "scope": [{"field": c.question,
                   "from": _shown(c.before), "to": _shown(c.after)}
                  for c in quote.scope_moved],
    }, store)


def record_revision(ref: str, entry: dict, store: Path | None = None) -> Path:
    """Append one re-quote to the engagement's own file.

    APPEND ONLY, never rewritten, never pruned -- `engagements.record_override`
    in every respect, and deliberately the same shape. What it holds is the
    answer to the only question anybody asks about a price that moved: what
    did we know, when did we know it, and who said so.
    """
    import json
    path = engagements._dir(store or engagements.STORE, ref) / "revisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                log = existing
        except json.JSONDecodeError:
            log = [{"unreadable": path.with_suffix(".corrupt").name}]
            path.replace(path.with_suffix(".corrupt"))
    log.append(entry)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def revisions(ref: str, store: Path | None = None) -> list[dict]:
    """Every time this engagement's price has moved, oldest first."""
    import json
    path = engagements._dir(store or engagements.STORE, ref) / "revisions.json"
    if not path.exists():
        return []
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return got if isinstance(got, list) else []
