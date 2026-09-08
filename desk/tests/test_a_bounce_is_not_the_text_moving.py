"""Landing somewhere else is not the publisher rewriting the page.

THE INCIDENT, 8 September 2026, found on the firm's own machine and not by
anything here. `ecfr.gov` does not block this repository's tie-out by egress —
it blocks it by USER-AGENT. The shipped UA (`tools/tieout.py`,
`satc-desk-tieout`) is redirected to an interstitial on
`unblock.federalregister.gov` which answers **HTTP 200** with 10,596 bytes that
are not the regulation. The same URL under a browser UA returns 584,798 bytes
with the stored passage present, once.

    UA satc-desk-tieout  -> 10,596 b   unblock page
    UA python-urllib     -> 10,596 b   unblock page
    UA curl              -> 10,596 b   unblock page
    UA Chrome            -> 584,798 b  THE REGULATION

WHY THE 200 IS THE DANGEROUS PART. `prove` turns a network exception into
COULD_NOT, correctly — a network that is down says nothing about whether the
text moved. But a clean 200 carrying the wrong document fell through to DIFFERS,
and `ask.answer` reads DIFFERS as `authority_has_moved` and WITHDRAWS the
answer. The desk that found it:

    "Run a tie-out over the desks today and every primary-authority citation is
     withdrawn as 'the publisher no longer carries it' when nothing has moved."

`authority_has_moved` is a claim ABOUT THE PUBLISHER. Being bounced by a bot
filter is not one — it is a claim about us, and the honest verdict is COULD NOT.

WHAT THIS DOES NOT DECIDE: what user agent this desk announces itself with. That
is the firm's call and is recorded in `docs/DECISIONS-2026-09-08-ELEVENTH.md`,
not settled here. This fix makes the failure HONEST rather than making it go
away, and both fetches above are still wrong today.
"""
from pathlib import Path

import pytest

import engine
import proving
import record

HERE = Path(__file__).resolve().parents[1]
CITATION = "26 CFR 1.263(a)-2(d)(1)"


class _Reply:
    """What a transport hands back, with the landing URL a bounce reveals."""

    def __init__(self, url, text):
        self.status, self.url, self.text = 200, url, text
        self.body = text.encode("utf-8")


@pytest.fixture
def served():
    desk = record.load(HERE / "desks" / "fixed-assets")
    out = engine.serve(engine.Answer(position="capitalized", citation=CITATION),
                       desk, question="we bought a forklift")
    assert isinstance(out, engine.Served)
    return out, desk


BOUNCE = "You have been blocked. Please click below to continue."
REAL = "https://www.ecfr.gov/current/title-26/section-1.263(a)-2"


def test_a_bounce_to_another_host_is_could_not(served):
    out, desk = served
    proof = proving.prove(out, desk, lambda s, c: _Reply(
        "https://unblock.federalregister.gov/interstitial", BOUNCE))
    assert proof.verdict == proving.COULD_NOT


def test_and_it_says_where_it_landed(served):
    """A verdict that does not name the wrong host cannot be diagnosed."""
    out, desk = served
    proof = proving.prove(out, desk, lambda s, c: _Reply(
        "https://unblock.federalregister.gov/interstitial", BOUNCE))
    assert "ecfr.gov" in proof.note and "unblock.federalregister.gov" in proof.note


def test_and_says_the_passage_may_not_have_moved(served):
    """The whole point: this must not read as a finding about the publisher."""
    out, desk = served
    proof = proving.prove(out, desk, lambda s, c: _Reply(
        "https://unblock.federalregister.gov/x", BOUNCE))
    assert "nothing here says whether the passage moved" in proof.note


def test_a_real_rewrite_on_the_right_host_still_differs(served):
    """THE CONTROL, and it is the one that matters. A guard that turned every
    DIFFERS into COULD NOT would make the tie-out say nothing at all."""
    out, desk = served
    proof = proving.prove(out, desk, lambda s, c: _Reply(
        REAL, "the publisher has rewritten this section entirely"))
    assert proof.verdict == proving.DIFFERS


def test_the_real_passage_on_the_right_host_still_ties(served):
    out, desk = served
    passage = record.load(HERE / "desks" / "fixed-assets").passage(CITATION)
    proof = proving.prove(out, desk, lambda s, c: _Reply(REAL, passage.text))
    assert proof.verdict == proving.TIED


def test_a_redirect_within_the_publisher_is_not_a_bounce(served):
    """A publisher moving us to its own canonical URL HAS served us its page —
    http to https, a trailing slash, a rewritten path. Treating that as a bounce
    would break tie-outs on sources that are working perfectly."""
    out, desk = served
    passage = record.load(HERE / "desks" / "fixed-assets").passage(CITATION)
    proof = proving.prove(out, desk, lambda s, c: _Reply(
        "https://ecfr.gov/current/title-26/section-1.263(a)-2/", passage.text))
    assert proof.verdict == proving.TIED, proof.note


def test_a_transport_that_reports_no_url_is_trusted_as_before(served):
    """Not every transport says where it landed. Absence is not a bounce —
    inventing one would make every legacy transport fail."""
    out, desk = served
    passage = record.load(HERE / "desks" / "fixed-assets").passage(CITATION)

    class Silent:
        status, text = 200, passage.text
        body = passage.text.encode("utf-8")

    assert proving.prove(out, desk, lambda s, c: Silent()).verdict == proving.TIED


def test_a_network_failure_is_still_could_not_and_not_a_bounce(served):
    """The pre-existing guard, pinned: an exception says nothing about the text."""
    out, desk = served

    def dead(source, citation):
        raise TimeoutError("no route to host")

    proof = proving.prove(out, desk, dead)
    assert proof.verdict == proving.COULD_NOT
    assert "TimeoutError" in proof.note


def test_an_empty_landing_url_is_unknown_and_not_a_bounce(served):
    """`fetch.Response.url` DEFAULTS TO EMPTY, so this is the common case, not
    an edge one — and it is the case a naive `landed != asked` gets wrong.

    Caught by mutation M38 on 8 September: the first version of this file tested
    a transport with NO `url` attribute, where `getattr` falls back to the
    source's own URL and both the guard and the mutation agree. A transport that
    HAS the field and leaves it blank is the one that separates them."""
    out, desk = served
    passage = record.load(HERE / "desks" / "fixed-assets").passage(CITATION)

    class Blank:
        status, url = 200, ""            # exactly `fetch.Response`'s default
        text = passage.text
        body = passage.text.encode("utf-8")

    assert proving.prove(out, desk, lambda s, c: Blank()).verdict == proving.TIED
