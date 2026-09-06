"""The link on a source must be the page its text is actually on.

RIGHT TEXT, WRONG LINK — the tie-out's headline finding on 6 September 2026, and
the one no test in this repository could have made. The rewards desk recorded a
single source for four Code sections:

    S2 · Internal Revenue Code §§ 6041, 6041A, 6050W, 6071
    Url: ...granuleid:USC-prelim-title26-section6041...

reasoning that "the four sections are one document reached one way". Every one of
the six stored passages is verbatim what the publisher prints. But that URL is
the granule for § 6041 and serves ONLY § 6041: the text for 6041A, 6050W and 6071
is absent from it, longest matching prefix three characters. A reader following
the citation for three of the four landed on a page that did not contain it.

WHY NOTHING CAUGHT IT. Every other check reads the same stored files, so a
passage filed under the wrong source is stored wrong, served wrong and asserted
wrong together. Only opening the link could see it — and the tie-out did not see
it either, at first, because `tieout._statute_url` REWRITES the section token per
citation before fetching. The checker had been quietly reaching the right pages
while the record pointed at the wrong one, and the two never compared notes.

SO THIS COMPARES THEM, and it needs no network to do it. `_statute_url` is pure
string logic: given a source URL and a citation it says which page that citation
is really on. Where that differs from the URL the source records, the record is
lying about where its own text lives.

It is not the whole of what a tie-out does — it cannot tell whether the text at
that page still says what we stored, which is the fetch's job. It is the half
that can be checked on every commit, and it is the half that was wrong.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
import tieout                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402


def _desks():
    for d in sorted(DESKS.iterdir()):
        if (d / "SOURCES.md").is_file():
            yield record.load(d)


def test_every_statute_passage_is_on_the_page_its_source_names():
    """The check that the record and the checker agree about the link.

    Only the House US Code publishes one section per page in a way a URL can be
    derived for, which is why this is scoped to it — and it is where the defect
    was. A source whose URL is not rewritten per citation is one page for all
    its passages, and this says nothing about it.
    """
    wrong = []
    for desk in _desks():
        for p in desk.passages:
            source = desk.source(p.source_id)
            if "uscode.house.gov" not in source.url:
                continue
            real = tieout._statute_url(source.url, p.citation)
            if real != source.url:
                wrong.append(
                    f"{desk.name}/{p.citation}: filed under {source.id}, whose "
                    f"recorded Url is\n      {source.url}\n    but its text is "
                    f"published at\n      {real}")
    assert not wrong, (
        "these passages are verbatim correct and their citations link to a page "
        "that does not carry them. Nothing served is wrong; a reader checking it "
        "lands nowhere:\n  " + "\n  ".join(wrong))


def test_the_check_can_tell_a_wrong_link_from_a_right_one():
    """The guard's own guard. `_statute_url` returning the URL unchanged for
    everything would make the test above pass over any record at all, and that
    is precisely how it would rot: silently, while reading green."""
    base = ("https://uscode.house.gov/view.xhtml?req=granuleid:"
            "USC-prelim-title26-section6041&num=0&edition=prelim")
    assert tieout._statute_url(base, "26 USC 6041(a)") == base
    for citation, token in (("26 USC 6041A(a)", "section6041A"),
                            ("26 USC 6050W(e)", "section6050W"),
                            ("26 USC 6071(c)", "section6071")):
        moved = tieout._statute_url(base, citation)
        assert moved != base and token in moved, (citation, moved)


def test_a_source_that_names_one_section_holds_only_that_section():
    """The shape the split produced, asserted so it cannot quietly merge back.

    A source covering several sections of one title is the arrangement that
    created the defect: one URL cannot serve them, and the passages underneath
    it inherit a link that is wrong for all but one. Every US Code source on
    every desk now names exactly one section.
    """
    for desk in _desks():
        for source in desk.sources:
            if "uscode.house.gov" not in source.url:
                continue
            mine = [p for p in desk.passages if p.source_id == source.id]
            pages = {tieout._statute_url(source.url, p.citation) for p in mine}
            assert len(pages) <= 1, (
                f"{desk.name}/{source.id} covers {len(pages)} different pages of "
                f"the Code under one recorded Url; its citations cannot all "
                f"resolve: {sorted(pages)}")


def test_the_rewards_desk_holds_the_four_sections_apart():
    """The specific record the firm answered about, named rather than swept.

    "Split into four" — fourth docket, 6 September 2026. Four sources, four
    URLs, and the prefixes have to stay disjoint under `from_source`, because
    `26 USC 6041` is a string prefix of `26 USC 6041A` and only the
    non-alphanumeric boundary rule keeps every 6041A citation off S2.
    """
    desk = record.load(DESKS / "rewards-and-information-returns")
    code = {s.id: s for s in desk.sources if "uscode.house.gov" in s.url}
    assert len(code) == 4, f"{sorted(code)} — the four sections are not four sources"
    assert len({s.url for s in code.values()}) == 4, "two share a Url"

    for citation, expect in (("26 USC 6041(a)", "26 USC 6041"),
                             ("26 USC 6041A(a)", "26 USC 6041A"),
                             ("26 USC 6050W(e)", "26 USC 6050W"),
                             ("26 USC 6071(c)", "26 USC 6071")):
        hit = [s.citation_prefix for s in code.values()
               if record.from_source(citation, s.citation_prefix)]
        assert hit == [expect], (
            f"{citation} resolves to prefixes {hit}, not exactly [{expect!r}]. "
            f"Two sources claiming one citation is how a 6041A passage ends up "
            f"filed under § 6041 again")
