"""Engagements on disk, so one exists between two commands.

`EngagementRef` is the join key the whole document set depends on: the letter,
the estimate, the onboarding letter and every invoice must carry byte-identical
values or they are not about the same engagement. Until now it was a string
typed on the command line — typed twice, in practice, which is the failure the
key exists to prevent.

Deliberately a directory of JSON files rather than a database. One engagement is
one folder a human can open, and the record is the same JSON `render` already
takes, so nothing new has to be learned to inspect or repair one.

Format is `YYYY-NNNN`, from `client-documents/README.md`: the leads workbook
generates `2026 - 0001` and the template format wins, so a lead's number becomes
its `EngagementRef` on conversion.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "engagements"

REF = re.compile(r"^\d{4}-\d{4}$")


class EngagementError(RuntimeError):
    pass


def _dir(store: Path, ref: str) -> Path:
    if not REF.match(ref):
        raise EngagementError(
            f"{ref!r} is not an engagement ref. The format is YYYY-NNNN and it "
            f"is byte-compared across every document, so it is validated here "
            f"rather than discovered on a client's letter."
        )
    return store / ref


def next_ref(year: int | None = None, store: Path = STORE) -> str:
    """The next unused ref for the year. Sequential, never reused."""
    year = year or date.today().year
    store.mkdir(parents=True, exist_ok=True)
    used = [int(p.name.split("-")[1]) for p in store.iterdir()
            if p.is_dir() and REF.match(p.name) and p.name.startswith(f"{year}-")]
    return f"{year}-{max(used, default=0) + 1:04d}"


def create(record: dict, ref: str | None = None, year: int | None = None,
           store: Path = STORE) -> tuple[str, Path]:
    """Write a new engagement. Refuses to overwrite one that exists."""
    store.mkdir(parents=True, exist_ok=True)
    ref = ref or next_ref(year, store)
    path = _dir(store, ref)
    if path.exists():
        raise EngagementError(
            f"engagement {ref} already exists at {path}. Refs are never reused "
            f"-- an overwrite would silently retarget every document that "
            f"already carries this one."
        )
    path.mkdir(parents=True)
    record = dict(record, EngagementRef=ref)
    save(record, ref, store)
    return ref, path


def save(record: dict, ref: str, store: Path = STORE) -> Path:
    path = _dir(store, ref) / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def load(ref: str, store: Path = STORE) -> dict:
    path = _dir(store, ref) / "record.json"
    if not path.exists():
        raise EngagementError(f"no engagement {ref} in {store}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_answers(answers: dict, ref: str, store: Path = STORE) -> Path:
    """The raw interview answers, beside the record.

    Kept because the record is lossy: it holds the merge fields, not the
    internal answers -- the red flags, the decision, the notes, the billable
    counts. Those are why the engagement was taken on, and they belong with it.
    """
    path = _dir(store, ref) / "interview.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def record_override(ref: str, entry: dict, store: Path = STORE) -> Path:
    """Append one waved-through gate failure to the engagement's own file.

    APPEND ONLY, and deliberately so. The firm chose a pre-send gate that
    blocks but never traps you -- ``--force`` writes the pack anyway. What
    makes that a gate rather than a suggestion is that the override is not
    silent: what failed, and the reason given, land here beside the record and
    can be read back at year end. An override nobody can see is just a second,
    quieter way to send a pack that did not pass.

    Never rewritten and never pruned. A log you can edit is not evidence.
    """
    path = _dir(store, ref) / "overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                log = existing
        except json.JSONDecodeError:
            # A corrupt log is still evidence that something happened. Keep it
            # beside the new one rather than overwriting it away.
            log = [{"unreadable": path.with_suffix(".corrupt").name}]
            path.replace(path.with_suffix(".corrupt"))
    log.append(entry)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def overrides(ref: str, store: Path = STORE) -> list[dict]:
    """Every gate failure ever waved through on this engagement."""
    path = _dir(store, ref) / "overrides.json"
    if not path.exists():
        return []
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return got if isinstance(got, list) else []


def listing(store: Path = STORE) -> list[dict]:
    """Every engagement, newest ref first."""
    if not store.exists():
        return []
    out = []
    for path in sorted(store.iterdir(), reverse=True):
        if not (path.is_dir() and REF.match(path.name)):
            continue
        try:
            record = load(path.name, store)
        except Exception:
            out.append({"ref": path.name, "client": "(unreadable record.json)"})
            continue
        out.append({
            "ref": path.name,
            "client": record.get("ClientFullName") or "(no name)",
            "period": record.get("PeriodLabel") or "",
        })
    return out
