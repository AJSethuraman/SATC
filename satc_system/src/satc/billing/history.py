"""PRICE HISTORY — what the practice charged, when it changed, and who changed it.

A rate is firm policy, not law (principle 4): the owner moves it over coffee, no
citation required. But "what were we charging in March?" is a real question a
practice gets asked — by a client querying a bill, by the owner comparing this
season to last, by anyone reconciling a quote given weeks before the invoice. A
config file cannot answer it, because a YAML file only ever says what the price
is *now*.

So every movement is a RECORDED FACT (principle 2): what changed, when, from
what to what, and how we know — including the case where the honest answer is
"we do not know who did this". :func:`rate_on` is the point of the whole module.
A change log the owner has to read backwards to answer a question is a log; a
record answers the question.

THREE THINGS THIS DELIBERATELY IS NOT
-------------------------------------

**It is not the source of truth for prices.** ``configs/billing/*.yaml`` is.
The record describes the file's movements; it never overrides them, and where
the two disagree :func:`rate_on` says so out loud rather than quietly preferring
its own copy. An override that silently beats a hand edit is the trap this
design exists to avoid — you change the file, nothing happens, and nothing says
why.

**It is not a mirror of the config.** The owner can still edit the YAML by hand,
in an editor, at midnight, and that is deliberate and is not going away. A
record that only knew about changes made through the app would be *complete
looking* and wrong, which is worse than being obviously partial: a gap looks
exactly like nothing having happened. So SATC fingerprints the files and, when
one has moved underneath it, records the movement with **no author** and with
the date pinned to an INTERVAL rather than to the day somebody happened to open
the app. An ugly honest row beats a silent gap (principles 1 and 2).

**It is not a place a model may write.** :func:`record_change` takes an actor
and refuses anything that is not the owner (principle 6). A model must not be
able to change what the practice charges — and, just as important, must not be
able to leave behind a record saying a human did.

WHAT AN ISSUED INVOICE DOES NOT NEED FROM THIS
----------------------------------------------

Nothing. ``InvoiceLine.standard_rate`` stores the rate ON THE LINE at the moment
the line is added, so an invoice already carries the price it was raised at and
a rate that moves in March cannot reprice a bill issued in February. This module
answers about the *catalogue*, not about invoices — which is why it can be added
without touching a line of invoicing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from satc.billing import catalogue
from satc.billing.invoice import BillingError
from satc.models.actor import Actor, require_human

# What KIND of priced thing moved. Two, because there are two files.
SERVICE = "service"
RATE_PLAN = "rate_plan"

# The fields whose movement is watched in the files themselves. Other fields
# (a name, a client label) can be recorded through record_change, but nothing
# reconstructs them from disk — they are not what the practice charges.
STANDARD_RATE = "standard_rate"
DISCOUNT_PCT = "discount_pct"

_INSTEAD = (
    "ask the owner to make the change on the prices screen — a price is the "
    "practice's own policy, and the record of it has to name the person who set it"
)


def _service_values(config_root: Path | None) -> dict[str, str]:
    return {code: _norm(svc.standard_rate)
            for code, svc in catalogue.load_services(config_root).items()}


def _plan_values(config_root: Path | None) -> dict[str, str]:
    return {key: _norm(p.discount_pct)
            for key, p in catalogue.load_plans(config_root).items()}


@dataclass(frozen=True, slots=True)
class _Watched:
    """One priced file, and the one field in it that is money."""

    filename: str
    field: str
    noun: str
    read: Callable[[Path | None], dict[str, str]]


_WATCHED: dict[str, _Watched] = {
    SERVICE: _Watched("services.yaml", STANDARD_RATE, "service", _service_values),
    RATE_PLAN: _Watched("rate_plans.yaml", DISCOUNT_PCT, "rate plan", _plan_values),
}


def _norm(value) -> str:
    """One spelling per value, so a reformat is not mistaken for a price change.

    ``450`` and ``450.00`` are the same rate, and a record that announced a
    change every time the owner tidied the file would be exactly the noise
    principle 13 warns about — the owner learns to scroll past it, and then
    scrolls past the one that mattered. ``format(..., "f")`` because
    ``Decimal("450.00").normalize()`` is ``4.5E+2``, which no one would read as
    a price.
    """
    text = " ".join(str(value).split())
    try:
        number = Decimal(text)
        if not number.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ArithmeticError, ValueError):
        return text
    return format(number.normalize(), "f")


def _norm_opt(value) -> str | None:
    """``None`` means NOT RECORDED and survives as ``None``. It is never a zero."""
    return None if value is None else _norm(value)


@dataclass(frozen=True, slots=True)
class PriceChange:
    """One movement in what the practice charges. A fact, not a decision.

    ``old_value`` / ``new_value`` are text, because this table holds discounts
    and rates and one day a renamed label, and because the value that was true
    in March must not be re-rounded by a later build. They come back as Decimal
    through :attr:`old_rate` / :attr:`new_rate` when they are money.

    ``None`` in either means **not recorded** — never zero, never "no change".
    The only way to get one is an edit made outside the app before SATC had ever
    read the file, and it renders as "not recorded" wherever it is shown.
    """

    kind: str
    subject: str
    field: str
    old_value: str | None
    new_value: str | None
    changed_on: date
    changed_by: Actor | None = None
    """None when the author is genuinely unknown — an edit made outside the app.

    NOT a system actor standing in for one. SATC *noticed* that change; it did
    not make it, and a row claiming otherwise would be a fabricated fact in the
    one column a later reader would rely on."""

    note: str = ""
    not_before: date | None = None
    """The last date the OLD value was still on disk.

    An out-of-band edit happened somewhere between this and ``changed_on``, and
    nothing in the file records which day. Pinning it to an interval is what
    lets :func:`rate_on` refuse a date inside the gap instead of answering
    confidently on a coin flip (principle 5)."""

    recorded_at: datetime | None = None
    """When the row was WRITTEN, which is not when the price moved.

    Its job is ordering. A pricing pass can move the same service twice in one
    morning — 450 to 495, then a correction to 595 ten minutes later — and two
    changes sharing a date have no order at all unless one is recorded. Without
    it, ``rate_on`` picked whichever hashed higher, which is a coin flip
    answering a question about money. The order is RECORDED rather than inferred
    by chaining old values onto new ones (principle 2)."""

    # -- identity ----------------------------------------------------------

    @property
    def change_id(self) -> str:
        """Derived from what the change IS, so recording it twice is once.

        Principle 8. The same detection running on two page loads, or the owner
        double-submitting the form, lands on the same primary key and REPLACES
        its row rather than filing a second identical movement. The author is
        deliberately not in the hash: who recorded a change is not part of which
        change it is, and including it would let the same edit appear twice
        under two hands.
        """
        blank = chr(0)   # so a NOT-RECORDED value can never collide with a real one
        raw = "|".join([
            self.kind, self.subject, self.field,
            self.old_value if self.old_value is not None else blank,
            self.new_value if self.new_value is not None else blank,
            self.changed_on.isoformat(),
            self.not_before.isoformat() if self.not_before else "",
        ])
        return "prc_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    # -- money -------------------------------------------------------------

    @property
    def old_rate(self) -> Decimal | None:
        return _as_money(self.old_value)

    @property
    def new_rate(self) -> Decimal | None:
        return _as_money(self.new_value)

    # -- how it reads ------------------------------------------------------

    @property
    def author_is_recorded(self) -> bool:
        return self.changed_by is not None

    @property
    def author_label(self) -> str:
        return self.changed_by.handle if self.changed_by else "author not recorded"

    @property
    def is_dated_exactly(self) -> bool:
        """False when all we know is that it happened in a window."""
        return self.not_before is None or self.not_before >= self.changed_on

    @property
    def when_label(self) -> str:
        if self.is_dated_exactly:
            return self.changed_on.isoformat()
        return f"between {self.not_before} and {self.changed_on}"

    def value_label(self, value: str | None) -> str:
        return "not recorded" if value is None else value

    def summary(self) -> str:
        """The row as the owner reads it, evidence and all, in one line.

        Principle 13: two rows never say the same thing. The note is what makes
        an authorless row readable as *what happened* rather than as a blank
        somebody forgot to fill in.
        """
        head = (f"{self.subject} {self.field.replace('_', ' ')} "
                f"{self.value_label(self.old_value)} → {self.value_label(self.new_value)}")
        tail = f"{self.when_label}, {self.author_label}"
        return f"{head} · {tail}" + (f" · {self.note}" if self.note else "")


def _as_money(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(value)
    except (InvalidOperation, ArithmeticError, ValueError):
        return None
    return number if number.is_finite() else None


# --- recording a change the app made ---------------------------------------


def record_change(store, *, kind: str, subject: str, field: str,
                  old_value, new_value, actor: Actor,
                  changed_on: date | None = None, note: str = "",
                  recorded_at: datetime | None = None,
                  config_root: Path | None = None) -> PriceChange:
    """Record a price change the owner just made. Refuses anyone but the owner.

    The actor is DERIVED by the caller from the request context
    (``satc.app.state.acting_actor``) and passed in — it is never a string this
    function will believe. A model rung, an API tool, a sweep or a script gets a
    non-human actor and is refused here, at the engine, rather than in a prompt
    (principle 6).

    CALL THIS AFTER WRITING THE FILE, not before. The file is the source of
    truth, so the record is only worth keeping if it agrees with it; a watched
    field whose new value is not what the file now says is refused, naming the
    order to do it in. Recording it anyway would leave the two disagreeing with
    nothing to say which was right.

    It also re-fingerprints the file, which is not incidental: without it the
    owner's own edit would be re-discovered a moment later and recorded a second
    time as "changed outside the app, author not recorded" — the record calling
    the owner a stranger in their own log.
    """
    require_human(actor, f"change what the practice charges for {subject!r}",
                  instead=_INSTEAD)
    watched = _WATCHED.get(kind)
    if watched is None:
        raise BillingError(
            f"{kind!r} is not something this practice prices. Use "
            f"{SERVICE!r} for a service rate or {RATE_PLAN!r} for a plan discount.")

    when = changed_on or date.today()
    change = PriceChange(
        kind=kind, subject=subject, field=field,
        old_value=_norm_opt(old_value), new_value=_norm_opt(new_value),
        changed_on=when, changed_by=actor, note=note,
        recorded_at=recorded_at or datetime.now())

    values = watched.read(config_root)          # ConfigError names the bad file
    if field == watched.field:
        on_disk = values.get(subject)
        if on_disk != change.new_value:
            raise BillingError(
                f"The record was not written: {watched.filename} says "
                f"{subject} is {on_disk if on_disk is not None else 'not in the file'}, "
                f"not {change.new_value}. The file is the source of truth for "
                f"prices — write the change to it first, then record it.")

    store.save_price_changes([change])
    # The file as it now stands is what the next reconciliation compares against.
    _remember(store, kind, values=values, on=when, config_root=config_root)
    return change


def changes_for(store, subject: str) -> list[PriceChange]:
    """Every recorded movement of one service or plan, oldest first."""
    return _sorted(store.load_price_changes(subject))


def all_changes(store) -> list[PriceChange]:
    """The whole record, oldest first."""
    return _sorted(store.load_price_changes())


def _sorted(changes) -> list[PriceChange]:
    """Oldest first, and never in hash order.

    ``recorded_at`` breaks a tie between two changes made on the same day; the
    change_id is only the last resort, and reaching it means two rows are
    indistinguishable in every recorded respect.
    """
    return sorted(changes, key=lambda c: (c.changed_on,
                                          c.recorded_at or datetime.min,
                                          c.subject, c.change_id))


# --- noticing what the app did not do --------------------------------------
#
# The owner edits the YAML by hand and always will. Everything below exists so
# that the record does not quietly pretend otherwise.


def _digest(path: Path) -> str:
    """A content hash of a priced file. Empty string when it is not there."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _watch_key(kind: str) -> str:
    return f"price_watch:{_WATCHED[kind].filename}"


def _watch_record(store, kind: str) -> dict | None:
    """What the file looked like the last time SATC read it, or None.

    Unreadable JSON is treated as no record at all rather than as an empty one:
    a corrupt marker is not evidence that every price just changed, and the
    resulting flood of authorless rows would be exactly the noise that teaches
    the owner to ignore this screen.
    """
    raw = store.get_meta(_watch_key(kind))
    if not raw:
        return None
    try:
        seen = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return seen if isinstance(seen, dict) else None


def _remember(store, kind: str, *, values: dict[str, str], on: date,
              config_root: Path | None = None) -> None:
    """Pin what the file says now, so the next look can tell what moved.

    ``began`` is written once and then carried forward untouched. ``checked_on``
    moves with every look; ``began`` is the day the record started and must not,
    or the record would keep claiming to begin this morning and lose the ability
    to say "nothing is recorded about February".

    ``checked_on`` never moves BACKWARDS either. A change the owner dates to
    last Monday is still a file SATC is looking at today, and letting the
    backdate rewind it would widen the window on the next out-of-band edit into
    days we can in fact account for.
    """
    seen = _watch_record(store, kind) or {}
    looked = max([on, *(d for d in [_as_date(seen.get("checked_on"))] if d)])
    path = catalogue.billing_dir(config_root) / _WATCHED[kind].filename
    store.set_meta(_watch_key(kind), json.dumps({
        "hash": _digest(path),
        "began": str(seen.get("began") or looked.isoformat()),
        "checked_on": looked.isoformat(),
        "values": values}))


def record_begins(store, kind: str = SERVICE, *, today: date | None = None) -> date:
    """The first date this record can speak about at all.

    Before it, the file was whatever it was and SATC was not watching. Saying so
    is the difference between a record and a guess: extrapolating today's rate
    backwards past the day we started looking is inventing a value (principle 1).
    """
    seen = _watch_record(store, kind) or {}
    for key in ("began", "checked_on"):
        when = _as_date(seen.get(key))
        if when is not None:
            return when
    return today or date.today()


def reconcile_files(store, *, today: date | None = None,
                    config_root: Path | None = None) -> list[PriceChange]:
    """Compare the priced files with what SATC last saw, and record the difference.

    Returns the changes it recorded — usually none, because usually nothing has
    moved. A first look records nothing and simply starts watching: there is
    nothing to compare against yet, and inventing a change out of the first
    sighting would put a fictional movement in the record.

    A ConfigError from a broken file is left to escape. Serving a comparison
    against a file that will not parse is the one thing worse than raising, and
    the caller for this is the prices screen, where a bad edit already has to be
    shown to the owner (principle 5, and ``catalogue._fresh`` does the same).
    """
    when = today or date.today()
    recorded: list[PriceChange] = []
    for kind in _WATCHED:
        recorded.extend(_reconcile_one(store, kind, today=when, config_root=config_root))
    return recorded


def _reconcile_one(store, kind: str, *, today: date,
                   config_root: Path | None) -> list[PriceChange]:
    watched = _WATCHED[kind]
    path = catalogue.billing_dir(config_root) / watched.filename
    digest = _digest(path)
    seen = _watch_record(store, kind)
    values = watched.read(config_root)

    if seen is None:
        _remember(store, kind, values=values, on=today, config_root=config_root)
        return []
    if seen.get("hash") == digest:
        return []

    # The file moved. A comment-only or whitespace-only edit moves the hash and
    # no price, and produces no rows — the record is of what the practice
    # charges, not of when the file was saved.
    before: dict[str, str] = seen.get("values") or {}
    last = _as_date(seen.get("checked_on")) or today
    noticed_at = datetime.now()
    changes = [
        PriceChange(
            kind=kind, subject=subject, field=watched.field,
            old_value=before.get(subject), new_value=values.get(subject),
            changed_on=today, changed_by=None,
            note=_outside_note(watched, last, today,
                               added=subject not in before,
                               removed=subject not in values),
            not_before=last, recorded_at=noticed_at)
        for subject in sorted(set(before) | set(values))
        if before.get(subject) != values.get(subject)
    ]
    if changes:
        store.save_price_changes(changes)
    _remember(store, kind, values=values, on=today, config_root=config_root)
    return changes


def _as_date(text) -> date | None:
    try:
        return date.fromisoformat(str(text))
    except (ValueError, TypeError):
        return None


def _outside_note(watched: _Watched, last: date, today: date, *,
                  added: bool, removed: bool) -> str:
    """Say plainly what is known and what is not.

    The window matters. "Changed on the 20th" would be a fact SATC does not
    have — all it knows is that the file said one thing on the 12th and another
    on the 20th, and a client asking about a bill dated the 15th deserves the
    honest "the record cannot say" rather than a confident wrong answer.
    """
    window = (f"between {last} and {today}" if last < today else f"on {today}")
    note = f"changed outside the app, {window} — author not recorded"
    if added:
        note += f". This {watched.noun} was not in the file before."
    elif removed:
        note += f". This {watched.noun} is no longer in the file."
    return note


# --- the question the record exists to answer ------------------------------


@dataclass(frozen=True, slots=True)
class RateAsOf:
    """A rate on a date, and HOW WE KNOW — or an explicit "not recorded".

    The basis is not decoration. This answer gets quoted to a client, so the
    difference between "the file said so on the day" and "nobody recorded that
    week" has to travel with the number (principle 2). An unknown rate is None
    and says why; it is never a plausible-looking figure.
    """

    rate: Decimal | None
    basis: str

    @property
    def is_known(self) -> bool:
        return self.rate is not None

    def __str__(self) -> str:
        head = f"{self.rate:,.2f}" if self.is_known else "not recorded"
        return f"{head} — {self.basis}"


def rate_on(store, code: str, when: date, *, today: date | None = None,
            config_root: Path | None = None) -> RateAsOf:
    """What was this service's standard rate on that date?

    The question a practice actually asks: a client queries a bill from March, a
    quote given in February is honoured in May, last season is compared with
    this one. Answered from recorded facts, and refused where the record has a
    hole in it rather than filled in with today's number — which is the same
    number the owner could have read off the screen, dressed up as history.

    Note what this does NOT answer: what a particular client PAID. That is the
    standard rate crossed with their rate plan, and for anything already
    invoiced it is on the invoice line, which stores the rate it was raised at.
    """
    now = today or date.today()
    changes = [c for c in changes_for(store, code)
               if c.kind == SERVICE and c.field == STANDARD_RATE]

    # TODAY IS NOT HISTORY. The file is the source of truth for prices, so a
    # question about now is answered by reading it, not by trusting the log to
    # have kept up. Where the two disagree the file wins and the answer says so
    # — a record silently outranking a hand edit is the failure this whole
    # design was chosen to avoid.
    if when >= now:
        live = _catalogue_rate(code, config_root)
        if live is not None:
            basis = f"what configs/billing/services.yaml says today ({now})"
            last = changes[-1] if changes else None
            if last is not None and last.new_rate is not None and last.new_rate != live:
                basis += (f" — the price record's last entry says {last.new_value}, "
                          f"{last.when_label}; SATC records the difference the next "
                          f"time it reads the file")
            return RateAsOf(live, basis)

    # An edit made outside the app is dated to a WINDOW. A date inside it is
    # genuinely unanswerable, and a coin flip here is a confident wrong answer
    # about money (principle 5).
    for change in changes:
        if change.not_before is not None and change.not_before < when < change.changed_on:
            return RateAsOf(None, (
                f"{code} was changed outside the app between {change.not_before} and "
                f"{change.changed_on}, and nothing records which side of {when} it "
                f"fell. The rate was either {change.value_label(change.old_value)} or "
                f"{change.value_label(change.new_value)}"))

    prior = [c for c in changes if c.changed_on <= when]
    if prior:
        last = prior[-1]
        if last.new_rate is None:
            return RateAsOf(None, (
                f"{code} changed on {last.changed_on} and what it changed to was "
                f"not recorded ({last.note or 'no note'})"))
        return RateAsOf(last.new_rate, (
            f"changed to {last.new_value} {last.when_label} by {last.author_label}"))

    began = record_begins(store, SERVICE, today=now)
    if when < began:
        return RateAsOf(None, (
            f"the price record begins on {began}, and nothing is recorded about "
            f"{code} before that. configs/billing/services.yaml is edited by hand, "
            f"so what it said earlier is only knowable from the file's own history "
            f"— try git log on it"))

    later = [c for c in changes if c.changed_on > when]
    if later:
        first = later[0]
        if first.old_rate is None:
            return RateAsOf(None, (
                f"the first recorded change to {code} is {first.when_label}, and "
                f"what it was before that was not recorded ({first.note or 'no note'})"))
        return RateAsOf(first.old_rate, (
            f"in force from {began} until it changed to "
            f"{first.value_label(first.new_value)} {first.when_label}"))

    live = _catalogue_rate(code, config_root)
    if live is None:
        return RateAsOf(None, (
            f"there is no service called {code!r} in the catalogue and no change "
            f"recorded against it. Check the code against configs/billing/services.yaml"))
    return RateAsOf(live, f"unchanged since the price record began on {began}")


def _catalogue_rate(code: str, config_root: Path | None) -> Decimal | None:
    """Today's rate from the file, or None if it cannot be read.

    Swallowing the ConfigError is deliberate HERE and nowhere else: this is a
    question about a past date that the caller can still be given a recorded
    answer to, and refusing to open the record because today's file has a typo
    in it would take the history away exactly when somebody is fixing something.
    The refusal still happens loudly wherever the catalogue itself is loaded.
    """
    from satc.config import ConfigError

    try:
        found = catalogue.load_services(config_root).get(code)
    except ConfigError:
        return None
    return None if found is None else found.standard_rate
