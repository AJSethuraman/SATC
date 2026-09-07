"""WHAT CAN I PICK UP RIGHT NOW, AND WHICH ONE FIRST.

A tax practice in March is not a to-do list, it is a queue with constraints.
Almost every open file is blocked on somebody else — a missing 1099, a review, a
signature — so the scarce resource is not hours, it is UNBLOCKED WORK. "What
needs doing" has a useless answer (everything). "What can I sit down and do, and
which one first" has a useful one.

This module computes that, and computes it in two halves that are equally
important:

* :func:`workable` — the jobs somebody could start this minute, ordered, each
  carrying the reason it sits where it does.
* :func:`not_workable` — the counterpart, and the reason it is not an
  afterthought. *"You have nothing to pick up because fourteen files are waiting
  on clients"* is a completely different answer from an empty list, and it is
  the one that tells the owner to spend the morning chasing rather than
  preparing.

WHAT ORDERS IT IS FIRM POLICY. Whether a stale file outranks a near deadline is
a judgement about how this practice likes to work; no statute has an opinion. So
the weights live in ``configs/firm_policy.yaml`` next to the document cutoffs,
load through :func:`load_queue_policy` (which requires no citation, because
nothing here has an authority behind it), and everything derived from them is
flagged ``ordering_is_firm_policy`` so the screen can render a rank as a
suggestion. The one input that is NOT settable there is the deadline itself:
how close a deadline is comes from the cited rules in ``configs/obligations/``,
via an already-materialised :class:`ObligationInstance`. A date typed into the
policy file would be a preference wearing the clothes of law.

IT PROPOSES, IT NEVER DISPOSES. This ranks and explains. It assigns nothing,
starts nothing, reserves nothing, and writes nothing — not even the stale
``Job.stage`` cache it deliberately ignores. Ordering IS proposing; the moment a
queue picks the work it has taken the decision away from the person who has to
sign the return.

AND IT NEVER INVENTS A DEADLINE. A job with no obligation on file has no
computable due date, so it says so out loud and is ranked on what IS known. The
hand-typed ``Job.due_date`` is deliberately not used for this: it is a date
somebody keyed into a form, and scoring it as though it were statutory would
quietly erase the distinction the whole system is built to keep.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml

from satc.config import CONFIG_ROOT, ConfigError, read_yaml
from satc.models.readiness import Readiness, assess
from satc.models.work import Job
from satc.work.stage import StageView, derive_stage

POLICY_FILE = "firm_policy.yaml"
POLICY_SECTION = "queue"

# The factors, in a FIXED order. Iterating a dict of weights would make the
# output depend on YAML key order, and "deterministic and stable" has to mean
# stable against the config being reformatted too.
FACTOR_KEYS: tuple[str, ...] = ("deadline", "idle", "unblocks", "quick_win")

# Owner-facing names live here, in the engine, keyed by the factor. The config
# carries numbers only — a label typed into firm policy is a sentence nobody
# reviewed reaching a screen that looks authoritative.
FACTOR_LABELS: dict[str, str] = {
    "deadline": "Deadline pressure",
    "idle": "Sitting untouched",
    "unblocks": "Frees up other work",
    "quick_win": "Nearly finished",
}

# What SATC does when the practice has recorded no preference at all. These are
# NOT the owner's choice and :attr:`QueuePolicy.configured` says so — a default
# nobody picked must never be readable as a decision somebody made.
DEFAULT_WEIGHTS: dict[str, float] = {
    "deadline": 1.0, "idle": 0.4, "unblocks": 0.3, "quick_win": 0.2,
}
DEFAULT_HORIZON_DAYS = 45
DEFAULT_STALE_AFTER_DAYS = 14

# How much harder an overdue deadline pulls than one due today, at most. Not a
# preference and so not in the config: it is the shape of the curve, there to
# stop one ancient file from owning the top of the queue forever. Principle 13 —
# a row that can never be cleared is the row that teaches the owner to scroll.
_OVERDUE_CEILING = 2.0

# Short, in the owner's language. Keyed off the DERIVED stage, never the stored
# one.
_STAGE_PHRASE: dict[str, str] = {
    "prep_ready": "Ready to start",
    "in_prep": "In prep",
    "in_review": "In review",
    "ready_to_deliver": "Ready to go out",
}


# --------------------------------------------------------------------------
# The policy — preference, loaded as preference
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class QueuePolicy:
    """How the owner wants their week ordered. No citations, by design.

    Loaded by :func:`load_queue_policy` and NEVER by the statutory rule loader.
    That loader refuses a rule with no ``source``; this one asks for none,
    because there is no authority behind "chase the stale ones first".
    """

    weights: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    horizon_days: int = DEFAULT_HORIZON_DAYS
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS

    configured: bool = False
    """Whether the practice actually recorded an ordering preference.

    False means SATC's defaults are in use because the ``queue:`` section is
    absent — which is not the same fact as the owner having chosen these
    numbers. An unanswered question is not an answer (principle 2)."""

    defaulted_weights: tuple[str, ...] = ()
    """Factors the config did not mention, so are running on SATC's number.

    Same reason as :attr:`configured`, one factor at a time: an owner who
    deleted a line should be able to see that they did."""

    is_firm_policy: bool = True
    """Always true. Present so a caller cannot forget what it is holding."""

    def weight(self, key: str) -> float:
        return float(self.weights.get(key, 0.0))


def _number(raw, *, name: str, path: Path) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ConfigError(
            f"Queue ordering weight {name!r} must be a number, got {raw!r}. "
            f"Fix the {POLICY_SECTION}: weights block in {path}.")
    value = float(raw)
    if value < 0:
        # A negative weight would mean "prefer the job further from its
        # deadline", which nobody means. Refuse rather than silently invert.
        raise ConfigError(
            f"Queue ordering weight {name!r} is negative ({value}). A weight is "
            f"how hard a factor pulls, never which way — set it to 0 to switch "
            f"the factor off, in {path}.")
    return value


def _positive_int(raw, *, name: str, path: Path, fallback: int) -> int:
    if raw is None:
        return fallback
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ConfigError(
            f"Queue setting {name!r} must be a whole number of days, got {raw!r}. "
            f"Fix it in {path}.") from None
    if value <= 0:
        raise ConfigError(
            f"Queue setting {name!r} must be at least 1 day, got {value}. Fix it "
            f"in {path}.")
    return value


def load_queue_policy(config_root: Path | None = None) -> QueuePolicy:
    """Read the ``queue:`` section of ``configs/firm_policy.yaml``.

    Deliberately a separate function from the statutory loader, and deliberately
    reading the *policy* file. A missing file, or a file with no ``queue:``
    section, means "the practice has no recorded preference" — which is answered
    with SATC's defaults, flagged as defaults.
    """
    path = (config_root or CONFIG_ROOT) / POLICY_FILE
    if not path.exists():
        return QueuePolicy()

    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(f"Firm policy must be a mapping: {path}")

    section = data.get(POLICY_SECTION)
    if section is None:
        return QueuePolicy()
    if not isinstance(section, dict):
        raise ConfigError(
            f"The {POLICY_SECTION!r} section of {path} must be a mapping of "
            f"settings, got {type(section).__name__}.")

    raw_weights = section.get("weights") or {}
    if not isinstance(raw_weights, dict):
        raise ConfigError(
            f"{POLICY_SECTION}.weights in {path} must be a mapping of factor to "
            f"number. Known factors: {', '.join(FACTOR_KEYS)}.")

    unknown = sorted(str(k) for k in raw_weights if str(k) not in FACTOR_KEYS)
    if unknown:
        # A typo here would silently do nothing, and a weight the owner believes
        # they set is worse than one they know they have not.
        raise ConfigError(
            f"{POLICY_SECTION}.weights in {path} names factors SATC does not "
            f"compute: {', '.join(unknown)}. The factors are: "
            f"{', '.join(FACTOR_KEYS)}. Remove the line or correct the spelling.")

    weights: dict[str, float] = {}
    defaulted: list[str] = []
    for key in FACTOR_KEYS:
        if key in raw_weights:
            weights[key] = _number(raw_weights[key], name=key, path=path)
        else:
            weights[key] = DEFAULT_WEIGHTS[key]
            defaulted.append(key)

    if not any(weights.values()):
        raise ConfigError(
            f"Every queue ordering weight in {path} is 0, so the queue would have "
            f"nothing to order on and would fall back to job id. Give at least "
            f"one factor a weight, or delete the {POLICY_SECTION}: section to use "
            f"SATC's defaults.")

    return QueuePolicy(
        weights=weights,
        horizon_days=_positive_int(section.get("horizon_days"), name="horizon_days",
                                   path=path, fallback=DEFAULT_HORIZON_DAYS),
        stale_after_days=_positive_int(section.get("stale_after_days"),
                                       name="stale_after_days", path=path,
                                       fallback=DEFAULT_STALE_AFTER_DAYS),
        configured=True,
        defaulted_weights=tuple(defaulted))


@lru_cache(maxsize=1)
def _cached_policy() -> QueuePolicy:
    return load_queue_policy()


def queue_policy() -> QueuePolicy:
    """The installed ordering preference (cached — config doesn't change while running)."""
    return _cached_policy()


# --------------------------------------------------------------------------
# What comes out
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Factor:
    """One reason a job ranks where it does, with the evidence behind it."""

    key: str
    label: str
    score: float
    """Normalised pull, before weighting. 0 means "this factor says nothing"."""

    weight: float
    detail: str
    """The actual evidence, in the owner's language: a date, a count, a gap."""

    known: bool = True
    """False when the practice holds no fact this factor could read.

    Distinct from a score of 0. "No statutory deadline on file" and "the
    deadline is months away" are different statements and the queue says which
    (principles 1 and 2)."""

    @property
    def contribution(self) -> float:
        return self.score * self.weight


@dataclass(frozen=True, slots=True)
class WorkItem:
    """A job somebody can pick up, where it ranks, and why it ranks there."""

    job: Job
    view: StageView
    rank: int
    """1-based position. A SUGGESTION — see :attr:`ordering_is_firm_policy`."""

    score: float
    factors: tuple[Factor, ...]
    why: str
    """One line naming the real evidence. A rank with no reason is a number
    nobody can argue with, and a row the owner cannot audit is one they learn to
    scroll past (principle 13)."""

    deadline: date | None = None
    """The STATUTORY deadline, computed from cited rules. ``None`` when the
    practice holds no obligation for this job — never a stand-in."""

    deadline_known: bool = False
    ordering_is_firm_policy: bool = True
    """The rank is the owner's preference, not law. The UI must not render it
    the way it renders a statutory date."""

    @property
    def job_id(self) -> str:
        return self.job.job_id


@dataclass(frozen=True, slots=True)
class BlockedItem:
    """A job nobody can pick up, and what it is actually waiting on."""

    job: Job
    view: StageView
    waiting_on: tuple[str, ...]
    why: str
    next_step: str = ""
    longest_wait_days: int | None = None
    """Days since the oldest outstanding blocking request was made, when the
    practice recorded when it asked. ``None`` when it did not."""

    @property
    def job_id(self) -> str:
        return self.job.job_id


@dataclass(frozen=True, slots=True)
class Board:
    """Both halves of the answer, computed once."""

    workable: tuple[WorkItem, ...]
    not_workable: tuple[BlockedItem, ...]
    policy: QueuePolicy
    ordering_is_firm_policy: bool = True

    def summary_line(self) -> str:
        """The sentence that makes an empty queue useful."""
        waiting = [b for b in self.not_workable if b.view.is_waiting]
        unplanned = [b for b in self.not_workable if not b.view.is_waiting]
        if not self.workable:
            if waiting:
                return (f"Nothing to pick up — {_n(len(waiting), 'file')} "
                        f"{'is' if len(waiting) == 1 else 'are'} waiting on clients.")
            if unplanned:
                return (f"Nothing to pick up — {_n(len(unplanned), 'job')} "
                        f"{'has' if len(unplanned) == 1 else 'have'} no work planned yet.")
            return "Nothing open."
        parts = [f"{_n(len(self.workable), 'job')} you can pick up now"]
        if waiting:
            parts.append(f"{len(waiting)} waiting on clients")
        if unplanned:
            parts.append(f"{len(unplanned)} with no work planned yet")
        return "; ".join(parts) + "."


def _n(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


# --------------------------------------------------------------------------
# The factors
# --------------------------------------------------------------------------

def _as_date(value) -> date | None:
    """Best-effort date out of whatever the record actually holds.

    Timestamps arrive as ISO strings from SQLite and as ``datetime`` from
    in-memory completions, and the two are not comparable when one is
    timezone-aware. Everything is reduced to a plain date before anything is
    subtracted; a day's resolution is all the queue reasons in anyway.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _last_movement(job: Job) -> date | None:
    """The most recent thing the practice can PROVE happened on this job.

    Not "when it entered its current stage" — the stage is derived, so nothing
    records when it changed, and inventing an entry time would be exactly the
    guess this system refuses. What is genuinely on file is when the job record
    was written and when each finished task was finished, so that is what is
    measured, and the reason line says so in those words.
    """
    candidates = [_as_date(job.created_at), _as_date(job.updated_at)]
    candidates += [_as_date(t.completion.at) for t in job.tasks if t.completion]
    real = [c for c in candidates if c is not None]
    return max(real) if real else None


def _deadline_factor(duty, *, today: date, policy: QueuePolicy) -> Factor:
    """How close the STATUTORY deadline is — computed, or honestly absent."""
    weight = policy.weight("deadline")
    if duty is None:
        # Principle 1: the slot is visibly marked, never filled with the
        # hand-typed Job.due_date, which has no rule behind it.
        return Factor(key="deadline", label=FACTOR_LABELS["deadline"], score=0.0,
                      weight=weight, known=False,
                      detail="no statutory deadline on file for this job, so it is "
                             "ranked on what is known")

    days = duty.days_until(today)
    horizon = policy.horizon_days
    if days >= horizon:
        score = 0.0
    else:
        score = min((horizon - days) / horizon, _OVERDUE_CEILING)

    form = (getattr(duty, "form", "") or "").strip()
    lead = f"{form} " if form else ""
    if days < 0:
        detail = f"{lead}was due {duty.due:%b %d} — {-days} days overdue"
    elif days == 0:
        detail = f"{lead}due today ({duty.due:%b %d})"
    else:
        detail = f"{lead}due {duty.due:%b %d} — {days} days away"
    if getattr(duty, "is_assumed", False):
        # Same wording the action queue uses: a duty built on an unconfirmed
        # fact is a guess wearing a deadline, and it says so.
        detail += " (from an unconfirmed assumption about this client)"
    return Factor(key="deadline", label=FACTOR_LABELS["deadline"], score=score,
                  weight=weight, detail=detail)


def _idle_factor(job: Job, *, today: date, policy: QueuePolicy) -> Factor:
    """How long since anything was recorded against this job."""
    weight = policy.weight("idle")
    moved = _last_movement(job)
    if moved is None:
        return Factor(key="idle", label=FACTOR_LABELS["idle"], score=0.0,
                      weight=weight, known=False,
                      detail="no dated record of when this job last moved")
    days = max((today - moved).days, 0)
    score = min(days / policy.stale_after_days, 1.0)
    detail = ("worked on today" if days == 0
              else f"nothing recorded on it for {_n(days, 'day')}")
    return Factor(key="idle", label=FACTOR_LABELS["idle"], score=score,
                  weight=weight, detail=detail)


def _unblocks_factor(job: Job, *, policy: QueuePolicy) -> Factor:
    """How much other work inside this job is queued behind the current work.

    Counted from ``Task.blocked_by``, which is a recorded fact. Cross-job
    dependencies are not modelled anywhere, so they are not counted and not
    guessed at.
    """
    weight = policy.weight("unblocks")
    blocked = [t for t in job.tasks
               if t.audience == "internal" and t.is_open and t.blocked_by]
    count = len(blocked)
    # Saturating rather than linear: the second blocked task matters much less
    # than the first, and no knob is needed to say so.
    score = 1.0 - 1.0 / (1 + count)
    detail = ("" if count == 0
              else f"finishing this frees {_n(count, 'blocked task')}")
    return Factor(key="unblocks", label=FACTOR_LABELS["unblocks"], score=score,
                  weight=weight, detail=detail)


def _quick_win_factor(job: Job, *, policy: QueuePolicy) -> Factor:
    """How few things stand between this job and being off the board."""
    weight = policy.weight("quick_win")
    open_internal = [t for t in job.tasks if t.audience == "internal" and t.is_open]
    count = len(open_internal)
    score = 1.0 / max(count, 1)
    detail = ("nothing left on it but sending it out" if count == 0
              else f"{_n(count, 'task')} left")
    return Factor(key="quick_win", label=FACTOR_LABELS["quick_win"], score=score,
                  weight=weight, detail=detail)


# --------------------------------------------------------------------------
# Putting it together
# --------------------------------------------------------------------------

def _readiness_for(job: Job, requested: Sequence, *,
                   tax_year: int | None) -> Readiness | None:
    """Assess this job's client, or admit that no document check was possible.

    Returns ``None`` rather than an empty :class:`Readiness` when the year is
    unknown: an empty Readiness reads as "everything is in", which is a
    confident wrong answer about the one thing that decides whether a file can
    be touched at all.
    """
    year = job.tax_year if job.tax_year is not None else tax_year
    if year is None:
        return None
    return assess(requested, client_id=job.client_id, tax_year=int(year))


def _duty_for(job: Job, by_key: Mapping[str, object]):
    """The materialised obligation this job discharges, if one is on file.

    Matched on ``Job.obligation_key`` — the recorded link, not a guess from the
    workflow name and the year. A job with no key, or a key nothing matches, has
    no computable deadline, and that is reported rather than papered over.
    """
    key = (job.obligation_key or "").strip()
    return by_key.get(key) if key else None


def _reason(view: StageView, factors: Sequence[Factor]) -> str:
    """One line, in the owner's language, naming the actual evidence."""
    contributing = sorted((f for f in factors if f.known and f.contribution > 0
                           and f.detail),
                          key=lambda f: (-f.contribution, f.key))
    missing = [f for f in factors if not f.known and f.detail]
    parts = [f.detail for f in contributing[:3]] + [f.detail for f in missing]
    phrase = _STAGE_PHRASE.get(view.stage, view.stage.replace("_", " ").capitalize())
    if not parts:
        # Nothing pulled it anywhere — say what the job IS rather than emit a
        # bare rank. Principle 13: a row with no reason is a row to scroll past.
        return f"{phrase} — {view.why}"
    return f"{phrase} — {'; '.join(parts)}."


def _score(job: Job, duty, *, today: date,
           policy: QueuePolicy) -> tuple[float, tuple[Factor, ...]]:
    factors = (
        _deadline_factor(duty, today=today, policy=policy),
        _idle_factor(job, today=today, policy=policy),
        _unblocks_factor(job, policy=policy),
        _quick_win_factor(job, policy=policy),
    )
    # Summed in FACTOR_KEYS order, which is fixed above — float addition is not
    # associative, so the order has to be pinned for the score to be repeatable.
    ordered = {f.key: f for f in factors}
    total = sum(ordered[k].contribution for k in FACTOR_KEYS)
    return total, tuple(ordered[k] for k in FACTOR_KEYS)


def _split(jobs: Iterable[Job], *, requested: Sequence, obligations: Sequence,
           today: date, tax_year: int | None, policy: QueuePolicy):
    """Derive every job's stage once and sort it into the two halves."""
    by_key = {}
    for duty in obligations:
        key = (getattr(duty, "obligation_key", "") or "").strip()
        if key and key not in by_key:
            by_key[key] = duty

    ready: list[tuple[float, str, Job, StageView, tuple[Factor, ...], object]] = []
    stuck: list[BlockedItem] = []

    for job in jobs:
        if tax_year is not None and job.tax_year is not None \
                and int(job.tax_year) != int(tax_year):
            continue
        readiness = _readiness_for(job, requested, tax_year=tax_year)
        view = derive_stage(job, readiness=readiness, today=today)
        if view.is_workable:
            duty = _duty_for(job, by_key)
            score, factors = _score(job, duty, today=today, policy=policy)
            ready.append((score, job.job_id, job, view, factors, duty))
        else:
            stuck.append(_blocked(job, view, readiness, today=today))

    # Highest score first; ties broken on job_id, never on input order. Sorting
    # a tuple whose second element is the id makes the order total and
    # repeatable even when two jobs score identically.
    ready.sort(key=lambda row: (-row[0], row[1]))
    stuck.sort(key=lambda b: ((b.longest_wait_days is None), -(b.longest_wait_days or 0),
                              b.job_id))
    return ready, stuck


def _blocked(job: Job, view: StageView, readiness: Readiness | None, *,
             today: date) -> BlockedItem:
    waits = []
    if readiness is not None:
        waits = [d for d in (i.days_waiting(today) for i in readiness.blocking_open)
                 if d is not None]
    longest = max(waits) if waits else None
    why = view.why
    if longest is not None:
        why = f"{why} Asked {_n(longest, 'day')} ago."
    return BlockedItem(job=job, view=view, waiting_on=view.blocked_by, why=why,
                       next_step=view.next_step, longest_wait_days=longest)


def _items(ready) -> list[WorkItem]:
    """Turn the sorted rows into ranked items. The rank IS the sort position —
    it is never stored, so it cannot go stale (principle 3)."""
    return [
        WorkItem(job=job, view=view, rank=position, score=score, factors=factors,
                 why=_reason(view, factors),
                 deadline=getattr(duty, "due", None) if duty is not None else None,
                 deadline_known=duty is not None)
        for position, (score, _id, job, view, factors, duty)
        in enumerate(ready, start=1)
    ]


def workable(jobs: Iterable[Job], *, requested: Sequence = (),
             obligations: Sequence = (), today: date,
             tax_year: int | None = None,
             policy: QueuePolicy | None = None) -> list[WorkItem]:
    """The jobs somebody can pick up right now, best first.

    ``requested`` is the client's outstanding asks; without them nothing can be
    known to be blocked, and the reason line says so rather than implying the
    file is clean. ``obligations`` are already-materialised duties, whose dates
    were computed from the cited statutory rules — pass none and every job
    reports an unknown deadline instead of borrowing a plausible one.

    Reads only. Nothing is assigned, started, reserved or written; the stored
    ``Job.stage`` is neither consulted nor updated.
    """
    pol = policy or queue_policy()
    ready, _ = _split(jobs, requested=requested, obligations=obligations,
                      today=today, tax_year=tax_year, policy=pol)
    return list(_items(ready))


def not_workable(jobs: Iterable[Job], *, requested: Sequence = (),
                 obligations: Sequence = (), today: date,
                 tax_year: int | None = None,
                 policy: QueuePolicy | None = None) -> list[BlockedItem]:
    """The jobs nobody can pick up, and what each one is actually waiting on.

    The counterpart to :func:`workable`, and not an afterthought: an empty
    workable list means nothing on its own, while "fourteen files are waiting on
    clients" tells the owner to spend the morning chasing.
    """
    pol = policy or queue_policy()
    _, stuck = _split(jobs, requested=requested, obligations=obligations,
                      today=today, tax_year=tax_year, policy=pol)
    return stuck


def board(jobs: Iterable[Job], *, requested: Sequence = (),
          obligations: Sequence = (), today: date, tax_year: int | None = None,
          policy: QueuePolicy | None = None) -> Board:
    """Both halves in one pass — what the screen actually renders."""
    pol = policy or queue_policy()
    ready, stuck = _split(jobs, requested=requested, obligations=obligations,
                          today=today, tax_year=tax_year, policy=pol)
    return Board(workable=tuple(_items(ready)), not_workable=tuple(stuck), policy=pol)
