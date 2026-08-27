"""The events after the opening pack, and the documents they produce.

WHY THIS EXISTS. Four documents could not be produced by any command a
preparer can run -- the delivery letter, the organizer cover, the extension
notice and the disengagement letter. Each needs facts that do not exist when
the engagement is created: a signature deadline, an extended deadline, what
was actually delivered, the date an engagement ended. Nothing collected them.
`doctor` reported the organizer letter blocked on every engagement in the
store, correctly, and there was no way to unblock it.

So the opening pack was a third of the process and the other two thirds had no
front door at all. Found by opening 303 rendered documents, not by any test --
because every test renders from a fixture that already carries the answers.

What is asked lives in `registry/lifecycle.yaml`, the same way the close-out's
questions do, so adding one is an edit to data rather than a change here.

TWO FLAGS FROM ONE ANSWER, ALWAYS. Where a document has an inverse pair, the
registry declares `pair:` and this module derives both from a single answer.
Two independent booleans can both be false, and when they were, the extension
notice printed a heading warning that the payment deadline had not moved and
then nothing at all in the section that was supposed to say what to do.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

import engagements

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry" / "lifecycle.yaml"


class LifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class Event:
    key: str
    document: str
    what: str
    questions: list
    rows: list


def load(path: Path | str = REGISTRY) -> dict[str, Event]:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out: dict[str, Event] = {}
    for key, entry in (spec.get("events") or {}).items():
        for q in entry.get("questions") or []:
            supplies = q.get("supplies")
            pair = q.get("pair")
            flag = q.get("flag")
            for option in (pair or {}):
                if not isinstance(option, str):
                    raise LifecycleError(
                        f"{key}.{q.get('id')} has a non-string option "
                        f"{option!r} in its pair. YAML 1.1 reads a bare "
                        f"`yes:` or `no:` as a BOOLEAN, so the key never "
                        f"matches the answer a preparer types and both flags "
                        f"come out false — which is exactly the empty section "
                        f"the pair exists to prevent. Quote it.")
            if not (supplies or pair or flag):
                raise LifecycleError(
                    f"{key}.{q.get('id')} supplies nothing — every question "
                    f"here fills a merge field, sets a flag, or derives a "
                    f"pair. One that does none of those is a question nobody "
                    f"can act on.")
        out[key] = Event(key=key, document=entry["document"],
                         what=entry.get("what", ""),
                         questions=entry.get("questions") or [],
                         rows=entry.get("rows") or [])
    return out


def event(key: str, path: Path | str = REGISTRY) -> Event:
    events = load(path)
    if key not in events:
        raise LifecycleError(
            f"no lifecycle event {key!r}. Known: {', '.join(sorted(events))}")
    return events[key]


def asks(question: dict, answers: dict) -> bool:
    """Whether this question applies, given what has been answered.

    `when:` is a plain equality against another answer in the same event --
    "how much should they pay" is asked only where a payment is due. Anything
    more expressive belongs in the interview schema, which already has a
    parser for it; a second half-grammar in a second file is how two things
    that should agree start to differ.
    """
    gate = question.get("when")
    if not gate:
        return True
    return all(str(answers.get(k, "")) == str(v) for k, v in gate.items())


def fields(key: str, answers: dict, rows: dict | None = None,
           path: Path | str = REGISTRY) -> dict:
    """The merge fields this event's answers produce.

    Every flag pair is derived from ONE answer, so the two can never disagree.
    A flag whose question was not asked is set FALSE rather than left absent:
    absent and false render the same and mean different things, and `merge`
    can only report what it can see.
    """
    ev = event(key, path)
    out: dict = {}

    for q in ev.questions:
        asked = asks(q, answers)
        value = answers.get(q["id"])

        if q.get("pair"):
            chosen = str(value or "")
            for option, flag in q["pair"].items():
                out[flag] = asked and chosen == str(option)
            continue

        if q.get("flag"):
            out[q["flag"]] = asked and str(value or "").lower() in ("yes", "true")
            continue

        if not asked:
            continue
        if value not in (None, ""):
            out[q["supplies"]] = value

    for spec in ev.rows:
        supplied = (rows or {}).get(spec["list"])
        if supplied is not None:
            out[spec["list"]] = supplied

    return out


def missing(key: str, merged: dict, path: Path | str = REGISTRY) -> list[str]:
    """What this event still needs before its document can be honest."""
    ev = event(key, path)
    out = []
    for q in ev.questions:
        target = q.get("supplies")
        if target and target not in merged and asks(q, {}):
            out.append(target)
    for spec in ev.rows:
        if spec.get("required") and not merged.get(spec["list"]):
            out.append(spec["list"])
    return out


# ── the store ─────────────────────────────────────────────────────────────

def save(ref: str, key: str, payload: dict,
         store: Path = engagements.STORE) -> Path:
    """What a preparer answered, beside the record.

    One file per event, named for it: an engagement can be extended and later
    disengaged, and the second must not overwrite the first.
    """
    path = engagements._dir(store, ref) / f"event-{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def load_saved(ref: str, key: str,
               store: Path = engagements.STORE) -> dict | None:
    path = engagements._dir(store, ref) / f"event-{key}.json"
    if not path.exists():
        return None
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return got if isinstance(got, dict) else None


def events_on(ref: str, store: Path = engagements.STORE) -> list[str]:
    """Which lifecycle events this engagement has been through."""
    folder = engagements._dir(store, ref)
    if not folder.exists():
        return []
    return sorted(p.stem[len("event-"):] for p in folder.glob("event-*.json"))
