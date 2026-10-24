"""Every item in the fee schedule has a price, or is deliberately hourly.

**THE RULE THIS ENFORCES.** The firm, 7 September 2026:

    "generally speaking, if we have no price it should be assumed to be $175
     (is this what we agreed on?) but the goal would be to establish a price"

Read as the hourly *rate* rather than a flat $175 -- a flat figure would price
five minutes and six hours identically, and $175 is the rate set the same day.

The rule has two halves and only one of them is a default:

1. **Work with no price is billed hourly.** That already existed: it is what
   `hourly.situations` is, and those entries carry no `amount` on purpose.
2. **The goal is to establish a price.** Which makes the fallback a WORKLIST,
   not a resting place -- and a worklist nobody can see is a resting place.

**WHY A DEFAULT NEEDS A GUARD.** `pricing.py` opens by saying *"an unpriced item
does not become zero"*: a missing amount carries a `[CONFIRM:` all the way to the
total and the estimate refuses to render, because *"quoting a client $0 for a
service is worse than quoting nothing at all"*. That refusal is what has been
making prices get set.

A fallback to hourly softens it. An item that should have had a price can now
render as hourly and never be noticed, because the estimate no longer stops. So
the fallback has to be a **closed set the firm has agreed to**, not a catch-all:
this file asserts that everything else resolves to a number, and that a new item
arriving without one fails here rather than quietly joining the fallback.

**WHAT IT FOUND WHEN FIRST RUN: nothing, and that was the answer.** The first
scan reported fifteen unpriced items and every one was the checker's fault --
`per_form.forms.*` inherit a $50 default from their parent and are priced, and
`assumed.*` are gates (`when`, `trigger`, `beyond`) rather than priced items at
all. Corrected, the real count of accidentally-unpriced items in the schedule is
**zero**. The rule the firm described was already how the file worked; what was
missing was anything that would keep it true.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pricing  # noqa: E402

#: The complete set of work billed at the hourly rate instead of a fixed price.
#: Adding to this is a pricing decision: it says the firm has chosen NOT to set
#: a price for something, which is different from not having got to it yet.
DELIBERATELY_HOURLY = {
    "keyed_brokerage", "foreign_interest", "notice", "officer_pay", "cleanup",
}

#: Keys whose presence means "this resolves to money".
PRICE_KEYS = ("amount", "tiers", "rate")

#: Branches that describe WHEN work happens, not what it costs. `assumed.*`
#: gates carry `when`/`trigger`/`beyond`; the phrase and wording registries carry
#: sentences. Walking into them and calling every label unpriced is exactly the
#: false positive that made the first version of this file report fifteen
#: problems that were not there.
NOT_PRICE_BRANCHES = {"assumed", "phrases", "wording", "hourly", "interview",
                      "questions", "copy", "labels"}


@pytest.fixture(scope="module")
def schedule():
    return pricing.load()


def _unpriced(node, path="", inherited=False):
    """Every labelled item that resolves to no money at all.

    `inherited` carries down whether an ancestor supplied a default amount --
    `per_form` sets $50 and its forms override it individually, so a form
    without its own `amount` is priced, not unpriced. Missing that is what
    produced six false positives on the first run.
    """
    found = []
    if isinstance(node, dict):
        here = inherited or any(k in node for k in PRICE_KEYS)
        if "label" in node and not any(k in node for k in PRICE_KEYS) and not inherited:
            found.append(path)
        for key, value in node.items():
            if path == "" and key in NOT_PRICE_BRANCHES:
                continue
            found += _unpriced(value, f"{path}.{key}" if path else key, here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += _unpriced(value, f"{path}[{i}]", inherited)
    return found


# ── the guard ────────────────────────────────────────────────────────────────

def test_nothing_is_unpriced_by_accident(schedule):
    """THE GUARD. A new item added without a price fails here.

    Before the fallback rule, such an item stopped the estimate rendering and
    somebody had to set a price. Now it would render as hourly, so this is the
    thing that notices instead.
    """
    unpriced = _unpriced(schedule)
    assert not unpriced, (
        f"{len(unpriced)} item(s) in the fee schedule resolve to no price:\n  "
        + "\n  ".join(unpriced)
        + "\n\nEither give it an amount, or -- if it is genuinely hourly work --"
          " add it to `hourly.situations` AND to DELIBERATELY_HOURLY here, which"
          " is a pricing decision and the firm's to make."
    )


def test_the_hourly_fallback_is_a_closed_set_the_firm_agreed_to(schedule):
    """A catch-all default is not a default, it is a way to stop noticing.

    The five below are what the firm has accepted as billed-by-the-hour. A
    sixth appearing means somebody chose the fallback instead of a price, and
    that is a decision, not an implementation detail.
    """
    assert set(schedule["hourly"]["situations"]) == DELIBERATELY_HOURLY


def test_everything_hourly_is_billed_at_the_rate_and_nothing_else_is(schedule):
    """The fallback resolves to the standard rate -- $175 as of 7 September
    2026 -- and reads it from the schedule rather than repeating it here."""
    rate = schedule["basis"]["rate"]
    for name in sorted(DELIBERATELY_HOURLY):
        line = pricing.hourly_line(name, 1)
        assert line["Amount"] == pricing.m.money(rate), (
            f"{name} does not bill at the standard rate")
        assert "hour" in line["Detail"], f"{name} does not say it is hourly"


def test_an_hourly_line_says_it_is_hourly_on_its_face(schedule):
    """A client reading the estimate must be able to tell that a line is time,
    not a fixed price. A fallback that looks like a quote is the failure."""
    detail = pricing.hourly_line("cleanup", 2)["Detail"]
    assert "hour" in detail
    assert str(schedule["basis"]["rate"]) in detail, (
        "the rate a client will be billed at is not on the line")


# ── the worklist half of the rule ────────────────────────────────────────────

def test_the_fallback_list_is_a_worklist_and_says_so(schedule):
    """*"The goal would be to establish a price."* Anything sitting in the
    hourly set is work with no price yet, and the schedule has to say that where
    somebody editing it will read it -- not only in a test."""
    text = (Path(pricing.SCHEDULE)).read_text(encoding="utf-8")
    assert "the goal would be to establish a price" in text.lower(), (
        "the rule is enforced but not written down where an editor sees it")
    assert "WORKLIST" in text, "nothing says the fallback list is not a resting place"


def test_the_notice_entry_is_the_rule_contradicting_a_decision(schedule):
    """THE LIVE CASE, asserted so it cannot be quietly resolved either way.

    On 26 August 2026 the firm ruled that notices belong in a separate letter
    engagement -- explicitly NOT hourly work. No price was ever set for that
    engagement. So the fallback bills a notice hourly, which is the default
    working correctly AND overriding a decision at the same time.

    This is not a bug to fix in code. It is the strongest argument for the
    second half of the firm's own rule, and it stays visible until they set a
    price or reverse the ruling.
    """
    notice = schedule["hourly"]["situations"]["notice"]
    assert notice.get("on_price_page") is False, (
        "the notice line is advertised again -- the 26 August ruling was reversed "
        "and this test should be too")
    assert notice.get("interim_until"), (
        "nothing records that this is a fallback awaiting a real price")
