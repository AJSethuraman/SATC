"""Does a package of documents agree with itself?

The firm's ask, 26 August 2026: *"i want you to come back and also show me how
you can tell it all goes together (so i can see consistency)."* Fair question.
Every document renders from one record, which makes agreement *likely* and
proves nothing -- the two failures that actually happened were both inside one
record:

  * The engagement letter's scope said "Schedules A, C, and SE" while the
    estimate billed a $145 Rental schedule. Schedule E was on the bill and
    outside the scope the client had signed.
  * A fee estimate carried a services table with no rows and "Total estimate
    $785" underneath it, and reported success.

So this reads the RENDERED documents, not the record, and states the joins as
claims that can fail. `python cli.py check <record.json>` prints them.

Nothing here is a merge-time guard: `merge.render` already refuses a holed
document, and refusing is the right response to a hole. This is the other
question -- everything resolved, and do the resolved values tell one story.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import merge


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

    def __bool__(self) -> bool:
        return self.ok


# "Schedules A, C, E, and SE" and "Schedule E" alike. Anchored on the word, so
# an "E" loose in a sentence is not a schedule.
_SEP = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+)"
_SCHEDULES = re.compile(
    rf"\bSchedules?\s+((?:[A-Z]{{1,2}}(?:-?\d)?(?![A-Za-z]))(?:{_SEP}[A-Z]{{1,2}}(?:-?\d)?(?![A-Za-z]))*)")


def schedules(text: str) -> set[str]:
    """Every federal schedule a piece of text names.

    "Schedules A, C, E, and SE" is one run of four, and the separator has to
    take the Oxford comma or the last one is silently dropped -- which would
    have made SE look like a schedule billed outside the scope that names it.
    """
    found: set[str] = set()
    for run in _SCHEDULES.findall(text or ""):
        found.update(t for t in re.split(_SEP, run) if t)
    return found


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def report(record: dict, rendered: dict[str, str]) -> list[Check]:
    """`rendered` is {document name -> its HTML}, as `cli.render` produces.

    Every check is skipped rather than failed when the documents it compares
    are not both in the set: a run that renders one document is not evidence
    that two documents disagree.
    """
    out: list[Check] = []
    text = {name: _text(html) for name, html in rendered.items()}

    def both(a, b):
        return a in text and b in text

    # ── the join key ──────────────────────────────────────────────────────
    ref = (record.get("EngagementRef") or "").strip()
    if ref and len(rendered) > 1:
        absent = sorted(n for n, t in text.items() if ref not in t)
        out.append(Check(
            "one engagement reference",
            not absent,
            f"{ref} on all {len(rendered)}" if not absent
            else f"{ref} is missing from: {', '.join(absent)}"))

    # ── one date across the package ───────────────────────────────────────
    date = (record.get("LetterDate") or "").strip()
    if date and len(rendered) > 1:
        absent = sorted(n for n, t in text.items() if date not in t)
        out.append(Check(
            "one letter date",
            not absent,
            f"{date} on all {len(rendered)}" if not absent
            else f"{date} is missing from: {', '.join(absent)}"))

    # ── the letter and the estimate state one scope ───────────────────────
    #
    # The estimate repeats the letter's four scope lines from the same fields.
    # Checking the VALUES on the rendered pages is what makes it a check
    # rather than a restatement of where the data came from.
    for letter in ("tax-letter", "business-letter"):
        if not both(letter, "fee-estimate"):
            continue
        wrong = []
        for field in ("FederalReturns", "StateReturns", "LocalReturns",
                      "AdditionalForms"):
            value = (record.get(field) or "").strip()
            if not value:
                continue
            for name in (letter, "fee-estimate"):
                if value not in text[name]:
                    wrong.append(f"{field} not on the {name}")
        out.append(Check(
            "the letter and the estimate state one scope",
            not wrong,
            "all four scope lines on both" if not wrong else "; ".join(wrong)))

        # ── nothing is billed outside the scope ───────────────────────────
        #
        # THE BUG THIS IS HERE FOR. The reverse direction is deliberately not
        # checked: a scope naming Schedules A and SE is correct with neither
        # appearing on the estimate, because both are inside the package
        # price. A schedule that is BILLED and not in scope is the failure.
        in_scope = schedules(record.get("FederalReturns") or "")
        billed = schedules(text["fee-estimate"])
        outside = sorted(billed - in_scope)
        out.append(Check(
            "nothing is billed outside the scope",
            not outside,
            "every schedule on the estimate is in the letter's scope"
            if not outside else
            f"the estimate names Schedule {', '.join(outside)}, which the "
            f"letter's scope does not"))

    # ── the total is the sum of the lines ─────────────────────────────────
    items = record.get("LineItems") or []
    total = record.get("EstimateTotal") or record.get("Subtotal")
    if items and isinstance(total, str):
        def cents(s):
            digits = re.sub(r"[^0-9.]", "", s or "")
            return round(float(digits) * 100) if digits else None
        parts = [cents(i.get("Amount", "")) for i in items]
        want, got = cents(total), (sum(parts) if all(p is not None for p in parts) else None)
        out.append(Check(
            "the total is the sum of the lines",
            got is not None and want == got,
            f"{total} over {len(items)} line(s)" if got is not None and want == got
            else f"{total} against lines summing to "
                 f"{'an amount that will not parse' if got is None else got / 100:,}"))

    # ── the deadline is one date ──────────────────────────────────────────
    deadline = (record.get("MaterialsDeadline") or "").strip()
    if deadline:
        says = {n for n, t in text.items() if "complete information by" in t
                or "send everything by" in t.lower()}
        absent = sorted(n for n in says if deadline not in text[n])
        if says:
            out.append(Check(
                "one materials deadline",
                not absent,
                f"{deadline} on {len(says)} document(s)" if not absent
                else f"a document states a deadline that is not {deadline}: "
                     f"{', '.join(absent)}"))

    return out


def render_package(record: dict, documents: dict, template_dir) -> dict[str, str]:
    """{document name -> HTML}, for whichever documents the record can fill."""
    out = {}
    for name, (filename, _) in documents.items():
        try:
            out[name] = merge.render(
                (template_dir / filename).read_text(encoding="utf-8"), record).html
        except merge.MergeError:
            continue        # not this engagement's document; not a disagreement
    return out
