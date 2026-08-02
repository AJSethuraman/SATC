"""WHAT WE PROMISE — turnaround the practice offers, and whether it kept it.

A service level is a **promise**, which makes it firm policy and never law
(principle 4). "We come back on a notice within two business days" has no
authority behind it: the owner said it, the owner can change it over coffee,
and the worst consequence of breaking it is an apology. A statutory deadline is
computed from a cited rule, cannot be argued with, and the consequence of
missing it is a penalty. Those two things must not look alike **anywhere** — so
the durations live in ``configs/firm_policy.yaml`` beside the other
preferences, they carry no citation, the loader *refuses* one that tries to,
and everything derived here is flagged :attr:`SLAPromise.is_firm_policy` so a
screen can render it as a promise rather than as a date with teeth.

THE HARD PART: A CLOCK NEEDS A RECORDED START AND A RECORDED STOP.

Most of the promises a tax practice makes cannot be measured in this codebase
today, and saying so is the entire value of this module. There is no inbound
message anywhere — SATC records *documents* arriving, not correspondence. There
is no "the documents went complete at" fact: readiness is computed from what is
outstanding right now, so the moment the last blocking item landed is nowhere.
There is no delivery fact at all — ``satc.work.stage`` refuses to conclude
``delivered`` for exactly this reason. And an 8879 out for signature is an
Authorization, which ``satc.models.evidence`` says is deliberately not modelled
yet.

The tempting move is to substitute something plausible: treat the last completed
task as delivery, or the job's creation as first contact. That is precisely how
a metric becomes a lie — it would report a green tick derived from a guess, and
nobody downstream could tell it from a measured one. So where a fact is not
recorded, :func:`compliance` REFUSES and NAMES the fact that is missing
(principles 1, 5 and 10). "SATC cannot tell you whether this was met: nothing
records when the documents went complete" is the honest answer, and it is far
more useful than a tick.

Which facts the practice actually records is a question about this CODEBASE, not
a preference, so it lives in :data:`FACTS` here rather than in the owner's YAML.
The owner sets durations; the code knows what it can see. When a Deliverable
entity lands, one entry here gains a ``recorded_as`` and every promise resting
on it starts answering — with no change to the config and no change to callers.

Business-day arithmetic goes through ``satc.obligations.calendar``. There is one
weekend rule in this system and it is not in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import yaml

from satc.config import CONFIG_ROOT, ConfigError
from satc.obligations.calendar import next_business_day

POLICY_FILE = "firm_policy.yaml"


def policy_file(config_root: Path | None = None) -> Path:
    return (config_root or CONFIG_ROOT) / POLICY_FILE


# --- what the practice can actually see ------------------------------------


@dataclass(frozen=True, slots=True)
class FactRef:
    """One end of an SLA clock, and whether anything in SATC records it.

    ``recorded_as`` is empty when nothing does. That emptiness is the point:
    it is what turns a compliance question into a named refusal instead of a
    guess.
    """

    key: str
    describes: str
    """In the owner's words — "when the notice reached us"."""

    recorded_as: str = ""
    """Where SATC holds this fact. Empty means nowhere, and nothing may pretend
    otherwise."""

    would_need: str = ""
    """What would have to exist for this to become measurable. Principle 10:
    a refusal that only says "no" ends the conversation."""

    @property
    def is_recorded(self) -> bool:
        return bool(self.recorded_as)


# The finite set of clock ends, and the honest state of each one TODAY. Adding
# a promise means picking two of these — a config that names anything else is
# refused at load, because a clock end nobody can produce is a metric that will
# quietly never be measured.
FACTS: dict[str, FactRef] = {f.key: f for f in (
    FactRef(
        key="client_message_received",
        describes="when a client's message reached us",
        would_need=(
            "SATC records documents arriving, not correspondence — nothing holds "
            "an inbound email, call or portal note. Recording client "
            "correspondence as it arrives would settle it.")),
    FactRef(
        key="reply_sent",
        describes="when we replied",
        would_need=(
            "Nothing in SATC sends, and nothing records that the owner sent "
            "something (principle 9). A recorded 'replied on' against the "
            "message would settle it.")),
    FactRef(
        key="notice_received",
        describes="when the notice reached us",
        recorded_as=("ReceivedDocument.obtained_at, on a document typed as an "
                     "IRS or state notice")),
    FactRef(
        key="notice_response_sent",
        describes="when our response to the notice went out",
        would_need=(
            "A response leaves on paper or in the owner's own mail client, and "
            "nothing records that it did. A Deliverable with a sent date would "
            "settle it.")),
    FactRef(
        key="documents_complete",
        describes="when the documents went complete",
        would_need=(
            "Readiness is computed from what is outstanding RIGHT NOW, so the "
            "moment the last blocking item landed is nowhere. The individual "
            "arrival times exist; a recorded 'went complete on' does not.")),
    FactRef(
        key="return_delivered",
        describes="when the return went to the client",
        would_need=(
            "satc.work.stage refuses to conclude delivery for this exact "
            "reason — a finished task list is not a delivery. A Deliverable "
            "carrying a sent date would settle it.")),
    FactRef(
        key="authorization_signed",
        describes="when the signed 8879 came back",
        would_need=(
            "An 8879 out for signature is an Authorization, which "
            "satc.models.evidence says is deliberately not modelled yet — the "
            "signature lifecycle comes with it.")),
    FactRef(
        key="acknowledgement_sent",
        describes="when we acknowledged the signature",
        would_need=(
            "Same gap as every other outbound act: SATC proposes and does not "
            "send, so nothing records that the acknowledgement went.")),
    FactRef(
        key="efile_rejected",
        describes="when the rejection was keyed off Drake",
        recorded_as="Filing.ack_date, on a filing whose ack_code is 'R'"),
    FactRef(
        key="efile_retransmitted",
        describes="when the fixed return went back out",
        recorded_as=("Filing.transmitted_at, on the next filing for the same "
                     "return")),
)}


def _fact(key: str, *, sla_key: str, side: str) -> FactRef:
    found = FACTS.get(key)
    if found is None:
        raise ConfigError(
            f"SLA {sla_key!r} says it {side} {key!r}, which is not a fact SATC "
            f"knows about. Pick one of: {', '.join(sorted(FACTS))}. A clock end "
            f"nobody can produce is a promise that will never be measured.")
    return found


# --- the promise itself -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class SLADef:
    """One promise the practice makes. FIRM POLICY — no citation, ever."""

    key: str
    label: str
    days: int
    business_days: bool
    """Whether the count skips weekends and legal holidays. Required in the
    config rather than defaulted: two business days and two calendar days are
    different promises, and guessing which one the owner meant would invent the
    answer."""

    starts_when: FactRef
    ends_when: FactRef
    note: str = ""

    @property
    def is_measurable(self) -> bool:
        """Whether SATC could EVER answer this, for anybody."""
        return self.starts_when.is_recorded and self.ends_when.is_recorded

    @property
    def missing_fact(self) -> FactRef | None:
        """The end of the clock nothing records — start first, it blocks more."""
        if not self.starts_when.is_recorded:
            return self.starts_when
        if not self.ends_when.is_recorded:
            return self.ends_when
        return None

    def why_unmeasurable(self) -> str:
        """The named refusal, or ``""`` when this one can be measured."""
        gap = self.missing_fact
        if gap is None:
            return ""
        return (f"SATC cannot tell you whether this was met: nothing records "
                f"{gap.describes}. {gap.would_need}")

    def duration(self) -> str:
        """The promise as the owner would say it: ``two business days``."""
        unit = "business day" if self.business_days else "calendar day"
        return f"{self.days} {unit}{'s' if self.days != 1 else ''}"

    def landing(self, started_on: date) -> date:
        """Where the promise lands, counting from the day the clock started.

        The start day itself never counts — a notice that arrives on Tuesday
        with a two-business-day promise is answered by Thursday, not Wednesday.

        A calendar-day promise is deliberately NOT shifted off a weekend. IRC
        §7503 moves an *act with legal consequence*; a promise has none, and
        shifting it would hand the practice extra time it never offered. A
        business-day promise skips weekends because that is what the owner
        chose by writing ``business_days: true``.
        """
        if self.business_days:
            day = started_on
            for _ in range(self.days):
                day = next_business_day(day)
            return day
        return started_on + timedelta(days=self.days)


@dataclass(frozen=True, slots=True)
class SLAPromise:
    """A promise landed on a calendar. NOT a deadline, and it says so.

    There is no ``citation`` on this type and there never will be. Anything with
    an authority behind it is an obligation and belongs in
    ``configs/obligations/`` with its source.
    """

    kind: str
    label: str
    started_on: date
    promised_date: date
    duration: str
    as_of: date
    is_firm_policy: bool = True
    """Always true. Read by the UI so a promise cannot be rendered like a
    statutory date — see principle 4."""

    @property
    def by(self) -> date:
        """Alias for :attr:`promised_date`, for the screen that reads ``.by``.

        Deliberately not a second field: one date, one storage slot, so the two
        names cannot ever disagree. ``promised_date`` is the canonical name —
        this exists because the plan screen was written against ``.by`` while
        this module was being built, and a rename on either side is cheaper to
        do later than a wrong date is to notice.
        """
        return self.promised_date

    @property
    def days_left(self) -> int:
        """Negative once the promise date has gone by."""
        return (self.promised_date - self.as_of).days

    @property
    def has_passed(self) -> bool:
        return self.as_of > self.promised_date

    def why(self) -> str:
        """One line, in the owner's language. Never uses the word deadline."""
        return (f"{self.label}: we promise {self.duration} from {self.started_on}, "
                f"so this one is on us by {self.promised_date}. Our own promise, "
                f"set in configs/{POLICY_FILE} — not a filing date.")


SLAStatus = Literal["met", "missed", "open", "unmeasurable"]


@dataclass(frozen=True, slots=True)
class SLAOutcome:
    """Whether a promise was kept — or a refusal that names what is missing.

    ``unmeasurable`` is a first-class answer here, not an error state. An
    unanswered question is not an answer (principle 2), and a promise whose
    clock has no recorded start is not a promise that was kept.
    """

    kind: str
    label: str
    status: SLAStatus
    why: str
    promise: SLAPromise | None = None
    missing_fact: str = ""
    """The KEY of the fact that is not recorded. Named, so a caller can group
    every promise waiting on the same gap."""

    is_firm_policy: bool = True

    @property
    def is_measurable(self) -> bool:
        return self.status != "unmeasurable"

    @property
    def is_met(self) -> bool:
        return self.status == "met"

    @property
    def is_missed(self) -> bool:
        """A missed promise is an apology, never a penalty. Nothing here is law."""
        return self.status == "missed"


# --- reading the config -----------------------------------------------------


def load_slas(config_root: Path | None = None) -> dict[str, SLADef]:
    """Read the ``slas:`` section of ``configs/firm_policy.yaml``.

    A missing file, or a file with no ``slas:`` section, means the practice has
    promised nothing — which is a legitimate state and not an error. A *broken*
    entry is an error, and the message names the fix.
    """
    path = policy_file(config_root)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"Firm policy must be a mapping: {path}")

    section = data.get("slas") or {}
    if not isinstance(section, dict):
        raise ConfigError(
            f"The 'slas' section of {path} must be a mapping of key to promise.")

    out: dict[str, SLADef] = {}
    for key, spec in section.items():
        name = str(key)
        if not isinstance(spec, dict):
            raise ConfigError(f"SLA {name!r} must be a mapping: {spec!r}")

        # Principle 4, enforced rather than intended. A citation means somebody
        # thinks there is an authority behind this promise — and if there is,
        # it is not a promise. The statutory loader refuses an UNCITED rule;
        # this one refuses a CITED preference. Symmetry on purpose.
        for banned in ("citation", "source", "authority", "irc"):
            if banned in spec:
                raise ConfigError(
                    f"SLA {name!r} carries a {banned!r}. A service level is a "
                    f"promise this practice makes, and nothing in "
                    f"configs/{POLICY_FILE} has an authority behind it. If this "
                    f"date really is required by law it is an obligation — move "
                    f"it to configs/obligations/ with its source.")

        if "days" not in spec:
            raise ConfigError(f"SLA {name!r} has no 'days'.")
        try:
            days = int(spec["days"])
        except (TypeError, ValueError):
            raise ConfigError(
                f"SLA {name!r} has a non-numeric 'days': {spec['days']!r}") from None
        if days < 1:
            raise ConfigError(
                f"SLA {name!r} promises {days} days, which is not a turnaround. "
                f"Set it to at least 1 in configs/{POLICY_FILE}.")

        if "business_days" not in spec:
            # Never invent a value. "Two days" is two different promises and
            # the owner is the only one who knows which they meant.
            raise ConfigError(
                f"SLA {name!r} does not say whether it counts business days. Add "
                f"'business_days: true' or 'business_days: false' in "
                f"configs/{POLICY_FILE} — two business days and two calendar "
                f"days are different promises and SATC will not pick one.")

        for side in ("starts_when", "ends_when"):
            if not spec.get(side):
                raise ConfigError(
                    f"SLA {name!r} has no {side!r}. A promise with only one end "
                    f"of its clock can never be measured. Pick one of: "
                    f"{', '.join(sorted(FACTS))}.")

        out[name] = SLADef(
            key=name,
            label=" ".join(str(spec.get("label", name)).split()),
            days=days,
            business_days=bool(spec["business_days"]),
            starts_when=_fact(str(spec["starts_when"]), sla_key=name,
                              side="starts when"),
            ends_when=_fact(str(spec["ends_when"]), sla_key=name,
                            side="ends when"),
            note=" ".join(str(spec.get("note", "")).split()))
    return out


# The owner edits these by hand and expects the edit to take. Same reasoning as
# the price catalogue: a cache for the life of the process means an edit appears
# to do nothing until somebody restarts the app, and the failure is silent. So
# the cache is keyed on what the FILE looks like.
_cache: dict[str, tuple[object, object]] = {}


def _stamp(path: Path) -> tuple:
    try:
        st = path.stat()
    except OSError:
        return ()
    return (st.st_mtime_ns, st.st_size)


def forget_slas() -> None:
    """Drop the cache. For tests, and for anything editing config in-process."""
    _cache.clear()


def slas() -> dict[str, SLADef]:
    """Every promise on file, re-read when the file changes."""
    path = policy_file()
    stamp = _stamp(path)
    hit = _cache.get("slas")
    if hit is not None and hit[0] == stamp:
        return hit[1]  # type: ignore[return-value]
    value = load_slas()
    _cache["slas"] = (stamp, value)
    return value


def sla(kind: str) -> SLADef:
    """One promise by key. Refuses an unknown one and names what exists."""
    known = slas()
    found = known.get(kind)
    if found is not None:
        return found
    if not known:
        raise ConfigError(
            f"No service levels are on file, so SATC cannot answer for {kind!r}. "
            f"Add an 'slas:' section to configs/{POLICY_FILE}.")
    raise ConfigError(
        f"No service level called {kind!r}. The practice promises: "
        f"{', '.join(sorted(known))}. Add it to configs/{POLICY_FILE} if it is "
        f"a promise this firm makes.")


# --- answering --------------------------------------------------------------


def promised_by(kind: str, *, started_on: date | None,
                today: date) -> SLAPromise | None:
    """When this promise lands, given the day its clock started.

    Returns ``None`` when ``started_on`` is ``None`` — there is no promise to
    show, because a promise counted from a date nobody recorded would be
    invented. **A ``None`` here is not "kept" and not "fine".** Anything showing
    this to a human should call :func:`compliance`, which never returns a bare
    nothing: it returns the refusal, with the missing fact named.
    """
    spec = sla(kind)
    if started_on is None:
        return None
    return SLAPromise(
        kind=spec.key, label=spec.label, started_on=started_on,
        promised_date=spec.landing(started_on), duration=spec.duration(),
        as_of=today)


def compliance(kind: str, *, started_on: date | None = None,
               closed_on: date | None = None, today: date) -> SLAOutcome:
    """Did we keep this promise? Or, honestly, can we even tell?

    The order of the gates is the whole design:

    1. A clock end **nothing in SATC records** — refuse, and name it. This is
       the answer for most of the practice's promises today, and no amount of
       data changes it: the fact does not exist to be recorded.
    2. A recordable start that **is not recorded on this item** — refuse, and
       say where it would go. Different refusal, different fix.
    3. Both ends recorded: met if we closed it by the promised date, missed if
       we closed it after. And a promise whose date has gone by with nothing
       recorded against it is MISSED — reachable only when the closing fact is
       recordable, so it is a statement about this item and not about the
       codebase's gaps.
    """
    spec = sla(kind)

    gap = spec.missing_fact
    if gap is not None:
        return SLAOutcome(
            kind=spec.key, label=spec.label, status="unmeasurable",
            why=spec.why_unmeasurable(), missing_fact=gap.key)

    if started_on is None:
        start = spec.starts_when
        return SLAOutcome(
            kind=spec.key, label=spec.label, status="unmeasurable",
            why=(f"SATC cannot tell you whether this was met: nothing on this "
                 f"one records {start.describes}. It would be "
                 f"{start.recorded_as} — record it there and the promise can be "
                 f"measured."),
            missing_fact=start.key)

    if closed_on is not None and closed_on < started_on:
        # Two dates that cannot both be right. Reporting "met" here would be a
        # confident wrong answer built on a typo, and it would be the flattering
        # one — a clock that stopped before it started always looks fast.
        return SLAOutcome(
            kind=spec.key, label=spec.label, status="unmeasurable",
            why=(f"SATC cannot tell you whether this was met: "
                 f"{spec.ends_when.describes} is recorded as {closed_on}, "
                 f"before {spec.starts_when.describes} on {started_on}. One of "
                 f"those two dates is wrong — fix the record."))

    promise = SLAPromise(
        kind=spec.key, label=spec.label, started_on=started_on,
        promised_date=spec.landing(started_on), duration=spec.duration(),
        as_of=today)

    if closed_on is None:
        if promise.has_passed:
            return SLAOutcome(
                kind=spec.key, label=spec.label, status="missed", promise=promise,
                why=(f"{spec.label}: we promised {spec.duration()} from "
                     f"{started_on}, which was up on {promise.promised_date}, and "
                     f"nothing records {spec.ends_when.describes}. That is an "
                     f"apology to make, not a penalty to pay."))
        return SLAOutcome(
            kind=spec.key, label=spec.label, status="open", promise=promise,
            why=(f"{spec.label}: still within our own promise — "
                 f"{spec.duration()} from {started_on} runs to "
                 f"{promise.promised_date}."))

    if closed_on <= promise.promised_date:
        return SLAOutcome(
            kind=spec.key, label=spec.label, status="met", promise=promise,
            why=(f"{spec.label}: promised {spec.duration()} from {started_on} "
                 f"(by {promise.promised_date}); it was {closed_on} "
                 f"{spec.ends_when.describes}."))
    late = (closed_on - promise.promised_date).days
    return SLAOutcome(
        kind=spec.key, label=spec.label, status="missed", promise=promise,
        why=(f"{spec.label}: promised {spec.duration()} from {started_on} "
             f"(by {promise.promised_date}); it was {closed_on} "
             f"{spec.ends_when.describes}, {late} day{'s' if late != 1 else ''} "
             f"later. That is an apology to make, not a penalty to pay."))


def unmeasurable_promises() -> tuple[SLAOutcome, ...]:
    """Every promise on file that no amount of data could answer today.

    The list the owner should see once, not a row per client per week — a queue
    that repeats the same structural gap is the queue people learn to scroll
    past (principle 13). One line per missing fact is the honest shape.
    """
    return tuple(
        SLAOutcome(kind=d.key, label=d.label, status="unmeasurable",
                   why=d.why_unmeasurable(),
                   missing_fact=(d.missing_fact.key if d.missing_fact else ""))
        for d in slas().values() if not d.is_measurable)
