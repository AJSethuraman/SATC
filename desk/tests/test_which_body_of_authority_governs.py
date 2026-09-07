"""A publisher that ties out can still be the wrong body of authority.

THE INCIDENT, 7 September 2026, and it is the firm's own test that found it.
They asked *"how do i know if a lease should be booked as an asset"*. Every desk
refused `authority_absent`, so the searcher ran — and came back with four
passages off irs.gov that TIED OUT: re-fetched from the publisher, matched
character for character, one occurrence each. It recommended admitting them.

Every check passed. All four were about the TAX question — whether a lease is
deducted as rent or capitalised as a conditional sale. The firm asked the BOOK
question, which is US GAAP. The firm:

    "you don't check the IRS website for coding tips"

NOTHING COULD TELL. A desk knew its subjects and its sources and never knew which
BODY of authority it spoke for, so a competent search in the wrong universe was
indistinguishable from a competent search in the right one — and `authority_absent`
told the reader *"go and find the rule"* when the truthful refusal was *"this is
not a tax question."*

The fix is a map the firm writes once rather than a source list they curate:
*"i'm trying to avoid a million desk creations which means i always don't want to
have to personally find every possible source."* Tier follows the publisher.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

sys.path.insert(0, str(HERE / "tools"))

import domains                                              # noqa: E402
import record                                               # noqa: E402
import search_run                                           # noqa: E402
import tieout                                               # noqa: E402
import searching                                            # noqa: E402

LEASE = "how do i know if a lease should be booked as an asset"


@pytest.fixture(scope="module")
def maps():
    return domains.load()


# ── the map itself ───────────────────────────────────────────────────────────

def test_the_real_map_parses_and_names_a_body(maps):
    assert maps, "no domains; the map is what makes a tier mean anything"
    for d in maps:
        assert d.body and d.publishes and d.fires_on
        assert not d.body.endswith(("the", "and", "of", "through")), (
            f"{d.name}'s body reads {d.body!r} — a field truncated mid-sentence")


def test_a_wrapped_field_is_read_to_the_end_of_the_field():
    """THE BUG THIS CAUGHT ON ITSELF. `**Body:**` wraps in the real map, and the
    first parser read to the end of its first LINE — so a refusal printed
    "the Financial Accounting Standards Board, through the Accounting", naming a
    body that does not exist. Silent, and only in prose a person reads."""
    got = domains.parse(
        "## x · About\n\n**Body:** the Financial Accounting Standards Board, "
        "through the Accounting\nStandards Codification\n\n"
        "**Publishes:** fasb.org\n\n**Fires on:** gaap\n")
    assert got[0].body.endswith("Standards Codification")


@pytest.mark.parametrize("text,why", [
    ("## x · About\n\n**Body:** b\n\n**Fires on:** w\n", "no publisher"),
    ("## x · About\n\n**Body:** b\n\n**Publishes:** h.gov\n", "fires on nothing"),
    ("# nothing here\n", "an empty map"),
    ("## x · A\n\n**Body:** b\n\n**Publishes:** h.gov\n\n**Fires on:** w\n"
     "\n## x · B\n\n**Body:** c\n\n**Publishes:** i.gov\n\n**Fires on:** v\n",
     "a domain defined twice"),
])
def test_a_map_that_cannot_be_trusted_refuses_rather_than_defaults(text, why):
    with pytest.raises(domains.DomainError):
        domains.parse(text)


# ── tier follows the publisher, which is the part that scales ────────────────

def test_the_body_that_publishes_its_own_text_is_primary(maps):
    tax = next(d for d in maps if d.name == "federal-tax")
    assert domains.tier_for("https://www.ecfr.gov/current/title-26", tax) == "primary"


def test_a_publisher_nobody_listed_is_tertiary_not_primary(maps):
    """THE SAFE DIRECTION. An unknown host helps you FIND the authority and can
    never be the authority — so an unrecognised publisher must fall to tertiary
    rather than inherit the tier of the domain it was found in."""
    tax = next(d for d in maps if d.name == "federal-tax")
    for host in ("pwc.com", "somebodysblog.example", "taxnotes.com"):
        assert domains.tier_for(host, tax) == "tertiary"
        assert not domains.governs(host, tax)


def test_a_registered_domain_covers_its_subdomains_and_not_its_lookalikes(maps):
    gaap = next(d for d in maps if d.name == "us-gaap")
    assert domains.tier_for("https://asc.fasb.org/842", gaap) == "primary"
    assert domains.tier_for("https://notfasb.org/842", gaap) == "tertiary", (
        "a lookalike host inherited the real one's tier; the boundary is a dot")


def test_a_body_that_both_governs_and_explains_stays_primary(maps):
    """irs.gov publishes the regulations AND its own plain-English guides, so it
    is listed in both places. Checking `explains` first would demote the
    regulations to secondary, which is why the order in `Domain.tier` is
    load-bearing rather than incidental."""
    tax = next(d for d in maps if d.name == "federal-tax")
    assert domains.tier_for("https://www.irs.gov/publications/p583", tax) == "primary"


# ── classification, and what it refuses to do ────────────────────────────────

def test_the_firms_lease_question_is_a_gaap_question(maps):
    v = domains.classify(LEASE, maps)
    assert v and v.domain.name == "us-gaap", (
        f"the question that produced the defect classifies as "
        f"{v.domain.name if v else None}")


def test_the_irs_cannot_settle_it(maps):
    v = domains.classify(LEASE, maps)
    assert not domains.governs("https://www.irs.gov/faqs/x", v.domain), (
        "the exact hit the searcher proposed is still competent")


def test_a_question_about_nothing_gets_no_domain_rather_than_a_guess(maps):
    assert not domains.classify("what is the best pizza in cleveland", maps)
    assert domains.classify("", maps).domain is None


def test_whole_words_only(maps):
    """The same rule SUBJECTS.md matches on, for the same recorded reason:
    substring matching once made "extension" fire on "extensive"."""
    tax = next(d for d in maps if d.name == "federal-tax")
    assert "basis" in tax.fires_on
    assert not domains.classify("the basiswerk is done", maps).matched


def test_a_multi_word_entry_matches_as_a_phrase(maps):
    gaap = next(d for d in maps if d.name == "us-gaap")
    assert "balance sheet" in gaap.fires_on
    assert "balance sheet" in domains.classify("is it on the balance sheet",
                                               maps).matched
    assert "balance sheet" not in domains.classify(
        "what is the bank balance", maps).matched


# ── the straddle, which is the half that is easy to get wrong ────────────────

def test_a_lease_question_straddles_and_says_so(maps):
    """A lease IS taxed and IS booked. `classify` orders by how many words
    fired, and that is a weak signal doing a strong job — so the straddle is
    surfaced rather than resolved, and a caller that answers one half without
    saying the other exists is answering half a question confidently."""
    v = domains.classify(LEASE, maps)
    assert v.straddles
    assert [d.name for d in v.bodies] == ["us-gaap", "federal-tax"]


def test_a_single_domain_question_does_not_straddle(maps):
    v = domains.classify("can i deduct the estimated tax withholding", maps)
    assert v and not v.straddles and len(v.bodies) == 1


# ── the gate where the defect actually happened ──────────────────────────────

def _tied(url, citation="X 1", text="words"):
    """A candidate that has already passed every check the searcher makes:
    re-fetched from the publisher, matched character for character, once. That
    is the point — the defect was not a failed check, it was four passed ones."""
    return searching.Candidate(
        citation=citation, text=text, kind="rule", query="",
        found_at=url, fetched_from=url,
        verdict=searching.TIED, occurrences=1, checked="2026-09-07",
        source_id="")


def test_dispose_refuses_a_tied_passage_from_the_wrong_body(maps):
    import searching
    desk = record.load(HERE / "desks" / "capitalization-and-de-minimis")
    gaap = next(d for d in maps if d.name == "us-gaap")

    what, why = searching.dispose(
        _tied("https://www.irs.gov/faqs/x"), desk, gaap)
    assert what == searching.REFUSE
    assert "does not settle us-gaap" in why
    assert "Standards Codification" in why, "the body is truncated again"


def test_the_same_passage_is_proposed_when_the_domain_is_right(maps):
    """THE OTHER HALF, and the one that proves the gate is not just a blanket
    no. Identical candidate, identical desk — only the question's domain
    differs, and the disposal flips."""
    import searching
    desk = record.load(HERE / "desks" / "capitalization-and-de-minimis")
    tax = next(d for d in maps if d.name == "federal-tax")

    what, _ = searching.dispose(_tied("https://www.irs.gov/faqs/x"), desk, tax)
    assert what != searching.REFUSE


def test_no_domain_behaves_exactly_as_before(maps):
    """A caller that does not classify is NOT silently protected. Passing None
    must leave the old behaviour untouched, or the gate becomes a thing that
    quietly changes results depending on whether somebody remembered it."""
    import searching
    desk = record.load(HERE / "desks" / "capitalization-and-de-minimis")
    assert (searching.dispose(_tied("https://www.irs.gov/faqs/x"), desk, None)
            == searching.dispose(_tied("https://www.irs.gov/faqs/x"), desk))


def test_a_refusal_says_where_the_passage_would_have_been_competent(maps):
    """Refusing flat throws away that the IRS passages ARE sound law on the tax
    half. Reporting a searched question as nothing-found is a second wrong
    answer, so the straddle rides along into the refusal."""
    import searching
    desk = record.load(HERE / "desks" / "capitalization-and-de-minimis")
    gaap = next(d for d in maps if d.name == "us-gaap")
    tax = next(d for d in maps if d.name == "federal-tax")

    _, why = searching.dispose(_tied("https://www.irs.gov/faqs/x"), desk,
                               gaap, (tax,))
    assert "federal-tax half" in why


def test_the_firms_own_search_now_refuses_end_to_end(tmp_path, monkeypatch):
    """RUN, NOT DESCRIBED. The passage the searcher recommended admitting is fed
    back through the whole tool and must come out refused.

    THE FIRST VERSION OF THIS TEST PROVED ITSELF. It passed an empty
    `proposals` list and asserted nothing was proposed — true of any code, gate
    or no gate, and it stayed green when the gate was mutated out. A real
    proposal is fed in now, with the publisher fetch replaced so the suite stays
    offline: the tie-out must SUCCEED, so that what refuses it is the domain and
    not a failed fetch.
    """
    import json

    words = "You must first determine whether your agreement is a lease"
    monkeypatch.setattr(search_run, "transport", lambda url: tieout.Fetched(
        words, url, "", len(words), "2026-09-07 00:00:00Z"))

    spec = {
        "desk": "capitalization-and-de-minimis", "question": LEASE,
        "reason": "authority_absent", "queries": ["x"],
        "hits": [{"url": "https://www.irs.gov/faqs/x", "title": "t",
                  "snippet": "s", "query": "x"}],
        "proposals": [{"citation": "IRS, Income & Expenses 7",
                       "quoted": words, "kind": "rule",
                       "found_at": "https://www.irs.gov/faqs/x"}],
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    s = search_run.run(json.loads(p.read_text(encoding="utf-8")))

    assert s.findings, "nothing was read; the test would pass on any code"
    assert not s.of(searching.PROPOSE), (
        "a us-gaap question still proposes an irs.gov source")
    why = s.of(searching.REFUSE)[0].why
    assert "does not settle us-gaap" in why, (
        f"refused for the wrong reason: {why}")


def test_that_end_to_end_test_would_propose_without_the_domain(tmp_path, monkeypatch):
    """AND THE OTHER HALF, so the test above cannot pass for the wrong reason.
    Identical input, domain classification removed — it must PROPOSE. Without
    this, a tie-out that silently failed would look exactly like the gate
    working."""
    import json

    words = "You must first determine whether your agreement is a lease"
    monkeypatch.setattr(search_run, "transport", lambda url: tieout.Fetched(
        words, url, "", len(words), "2026-09-07 00:00:00Z"))
    monkeypatch.setattr(search_run.domains, "classify",
                        lambda q, *a, **k: domains.Verdict())

    spec = {
        "desk": "capitalization-and-de-minimis", "question": LEASE,
        "reason": "authority_absent", "queries": ["x"],
        "hits": [{"url": "https://www.irs.gov/faqs/x", "title": "t",
                  "snippet": "s", "query": "x"}],
        "proposals": [{"citation": "IRS, Income & Expenses 7",
                       "quoted": words, "kind": "rule",
                       "found_at": "https://www.irs.gov/faqs/x"}],
    }
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    s = search_run.run(json.loads(p.read_text(encoding="utf-8")))
    assert s.of(searching.PROPOSE), (
        "it refuses even with no domain, so the gate is not what refused it")
