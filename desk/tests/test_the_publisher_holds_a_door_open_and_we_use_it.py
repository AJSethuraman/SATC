"""eCFR through the API its own refusal page names — free, keyless, honest.

THE FIRM, 8 September 2026, after #344 measured what an honest browser costs at
that publisher: *"I'm totally open to API pulls"*, with one condition — *"if
there is any cost to using it, it's not just public I'm not sure I want to use
it"* — and then *"if we can use an API that's free and verify the stuff coming
out or whatever why not but either way, yeah we want both."*

MEASURED BEFORE ANYTHING WAS BUILT ON IT, which is the condition they set: no
key, no cost, no sign-up, HTTP 200 to a plain client with no browser user-agent.
That measurement is a live fact about the world and cannot be a test — this
suite has no network. What IS tested here is everything decided by the code:
the citation parsed, the URL built, the two ways this publisher refuses a naive
client, and the markup rule that took three regulations from DIFFERS to TIED.

IT IS A TRANSPORT AND NOT A SHORTCUT PAST VERIFICATION. Everything it returns
goes through `proving.prove_passage` exactly as a browser fetch does, and one
test below pins that: an API that answers 200 about the wrong section is refused
like anything else.

WHAT THE LIVE RUN FOUND, recorded here because no test can reach it:

    19 of 19 distinct eCFR sources across the seven desks tie out live
    through this API, sub-second, with the passage present.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ecfr                                                 # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                  # noqa: E402


def _source(url="https://www.ecfr.gov/current/title-26/section-1.263(a)-2"):
    return record.Source(
        id="S1", title="eCFR", tier="primary", access="public_fetch",
        may_store="full_text", checked="2026-09-08",
        citation_prefix="26 CFR 1.263(a)-2", url=url)


# ── the citations these desks actually cite ────────────────────────────────

def test_every_ecfr_citation_the_desks_hold_parses():
    """READ OFF THE RECORD, not a list typed here. A section shape that stops
    parsing is a source that silently loses its API route, and the desks carry
    the awkward ones: `1.274-5T`, `1.280F-6`, `1.6050W-1`, `1.263(a)-2`."""
    seen = 0
    for d in [CORPUS]:
        for s in record.load(d).sources:
            if not ecfr.serves(s):
                continue
            seen += 1
            title, part, section = ecfr.parse(s.citation_prefix)
            assert title == 26 and part == "1", s.citation_prefix
            assert section in s.citation_prefix, s.citation_prefix
    assert seen >= 19, f"only {seen} eCFR sources found; the fixture is thin"


@pytest.mark.parametrize("citation,section", [
    ("26 CFR 1.162-3", "1.162-3"),
    ("26 CFR 1.263(a)-2", "1.263(a)-2"),      # the section's OWN parenthesis
    ("26 CFR 1.274-5T", "1.274-5T"),          # a temporary regulation
    ("26 CFR 1.280F-6", "1.280F-6"),          # a letter inside the number
    ("26 CFR 1.6050W-1", "1.6050W-1"),
])
def test_the_shapes_that_look_like_typos_and_are_not(citation, section):
    assert ecfr.parse(citation)[2] == section


def test_a_subparagraph_is_not_a_section():
    """A desk cites the paragraph it relies on; the API serves whole sections,
    and `proving` finds the paragraph inside what comes back."""
    assert ecfr.parse("26 CFR 1.263(a)-2(d)(1)")[2] == "1.263(a)-2"


def test_a_citation_this_publisher_cannot_serve_refuses_rather_than_guessing():
    """21 of the 33 sources these desks cite are eCFR. The rest are
    uscode.house.gov and IRS publications, and this module reaches neither —
    a URL invented for one of those would fetch something real and wrong."""
    for other in ("IRS Pub. 583", "26 USC 6041", "ASC 842-20-25-1", ""):
        with pytest.raises(ecfr.NotOnThisPublisher):
            ecfr.parse(other)


def test_it_only_claims_its_own_publisher():
    assert ecfr.serves(_source())
    assert ecfr.serves("https://ecfr.gov/x")
    assert not ecfr.serves("https://www.irs.gov/pub/x")
    # A LOOKALIKE HOST IS NOT THE PUBLISHER. The boundary is a dot.
    assert not ecfr.serves("https://notecfr.gov/x")


# ── the URL, and the two refusals a naive client earns ────────────────────

def test_the_url_names_the_section_and_the_date():
    url = ecfr.url_for("26 CFR 1.263(a)-2(d)(1)", "2026-09-03")
    assert url.startswith(ecfr.API + "/full/2026-09-03/title-26.xml")
    assert "part=1" in url and "section=1.263(a)-2" in url


def test_the_date_is_asked_for_rather_than_assumed():
    """A URL BUILT WITH TODAY'S DATE ANSWERS 404, and today is the date every
    first implementation reaches for. Measured 8 September 2026: `2026-09-08`
    404, `2026-09-03` 200. So the date comes from eCFR's own `titles.json`."""
    ecfr._DATES.clear()
    asked = []

    def opener(url):
        asked.append(url)
        return '{"titles":[{"number":26,"up_to_date_as_of":"2026-09-03"}]}'

    assert ecfr.current_date(26, opener=opener) == "2026-09-03"
    assert asked == [ecfr.API + "/titles.json"]
    # ASKED ONCE PER PROCESS. The answer cannot change while a run is going on,
    # and a request per section would triple the traffic for nothing.
    assert ecfr.current_date(26, opener=opener) == "2026-09-03"
    assert len(asked) == 1
    ecfr._DATES.clear()


def test_a_title_with_no_date_refuses_rather_than_inventing_one():
    ecfr._DATES.clear()
    with pytest.raises(ecfr.NotOnThisPublisher):
        ecfr.current_date(26, opener=lambda u: '{"titles":[{"number":26}]}')
    with pytest.raises(ecfr.NotOnThisPublisher):
        ecfr.current_date(99, opener=lambda u: '{"titles":[]}')
    ecfr._DATES.clear()


# ── the markup rule that took three sources from DIFFERS to TIED ──────────

def test_an_inline_tag_leaves_no_space_behind():
    """THE BUG THAT WOULD HAVE BEEN REPORTED AS THREE MOVED REGULATIONS.

    eCFR sets run-in headings in italics, so the real markup is

        <P>(a) <I>In general</I>—(1) <I>Non-incidental materials…</I> Except…

    Replacing every tag with a space turns `In general—(1)` into
    `In general —(1)`, and the stored passage then fails by ONE CHARACTER.
    Three of nineteen sources came back DIFFERS on the first live run for
    exactly this — and DIFFERS withdraws a citation and tells a preparer to
    retire it. The #344 defect in a new costume: a fault of ours presented as a
    finding about the publisher.
    """
    xml = "<P>(a) <I>In general</I>—(1) <I>Non-incidental supplies.</I> Except</P>"
    assert ecfr.as_text(xml) == "(a) In general—(1) Non-incidental supplies. Except"


def test_a_block_tag_still_separates_words():
    """The other half, and without it this rule would run sentences together."""
    assert ecfr.as_text("<P>first.</P><P>second.</P>") == "first. second."
    assert ecfr.as_text("<HEAD>§ 1.162-3 Materials.</HEAD><P>(a) Text</P>") == (
        "§ 1.162-3 Materials. (a) Text")


def test_the_markup_rule_is_read_off_the_real_document():
    """`_INLINE` is a hand-typed list, so it can drift from what eCFR sends.
    These are the tags title 26 actually uses; only the emphasis pair is
    inline, and a session that adds one has to say why here."""
    assert set(ecfr._INLINE) >= {"I", "E"}
    for block in ("P", "HEAD", "HED", "PSPACE", "EXAMPLE", "DIV8"):
        assert block not in ecfr._INLINE, f"{block} separates words"


# ── it is a transport, and verification still runs on what it returns ─────

def test_what_comes_back_is_still_proved(tmp_path):
    """*"and verify the stuff coming out"*. An API answering 200 is not
    evidence that it answered about the right thing."""
    passage = "amounts paid to acquire or produce a unit of real property"
    served = ecfr.Reply(text=f"§ 1.263(a)-2 ... {passage} ... more",
                        url="https://www.ecfr.gov/api/x")
    proof = proving.prove_passage(
        "26 CFR 1.263(a)-2(d)(1)", passage, _source(), lambda s, c: served)
    assert proof.verdict == proving.TIED
    assert proof.matched_chars == len(passage)


def test_an_api_that_answers_about_the_wrong_section_is_refused():
    """The #344 guard applies here too: withdrawing a citation needs positive
    evidence that this IS the document asked for."""
    served = ecfr.Reply(text="§ 9.999-9 An entirely different rule.",
                        url="https://www.ecfr.gov/api/x")
    proof = proving.prove_passage(
        "26 CFR 1.263(a)-2(d)(1)", "amounts paid to acquire",
        _source(), lambda s, c: served)
    assert proof.verdict == proving.COULD_NOT
    assert "does not mention" in proof.note


def test_the_reply_is_the_shape_proving_reads():
    r = ecfr.Reply(text="hello", url="https://www.ecfr.gov/api/x")
    assert r.text == "hello" and r.nbytes == 5 and r.body == b"hello"


def test_nothing_reaches_the_network_by_importing_this():
    """`comparing.py` records what happened the one time a front-door module
    could reach a fetcher by import: `http.client` pulls in `ssl`, and this
    suite replaces the socket layer, so every test in an unrelated file died
    inside `ssl.py`. IT PARSES THE IMPORTS rather than scanning the prose —
    this file's own docstring says the word `network`."""
    import ast

    tree = ast.parse((HERE / "ecfr.py").read_text(encoding="utf-8"))
    top = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            top.append(node.module or "")
    for name in top:
        assert not name.startswith(("urllib", "http", "ssl", "socket")), (
            f"{name} is imported at module level and reaches the network")
