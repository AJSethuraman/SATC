"""What the interview says the work will cost — priced before any of it is done.

The interview is the origin fact of an engagement. It already decides which
documents to ask for and which tasks exist; this module makes it decide the
money too, so nobody maintains a second list of "this client has a rental".

A QUOTE IS NOT AN INVOICE, and the separation here is structural rather than
polite. An invoice is a claim on somebody's bank account: it carries a number in
a sequence, a date it was fixed, and lines somebody performed. A quote is a
sentence about work that has not happened. They share a SHAPE — full value, then
the named reduction, then the total, because a client on a reduced rate should
see what they are being given either way — and they share nothing else. There is
no ``issue()``, no ``add()``, and asking a :class:`Quote` for an invoice number
raises rather than answering, so a quote cannot drift into the invoice register
through code nobody has written yet.

WHERE THE PRICES COME FROM. The mapping from an answer to a catalogue service is
config: a ``services:`` block in ``configs/workflows/<key>.yaml``, gated by the
same condition grammar the tasks already use. Adding a service to a branch is an
edit to a YAML file, and the schema is documented in the reference header of
``personal_1040_core.yaml``.

WHAT IT REFUSES TO PRICE. Three things go in :attr:`Quote.unpriced` instead of
becoming a line: a per-hour service (nobody knows the hours before the work), a
service whose quantity the interview does not record (``quantity: unknown``), and
a service whose gate is satisfied only because a question has not been answered.
All three stay VISIBLE with the answer — or the silence — that implied them.
Dropping them understates the quote; inventing a number for them is principle 1
exactly.

WHAT IT REFUSES OUTRIGHT. A quote a client reads must be a quote the practice
can bill, so this module refuses every state the invoice engine would refuse
later: a reduced rate plan with no recorded basis (``Invoice.issue`` refuses it,
and a discount promised then withdrawn is worse than one never offered), and a
fixed-price service quoted at a quantity other than one (``Invoice.add`` refuses
it). A guard on one path is not a guard — it is the other path.

WHEN IT REFUSES. When the CONFIG IS READ, never when a client happens to fire
the broken entry. An error found by quoting a client is an error the owner meets
in front of that client. So :func:`load_service_map` resolves every rule against
the catalogue and checks every quantity against its unit, whether or not any
answer would ever select it — and the condition grammar it shares with the
tasks: block is validated by the workflow engine that owns it
(:func:`satc.intake.workflows.validate_conditions`), so one read of the file
validates all of the file.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from satc.billing.catalogue import RatePlan, Service, _money, plan, service
from satc.config import CONFIG_ROOT, ConfigError, _load_yaml
from satc.intake.workflows import (
    answered,
    condition_holds_by_silence,
    evaluate_condition,
    validate_conditions,
)
from satc.models.intake import WorkflowDef
from satc.models.work import Engagement, rate_plan_for


class QuoteError(Exception):
    """A quote was asked to behave like an invoice."""


# ---------------------------------------------------------------------------
# The config: which answers imply which catalogue services
# ---------------------------------------------------------------------------

# "unknown" is the only word accepted where a quantity goes. Spelling it out in
# the config is the point: it is the owner saying "this one is real work, and
# the interview does not tell us how much of it", which is a different fact from
# leaving the service off the workflow entirely.
_UNKNOWN_QUANTITY = "unknown"


@dataclass(frozen=True, slots=True)
class ServiceRule:
    """One line of a workflow's ``services:`` block, as loaded."""

    service_code: str
    condition: dict[str, Any] | None = None
    quantity: Decimal | None = None
    """How many. ``None`` means the interview does not record it — the service is
    real, the count is not known, and the quote says so rather than assuming 1."""

    because: str = ""
    """The practice's own sentence for why this is on the quote. Optional: when
    it is blank the engine writes one from the question labels, which is duller
    but cannot disagree with the condition it is describing."""

    from_questions: tuple[str, ...] = ()
    """The question ids this rule's condition consults, in the order it reads
    them. Derived, never authored — it is what makes a quote auditable against
    the interview mechanically rather than by trusting the prose."""


def _questions_in(condition: dict[str, Any] | None) -> tuple[str, ...]:
    """Every question id a condition looks at, in order, without duplicates."""
    found: list[str] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        for branch in ("all", "any"):
            for child in node.get(branch) or []:
                walk(child)
        qid = node.get("question_id")
        if qid and qid not in found:
            found.append(str(qid))

    walk(condition)
    return tuple(found)


def _quantity(raw: Any, *, code: str, path: Path) -> Decimal | None:
    if raw is None:
        return Decimal(1)
    if isinstance(raw, str) and raw.strip().lower() == _UNKNOWN_QUANTITY:
        return None
    try:
        qty = Decimal(str(raw))
    except InvalidOperation:
        raise ConfigError(
            f"{path.name} prices {code!r} with a quantity of {raw!r}. Write a "
            f"plain number, or the word 'unknown' if the interview does not "
            f"record how many.") from None
    if not qty.is_finite() or qty <= 0:
        raise ConfigError(
            f"{path.name} prices {code!r} with a quantity of {raw!r}. A quantity "
            f"has to be a positive number, or the word 'unknown'.")
    return qty


def workflow_path(workflow_key: str, config_root: Path | None = None) -> Path:
    return (config_root or CONFIG_ROOT) / "workflows" / f"{workflow_key}.yaml"


def load_service_map(workflow_key: str,
                     config_root: Path | None = None) -> tuple[ServiceRule, ...]:
    """Read the ``services:`` block of one workflow config.

    Read here rather than folded into :func:`~satc.intake.workflows.load_workflow`
    because a workflow is about what to ASK and what to CHASE; what it is worth
    is the catalogue's business. A workflow with no ``services:`` block prices
    nothing, which is a legitimate state — a monthly bookkeeping engagement is
    hourly work the catalogue cannot quote in advance.

    Not cached. The config loader re-reads the file, so an edit to a branch's
    pricing takes effect on the next quote rather than on the next restart —
    same reasoning as the price cache in :mod:`satc.billing.catalogue`.

    EVERYTHING THIS FILE SAYS IS CHECKED HERE, not only what a particular client
    happens to fire. The conditions go through
    :func:`~satc.intake.workflows.validate_conditions`, which reads the tasks:
    block as well — reading the file validates the file, whichever question
    brought you to it. And every rule is resolved against the catalogue now, so
    a service code that does not exist and a quantity its unit forbids are found
    when the config is READ rather than when somebody quotes the one client the
    entry fires for.
    """
    path = workflow_path(workflow_key, config_root)
    data = _load_yaml(path)
    validate_conditions(data, path)
    rules: list[ServiceRule] = []
    for entry in data.get("services") or []:
        if not isinstance(entry, dict):
            raise ConfigError(
                f"{path.name} has a services entry that is not a mapping: "
                f"{entry!r}. Each entry needs at least a 'service:' code.")
        code = str(entry.get("service", "")).strip()
        if not code:
            raise ConfigError(
                f"{path.name} has a services entry with no 'service:' code: "
                f"{entry!r}. Name a code from configs/billing/services.yaml.")
        condition = entry.get("condition")
        rule = ServiceRule(
            service_code=code,
            condition=condition,
            quantity=_quantity(entry.get("quantity"), code=code, path=path),
            because=" ".join(str(entry.get("because", "")).split()),
            from_questions=_questions_in(condition))
        _check_quantity_fits_the_unit(rule, _service_for(rule, path), path)
        rules.append(rule)
    return tuple(rules)


# ---------------------------------------------------------------------------
# The quote
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class QuoteLine:
    """One priced thing the answers imply, at full catalogue value."""

    service_code: str
    label: str
    quantity: Decimal
    standard_amount: Decimal
    because: str
    from_questions: tuple[str, ...] = ()

    def describe(self) -> str:
        return (f"{self.label} (x{self.quantity:g})" if self.quantity != 1
                else self.label)


@dataclass(frozen=True, slots=True)
class UnpricedWork:
    """Work the answers imply that the catalogue cannot put a number on yet.

    It carries the same ``because`` a line would, because the owner needs to see
    the same audit trail for the thing that has no number as for the things that
    do — that is the item most likely to turn into an argument later.
    """

    service_code: str
    label: str
    because: str
    reason: str
    """Why there is no number: the hours are not known, or the count is not."""

    from_questions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Quote:
    """An estimate of what an engagement will cost, derived from the interview.

    Frozen on purpose. A quote is the arithmetic of a set of answers against the
    catalogue at a moment; if an answer changes, the right move is to quote
    again, not to edit the old number and lose what it was based on.
    """

    client_id: str
    tax_year: int
    workflow_key: str
    lines: tuple[QuoteLine, ...]
    unpriced: tuple[UnpricedWork, ...]
    plan: RatePlan
    plan_is_fallback: bool
    plan_why: str
    """One line saying where the plan came from — an agreement, or the absence
    of one. A fallback that reads like an agreement is the specific wrong answer
    this field exists to prevent."""

    engagement_price: object = None
    """What the client was ACTUALLY quoted, read from the engagement record.

    An `EngagementPrice` when the ref resolves, a `NoPrice` saying why not
    otherwise, and `None` when nothing was looked up at all — three states, not
    two, because "not asked" and "asked and there is nothing" are different
    facts and a screen that shows them the same way is lying about one of them.

    **THIS IS THE PRICE.** The firm settled it on 4 September 2026
    (`registry/fee-schedule.yaml` is the price) and 5 September (show it via
    the ref). Everything in `lines` below is this catalogue's own view of work
    it does not price; where the two would disagree, this field is the one the
    client is holding."""

    # -- what it is, and is not -------------------------------------------

    @property
    def is_estimate(self) -> bool:
        """Always true, and not a field — so it cannot be constructed false."""
        return True

    @property
    def invoice_id(self) -> str:
        raise QuoteError(
            "A quote has no invoice number and must never be given one. An "
            "invoice number says a client owes this money; a quote says what "
            "the work would be worth. Raise an Invoice when the work is done.")

    def issue(self, *args: Any, **kwargs: Any) -> None:
        raise QuoteError(
            "A quote cannot be issued — nothing has been done yet. Send it to "
            "the client as an estimate, and raise an Invoice from the catalogue "
            "once the work exists.")

    def add(self, *args: Any, **kwargs: Any) -> None:
        raise QuoteError(
            "A quote is not built by hand — it is derived from the interview "
            "answers. Add the service to the workflow's services: block in "
            "configs/workflows/, or change the answer it is gated on.")

    # -- money -------------------------------------------------------------

    @property
    def standard_total(self) -> Decimal:
        """What the priced work is worth at full rate."""
        return _money(sum((line.standard_amount for line in self.lines), Decimal(0)))

    @property
    def discount_total(self) -> Decimal:
        # Summed per line, the same way an invoice does it, so a quote and the
        # invoice that follows it cannot disagree by a rounding cent.
        return _money(sum((self.plan.discount_on(line.standard_amount)
                           for line in self.lines), Decimal(0)))

    @property
    def total(self) -> Decimal:
        """The estimate: full value less the named reduction."""
        return _money(self.standard_total - self.discount_total)

    @property
    def shows_a_discount(self) -> bool:
        return self.discount_total > 0

    # -- how it reads ------------------------------------------------------

    def summary_block(self) -> str:
        """The estimate as the owner reads it, and as the client would.

        Full value first, then the reduction with its name, then the total —
        the invoice shape. Then the work that has no number, because an estimate
        that quietly omits the hourly half of the job is worse than no estimate.
        """
        width = 56
        rows = ["ESTIMATE — not a bill. No work has been done yet.", ""]
        for line in self.lines:
            rows.append(f"{line.describe():<{width}}{line.standard_amount:>12,.2f}")
            rows.append(f"    because {line.because}")
        if self.lines:
            rows.append("")
        if self.shows_a_discount:
            rows.append(f"{'Full value of work':<{width}}{self.standard_total:>12,.2f}")
            label = self.plan.client_label or self.plan.name
            rows.append(f"{label + '  ' + f'{self.plan.discount_pct:g}%':<{width}}"
                        f"{-self.discount_total:>12,.2f}")
            rows.append("")
        if self.lines:
            rows.append(f"{'ESTIMATED TOTAL' if not self.plan.is_free else 'ESTIMATED TOTAL — no charge':<{width}}"
                        f"{self.total:>12,.2f}")
        else:
            # A total of 0.00 on an engagement that is entirely hourly is a
            # confident wrong answer — it reads as "free" when it means "not
            # priced yet". Principle 5: say which one this is.
            rows.append("NOTHING HERE HAS A PRICE YET" if self.unpriced else
                        "NOTHING ON THIS ENGAGEMENT IS PRICED BY THESE ANSWERS")
        if self.plan_is_fallback:
            rows += ["", self.plan_why]
        if self.unpriced:
            rows += ["", "Not in the total — we cannot price these yet:"]
            for item in self.unpriced:
                rows.append(f"  {item.label} — {item.reason}, because {item.because}")
        return "\n".join(rows)

    def client_sentence(self) -> str:
        """One paragraph for a client, honest about what it is not."""
        cannot = "; ".join(item.label.lower() for item in self.unpriced)
        if not self.lines:
            # Never "the estimate is $0.00". Nothing priced is not free.
            if self.unpriced:
                return (f"We cannot put a number on this in advance: {cannot}. "
                        f"That work is charged as it is done rather than quoted "
                        f"up front.")
            return ("Nothing here has a price yet — what you have told us so far "
                    "does not say what the work is.")
        if self.plan.is_free:
            head = (f"There would be no charge for this — the work is itemised at "
                    f"its full value of ${self.standard_total:,.2f} so you can see "
                    f"what is involved.")
        elif self.shows_a_discount:
            head = (f"At our standard rates this work comes to "
                    f"${self.standard_total:,.2f}; with the {self.plan.name.lower()} "
                    f"applied, the estimate is ${self.total:,.2f}.")
        else:
            head = f"The estimate for this work is ${self.total:,.2f}."
        tail = (" This is an estimate based on what you have told us so far, "
                "not a bill.")
        if self.unpriced:
            tail += (f" It does not include these, which we cannot put a number "
                     f"on until we know more: {cannot}.")
        return head + tail


def _and_list(items: Sequence[str], word: str = "or") -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" {word} " + items[-1]


def _label(workflow: WorkflowDef, qid: str) -> str:
    question = workflow.question(qid)
    return question.label if question else qid


# ---------------------------------------------------------------------------
# Deriving the quote
# ---------------------------------------------------------------------------

def _because(rule: ServiceRule, workflow: WorkflowDef,
             answers: dict[str, Any]) -> str:
    """The sentence that says which answer put this line on the quote.

    The practice's own words when the config supplies them. Otherwise one built
    from the question labels — duller, but it is read off the same condition the
    engine just evaluated, so it cannot describe a different branch than the one
    that fired.

    Only ANSWERED questions are quoted back. An ``any:`` gate can fire on one
    branch while another sits unanswered, and ``you answered "" to "Digital
    assets?"`` is an empty pair of quotes reaching a client — a sentence that
    reports silence as though it were something the client said.
    """
    if rule.because:
        return rule.because
    said = [f'"{answers[qid]}" to "{_label(workflow, qid)}"'
            for qid in rule.from_questions if answered(answers.get(qid))]
    if not said:
        return f"this is part of every {workflow.name.lower()} engagement"
    return "you answered " + _and_list(said)


def quote_for(workflow: WorkflowDef, answers: dict[str, Any], *, client_id: str,
              tax_year: int, engagements: Iterable[Engagement] = (),
              config_root: Path | None = None,
              engagements_root: Path | str | None = None) -> Quote:
    """Price an engagement from the interview answers. Always an estimate.

    Deterministic: the lines come out in the order the workflow config lists
    them, so the same answers produce the same quote in the same order, and a
    diff between two quotes is a diff between two sets of answers.

    Refuses rather than defaults in four places, and three of them are the same
    refusal the invoice engine already makes — because a quote that cannot
    become an invoice is a number the owner has to walk back with a client, and
    the quote is the FIRST number that client sees.

    * A workflow that prices a service the catalogue does not have. That is a
      typo in a config the owner edits by hand, and a typo that silently drops a
      $450 line is the expensive kind of quiet.
    * A client whose recorded rate plan is no longer in the catalogue: nothing
      can be priced from a plan that does not exist, and guessing the default
      would invent an agreement.
    * A REDUCED PLAN WITH NO RECORDED BASIS. ``Invoice.issue`` refuses to bill
      it, so quoting it promises a discount the practice will then withdraw —
      and a discount withdrawn is worse than one never offered.
    * A fixed-price service quoted at a quantity other than one, which
      ``Invoice.add`` refuses for the same structural reason.
    """
    on_file = rate_plan_for(engagements, client_id=client_id, tax_year=tax_year)
    if on_file.plan_missing:
        raise ConfigError(on_file.why())
    if on_file.basis_missing:
        # The same rule as Invoice.issue, moved to the front of the conversation.
        # Quoting at STANDARD instead would be the other candidate fix, and it is
        # worse: the plan IS on file, only the reason is not, so charging a
        # hardship client full rate would overwrite a recorded fact with an
        # agreement nobody made (principle 1) — and it would tell someone having
        # a rough year a number the practice never intended to send them.
        raise ConfigError(
            f"{on_file.why()} Nothing can be quoted at that rate yet. A quote is "
            f"the first number this client sees, and an invoice on a reduced plan "
            f"with no basis cannot be issued — so quoting it promises a discount "
            f"the practice would have to take back. Record why on the {tax_year} "
            f"engagement, or move the client to a plan that needs no basis.")
    rate_plan = plan(on_file.plan_key)

    from satc.billing.engagement_price import price_for_ref
    from satc.models.work import engagement_for

    path = workflow_path(workflow.key, config_root)

    # THE PRICE THE CLIENT IS ACTUALLY HOLDING, looked up ONCE. Read through
    # the `engagement_ref` recorded on this year's engagement -- the same seam
    # `collect` resolves a drop folder on. `None` when the caller gave no
    # engagements to look in, which is a different fact from "looked and found
    # nothing" and reads differently on the screen.
    found = engagement_for(list(engagements), client_id=client_id,
                           tax_year=tax_year)
    priced = None
    if found is not None:
        priced = price_for_ref(getattr(found, "engagement_ref", ""),
                               root=engagements_root)

    lines: list[QuoteLine] = []
    unpriced: list[UnpricedWork] = []
    for rule in load_service_map(workflow.key, config_root):
        # Did the answers put this here, or did the silence? A gate satisfied
        # only because a question is unanswered has decided nothing (principle
        # 2), so it may never become money — but it may not vanish either, or a
        # $450 line disappears from an estimate with nothing said. The engine
        # answers both halves; this module no longer keeps its own copy of the
        # rule, which is how the two readings drifted apart in the first place.
        told_us_so = evaluate_condition(rule.condition, answers)
        if not told_us_so and not condition_holds_by_silence(rule.condition, answers):
            continue
        svc = _service_for(rule, path)

        silent = tuple(qid for qid in rule.from_questions
                       if not answered(answers.get(qid)))
        because = (_because(rule, workflow, answers) if told_us_so else
                   "nothing on file yet says whether this applies")

        reason = ""
        if svc.priced_by:
            # NOT OURS TO PRICE, AND NOW WE CAN SAY WHOSE IT IS. A number
            # invented here is a second source for money somebody else already
            # decided, and the client keeps whichever one says more. Where the
            # ref resolves, the refusal carries the real figure rather than a
            # file path -- the firm's answer on 5 September 2026 was "show the
            # engagement price via the ref", and a reason a person can act on
            # beats a reason they have to go and look up.
            if priced is not None and getattr(priced, "is_priced", False):
                reason = (f"covered by engagement {priced.ref} at "
                          f"{priced.total}, which is the figure the client was "
                          f"quoted")
            elif priced is not None:
                reason = (f"priced by the engagement, not by this catalogue — "
                          f"{priced.reason}")
            else:
                reason = (f"priced by {svc.priced_by}, not by this catalogue — "
                          f"the engagement carries the figure")
            # AND THE QUANTITY GAP IS STILL WORTH SAYING. The first version
            # made `priced_by` win the whole branch, so "the interview does not
            # record how many states" stopped being said at all the moment the
            # engagement took over the price. That fact is not about who
            # prices it: the ENGAGEMENT needs to know how many states too, and
            # the interview is where that would have been asked.
            if rule.quantity is None:
                reason += (" — and the interview does not record how many, "
                           "which the engagement needs as well")
        elif svc.unit == "per_hour":
            # Principle 1. The hours are the whole price here, and nobody knows
            # them before the work — a "typical" number would be a guess wearing
            # a dollar sign.
            reason = (f"charged at ${svc.standard_rate:,.2f} an hour, and the "
                      f"hours are not known until the work is done")
        elif rule.quantity is None:
            reason = (f"${svc.standard_rate:,.2f} each, and the interview does "
                      f"not record how many")
        elif told_us_so:
            lines.append(QuoteLine(
                service_code=svc.code, label=svc.label_for_client,
                quantity=rule.quantity,
                standard_amount=svc.amount_for(rule.quantity),
                because=because, from_questions=rule.from_questions))
            continue

        if not told_us_so:
            asked = _and_list([f'"{_label(workflow, qid)}"' for qid in silent], "and")
            verb = "is" if len(silent) == 1 else "are"
            unanswered = (f"we cannot tell whether this applies until {asked} "
                          f"{verb} answered")
            reason = f"{reason} — and {unanswered}" if reason else unanswered
        unpriced.append(UnpricedWork(
            service_code=svc.code, label=svc.label_for_client, because=because,
            reason=reason, from_questions=rule.from_questions))

    return Quote(
        client_id=client_id, tax_year=tax_year, workflow_key=workflow.key,
        lines=tuple(lines), unpriced=tuple(unpriced), plan=rate_plan,
        plan_is_fallback=on_file.is_fallback, plan_why=on_file.why(),
        engagement_price=priced)


def _check_quantity_fits_the_unit(rule: ServiceRule, svc: Service,
                                  path: Path) -> None:
    """A fixed-price service is one charge, so a quote may only ever say one.

    ``Invoice.add`` already refuses any quantity but 1 on a fixed service — it
    is one charge however long the work took, which is what "fixed" means. The
    quote asked only whether the number was positive and finite, and never asked
    the catalogue what it was counting, so a config edit could produce a total
    the invoice engine structurally cannot bill: an estimate the owner has to
    walk back with a client who has already read it.

    CALLED FROM :func:`load_service_map`, not from the per-rule loop in
    :func:`quote_for`. Inside the loop it only ran for entries a particular
    client's answers fired, so a broken ``services:`` entry sat in the file
    until somebody happened to quote the one client it applied to — a config
    error found by a client rather than by reading the config. Every other check
    on this file happens when the file is read, and so does this one.
    """
    if svc.unit != "fixed" or rule.quantity == 1:
        return
    said = _UNKNOWN_QUANTITY if rule.quantity is None else f"{rule.quantity:g}"
    raise ConfigError(
        f"{path.name} prices {svc.code!r} at "
        f"a quantity of {said}, but configs/billing/services.yaml calls "
        f"{svc.name} a FIXED-price service — one charge, however long it takes. "
        f"An invoice refuses any quantity but 1 on it, so this quote could never "
        f"be billed. Drop the quantity, or make the service per_form in the "
        f"catalogue if it genuinely multiplies.")


def _service_for(rule: ServiceRule, path: Path) -> Service:
    try:
        return service(rule.service_code)
    except ConfigError as unknown:
        # Principle 10: name both files, because the fix is in one of them and
        # the reader cannot tell which without being told what each says.
        raise ConfigError(
            f"{path.name} prices "
            f"{rule.service_code!r}, which the service catalogue does not have. "
            f"Either add it to configs/billing/services.yaml or correct the "
            f"services: block. ({unknown})") from None
