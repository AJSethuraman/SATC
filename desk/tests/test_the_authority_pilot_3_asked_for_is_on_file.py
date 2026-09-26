"""The five sections Sarcia pilot 3's refusals named are on file, and readable.

25 September 2026. Four of the desk's ten refusals named law the corpus did not
hold -- § 1.163 on interest, § 164 on taxes, § 1.461 and § 1.263(a)-4 on a
prepaid subscription, § 1.6001-1 on records -- zero passages each, all free on
ecfr.gov. The firm, the next day: *"i keep saying, over and over, to add
whatever"*. Admitted from the eCFR API issue of 2026-01-01, rules only.

ADMITTING THEM FOUND THREE DEFECTS IN THE READER, each checked here on the exact
markup the publisher served:

  - `<FP>` (a flush paragraph) was never read. § 1.164-1's rule that business
    taxes beyond (a)(1)-(5) are deductible is one; seven more across five
    sections already stored never reached the corpus either.
  - `<I>…intangible</I>s—(1)`: italics closed one word-end early, so the run-in
    was not seen and § 1.263(a)-4 had no reading at all.
  - `<I>Created intangibles—(1) In general.</I>`: the label inside the italics.
"""
from __future__ import annotations

import pathlib
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import extract_ecfr as X                                    # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402


def _outline(tmp_path, body):
    f = tmp_path / "s.xml"
    f.write_text(f"<SECTION>{body}</SECTION>", encoding="utf-8")
    got = {}
    for p in X.outline(f)[0]:
        got.setdefault(p.label, []).append(p.text)
    return {k: " ".join(v) for k, v in got.items()}


def test_a_flush_paragraph_belongs_to_the_parent_of_the_list_above_it(tmp_path):
    got = _outline(tmp_path,
                   "<P>(a) <I>In general.</I> Only the following taxes:</P>"
                   "<P>(1) Real property taxes.</P><P>(2) Sales taxes.</P>"
                   "<FP>In addition, taxes paid in carrying on a trade.</FP>"
                   "<P>(b) Other.</P>")
    assert "In addition, taxes paid in carrying on a trade." not in got["(a)(2)"]
    assert "Only the following taxes" in got["(a)"]
    assert "In addition, taxes paid in carrying on a trade." in got["(a)"]


def test_the_flush_paragraph_is_emitted_on_the_parent(tmp_path):
    f = tmp_path / "s.xml"
    f.write_text("<SECTION><P>(a) <I>In general.</I> Lead.</P><P>(1) One.</P>"
                 "<FP>Flush text.</FP></SECTION>", encoding="utf-8")
    paras = X.outline(f)[0]
    assert ("(a)", "Flush text.") in {(p.label, p.text) for p in paras}


def test_a_flush_paragraph_with_nothing_above_it_is_refused(tmp_path):
    f = tmp_path / "s.xml"
    f.write_text("<SECTION><FP>Orphan.</FP><P>(a) A.</P></SECTION>",
                 encoding="utf-8")
    try:
        X.outline(f)
    except ValueError as e:
        assert "nothing above it" in str(e)
    else:
        raise AssertionError("an orphan flush paragraph was placed somewhere")


def test_italics_closed_one_word_end_early_still_open_the_child(tmp_path):
    got = _outline(tmp_path,
                   "<P>(a) A.</P>"
                   "<P>(b) <I>Capitalization with respect to intangible</I>s—(1) "
                   "<I>In general.</I> A taxpayer must capitalize—</P>"
                   "<P>(i) An amount paid.</P>")
    assert {"(b)", "(b)(1)", "(b)(1)(i)"} <= set(got)


def test_a_label_swallowed_by_the_italics_still_opens_the_child(tmp_path):
    got = _outline(tmp_path,
                   "<P>(a) A.</P>"
                   "<P>(b) <I>Created intangibles—(1) In general.</I> Except as "
                   "provided, a taxpayer must capitalize.</P>"
                   "<P>(2) Second.</P>")
    assert {"(b)", "(b)(1)", "(b)(2)"} <= set(got)


def test_the_repairs_move_fences_never_text():
    for markup in ("<P>(b) <I>Heading intangible</I>s—(1) <I>In general.</I> x</P>",
                   "<P>(d) <I>Created intangibles—(1) In general.</I> x</P>"):
        elem = ET.fromstring(markup)
        plain = " ".join("".join(elem.itertext()).split())
        assert X._plain(X._marked(elem)) == plain


WANTED = {
    "26 CFR 1.6001-1(a)": "shall keep such permanent books of account or records",
    "26 CFR 1.164-1(a)": "In addition, there shall be allowed as a deduction",
    "26 CFR 1.461-1(a)(1)": "Under the cash receipts and disbursements method",
    "26 CFR 1.263(a)-4(f)(1)": "12 months after the first date on which the taxpayer",
    "26 CFR 1.163-8T(a)(3)": "allocated",
}


def test_the_rules_the_refusals_needed_are_stored_word_for_word():
    held = {p.citation: p for p in record.load(CORPUS).passages}
    for citation, words in WANTED.items():
        assert citation in held, f"{citation} is not stored"
        assert words in held[citation].text or any(
            words in p.text for c, p in held.items()
            if c.startswith(citation)), (citation, words)


def test_their_examples_are_not_stored_until_they_can_be_placed():
    """§ 1.163-8T's extractor run filed all eleven of paragraph (c)'s examples
    under (c)(2)(iii). An example cited to the wrong rule is worse than none,
    so S37-S39 hold rules only and say so in SOURCES.md."""
    desk = record.load(CORPUS)
    for sid in ("S35", "S36", "S37", "S38", "S39"):
        held = [p for p in desk.passages if p.source_id == sid]
        assert held, sid
        assert all(p.kind == record.RULE for p in held), sid


def test_a_paragraph_in_pieces_is_emitted_once_with_its_gap_marked(tmp_path):
    """Codex on #398: the flush text became a second `Paragraph` on the
    parent's path, `build()` wrote one heading per piece, and the record
    refused the duplicate citation. One heading per paragraph; text the
    publisher prints after the children joins with the omission mark, so a
    tie-out does not read the two as adjacent."""
    f = tmp_path / "s.xml"
    f.write_text("<SECTION><P>(a) <I>In general.</I> Only these:</P>"
                 "<P>(1) One.</P><P>(2) Two.</P>"
                 "<FP>In addition, the rest.</FP><P>(b) Other.</P></SECTION>",
                 encoding="utf-8")
    got = X.merged(X.outline(f)[0])
    labels = [label for label, _ in got]
    assert labels.count("(a)") == 1
    assert dict(got)["(a)"] == "In general. Only these: [...] In addition, the rest."
