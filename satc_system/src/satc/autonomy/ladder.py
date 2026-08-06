"""THE LADDER — charter §4: draft_only, ``N`` clean approvals in a row, earned.

    draft_only  ──[ N consecutive approvals, zero edits ]──▶  earned
                ◀────────────[ any correction ]──────────────

PRINCIPLE 3 IS THE WHOLE DESIGN. A streak is not a column anywhere — it is
walked fresh, in time order, from :mod:`satc.autonomy.approval`'s recorded
facts, every time somebody asks. A stored counter is a status that lies the
moment an approval is corrected, deleted, or simply arrives out of order, and
this codebase has already been burned by exactly that shape of bug twice: job
stage, and invoice ``paid_on`` (see ``satc/billing/payment.py``'s header). The
fix both times was the same one applied here first: compute it, don't cache
it.

WHAT "CONSECUTIVE" MEANS: consecutive *for that pair*, in time order, with no
correction of that pair between them. A gap in time is not a break — a client
emailed twice a year takes three years to reach rung 5, and that is the
correct amount of evidence, not a bug to route around (charter §4).

WHAT A CORRECTION DOES: resets the corrected pair to zero (charter §5). A
``wrong_fact`` correction additionally resets *every other pair already on
record for that template* — a merge field that lied for one client is a
defect in the template or the data behind it, not that client's problem alone.
The other four reason codes touch only the pair that was corrected. This is
computed by the same single chronological walk as the streak itself: the
reset has to land at the point in time the correction happened, not be
applied retroactively to whatever the state looks like now, or a wrong_fact
correction from March would wrongly erase approvals genuinely earned in June.

WHAT GATES ALL OF IT: :mod:`satc.autonomy.preconditions`. Before that gate
holds, every pair answers at rung zero, no matter what the approval record
says — see :func:`_build_rung` and the module docstring over there for the
missing/lapsed distinction.

N IS FIRM POLICY, not a constant in this file. See :func:`load_autonomy_policy`
and the ``autonomy:`` section of ``configs/firm_policy.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal, Sequence

from satc.autonomy.approval import REASON_CODES, Approval, all_approvals
from satc.autonomy.preconditions import PreconditionGate, PreconditionRecord, gate_status
from satc.config import CONFIG_ROOT, ConfigError, read_yaml

Pair = tuple[str, str]
RungState = Literal["draft_only", "earned"]
Classification = Literal["routine", "money_or_deadline"]

_DEFAULT_ROUTINE_N = 5
_DEFAULT_MONEY_OR_DEADLINE_N = 10
_DEFAULT_CADENCE_DAYS = 90


# --- N is firm policy, not code ----------------------------------------------

@dataclass(frozen=True, slots=True)
class AutonomyPolicy:
    """The owner's own thresholds, cadence, and template classification.

    No citation, same as everything else ``load_policy`` in
    ``satc/obligations/policy.py`` reads — these are choices the owner can
    revisit over coffee, not rules with an authority behind them. Loaded
    separately from that module on purpose (principle 4: the statutory loader
    and the firm-policy loader must never be the same function), even though
    both read files named ``firm_policy.yaml``.
    """

    routine_n: int = _DEFAULT_ROUTINE_N
    money_or_deadline_n: int = _DEFAULT_MONEY_OR_DEADLINE_N
    precondition_cadence_days: int = _DEFAULT_CADENCE_DAYS
    routine_templates: frozenset[str] = field(default_factory=frozenset)
    money_or_deadline_templates: frozenset[str] = field(default_factory=frozenset)
    """Kept only for the overlap check in :func:`load_autonomy_policy` and to
    let a screen say "explicitly classified" vs "defaulted". Classification
    itself never consults this set — see :meth:`classification_for`."""

    def classification_for(self, template_key: str) -> Classification:
        """routine or money_or_deadline — charter §4's stricter default wins.

        A template not in the routine list reads as ``money_or_deadline``
        whether or not anyone bothered to also list it there explicitly.
        "Unclassified" is not a third state with its own threshold; it is
        just an unclassified template landing on the strict one, because
        nobody having thought about a template is not evidence it is safe
        (principle 5).
        """
        return "routine" if template_key in self.routine_templates else "money_or_deadline"

    def threshold_for(self, template_key: str) -> int:
        return (self.routine_n if self.classification_for(template_key) == "routine"
                else self.money_or_deadline_n)


def load_autonomy_policy(config_root: Path | None = None) -> AutonomyPolicy:
    """Read the ``autonomy:`` section of ``configs/firm_policy.yaml``.

    THE FIRM-POLICY LOADER, NEVER THE STATUTORY ONE (principle 4) — ``N`` is a
    preference the owner sets, not a computed rule. A missing file, or a file
    with no ``autonomy:`` block, means "no preferences recorded yet" and reads
    as the built-in defaults (5 / 10 / 90, all money_or_deadline until told
    otherwise) rather than as an error — refusing outright here would make the
    whole ladder unusable the moment somebody deletes a comment, which is a
    worse failure than falling back to the strictest sensible defaults.

    ``config_root`` exists so a test (or a future admin screen previewing a
    change) can point this at a temp directory and get a different answer with
    no code change — the same seam every other loader in this codebase uses.
    """
    path = (config_root or CONFIG_ROOT) / "firm_policy.yaml"
    if not path.exists():
        return AutonomyPolicy()

    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(f"Firm policy must be a mapping: {path}")
    section = data.get("autonomy") or {}
    if not isinstance(section, dict):
        raise ConfigError(f"The autonomy: section of {path} must be a mapping.")

    thresholds = section.get("thresholds") or {}
    routine_n = int(thresholds.get("routine", _DEFAULT_ROUTINE_N))
    money_n = int(thresholds.get("money_or_deadline", _DEFAULT_MONEY_OR_DEADLINE_N))
    cadence = int(section.get("precondition_reconfirm_days", _DEFAULT_CADENCE_DAYS))

    templates = section.get("templates") or {}
    routine_t = frozenset(str(t) for t in (templates.get("routine") or []))
    money_t = frozenset(str(t) for t in (templates.get("money_or_deadline") or []))
    overlap = routine_t & money_t
    if overlap:
        # Refuse rather than default (principle 5): silently picking a side
        # for a template listed under both would hide a config typo behind a
        # plausible-looking rung the next time somebody reads the screen.
        raise ConfigError(
            f"{sorted(overlap)} listed under BOTH routine and money_or_deadline "
            f"in {path} — a template can only be one. Remove it from one list.")

    return AutonomyPolicy(routine_n=routine_n, money_or_deadline_n=money_n,
                          precondition_cadence_days=cadence,
                          routine_templates=routine_t, money_or_deadline_templates=money_t)


# --- the streak, walked once from the recorded facts -------------------------

@dataclass(frozen=True, slots=True)
class _PairState:
    """Where one pair's streak stands after the walk reaches its last event."""

    streak: int = 0
    why: str = "no approvals recorded yet for this pair"


def _reset(ev: Approval) -> _PairState:
    label = REASON_CODES.get(ev.reason, ev.reason or "an unrecorded reason")
    return _PairState(streak=0, why=f"last correction was {label}, {ev.decided_on:%b %d, %Y}")


def _compute(approvals: Sequence[Approval],
             frozen_since: date | None = None) -> dict[Pair, _PairState]:
    """Walk every recorded decision in time order once, deriving every pair's
    current streak together. Has to be ONE walk, not one per pair: a
    ``wrong_fact`` correction on client A's copy of a template reaches into
    client B's streak for the same template, and only a single pass across the
    whole record in true time order lands that reset at the moment it actually
    happened (see the module docstring).
    """
    state: dict[Pair, _PairState] = {}
    for ev in all_approvals(approvals):
        # A cutoff is used ONLY to answer "what had this pair earned before the
        # freeze". It is never used for the streak the owner is shown — see
        # _build_rung for why the two answers differ.
        if frozen_since is not None and ev.decided_on >= frozen_since:
            continue
        pair = ev.pair
        if ev.is_correction:
            state[pair] = _reset(ev)
            if ev.reason == "wrong_fact":
                # Every OTHER pair already on record for this template — never
                # a pair we haven't seen yet, which is already sitting at zero
                # with nothing to reset.
                sibling_why = (f"reset by a wrong-fact correction on "
                               f"{ev.client_id}'s {ev.template_key} draft, "
                               f"{ev.decided_on:%b %d, %Y}")
                for other in list(state):
                    if other[0] == ev.template_key and other != pair:
                        state[other] = _PairState(streak=0, why=sibling_why)
        else:
            prior = state.get(pair, _PairState())
            state[pair] = _PairState(
                streak=prior.streak + 1,
                why=f"last approved unchanged {ev.decided_on:%b %d, %Y}")
    return state


# --- the rung ------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Rung:
    """Where one (template, client) pair stands, and why — for a screen or an
    audit, never re-derived from anything this object itself stores."""

    pair: Pair
    state: RungState
    streak: int
    needed: int
    why: str
    """One line, in the owner's language, naming the evidence (principle 13):
    "3 of 5 — last approved unchanged Jun 02, 2026" beats a bare number."""
    blocked_reason: str = ""
    """Non-empty only when the PRECONDITION GATE, not the streak, is why this
    pair cannot be ``earned`` right now. Separate from ``why`` so a screen can
    render a lock icon without parsing prose."""


def _build_rung(pair: Pair, info: _PairState, *, policy: AutonomyPolicy,
                earned_before: bool = False,
                gate: PreconditionGate) -> Rung:
    template_key, _client_id = pair
    needed = policy.threshold_for(template_key)

    if gate.missing:
        # Charter §3: never confirmed at all means nothing has ever been
        # allowed to count, so this pair reads exactly as if no history
        # existed — not merely "can't advance", the position itself is zero.
        return Rung(pair=pair, state="draft_only", streak=0, needed=needed,
                   why=f"Held at rung zero — {gate.why}", blocked_reason=gate.why)

    if gate.lapsed:
        # CHARTER SECTION 3 MAKES TWO PROMISES AND THEY PULL DIFFERENT WAYS:
        # a lapse "freezes accrual" AND "demotes nothing". Implementing either
        # alone is wrong, and both wrong answers were written before this
        # comment existed.
        #
        # Reading it as "stop counting" discards evidence the practice actually
        # produced — five clean approvals during a lapsed backup confirmation
        # really did happen (principle 2), and wiping them is a demotion in
        # substance however it is labelled. That is the resentment the charter
        # names.
        #
        # Reading it as "cannot be earned" knocks an ALREADY EARNED pair back to
        # draft_only the day a confirmation goes stale, which is a demotion in
        # plain sight.
        #
        # So: the streak the owner sees is the real one, still climbing. What
        # freezes is the PERMISSION — it cannot cross while the gate is stale.
        # And a pair that had already crossed BEFORE the freeze stays across,
        # which is what earned_before measures.
        state = "earned" if earned_before else "draft_only"
        held = ("earned before the freeze" if state == "earned"
                else f"{info.streak} of {needed}, frozen below earned")
        return Rung(pair=pair, state=state, streak=info.streak, needed=needed,
                   why=f"{held} — {gate.why}", blocked_reason=gate.why)

    if info.streak >= needed:
        return Rung(pair=pair, state="earned", streak=info.streak, needed=needed,
                   why=f"{info.streak} of {needed} — earned")

    return Rung(pair=pair, state="draft_only", streak=info.streak, needed=needed,
               why=f"{info.streak} of {needed} — {info.why}")


def rung_for(pair: Pair, approvals: Sequence[Approval], *, policy: AutonomyPolicy,
            preconditions: Sequence[PreconditionRecord], today: date | None = None) -> Rung:
    """Where ONE pair stands. Walks the WHOLE approval record, not just this
    pair's rows — a wrong_fact correction elsewhere on the same template can
    be the reason this pair is at zero, and the only way to know that is to
    walk everything in time order (see :func:`_compute`).

    ``today`` is the same optional testing seam as
    :func:`~satc.autonomy.preconditions.gate_status` — a screen leaves it
    unset and gets the real date; a test pins it so a cadence check does not
    depend on when the suite happens to run.
    """
    gate = gate_status(preconditions, cadence_days=policy.precondition_cadence_days, today=today)
    info = _compute(approvals).get(pair, _PairState())
    # A SECOND walk, cut off at the freeze, answering only "had this already
    # crossed before the gate went stale". Never the streak that is displayed.
    before = _compute(approvals, gate.frozen_since).get(pair, _PairState())
    earned = before.streak >= policy.threshold_for(pair[0])
    return _build_rung(pair, info, policy=policy, gate=gate, earned_before=earned)


def streaks(approvals: Sequence[Approval], *, policy: AutonomyPolicy,
           preconditions: Sequence[PreconditionRecord], today: date | None = None) -> list[Rung]:
    """Every pair the approval record has ever seen, each at its current rung.

    Ordered by (template_key, client_id) so the screen is stable run to run
    rather than shuffling with whatever order the store happened to load rows
    in — a queue that reorders itself for no reason is noise (principle 13).
    """
    gate = gate_status(preconditions, cadence_days=policy.precondition_cadence_days, today=today)
    computed = _compute(approvals)
    before = _compute(approvals, gate.frozen_since) if gate.frozen_since else computed
    return [_build_rung(pair, computed[pair], policy=policy, gate=gate,
                        earned_before=(before.get(pair, _PairState()).streak
                                       >= policy.threshold_for(pair[0])))
            for pair in sorted(computed)]
