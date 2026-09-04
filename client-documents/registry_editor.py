"""Change a price in the browser, without touching YAML by hand.

The firm, 26 August 2026: *"i want this to be GUI-based like i think you made
the changing of templates."* This is the registry half of `editor.py`.

WHY THIS IS NOT `yaml.safe_dump`. `fee-schedule.yaml` is 58 KB and most of it
is comments -- who decided a price, when, in whose words, and what was rejected
along the way. Round-tripping it through PyYAML would produce a valid file with
every one of those decisions deleted. So an edit here is a SURGICAL TEXT EDIT:
find the one `amount:` line a path names, replace the number on it, and leave
every byte around it alone. That is the same choice `editor.py` makes about
template HTML, and for the same reason.

The safety property, which `test_registry_editor.py` holds:

    set_amount(path, current_amount)  leaves the file BYTE-IDENTICAL

A writer that cannot rewrite a value as itself is a writer that is quietly
reformatting something, and the thing it reformats will be a comment.

WHAT THIS DELIBERATELY WILL NOT DO. It edits amounts. It does not add or remove
a price, rename one, change a gate, or edit a `publish:` decision. Those change
what the pipeline can express, and `docs/pipeline-map.md` §5 lists eight ways
that goes wrong without producing an error -- a price nothing reads, a gate on
a question nobody is asked, a `supersedes:` string whose lower rung got
reworded. A number is the safe half, and it is the half the firm asked for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pricing

ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "registry" / "fee-schedule.yaml"


class RegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class Price:
    path: str          # "base.1040.tiers.standard" -- how pricing names it
    label: str         # what a person calls it
    amount: int
    line: int          # 1-based, in fee-schedule.yaml
    published: bool    # does this figure reach satcllp.com?
    where: str         # which part of the schedule it sits in


# Every place an amount lives, and how to walk to it. Written out rather than
# discovered, because "every `amount:` in the file" would also offer to edit
# the ones inside `minimum:` guards and example blocks.
def _walk(sched: dict) -> list[tuple[str, str, int, bool, str]]:
    out = []
    for form, block in (sched.get("base") or {}).items():
        for key, tier in (block.get("tiers") or {}).items():
            if "amount" not in tier:
                continue
            out.append((f"base.{form}.tiers.{key}",
                        tier.get("label", key), tier["amount"],
                        str(tier.get("publish", "")).lower() == "yes",
                        f"The {form} ladder"))
        if "amount" in block:
            out.append((f"base.{form}", block.get("label", form), block["amount"],
                        str(block.get("publish", "")).lower() == "yes",
                        "Entity returns"))
    for key, unit in (sched.get("per_unit") or {}).items():
        if "amount" in unit:
            out.append((f"per_unit.{key}", unit.get("label", key), unit["amount"],
                        str(unit.get("publish", "")).lower() == "yes", "Per item"))
        for tkey, tier in (unit.get("tiers") or {}).items():
            if "amount" in tier:
                out.append((f"per_unit.{key}.tiers.{tkey}",
                            tier.get("label", tkey), tier["amount"],
                            str(tier.get("publish", "")).lower() == "yes", "Per item"))
    for key, tier in ((sched.get("amendment") or {}).get("tiers") or {}).items():
        if "amount" in tier:
            out.append((f"amendment.tiers.{key}", tier.get("label", key), tier["amount"],
                        str(tier.get("publish", "")).lower() == "yes", "Amendments"))
    per_form = sched.get("per_form") or {}
    if "amount" in per_form:
        out.append(("per_form", "One price for any named form", per_form["amount"],
                    str(per_form.get("publish", "")).lower() == "yes", "Named forms"))
    basis = sched.get("basis") or {}
    if "rate" in basis:
        out.append(("basis.rate", "The hourly rate", basis["rate"], True, "Hourly"))
    return out


def _key_of(path: str) -> str | None:
    """The key holding the number, or None when the path already names it.

    Almost every price sits at `<something>.amount`. The hourly rate does not
    -- it is `basis.rate`, and the path already ends at the value. Returning
    None rather than "rate" is what stops the walk looking for `basis.rate.rate`.
    """
    return None if path == "basis.rate" else "amount"


def _line_of(text: str, path: str) -> int:
    """1-based line number of the amount `path` names.

    Walks the file by indentation rather than by parsing, because the point of
    this module is to touch one line and leave the rest byte-identical. A path
    that does not resolve raises rather than guessing at a nearby line -- an
    edit written to the wrong line is worse than an edit that refuses.
    """
    key = _key_of(path)
    parts = path.split(".") + ([key] if key else [])
    lines = text.splitlines()
    at, depth = 0, -1
    for want in parts:
        found = None
        for i in range(at, len(lines)):
            line = lines[i]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if depth >= 0 and indent <= depth and i > at:
                break
            m = re.match(rf'^(\s*)"?{re.escape(want)}"?\s*:', line)
            if m and (depth < 0 or indent > depth):
                found, depth = i, indent
                break
        if found is None:
            raise RegistryError(
                f"{path!r} does not name a price in fee-schedule.yaml. "
                f"Stopped looking for {want!r}."
            )
        at = found + 1
    return found + 1


def prices(schedule: dict | None = None, text: str | None = None) -> list[Price]:
    """Every amount a person may edit, in the order the file states them."""
    sched = schedule if schedule is not None else pricing.load()
    body = text if text is not None else SCHEDULE.read_text(encoding="utf-8")
    out = []
    for path, label, amount, published, where in _walk(sched):
        out.append(Price(path=path, label=label, amount=amount,
                         line=_line_of(body, path), published=published, where=where))
    return out


_AMOUNT = re.compile(r"^(?P<head>\s*\"?\w+\"?\s*:\s*)(?P<num>-?\d+)(?P<tail>\s*(?:#.*)?)$")


def set_amount(path: str, amount: int, *, text: str | None = None) -> str:
    """The file with one number changed, and nothing else touched at all.

    Returns the new text rather than writing it, so a caller can show the
    difference before committing to it -- which is the whole reason a GUI is
    better than editing YAML: you see what moved.
    """
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise RegistryError(f"a price is a whole number of dollars, not {amount!r}")
    if amount < 0:
        raise RegistryError("a price cannot be negative")

    body = text if text is not None else SCHEDULE.read_text(encoding="utf-8")
    n = _line_of(body, path)
    lines = body.splitlines(keepends=True)
    line = lines[n - 1]
    m = _AMOUNT.match(line.rstrip("\n"))
    if not m:
        raise RegistryError(
            f"line {n} does not hold a plain number, so this editor will not "
            f"rewrite it: {line.strip()!r}"
        )
    ending = "\n" if line.endswith("\n") else ""
    lines[n - 1] = f"{m.group('head')}{amount}{m.group('tail')}{ending}"
    return "".join(lines)


def effect(path: str, amount: int, *, text: str | None = None) -> dict:
    """What changes if this price is saved. The reason to have a GUI at all.

    Reports the old and new figure, whether the number reaches the website,
    and -- the part that matters -- whether the schedule still loads and still
    prices the demo answers. A price edit that breaks `pricing.load()` should
    be refused in a form, not discovered by a test after it is committed.
    """
    import json
    import yaml

    before = text if text is not None else SCHEDULE.read_text(encoding="utf-8")
    was = {p.path: p for p in prices(text=before)}
    if path not in was:
        raise RegistryError(f"{path!r} is not an editable price")
    after_text = set_amount(path, amount, text=before)

    out = {"path": path, "label": was[path].label,
           "from": was[path].amount, "to": amount,
           "published": was[path].published, "line": was[path].line,
           "problems": []}
    try:
        sched = pricing.pricing_schedule(yaml.safe_load(after_text))
    except Exception as exc:                      # noqa: BLE001 - report, don't raise
        out["problems"].append(f"the schedule no longer loads: {exc}")
        return out

    answers_path = ROOT / "samples" / "interview-answers.json"
    if answers_path.exists():
        answers = json.loads(answers_path.read_text(encoding="utf-8"))
        try:
            items = pricing.line_items(answers, sched)
            out["sample_total_after"] = pricing.estimate_total(items, sched)
            old_items = pricing.line_items(answers, pricing.load())
            out["sample_total_before"] = pricing.estimate_total(old_items, pricing.load())
        except Exception as exc:                  # noqa: BLE001
            out["problems"].append(f"the demo engagement no longer prices: {exc}")
    return out


def save(path: str, amount: int) -> dict:
    """Write it. Refuses if `effect` found a problem -- a schedule that does
    not load takes every document down with it, and this is the last place
    that can be caught before it is on disk."""
    report = effect(path, amount)
    if report["problems"]:
        raise RegistryError("; ".join(report["problems"]))
    SCHEDULE.write_text(set_amount(path, amount), encoding="utf-8")
    return report
