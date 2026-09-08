"""An accountant writing about what already happened lost the domain gate.

FOUND IN THE FIRST LIVE CLOSE, 8 September 2026, Sarcia Services. Forge-Occam
asked three questions and `domain` came back **None on two of them**. It
diagnosed the one it could:

    "are those deducted or capitalized?"      -> no domain
    "do we deduct or capitalize them?"        -> federal-tax

Same question. Past participle versus infinitive. `DOMAINS.md` fires on
`deduct`, `deductible`, `deduction`, `capitalize`, `capitalise` — and not on
`deducted` or `capitalized`. **The past participle is the form somebody writes
when describing a transaction that has already happened**, which is every line
in a close.

WHY IT MATTERED LESS THAN IT LOOKS, AND WHY THAT IS NOT COMFORT. With no domain,
the wrong-body-of-authority gate is not watching at all — the check that exists
because a US GAAP lease question was answered from IRS Pub. 463 on 7 September.
It did no harm that night only because every desk reached happened to be a tax
desk. The gate was off and the room happened to be empty.

`expense`/`expensed` has the identical hole and is added with them.
"""
from __future__ import annotations

import domains

#: The pairs an accountant actually types, infinitive and past participle.
PAIRS = [
    ("do we deduct or capitalize them?", "are those deducted or capitalized?"),
    ("do we expense this?", "was this expensed?"),
    ("do we depreciate it?", "was it depreciated?"),
    ("do we amortize it?", "was it amortized?"),
]


def _domain(question: str):
    """`classify` returns a Verdict; None means no domain fired at all."""
    return domains.classify(question).domain


def test_the_two_forms_reach_the_same_domain():
    """Neither form may be silent where the other fires."""
    silent = []
    for infinitive, participle in PAIRS:
        a, b = _domain(infinitive), _domain(participle)
        if a and not b:
            silent.append((participle, a.name))
    assert not silent, (
        "these are the words a close is written in and they reach no domain, "
        "so the wrong-body gate is not watching: "
        + "; ".join(f"{q!r} (its infinitive reaches {d})" for q, d in silent))


def test_the_measured_case_from_the_sarcia_close():
    """The exact question Forge-Occam asked, which came back `domain: None`."""
    assert _domain(
        "a sole proprietor bought hand tools for the trade, a few hundred "
        "dollars each — are those deducted or capitalized?"), (
        "the question that ran the first live close still reaches no domain")
