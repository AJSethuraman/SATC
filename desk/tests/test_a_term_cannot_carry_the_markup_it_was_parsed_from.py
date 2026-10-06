"""No term in any domain's vocabulary carries the Markdown it was parsed out of.

THE INCIDENT. On 9 September 2026 Forge-Occam ran a real year-end close on the
installed plugin and reported, among six findings, that the bare stem `deduct`
reached no domain at all:

    "can we deduct it?"   -> NOTHING
    "is it deductible?"   -> federal-tax

The cause was one line of `DOMAINS.md` carrying its own label twice:

    **Fires on:** **Fires on:** deduct, deducted, ...

so the first term in the tuple was the literal string
`'**fires on:** deduct'` -- a term no question can ever contain -- and the word
`deduct` was gone from the vocabulary. It went in with `810e5dcb`, the commit
that REMOVED eighteen wrongly-added income words: the line was retyped by hand
and the label was pasted with it. It was live for a day.

WHY THIS TEST IS NOT `assert "deduct" in fires_on`. That assertion would have
caught this one slip and no other. The defect is not that `deduct` went missing;
it is that **a parser handed a term its own delimiter and nothing objected**, and
the next hand-edit of any label on any line does it again somewhere else. So the
check is over the whole vocabulary of every domain, and it is about shape rather
than membership: a term is words, and a term carrying `*`, `:` or a Markdown
label is a parse that leaked.

Behaviour: prevent rather than detect. `deduct` being back is asserted at the
bottom as the incident's own case, but the test above it is the one that has to
hold for terms nobody has thought of yet.
"""

import pytest

import domains


MARKUP = ("*", "_", "`", "#", "[", "]", "|", ":")


def _every_term():
    for domain in domains.load():
        for term in domain.fires_on:
            yield domain.name, term


def test_no_term_carries_markdown():
    """A vocabulary term is words. Anything else is the file leaking into it."""
    leaked = [
        (domain, term)
        for domain, term in _every_term()
        if any(ch in term for ch in MARKUP)
    ]
    assert not leaked, (
        "these terms carry the markup of the line they were parsed out of, so "
        "no question can ever contain them and the word they were meant to be "
        f"is silently absent from the vocabulary: {leaked}"
    )


def test_no_term_repeats_its_own_label():
    """The exact shape of the incident: the label pasted in front of the term."""
    carrying = [
        (domain, term)
        for domain, term in _every_term()
        if "fires on" in term.lower()
    ]
    assert not carrying, (
        "a term still has its `**Fires on:**` label attached -- the line in "
        f"DOMAINS.md carries the label twice: {carrying}"
    )


def test_no_term_is_empty_or_padded():
    """An empty term matches everything or nothing depending on the matcher, and
    a padded one silently never matches. Neither is a vocabulary entry."""
    wrong = [(d, repr(t)) for d, t in _every_term() if t != t.strip() or not t]
    assert not wrong, f"terms that are empty or carry whitespace: {wrong}"


@pytest.mark.parametrize(
    "question, expected",
    [
        # The pair Forge-Occam measured, and ONLY that pair -- both sentences
        # are theirs, not invented here. The second passed throughout; it is
        # present so a fix that broke it would be caught too.
        ("can we deduct it?", "federal-tax"),
        ("is it deductible?", "federal-tax"),
    ],
)
def test_the_reported_pair_both_reach_the_domain(question, expected):
    verdict = domains.classify(question)
    assert verdict, f"{question!r} reaches no domain"
    assert verdict.domain.name == expected
