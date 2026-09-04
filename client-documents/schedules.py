"""What the client told us -> which federal schedules the return needs.

The firm, 26 August 2026:

    "the interview needs to ask questions that then mean we definitely need a
     schedule - not straight ask 'what schedule is required'."

They are right, and the interview was asking the preparer's conclusion. It
offered a checklist reading "Schedule A — itemized deductions, Schedule B —
interest and dividends, Schedule C — sole proprietorship" and asked which
applied. A client does not know. A preparer does, but only AFTER hearing the
facts -- which is the thing the interview exists to collect.

So the sitting asks facts a person can answer about their own year, and this
module turns them into schedules. THE MAPPING IS THE FIRM'S, in the registry;
nothing here decides tax treatment on its own.

WHY THIS IS NOT DERIVED FROM THE COUNTS. `count_rentals` already exists and
"more than zero rentals" would look like the same signal. It is not.
`pricing._gate_holds` carries the reason: "A count can be blank when the thing
exists -- a client ticks the rentals schedule and leaves the number for later
-- and a gate that reads that as zero sends a landlord to the cheapest
package." A feature tick cannot be blank-but-true in that way.

THE PREPARER STILL DECIDES. `derive` returns a proposal and the reason for
each line, and the interview shows both before an engagement is created.
Schedule A is the clearest case: whether itemising beats the standard
deduction is an arithmetic question about a year that is not finished being
entered, so the feature question asks what the client HAS and the sentence
says so. Drake remains the system of record for what is actually filed.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "registry" / "interview.yaml"

# Where the feature -> schedule mapping lives, and the question whose options
# the features come from. Both in the registry, so the firm can change what a
# fact implies without anybody editing Python.
FEATURES_QUESTION = "return_features"
DERIVES = "federal_schedules"


class ScheduleError(RuntimeError):
    pass


# How a schedule reads to a person. Off the derived question's own options, so
# the name a preparer sees on the review screen is the name in the registry.
def _labels() -> dict:
    for section in _schema()["sections"]:
        for q in section["questions"]:
            if q["id"] == DERIVES:
                return {o["value"]: o["label"] for o in q.get("options") or []}
    return {}


@dataclass(frozen=True)
class Derived:
    schedules: tuple[str, ...]
    because: tuple[tuple[str, str], ...]      # (schedule, the fact behind it)


@lru_cache(maxsize=1)
def _schema() -> dict:
    return yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))


def _question(schema: dict | None = None) -> dict:
    for section in (schema or _schema())["sections"]:
        for q in section["questions"]:
            if q["id"] == FEATURES_QUESTION:
                return q
    raise ScheduleError(
        f"the interview has no {FEATURES_QUESTION!r} question, so nothing "
        f"says which facts imply which schedules."
    )


def mapping(schema: dict | None = None) -> dict[str, dict]:
    """Feature value -> {schedules, label}. Straight off the question."""
    q = _question(schema)
    out = {}
    for opt in q.get("options") or []:
        implies = opt.get("implies")
        if implies is None:
            raise ScheduleError(
                f"{FEATURES_QUESTION}/{opt['value']} has no `implies:`. Every "
                f"option has to say which schedules it means, or a client can "
                f"tick something that changes nothing and nobody finds out "
                f"until the letter's scope is wrong."
            )
        if isinstance(implies, str):
            implies = [implies]
        out[opt["value"]] = {"schedules": list(implies), "label": opt["label"]}
    return out


def derive(answers: dict, schema: dict | None = None) -> Derived:
    """The schedules these answers imply, and why each one is there.

    Order is the registry's, not the order a client happened to tick in, so
    two clients with the same return get the same scope sentence.
    """
    picked = answers.get(FEATURES_QUESTION) or []
    if isinstance(picked, str):
        picked = [s.strip() for s in picked.split(",") if s.strip()]
    picked = set(picked)

    seen, because = [], []
    for value, spec in mapping(schema).items():
        if value not in picked:
            continue
        for sched in spec["schedules"]:
            if sched not in seen:
                seen.append(sched)
                because.append((sched, spec["label"]))
    return Derived(tuple(seen), tuple(because))


def apply(answers: dict, schema: dict | None = None) -> dict:
    """`answers` with `federal_schedules` set from the features.

    Mutates and returns the same dict, because it runs inside a live sitting
    where the answers ARE the session. A preparer override wins: it is set
    only by someone who has looked at the derivation and disagreed, and the
    software second-guessing that would make the override pointless.
    """
    if answers.get(FEATURES_QUESTION) is None:
        return answers
    override = answers.get(f"{DERIVES}_override")
    answers[DERIVES] = list(override) if override else list(derive(answers, schema).schedules)
    return answers


LABELS = _labels()
