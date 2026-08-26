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
from datetime import datetime

import interview as iv
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


def _as_date(value):
    """A merge field read as a real date, or None if it is not one.

    Deliberately forgiving. `first_deliverable_target` invites "a real date or
    a phrase they can hold us to -- 'April 1, 2027', 'two weeks after the file
    is complete'", and a phrase is a legitimate answer that two dates cannot be
    compared against. None means "not comparable", never "wrong".
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%B %d, %Y").date()
    except ValueError:
        return None


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
        #
        # WHAT COUNTS AS "BILLED", and this is where the check was wrong.
        # It scanned the whole rendered estimate, which also carries each
        # package's `Includes:` list -- what the package WOULD cover, not what
        # is being charged. Standard's list says "One gig Schedule C on
        # standard mileage", so every ordinary Standard client (a couple who
        # itemise, a landlord, anyone with a K-1) was reported as having a
        # Schedule C billed outside their scope, and `cli.py check` exited 1
        # on them. The demo package was the one record that did not trip it,
        # because its scope happens to name a Schedule C -- so the suite was
        # green while the tool cried wolf at nearly every real engagement.
        # A check that fails on healthy work teaches whoever runs it to stop
        # reading it, which costs the five checks beside it too.
        #
        # So: what is billed is the LINES -- each item's service and its
        # detail -- and nothing else. Restricted to the schedules the scope
        # sentence can actually name, because "Schedule K-1 received" is a
        # line for entering somebody else's form, not a federal schedule that
        # could be in or out of scope.
        #
        # And the scope is BOTH lines of the letter that name forms: section
        # 01's "Federal:" and its "Also included:". A preparer who lists
        # "Form 8949 and Schedule D — sale of home" under additional forms has
        # put it in scope, and the check has to see that or the only way to
        # satisfy it is to stop billing honestly.
        in_scope = (schedules(record.get("FederalReturns") or "")
                    | schedules(record.get("AdditionalForms") or ""))
        billed = set()
        for item in record.get("LineItems") or []:
            billed |= schedules(f"{item.get('Service', '')} {item.get('Detail', '')}")
        outside = sorted((billed - in_scope) & iv.SCOPE_SCHEDULES)
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
            # An amount that will not parse comes back as None, which the
            # check below already knows how to report. It used to raise:
            # `[CONFIRM: ...]` reduces to ".." under this filter, and
            # `float("..")` is a ValueError, so `cli.py check` died with a
            # traceback on exactly the records that most need checking -- an
            # engagement carrying an unpriced line. The docstring below
            # already promised "an amount that will not parse"; only the code
            # disagreed.
            digits = re.sub(r"[^0-9.]", "", s or "")
            try:
                return round(float(digits) * 100)
            except ValueError:
                return None
        parts = [cents(i.get("Amount", "")) for i in items]
        want, got = cents(total), (sum(parts) if all(p is not None for p in parts) else None)
        if want is None:
            detail = (f"the total itself is not an amount — it reads {total!r}, "
                      f"which is what an unpriced line does to it")
        elif got is None:
            detail = f"{total} against lines including an amount that will not parse"
        elif want != got:
            detail = f"{total} against lines summing to {got / 100:,}"
        else:
            detail = f"{total} over {len(items)} line(s)"
        out.append(Check("the total is the sum of the lines",
                         got is not None and want == got, detail))

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

    # ── nothing is promised before the materials are due ──────────────────
    #
    # A JOIN NOTHING MADE. Two dates reach a client in one package from two
    # different places -- `MaterialsDeadline` from firm-settings, the target
    # from an answer somebody gives on the call -- and nothing has ever
    # compared them.
    #
    # Promise the earlier one and the package contradicts itself on its face.
    # The onboarding letter says "Please send everything by the 25th" and then
    # "Our target for your first deliverable is the 12th"; the business letter
    # says it in a single sentence -- "Our target for delivering the K-1s is
    # X, provided the entity's records reach us complete by Y" -- where X
    # before Y is not a tight promise, it is an impossible one. And on the
    # entity return it is the promise every owner's personal return is
    # planned around.
    #
    # Skipped rather than failed where a target is a phrase: the interview
    # invites one, and "two weeks after the file is complete" cannot be
    # compared to a date. Only a date against a date is evidence.
    due = _as_date(record.get("MaterialsDeadline"))
    for field, name, what in (
            ("FirstDeliverableTarget",
             "the first deliverable is not promised before the materials are due",
             "the first deliverable"),
            ("ScheduleK1Target",
             "the K-1s are not promised before the materials are due",
             "the K-1s")):
        promised = _as_date(record.get(field))
        if due is None or promised is None:
            continue
        stamp = "%B %-d, %Y"
        out.append(Check(
            name,
            promised >= due,
            f"{promised.strftime(stamp)}, on or after the {due.strftime(stamp)} "
            f"deadline" if promised >= due else
            f"{what} is promised for {promised.strftime(stamp)}, which is "
            f"before the {due.strftime(stamp)} date the same package tells the "
            f"client to send everything by"))

    return out


def render_package(record: dict, documents: dict, template_dir,
                   required_lists: dict | None = None) -> dict[str, str]:
    """{document name -> HTML}, for whichever documents the record can fill.

    `required_lists` is {document -> the lists that may not be empty}, exactly
    as `cli` passes to `merge.render`, and leaving it out is what let this
    compare a document nobody can send. An `[[EACH]]` over an empty list
    leaves no token behind, so the organizer cover letter -- whose `Requested`
    list nothing builds yet -- rendered here as a heading with nothing under
    it, joined the comparison, and was counted among the documents that agree.
    `render` and `package` both refuse it. Which lists may legitimately be
    empty is a judgement about the document and lives in registry/fields.yaml,
    so it is passed in rather than decided here.
    """
    required_lists = required_lists or {}
    out = {}
    for name, (filename, _) in documents.items():
        try:
            out[name] = merge.render(
                (template_dir / filename).read_text(encoding="utf-8"), record,
                required_lists=required_lists.get(name, ())).html
        except merge.MergeError:
            continue        # not this engagement's document; not a disagreement
    return out
