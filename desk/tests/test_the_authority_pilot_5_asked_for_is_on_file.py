"""§ 274(e) and § 1.162-21 are on file, word for word, and the engine cites them.

27 September 2026. In Sarcia pilot 5 the desk answered a streaming-subscription
question from § 1.274-11(a) and could only say its answer was "subject to"
§ 274(e): § 1.274-11(c) lists the nine statutory exceptions by number alone,
and the statute was not on file. In desk trial 1 it could not say whether a
town charge that is a fine is deductible, because § 162(f) and § 1.162-21 were
not on file. The firm's standing instruction: *"add whatever"*.

§ 1.162-21 came through `tools/extract_ecfr.py` like S35-S39. The statute is the
first thing sliced from the House's page since the rewards desk was built, and
`tools/extract_uscode.py` is what slices it -- reusing the two readers that cut
§§ 6041, 6041A, 6050W and 6071, and adding only a paragraph stored in pieces.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import extract_uscode as U                                  # noqa: E402
import judging                                              # noqa: E402
import record                                               # noqa: E402
from build_rewards_desk import html_text                    # noqa: E402
from comparing import ELLIPSIS                              # noqa: E402
from conftest import CORPUS                                 # noqa: E402

# ── the slicer, on the House's own markup ────────────────────────────────────

#: The shape the House serves, cut down: an `<h4>` per heading, a `<p>` per
#: body, a `<span>` cross-reference inside a sentence, and a flush sentence
#: that closes the subsection after its last paragraph.
PAGE = """<html><body>
<div>Text contains those laws in effect on September 25, 2026</div>
<h4 class="subsection-head">(e) Specific exceptions</h4>
<p class="statutory-body">Subsection (a) shall not apply to-</p>
<h4 class="paragraph-head">(1) Food</h4>
<p>Expenses for   food furnished for purposes of <span class="stdref">chapter 24</span> (relating to wages).</p>
<h4 class="paragraph-head">(2) Items</h4>
<p>Expenses made available to the public.</p>
<p class="statutory-body-flush0">For purposes of this subsection, any item is an expense.</p>
<h4 class="subsection-head">(f) Next</h4>
</body></html>"""

SPEC = (
    ("26 USC 1(e)", (("(e) Specific exceptions", "\n(1) Food", 1),
                     ("For purposes of this subsection", "\n(f) ", 1))),
    ("26 USC 1(e)(1)", (("\n(1) Food", "\n(2) Items", 1),)),
    ("26 USC 1(e)(2)", (("\n(2) Items", "\nFor purposes of this subsection", 1),)),
)


@pytest.fixture
def page(tmp_path):
    f = tmp_path / "usc.html"
    f.write_text(PAGE, encoding="utf-8")
    return html_text(f)


def test_a_flush_sentence_is_its_subsections_and_not_the_last_paragraphs(page):
    got = dict(U.sliced(page, SPEC))
    assert got["26 USC 1(e)"] == (
        f"(e) Specific exceptions Subsection (a) shall not apply to- {ELLIPSIS} "
        f"For purposes of this subsection, any item is an expense.")
    assert got["26 USC 1(e)(2)"] == (
        "(2) Items Expenses made available to the public.")


def test_the_slice_changes_nothing_but_whitespace(page):
    """Every segment is a run of the page's own words; a cross-reference inside
    a sentence stays in it, and nothing is dropped or added."""
    flat = " ".join(page.split())
    for _citation, words in U.sliced(page, SPEC):
        for segment in words.split(f" {ELLIPSIS} "):
            assert segment in flat, segment
    assert dict(U.sliced(page, SPEC))["26 USC 1(e)(1)"] == (
        "(1) Food Expenses for food furnished for purposes of chapter 24 "
        "(relating to wages).")


def test_an_anchor_that_matches_twice_is_refused(page):
    """One that begins matching a second place would move a stored passage
    without a line of the SPEC changing."""
    with pytest.raises(SystemExit, match="occurs 2x"):
        U.sliced(page, (("x", (("Expenses", "\n", 1),)),))


def test_a_missing_anchor_is_refused_rather_than_skipped(page):
    with pytest.raises(SystemExit, match="occurs 0x"):
        U.sliced(page, (("x", (("(9) Nothing here", "\n", 1),)),))


def test_the_currency_line_is_read_off_the_page_or_refused(page):
    assert U.currency(page) == ("Text contains those laws in effect on "
                                "September 25, 2026")
    with pytest.raises(ValueError, match="2 times"):
        U.currency(page + page)


def test_the_blocks_wrap_without_breaking_a_hyphen(page):
    long = "(1) Food " + " ".join(["a 10-percent interest"] * 12)
    out = U.blocks(long + "\n(2) Items", "S0", "2026-09-27",
                   spec=(("26 USC 1(e)(1)", (("(1) Food", "\n(2) Items", 1),)),))
    held = record.parse_passages(out[0])[0]
    assert held.text == long and held.kind == record.RULE


# ── what is stored ───────────────────────────────────────────────────────────

WANTED = {
    "26 USC 274(a)(1)": "type generally considered to constitute entertainment",
    "26 USC 274(e)": "Subsection (a) shall not apply to-",
    "26 USC 274(e)(2)": "as compensation to an employee",
    "26 USC 274(e)(4)": "primarily for the benefit of employees",
    "26 USC 274(e)(7)": "made available by the taxpayer to the general public",
    "26 USC 274(e)(8)": "sold by the taxpayer in a bona fide transaction",
    "26 CFR 1.162-21(a)(3)(i)": "includes a fine or penalty",
    "26 CFR 1.162-21(a)(3)(ii)": "does not include routine investigations",
}


def test_the_words_the_pilot_and_the_trial_needed_are_stored():
    held = {p.citation: p for p in record.load(CORPUS).passages}
    for citation, words in WANTED.items():
        assert citation in held, f"{citation} is not stored"
        assert words in held[citation].text, (citation, words)


def test_every_exception_in_274e_is_its_own_passage():
    """§ 1.274-11(c) names them by number, so each number must open."""
    held = {p.citation for p in record.load(CORPUS).passages}
    for n in range(1, 10):
        assert f"26 USC 274(e)({n})" in held, n
    assert "26 USC 274(e)(10)" not in held


def test_the_spec_is_what_is_stored():
    """The SPEC and the record name the same paragraphs, and every one is
    source S41 -- a row in one and not the other is a slice nobody ran."""
    desk = record.load(CORPUS)
    stored = sorted(p.citation for p in desk.passages if p.source_id == "S41")
    assert stored == sorted(c for c, _ in U.S274)
    assert all(p.kind == record.RULE for p in desk.passages
               if p.source_id == "S41")


def test_1_162_21s_examples_hang_off_their_own_paragraphs():
    """Unlike S37-S39, each example is a numbered paragraph, (f)(1)-(f)(13), so
    its path is the regulation's own. Its Facts and Analysis are stored inside
    it and nowhere else -- a sub-paragraph of an example stored as a rule would
    be a worked answer handed to a graded brief."""
    desk = record.load(CORPUS)
    mine = [p for p in desk.passages if p.source_id == "S40"]
    examples = [p for p in mine if p.kind == record.EXAMPLE]
    assert [p.citation for p in examples] == [
        f"26 CFR 1.162-21(f)({n}) Example {n}" for n in range(1, 14)]
    assert not [p for p in mine if p.kind == record.RULE
                and p.citation.startswith("26 CFR 1.162-21(f)")]
    for p in examples:
        assert p.text.startswith("Facts.") and f" {ELLIPSIS} Analysis." in p.text


# ── and the engine will cite them ────────────────────────────────────────────

def test_read_returns_the_stored_text():
    whole = ask.read("26 USC 274(e)", CORPUS)
    assert whole.startswith("### 26 USC 274(e)\n")
    assert "bona fide transaction" in whole          # (e)(8), a direct clause
    listed = ask.read("26 CFR 1.162-21", CORPUS)
    assert "`26 CFR 1.162-21(a)(3)(i)`" in listed
    assert "includes a fine or penalty" in ask.read("26 CFR 1.162-21(a)(3)(i)",
                                                    CORPUS)


QUESTION = ("A monthly streaming subscription is paid by a business that shows "
            "the service to customers in its waiting room. Is it deductible?")
POSITION = ("not disallowed as entertainment: expenses for goods or services "
            "sold by the taxpayer in a bona fide transaction are excepted")


def test_an_answer_citing_274e8_passes_the_citation_check():
    out = ask.answer(QUESTION, position=POSITION, citation="26 USC 274(e)(8)",
                     corpus=CORPUS, keep=False,
                     judged=judging.Judgment(
                         by="second reader", supports=True,
                         because="sold by the taxpayer in a bona fide transaction"))
    assert not isinstance(out, engine.Refusal), out


def test_a_paragraph_274e_does_not_have_is_still_refused():
    """The control: the same answer on a citation nobody stored."""
    out = ask.answer(QUESTION, position=POSITION, citation="26 USC 274(e)(10)",
                     corpus=CORPUS, keep=False)
    assert isinstance(out, engine.Refusal) and out.reason == "authority_absent"
