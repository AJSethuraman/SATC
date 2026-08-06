"""THE DIGEST AND THE SCOREBOARD — docs/AUTONOMY-CHARTER.md section 8.

    digest_for(day, ...) -> Digest        one day
    week_for(ending, ...) -> Scoreboard   the same numbers over seven days

READ FROM ENGINE STATE, NEVER FROM MODEL PROSE (``LOCAL-LLM-PATTERN`` rule
10). Both functions here are pure: every number is COUNTED from the recorded
facts the caller hands in, nothing is generated, and nothing is inferred. That
is what makes a digest a record rather than a claim — call ``digest_for`` for
the same day with the same facts twice and the two answers compare equal.

WHAT THIS MODULE COMPOSES, NOT REINVENTS. The pieces already exist, each built
and tested on its own seam, and this module's whole job is to put them
together into one day's picture and one week's:

* :mod:`satc.autonomy.approval` — the recorded decision ledger (charter §11).
  ``Approval.outcome`` is a hash comparison, never trusted from a caller.
* :mod:`satc.autonomy.ladder` — ``streaks()`` walks that ledger once and
  returns every pair's current :class:`~satc.autonomy.ladder.Rung`, already
  gated by preconditions and already carrying its own "why" sentence.
* :mod:`satc.autonomy.preconditions` — :func:`~satc.autonomy.preconditions.gate_status`,
  the missing/lapsed hard gate (charter §3).
* :mod:`satc.autonomy.traps` — :func:`~satc.autonomy.traps.run_drill`'s
  :class:`~satc.autonomy.traps.DrillResult`, one per night the drill ran
  (charter §7). "Fail toward the click" is already built into ``run_drill``
  itself — a trap that could not run is already recorded as a miss, so this
  module only has to ask "did today's drill miss anything", never re-derive
  what counts as a miss.

WHAT THIS MODULE DOES NOT HAVE A RECORDED HISTORY FOR, said out loud rather
than papered over. Two of the charter's five digest ingredients — "actions
proposed" and the nightly drill — are not, today, durable per-day facts
anywhere in this codebase:

* The trap drill (:func:`~satc.autonomy.traps.run_drill`) is pure and cheap,
  but nothing persists last night's result — there is no scheduler and no
  store table for it yet. So a drill result for TODAY can legitimately be
  produced by running the drill live; a drill result for a PAST day, if
  nobody captured it that night, does not exist and this module will not
  fabricate one by re-running today's code against a pretend date and
  presenting that as history.
* "Actions proposed" — how many client-facing drafts SATC had on offer — has
  no dated ledger either. :class:`Proposed` is the shape such a fact WOULD
  take (mirroring how this module already anticipated the other three seams
  before they existed), and the caller may supply it for today from a live
  read of the queue; for any other day the honest answer is none recorded.

Both gaps are named exactly where a screen renders them empty, rather than
silently reading as "nothing happened" — principle 1.

NEVER TOTAL THE FIVE REASON CODES INTO ONE FIGURE. Charter §6 is explicit:
``should_not_have_flagged`` at 30% and ``wrong_fact`` at 30% are different
practices in different trouble, and a combined "accuracy" percentage hides
which one you are looking at. :class:`ReasonTally` carries the five counts and
nothing that could be divided into a ratio — no ``total()`` weighed against
approvals, no ``rate()``, on purpose. See ``tests/test_digest.py`` for the
test that a figure like that can never appear here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence

from satc.autonomy.approval import REASON_CODES, Approval
from satc.autonomy.ladder import AutonomyPolicy, Pair, Rung, load_autonomy_policy, streaks
from satc.autonomy.preconditions import PreconditionGate, PreconditionRecord, gate_status
from satc.autonomy.traps import DrillResult

__all__ = [
    "Digest",
    "Proposed",
    "ReasonTally",
    "Scoreboard",
    "digest_for",
    "week_for",
]


@dataclass(frozen=True, slots=True)
class Proposed:
    """One client-facing draft SATC had on offer, on a given day.

    Not a persisted fact — see the module docstring's second gap. This exists
    so :func:`digest_for` can count "actions proposed" the same way it counts
    everything else here: a sequence of dated things, filtered by day. The
    only real producer of one today is a live read of
    :func:`satc.actions.build_queue`, filtered to rows carrying a
    ``template_key`` (a message, not a bare reminder), stamped with the date
    it was read on. Nothing else in this codebase records this historically,
    so a caller building a digest for a day other than today should pass an
    empty sequence rather than inventing a count for one (principle 1).
    """

    day: date
    template_key: str
    client_id: str

    @property
    def pair(self) -> Pair:
        return (self.template_key, self.client_id)


@dataclass(frozen=True, slots=True)
class ReasonTally:
    """Corrections counted PER REASON CODE — never summed into one figure.

    ``counts`` always carries all five keys from
    :data:`~satc.autonomy.approval.REASON_CODES`, zero where nothing
    happened, so a screen can print every row even on a day with no
    corrections at all rather than a table that silently shrinks.

    DELIBERATELY NO ``total()`` AND NO ``rate()``/``accuracy()``. Charter §6:
    the five codes are not interchangeable, and a screen — or a future
    refactor reaching for "just one summary number" — must not be able to
    collapse them by calling a method this class does not offer.
    """

    counts: dict[str, int] = field(default_factory=lambda: {code: 0 for code in REASON_CODES})

    def for_code(self, code: str) -> int:
        return self.counts.get(code, 0)


def _reason_tally(approvals: Sequence[Approval]) -> ReasonTally:
    counts = {code: 0 for code in REASON_CODES}
    for a in approvals:
        if a.is_correction:
            counts[a.reason] = counts.get(a.reason, 0) + 1
    return ReasonTally(counts=counts)


@dataclass(frozen=True, slots=True)
class Digest:
    """One day, entirely from recorded facts. See the module docstring."""

    day: date
    proposed: int
    """Client-facing drafts on offer this day. See :class:`Proposed` — real
    only for today; 0 (with the reason said on screen) for any other day."""

    approved_clean: int
    """Decisions this day whose sent text was byte-identical to what SATC
    rendered — :attr:`~satc.autonomy.approval.Approval.outcome` == "approval"."""

    corrections: ReasonTally
    """Corrections this day, broken out by reason code. Never a single count."""

    rungs: tuple[Rung, ...]
    """Every pair the approval ledger has ever seen, at its rung AS OF this
    day — :func:`~satc.autonomy.ladder.streaks` walked over only the approvals
    recorded on or before ``day``, so a digest for a past day does not see
    corrections or approvals that had not happened yet."""

    drill: DrillResult | None
    """Tonight's trap drill, if one is on record for this day — ``None`` when
    none is (see the module docstring's first gap; not the same thing as a
    drill that ran and passed everything)."""

    gave_up: int
    """Corrections this day reasoned ``gave_up`` — charter §6's give-up tail,
    called out on its own because it is EXPECTED (~1 in 6-9,
    ``LOCAL-LLM-PATTERN`` rule 9) and must read as harmless, not as a miss."""

    gate: PreconditionGate
    """The precondition gate as of THIS day (``gate_status(..., today=day)``),
    independent of :attr:`rungs`'s own (real-clock) gate check — see
    ``tests/test_digest.py`` and the report on this slice for why the two can
    differ for a past day, and why that is a known limit of
    :func:`~satc.autonomy.ladder.streaks` rather than something fixed here."""

    @property
    def any_trap_missed(self) -> bool:
        return self.drill is not None and bool(self.drill.misses)

    @property
    def drill_ran(self) -> bool:
        return self.drill is not None


@dataclass(frozen=True, slots=True)
class Scoreboard:
    """The same numbers as :class:`Digest`, over the seven days ending
    ``ending`` (inclusive) — charter §8's "one page, the same numbers over
    seven days, plus what moved."
    """

    ending: date
    days: tuple[Digest, ...]
    """The seven daily digests, oldest first."""

    proposed_total: int
    approved_clean_total: int
    corrections_total: ReasonTally
    """Summed across the week, still broken out by reason code — summing a
    week of ``wrong_fact`` counts is not the same mistake as summing
    ``wrong_fact`` against ``approved_clean``; the five stay five."""

    drill_misses_total: int
    gave_up_total: int
    moved: tuple[str, ...]
    """Every pair whose rung differs between the window's first and last day,
    as one readable line each — "what moved" (charter §8). Empty when nothing
    did, which is a fact worth a screen saying plainly rather than showing
    nothing at all."""


def digest_for(day: date, *, approvals: Sequence[Approval],
               drill_results: Sequence[DrillResult] = (),
               actions: Sequence[Proposed] = (),
               preconditions: Sequence[PreconditionRecord] = (),
               policy: AutonomyPolicy | None = None) -> Digest:
    """One day, computed fresh from the facts handed in.

    ``approvals``/``preconditions`` are the WHOLE ledgers, not pre-filtered to
    ``day`` — a streak position on August 6th depends on every approval up to
    and including that day, not just that day's own rows, so trimming before
    the call would silently answer the wrong question. This filters
    internally, the same shape as ``satc.billing.payment`` reading the whole
    ledger and computing per-invoice figures from it.

    REGENERABLE: nothing here reads the real clock except through ``day``
    and, transitively, :func:`~satc.autonomy.ladder.streaks`'s own precondition
    gate check (see :attr:`Digest.gate`'s docstring for that one caveat).
    Calling this twice with the same arguments returns equal ``Digest``
    objects — ``tests/test_digest.py`` asserts exactly that.
    """
    policy = policy or load_autonomy_policy()
    history = [a for a in approvals if a.decided_on <= day]
    todays_decisions = [a for a in history if a.decided_on == day]
    approved_clean = sum(1 for a in todays_decisions if not a.is_correction)
    corrections = _reason_tally(todays_decisions)

    # today=day, or a PAST day's digest computes its rung table against the
    # WALL CLOCK and the same object then contradicts itself: the gate below is
    # asked as of `day`, the rungs were asked as of now. Regenerating last
    # week's digest tomorrow gave a different answer, which makes it a claim
    # rather than a record (charter section 8).
    rungs = tuple(streaks(history, policy=policy, preconditions=preconditions,
                          today=day))
    gate = gate_status(preconditions, cadence_days=policy.precondition_cadence_days, today=day)

    matching_drills = [d for d in drill_results if d.today == day]
    # More than one on file for the same day should not happen — the drill is
    # a nightly job — but if it ever does, the last one supplied is treated as
    # the record, the same "latest wins" rule the rest of this codebase uses
    # for a re-confirmed fact rather than raising over something a screen can
    # show plainly instead.
    drill = matching_drills[-1] if matching_drills else None

    proposed = sum(1 for p in actions if p.day == day)

    return Digest(day=day, proposed=proposed, approved_clean=approved_clean,
                 corrections=corrections, rungs=rungs, drill=drill,
                 gave_up=corrections.for_code("gave_up"), gate=gate)


def week_for(ending: date, *, approvals: Sequence[Approval],
            drill_results: Sequence[DrillResult] = (),
            actions: Sequence[Proposed] = (),
            preconditions: Sequence[PreconditionRecord] = (),
            policy: AutonomyPolicy | None = None) -> Scoreboard:
    """The seven days ending ``ending`` (inclusive), plus what moved.

    Built entirely from seven calls to :func:`digest_for` — the daily and the
    weekly view are never two independent derivations of the same numbers,
    which is exactly the trap that let two screens disagree in this codebase
    before (``satc/billing/payment.py``'s header names the shape of that bug).
    """
    policy = policy or load_autonomy_policy()
    days = tuple(
        digest_for(ending - timedelta(days=6 - i), approvals=approvals,
                  drill_results=drill_results, actions=actions,
                  preconditions=preconditions, policy=policy)
        for i in range(7))

    week_counts = {code: 0 for code in REASON_CODES}
    for d in days:
        for code in REASON_CODES:
            week_counts[code] += d.corrections.for_code(code)

    first_rung = {r.pair: r.state for r in days[0].rungs}
    last_rung = {r.pair: r.state for r in days[-1].rungs}
    # Plain ASCII on purpose (not an arrow glyph) — this string reaches a
    # screen and, on a failing assertion, a terminal; Windows consoles on the
    # default codepage cannot encode most arrow characters, and a report that
    # cannot print is worse than one that spells the word out.
    moved = tuple(sorted(
        f"{pair[0]} / {pair[1]}: {first_rung.get(pair, 'no history yet')} -> {state}"
        for pair, state in last_rung.items() if first_rung.get(pair) != state))

    return Scoreboard(
        ending=ending, days=days,
        proposed_total=sum(d.proposed for d in days),
        approved_clean_total=sum(d.approved_clean for d in days),
        corrections_total=ReasonTally(counts=week_counts),
        drill_misses_total=sum(len(d.drill.misses) for d in days if d.drill is not None),
        gave_up_total=sum(d.gave_up for d in days),
        moved=moved)
