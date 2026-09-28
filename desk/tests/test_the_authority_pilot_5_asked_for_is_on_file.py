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
import proving                                              # noqa: E402
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


def test_the_limit_on_274e1_is_stored_with_its_date():
    """Codex on #403: from 2026 § 274(o) takes away the deduction for meals at an
    employer-operated eating facility and for § 119 meals, which (e)(1) would
    otherwise except. Storing (e)(1) without (o) would let a 2026 question be
    answered deductible under an exception that no longer reaches it. (o) does
    not carry its own date; the enacting law does, so that sentence is stored
    too, as the page prints it."""
    desk = record.load(CORPUS)
    o = desk.passage("26 USC 274(o)")
    assert o and "no deduction shall be allowed under this chapter for-" in o.text
    assert "(e)(8) or (n)(2)(C)" in o.text
    assert "section 132(e)(2)" in desk.passage("26 USC 274(o)(1)").text
    assert "section 119(a)" in desk.passage("26 USC 274(o)(2)").text
    note = desk.passage(U.O_DATE)
    assert note and "after December 31, 2025" in note.text
    assert "elimination of deduction for meals provided at convenience of employer" in note.text
    listed = ask.read("26 USC 274")
    for c in ("26 USC 274(o)", "26 USC 274(o)(1)", "26 USC 274(o)(2)", U.O_DATE):
        assert f"`{c}`" in listed, c


# ── (o) is READ WITH (e)(1), not merely stored beside it ────────────────────

EMPLOYEE_MEALS = ("Food and beverages furnished to employees on the business "
                  "premises: is the expense excepted under section 274(e)?")


@pytest.mark.parametrize("opened", ["26 USC 274(e)(1)", "26 USC 274(e)"])
def test_opening_the_exception_shows_the_limit_on_it(opened):
    """Codex on #403, after (o) was stored: `ask.read` prints a paragraph and
    its own children, and (o) is (e)(1)'s sibling-once-removed, so reading the
    exception still showed it without the provision that overrides it."""
    got = ask.read(opened)
    assert "### 26 USC 274(e)(1)" in got
    assert "### 26 USC 274(o)" in got
    assert "after December 31, 2025" in got
    assert got.index("### 26 USC 274(e)(1)") < got.index("### 26 USC 274(o)")
    # (o) is a lead-in; its two clauses are what it denies.
    assert "### 26 USC 274(o)(1)" in got and "### 26 USC 274(o)(2)" in got


@pytest.mark.parametrize("opened", ["26 USC 274(o)", "26 USC 274(o)(1)"])
def test_opening_the_denial_shows_when_it_starts(opened):
    """Codex on #403, the third time: the date was read with (e)(1) only, so
    opening (o) itself printed the denial with no year on it, and a 2025
    question read it as current. A clause of (o) carries its parent's limit."""
    got = ask.read(opened)
    assert f"### {opened}" in got
    assert f"### {U.O_DATE}" in got
    assert "after December 31, 2025" in got
    assert got.index(f"### {opened}") < got.index(f"### {U.O_DATE}")


FACILITY_2025 = ("In 2025, can a business deduct expenses for food or beverages "
                 "associated with its section 132(e)(2) facility?")


def test_a_brief_that_prints_a_clause_of_the_denial_names_its_date():
    """Codex on #403, the fourth time: `ask.read` inherited the parent's limit
    and the brief did not, so a brief quoting (o)(1) alone served a denial
    that is not yet in force for 2025 with nothing saying so."""
    got = ask.consult(FACILITY_2025)
    assert "### 26 USC 274(o)(1)" in got, "the question no longer reaches (o)(1)"
    tail = got[got.index("### 26 USC 274(o)(1)"):]
    tail = tail[:tail.find("\n### ", 5)] if "\n### " in tail[5:] else tail
    assert f"`{U.O_DATE}`" in tail


FINES_DATE = "26 CFR 1.162-21(g)"


@pytest.mark.parametrize("opened", ["26 CFR 1.162-21(a)",
                                    "26 CFR 1.162-21(b)(2)(iii)(A)",
                                    "26 CFR 1.162-21(f)(10) Example 10"])
def test_opening_the_fines_rule_shows_when_it_applies(opened):
    """Codex on #403: § 1.162-21(g) confines the whole section to taxable years
    beginning on or after 19 January 2021, and a grandfathered agreement
    escapes it; read without (g), a 2019 fine is denied by a rule that did
    not reach it. Every paragraph and every example is read with (g)."""
    got = ask.read(opened)
    assert f"### {FINES_DATE}" in got
    assert "January 19, 2021" in got


def test_opening_the_date_itself_does_not_print_it_twice():
    got = ask.read(FINES_DATE)
    assert got.count(f"### {FINES_DATE}") == 1


def test_a_brief_that_prints_the_exception_names_the_limit():
    got = ask.consult(EMPLOYEE_MEALS)
    assert "### 26 USC 274(e)(1)" in got, "the question no longer reaches (e)(1)"
    tail = got[got.index("### 26 USC 274(e)(1)"):]
    tail = tail[:tail.find("\n### ", 5)] if "\n### " in tail[5:] else tail
    assert "`26 USC 274(o)`" in tail


def test_read_with_must_name_what_the_corpus_holds(tmp_path):
    import shutil
    c = tmp_path / "corpus"
    shutil.copytree(CORPUS, c)
    s = (c / "SOURCES.md").read_text(encoding="utf-8")
    (c / "SOURCES.md").write_text(
        s.replace("**Read with:** 26 USC 274(e)(1) — 26 USC 274(o);",
                  "**Read with:** 26 USC 274(e)(1) — 26 USC 274(q);"),
        encoding="utf-8")
    with pytest.raises(record.RecordError, match="274\\(q\\)"):
        record.load(c)


# ── and the SERVED answer carries the limit, which is what the judge reads ──

EMPLOYER_MEALS_2026 = ("In 2026, are meals the employer furnishes on its "
                       "business premises for its convenience deductible?")
DEDUCTIBLE = ("Deductible: section 274(e)(1) excepts food and beverages "
              "furnished on the business premises primarily for employees.")
EXCEPTED = "Food, beverages, and facilities furnished on the business premises"


def _served_on_274e1(judged):
    return ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                      citation="26 USC 274(e)(1)", keep=False, judged=judged)


def test_a_served_answer_carries_what_the_record_reads_it_with():
    """Codex on #403, the fifth time: the brief and `ask.read` printed § 274(o)
    beside (e)(1) and the production path did not -- a 2026 answer calling
    employer-premises meals deductible was Served with (e)(1) alone, and judged
    against it. The limit is part of the passage served AND the one judged."""
    passage = next(p.text for p in record.load(CORPUS).passages
                   if p.citation == "26 USC 274(e)(1)")
    words = passage.split("(1)", 1)[-1].strip()[:40]
    out = _served_on_274e1(judging.Judgment(by="second-reader", supports=True,
                                            because=words))
    assert isinstance(out, engine.Served), out
    assert "26 USC 274(o)(1)" in out.passage
    assert "after December 31, 2025" in out.passage
    assert "after December 31, 2025" in str(out)


def test_the_judge_is_handed_the_limit():
    """What the second reader's quotation is checked against IS the served
    passage, so words quoted from § 274(o) are found there. Before, they were
    refused as `judgment_not_in_the_passage`: the judge had been handed (e)(1)
    alone. (A judge's NO is taken without a containment check, so only a
    quotation proves what they were given.)"""
    out = _served_on_274e1(judging.Judgment(
        by="second-reader", supports=True,
        because="shall apply to amounts incurred or paid after December 31, 2025"))
    assert isinstance(out, engine.Served), out
    assert out.judged.stands


def test_a_served_fines_answer_carries_the_applicability_date():
    out = ask.answer(
        "Is a fine paid to a town for a zoning violation deductible?",
        position="Not deductible: it is paid to a government in relation to "
                 "the violation of a law.",
        citation="26 CFR 1.162-21(a)", keep=False,
        judged=judging.Judgment(by="second-reader", supports=True,
                                because="paid or incurred"))
    assert isinstance(out, engine.Served), out
    assert "26 CFR 1.162-21(g)" in out.passage
    assert "January 19, 2021" in out.passage


# ── (o) names its own exception, § 274(n)(2)(C), and that is on file too ────

N2C = "26 USC 274(n)(2)(C)"
N2 = "26 USC 274(n)(2)"


def test_the_exception_to_the_denial_is_stored():
    """Codex on #403: (o) denies "other than expenses described in subsection
    (e)(8) or (n)(2)(C)", and (n)(2)(C) was not on file -- so the denial was
    served with a cross-reference nobody could open. It is the crew-and-
    offshore-platform rule, and (n)(2)'s closing sentence narrows two of its
    clauses, so that sentence is stored on (n)(2), as (e)'s is on (e)."""
    desk = record.load(CORPUS)
    c = desk.passage(N2C)
    assert c and c.text.startswith("(C) such expense is for food or beverages-")
    assert "drilling rig if the platform or rig is located offshore" in c.text
    assert c.text.endswith("(within the meaning of section 143(k)(2)(B)), or")
    two = desk.passage(N2)
    assert two and "Paragraph (1) shall not apply to any expense if-" in two.text
    assert ELLIPSIS in two.text
    assert "luxury water transportation" in two.text


@pytest.mark.parametrize("opened", ["26 USC 274(o)", "26 USC 274(e)(1)"])
def test_reading_the_denial_or_what_it_limits_reaches_the_exception(opened):
    """READ WITH IS TRANSITIVE: (e)(1) is read with (o), and (o) with the
    exception it names, so opening (e)(1) reaches (n)(2)(C) without anyone
    having to know to open (o) first."""
    got = ask.read(opened)
    assert f"### {N2C}" in got
    assert "luxury water transportation" in got


def test_a_served_answer_on_the_exception_carries_the_exception_to_it():
    out = _served_on_274e1(judging.Judgment(
        by="second-reader", supports=True,
        because="provided on an oil or gas platform or drilling rig"))
    assert isinstance(out, engine.Served), out
    assert f"{N2C}:" in out.passage


# ── (o) names two exceptions, and a clause carries its lead-in ──────────────

def test_the_denial_is_read_with_both_exceptions_it_names():
    """Codex on #403: (o) excepts "(e)(8) or (n)(2)(C)", and only the second
    was read with it, though (e)(8) was on file the whole time."""
    got = ask.read("26 USC 274(o)")
    assert "### 26 USC 274(e)(8)" in got
    assert "### 26 USC 274(n)(2)(C)" in got


@pytest.mark.parametrize("cited, lead_in", [
    ("26 USC 274(o)(1)", "no deduction shall be allowed under this chapter for-"),
    ("26 USC 274(n)(2)(C)", "Paragraph (1) shall not apply to any expense if-"),
    ("26 USC 274(e)(8)", "Subsection (a) shall not apply to-"),
])
def test_a_clause_is_served_with_the_words_that_give_it_effect(cited, lead_in):
    """Codex on #403: cited alone, (o)(1) is "any expense for the operation of a
    facility" -- the denial is in (o)'s lead-in, not in it. The same holds for
    (n)(2)(C), whose parent also carries the luxury-vessel carve-out, and for
    every exception in (e). Each § 274 subsection stored here is read with
    itself, so every clause under it carries the parent's words."""
    assert lead_in in ask.read(cited)
    out = ask.answer("Is it deductible?", position="It is not deductible.",
                     citation=cited, keep=False,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because=lead_in))
    assert isinstance(out, engine.Served), out
    assert lead_in in out.passage


# ── A LEAD-IN IS READ WITH ITS CLAUSES, AND A CLAUSE WITH ITS LEAD-IN ───────
#
# Codex on #403, after the § 274 lines: one record line per subsection kept
# leaking -- § 1.162-21(a)(3)(i) defines a fine and was served without (a)'s
# "no deduction is allowed" or the (a)(1)-(3) conditions, and § 274(o) was
# served ending "for-" with nothing after it. The rule is general now, read off
# the words: a paragraph that ends in a dash or a colon states nothing alone.

FINE = "26 CFR 1.162-21(a)(3)(i)"
DENIAL = "no deduction is allowed under chapter 1 of the Internal Revenue Code"


def _served(cited, because):
    return ask.answer("Is it deductible?", position="It is not deductible.",
                      citation=cited, keep=False,
                      judged=judging.Judgment(by="second-reader",
                                              supports=True, because=because))


def test_a_clause_is_served_with_its_lead_in_and_the_lead_ins_other_clauses():
    out = _served(FINE, "includes a fine or penalty")
    assert isinstance(out, engine.Served), out
    assert DENIAL in out.passage
    for c in ("(a)(1)", "(a)(2)", "(a)(3)"):
        assert f"26 CFR 1.162-21{c}:" in out.passage, c


@pytest.mark.parametrize("cited, clauses", [
    ("26 USC 274(o)", ("26 USC 274(o)(1)", "26 USC 274(o)(2)")),
    ("26 CFR 1.162-21(a)", tuple(f"26 CFR 1.162-21(a)({i})" for i in (1, 2, 3))),
])
def test_a_lead_in_is_served_with_its_clauses(cited, clauses):
    out = _served(cited, "paid or incurred" if "CFR" in cited else "no deduction")
    assert isinstance(out, engine.Served), out
    for c in clauses:
        assert f"{c}:" in out.passage, c


def test_reading_a_clause_shows_its_lead_in():
    got = ask.read(FINE)
    assert "### 26 CFR 1.162-21(a)\n" in got
    assert DENIAL in got


def test_a_parent_that_is_only_a_heading_is_not_pulled_in():
    """The control: § 274(a) is a heading, not a lead-in -- (a)(1) states the
    whole rule itself -- so nothing is added for it."""
    out = _served("26 USC 274(a)(1)", "No deduction otherwise allowable")
    assert isinstance(out, engine.Served), out
    assert "26 USC 274(a):" not in out.passage


def test_a_brief_that_prints_a_clause_names_its_lead_in():
    """Codex on #403: `frame` reached reads and served answers and not the
    brief, so a brief quoting § 1.162-21(a)(3)(i) -- a definition of "fine" --
    left out the rule it defines a word for. Named, not printed: a brief is
    narrowed on purpose, and `ask.read` prints the rest."""
    got = ask.consult("A fine was paid for breaking a law. Can we deduct it?",
                      limit=1)
    assert f"### {FINE}" in got, "the question no longer reaches (a)(3)(i)"
    tail = got[got.index(f"### {FINE}"):]
    tail = tail[:tail.find("\n### ", 5)] if "\n### " in tail[5:] else tail
    assert "`26 CFR 1.162-21(a)`" in tail
    assert "`26 CFR 1.162-21(a)(1)`" in tail


# ── WHAT A PARAGRAPH CITES AND THE RECORD DOES NOT HOLD, SAID ───────────────
#
# Codex on #403: § 274(o) denies only what § 132(e)(2) and § 119(a) describe,
# and neither is on file, so nothing could apply their tests -- and nothing said
# so. Every statute cites others; 264 of 1,257 stored paragraphs cite a Code
# section the record does not hold. Chasing each is endless; SAYING it is the
# rule: the desk names what it does not hold and says to escalate rather than
# assume, where it serves, reads and briefs.

def test_the_references_read_off_a_paragraph_are_code_sections_only():
    assert record.code_references(
        "a facility described in section 132(e)(2), and meals described in "
        "section 119(a).") == ["26 USC 132(e)(2)", "26 USC 119(a)"]
    # A regulation is not a Code section, and title 46 is not title 26.
    assert record.code_references("under section 1.263(a)-3 of this chapter") == []
    assert record.code_references("defined in section 2101 of title 46, United") == []


def test_a_served_answer_names_what_it_cites_and_the_record_does_not_hold():
    # § 274(o) itself: (o)(1) ends ", or", so citing it alone no longer carries
    # (o)(2) and its § 119(a) -- they are alternatives (Codex on #403).
    out = _served("26 USC 274(o)", "no deduction shall be allowed")
    assert isinstance(out, engine.Served), out
    assert "26 USC 132(e)(2)" in out.unheld
    assert "26 USC 119(a)" in out.unheld
    text = str(out)
    assert "NOT ON FILE" in text and "authority_absent" in text


def test_reading_the_denial_names_what_it_turns_on():
    got = ask.read("26 USC 274(o)")
    assert "`26 USC 132(e)(2)`" in got and "`26 USC 119(a)`" in got
    assert "authority_absent" in got


def test_a_brief_names_what_a_printed_paragraph_turns_on():
    got = ask.consult(FACILITY_2025)
    tail = got[got.index("### 26 USC 274(o)(1)"):]
    tail = tail[:tail.find("\n### ", 5)] if "\n### " in tail[5:] else tail
    assert "`26 USC 132(e)(2)`" in tail


def test_what_is_on_file_is_not_named():
    """The control: a section the record holds part of is not named; one it
    holds nothing of is."""
    desk = record.load(CORPUS)
    assert "26 USC 274(e)" not in desk.unheld("see section 274(e) and 274(o)")
    assert desk.unheld("see section 132(e)(2)") == ["26 USC 132(e)(2)"]


# ── The reader, against what a second reviewer reproduced on 5b762a5b ───────

@pytest.mark.parametrize("text, want", [
    # Other Acts, and other titles even with a subsection, are not the Code.
    ("section 16(a) of the Securities Exchange Act of 1934", []),
    ("section 502 of the Tax Reform Act of 1986", []),
    ("section 3 of Rev. Proc. 2019-46", []),
    ("section 13101 of Public Law 115-97", []),
    ("section 552(b)(3) of title 5", []),
    ("section 2101(a) of title 46", []),
    # ... but the Code named as the Code is.
    ("section 162(a) of title 26", ["26 USC 162(a)"]),
    ("section 162(a) of the Internal Revenue Code", ["26 USC 162(a)"]),
    ("section 61 of this title", ["26 USC 61"]),
    # Capitalised, the symbol, every item of a list, and a hyphenated number.
    ("Section 263A provides the rule.", ["26 USC 263A"]),
    ("under § 162 generally", ["26 USC 162"]),
    ("sections 162 and 212", ["26 USC 162", "26 USC 212"]),
    ("section 6042(a)(1), 6044(a)(1), 6047(e), 6049(a), or 6050N(a)",
     ["26 USC 6042(a)(1)", "26 USC 6044(a)(1)", "26 USC 6047(e)",
      "26 USC 6049(a)", "26 USC 6050N(a)"]),
    ("sections 179, 179B, or 179C", ["26 USC 179", "26 USC 179B", "26 USC 179C"]),
    ("section 1400Z-2(d)", ["26 USC 1400Z-2(d)"]),
    # Regulations stay out, alone or in a list.
    ("sections 1.162-3 and 1.263(a)-2", []),
    ("section 1.274-5T(c)", []),
    ("section 119(a).", ["26 USC 119(a)"]),
    # Re-review of 3e7a1e98: an "of" that is not an owner keeps the reference.
    ("described in section 224(d)(1) of the person receiving such tips",
     ["26 USC 224(d)(1)"]),
    ("under section 274(d) of $100x of meal expenses", ["26 USC 274(d)"]),
    ("section 162 of such Code", ["26 USC 162"]),
    ("section 172 of this chapter", ["26 USC 172"]),
    # A range is not a section, and cannot be read as its first member.
    ("see sections 261-276, inclusive", []),
    ("sections 1 through 5", []),
    # An owner named BEFORE the number.
    ("Pub. L. 115-97, § 13304(e)(2)", []),
    ("Rev. Proc. 2019-46, section 3.", []),
    # Codex on #403: the owner after a shared subparagraph, as § 1.446-1(e)(3)(iii)
    # writes it -- and an Act named with lowercase words in it.
    ("section 13261(g)(2) or (3) of the Revenue Reconciliation Act of 1993", []),
    ("section 13101 of the Tax Cuts and Jobs Act", []),
    ("section 2 of the Housing and Economic Recovery Act of 2008", []),
    ("section 168(k)(2) or (3) of the Code", ["26 USC 168(k)(2)", "26 USC 168(k)(3)"]),
    # Codex on #403, § 1.163-8T(a)(1)'s own words: an explanatory parenthetical
    # between items, and a space before a subsection.
    ("applying sections 469 (the \u201cpassive loss limitation\u201d) and 163 (d) "
     "and (h) (the \u201cnonbusiness interest limitation\u201d)",
     ["26 USC 469", "26 USC 163(d)", "26 USC 163(h)"]),
    # Codex on #403: a label after a list separator shares the prefix before it
    # -- § 1.263(a)-3(h)(3)(iv) names four paragraphs of § 1221(a), not one.
    ("section 1221(a)(1), (3), (4), or (5)",
     [f"26 USC 1221(a)({i})" for i in (1, 3, 4, 5)]),
    ("section 274(m)(1), (2), and (3)", [f"26 USC 274(m)({i})" for i in (1, 2, 3)]),
    ("section 163(d)(1) and (h)", ["26 USC 163(d)(1)", "26 USC 163(h)"]),
    # Codex on #403: a range that ends in labels is a range too, and is not
    # read as a truncated first end -- § 1.446-1(e)(2)(iii) Example 17 writes
    # "Section 168(g)(1)(A) through (D)", which read as 168(g)(1).
    ("Section 168(g)(1)(A) through (D)", []),
    ("section 274(e)(1) through (9)", []),
    ("section 274(e)(1)-(9)", []),
    # ... and a number inside an aside is not a section.
    ("sections 162 (amended in 2017) and 212", ["26 USC 162", "26 USC 212"]),
    # ... but a label opening a capitalised item is the paragraph's own list:
    # § 1.274-5T(a), "Gifts defined in section 274(b), or (4) Any listed property".
    ("(3) Gifts defined in section 274(b), or (4) Any listed property",
     ["26 USC 274(b)"]),
    ("section 45(b)(1), (2)(A), or (c)",
     ["26 USC 45(b)(1)", "26 USC 45(b)(2)(A)", "26 USC 45(c)"]),
    # Codex on #403, § 1.262-1(c): a one-word aside is not a subsection. A label
    # is a number, a capital, a lower-case letter (or one doubled) or a roman
    # numeral -- never a word.
    ("Section 163 (interest), Section 164 (taxes), and Section 165 (losses)",
     ["26 USC 163", "26 USC 164", "26 USC 165"]),
    ("sections 469 (interest) and 163(d)", ["26 USC 469", "26 USC 163(d)"]),
    ("section 401(a)(iii) and 45(aa)(B)", ["26 USC 401(a)(iii)", "26 USC 45(aa)(B)"]),
    ("section 162 (civil)", ["26 USC 162"]),
])
def test_the_reader_reads_code_sections_and_nothing_else(text, want):
    assert record.code_references(text) == want


def test_a_narrowed_desk_checks_against_the_corpus_it_came_from():
    """A brief built from a narrowed desk without `whole=` called § 274(e)(2)(A)
    not on file: the narrowed desk no longer held it. A narrowed desk now
    remembers the corpus it was cut from."""
    desk = record.load(CORPUS)
    narrow = desk.narrowed_to(["26 CFR 1.274-12(c)(2)(i)(A)"])
    got = ask.brief("x", narrow)
    assert "`26 USC 274(e)(2)(A)`" not in got


def test_unheld_asks_the_whole_corpus_whoever_calls_it():
    """`serve` calls `desk.unheld` on whatever desk it was handed; a narrowed
    one called a held § 274(e)(2)(A) not on file (re-review of 3e7a1e98)."""
    desk = record.load(CORPUS)
    narrow = desk.narrowed_to(["26 CFR 1.274-12(c)(2)(i)(A)"])
    assert narrow.unheld("see section 274(e)(2)(A)") == []


def test_a_late_depreciation_election_does_not_cite_another_act_as_the_code():
    """Codex on #403, with the corpus's own words: the consult reported a
    nonexistent 26 USC 13261(g)(2) and told the answerer to escalate."""
    got = ask.consult("Is making a late depreciation election a change in "
                      "accounting method?")
    assert "26 USC 13261" not in got


# ── A live proof checks what is served WITH the answer, not the cited paragraph alone

class _LivePage:
    def __init__(self, text):
        self.text, self.body, self.url = text, text.encode("utf-8"), ""
        self.at, self.nbytes = "2026-09-27T12:00:00+00:00", len(self.body)


def _live(desk, moved=()):
    """The publisher's document for a source: every stored paragraph of it --
    except those in `moved`, which the page names and says something else of."""
    def transport(source, citation):
        return _LivePage("\n\n".join(
            (f"{p.citation} now reads differently" if p.citation in moved
             else p.text)
            for p in desk.passages if p.source_id == source.id))
    return transport


def _served_274e1():
    return engine.Served(position="x", citation="26 USC 274(e)(1)",
                         tier="primary", checked=None)


def test_a_proof_ties_only_when_every_appended_paragraph_ties():
    """Codex on #403: the proof checked (e)(1) alone, so a § 274(o) date note
    that had moved or gone was served on a TIED proof as current authority."""
    desk = record.load(CORPUS)
    assert proving.prove(_served_274e1(), desk, _live(desk)).verdict == proving.TIED
    moved = proving.prove(_served_274e1(), desk, _live(desk, moved={U.O_DATE}))
    assert moved.verdict == proving.DIFFERS
    assert U.O_DATE in moved.note


def test_an_appended_paragraph_that_could_not_be_checked_is_not_a_tie(tmp_path):
    """Read with a paragraph from ANOTHER source, whose publisher hangs up: the
    cited paragraph ties and the answer still does not."""
    import shutil
    c = tmp_path / "corpus"
    shutil.copytree(CORPUS, c)
    src = (c / "SOURCES.md").read_text(encoding="utf-8")
    (c / "SOURCES.md").write_text(src.replace(
        "**Read with:** 26 USC 274(e)(1) — 26 USC 274(o);",
        "**Read with:** 26 USC 274(e)(1) — 26 CFR 1.162-21(g); 26 USC 274(o);"),
        encoding="utf-8")
    desk = record.load(c)
    whole = _live(desk)

    def half(source, citation):
        if source.id != "S41":
            raise ConnectionResetError("the publisher hung up")
        return whole(source, citation)

    got = proving.prove(_served_274e1(), desk, half)
    assert got.verdict == proving.COULD_NOT and not got.held
    assert "26 CFR 1.162-21(g)" in got.note


def test_a_proof_fetches_each_source_once():
    """Codex on #403: proving § 274(e)(1) with what is served beside it made
    sixteen requests to one House page."""
    desk = record.load(CORPUS)
    whole, calls = _live(desk), []

    def counting(source, citation):
        calls.append(source.id)
        return whole(source, citation)

    assert proving.prove(_served_274e1(), desk, counting).verdict == proving.TIED
    assert calls == ["S41"]


def test_the_judge_reads_the_cited_page_not_the_last_one_fetched():
    """The proof fetches (e)(1)'s page first and the appended paragraphs' after
    it; the judge's quotation is checked against the fetched document, which
    was whichever came back LAST until the pages were kept by citation."""
    desk = record.load(CORPUS)
    live = "ONLY ON THE LIVE PAGE: furnished on the business premises"

    whole = _live(desk)

    def transport(source, citation):
        page = whole(source, citation)
        return _LivePage(page.text + " " + live) if source.id == "S41" else page

    out = ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                     citation="26 USC 274(e)(1)", keep=False, prove=transport,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because="ONLY ON THE LIVE PAGE"))
    assert isinstance(out, engine.Served), out
    assert out.proof.verdict == proving.TIED
    assert out.judged.stands
    assert out.judged.against == "the document fetched from the publisher"


def _cross_source(tmp_path):
    """(e)(1) read with a paragraph of ANOTHER source, § 1.162-21(g) -- the
    shape no stored record has yet and the proof must handle anyway."""
    import shutil
    c = tmp_path / "corpus"
    shutil.copytree(CORPUS, c)
    src = (c / "SOURCES.md").read_text(encoding="utf-8")
    (c / "SOURCES.md").write_text(src.replace(
        "**Read with:** 26 USC 274(e)(1) — 26 USC 274(o);",
        "**Read with:** 26 USC 274(e)(1) — 26 CFR 1.162-21(g); 26 USC 274(o);"),
        encoding="utf-8")
    return c, record.load(c)


def test_a_moved_paragraph_of_another_source_differs_when_the_cited_one_could_not(tmp_path):
    """Codex on #403: a COULD NOT on the cited source returned before the other
    source was fetched, so its DIFFERS -- the worse verdict -- was never seen."""
    _c, desk = _cross_source(tmp_path)
    moved = _live(desk, moved={"26 CFR 1.162-21(g)"})

    def transport(source, citation):
        if source.id == "S41":
            raise ConnectionResetError("the publisher hung up")
        return moved(source, citation)

    got = proving.prove(_served_274e1(), desk, transport)
    assert got.verdict == proving.DIFFERS
    assert "26 CFR 1.162-21(g)" in got.note


def test_the_judge_may_quote_any_document_the_answer_was_proved_against(tmp_path):
    """Codex on #403: the judge was checked against the cited source's page
    only, so quoting the other source's -- served with the answer -- was
    refused as not in the passage."""
    c, desk = _cross_source(tmp_path)
    whole = _live(desk)

    def transport(source, citation):
        page = whole(source, citation)
        if source.id == "S40":
            return _LivePage(page.text + " ONLY ON THE REGULATION'S PAGE")
        return page

    out = ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                     citation="26 USC 274(e)(1)", corpus=c, keep=False,
                     prove=transport,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because="ONLY ON THE REGULATION'S PAGE"))
    assert isinstance(out, engine.Served), out
    assert out.judged.stands


def test_a_cited_heading_is_served_with_what_it_heads():
    """Codex on #403: § 1.162-21(b) is only "Exception for restitution ...", so
    an answer citing it was served the heading and (g) -- not (b)(1), which
    requires BOTH the identification and establishment tests. A heading is read
    off its words: no closing punctuation, and clauses under it."""
    assert record.is_heading("(b) Exception for restitution, remediation, or to "
                             "come into compliance with law")
    assert not record.is_heading("It is not deductible.")
    out = _served("26 CFR 1.162-21(b)", "Exception for restitution")
    assert isinstance(out, engine.Served), out
    assert "26 CFR 1.162-21(b)(1):" in out.passage
    assert "26 CFR 1.162-21(b)(2):" in out.passage


def test_a_heading_above_a_clause_is_still_not_pulled_in():
    """The control stands: § 274(a)(1) states its whole rule, and the heading
    above it adds nothing."""
    out = _served("26 USC 274(a)(1)", "No deduction otherwise allowable")
    assert "26 USC 274(a):" not in out.passage


def test_a_cited_heading_carries_the_tests_under_its_child_headings():
    """Codex on #403: (b)(2) and (b)(3) are headings too, and arrived as bare
    captions -- without (b)(2)(i)-(iii) and (b)(3)(i)-(ii), which say how the
    identification and establishment tests are met."""
    out = _served("26 CFR 1.162-21(b)", "Exception for restitution")
    for c in ("(b)(2)(i)", "(b)(2)(iii)", "(b)(3)(i)", "(b)(3)(ii)"):
        assert f"26 CFR 1.162-21{c}:" in out.passage, c


def test_a_brief_follows_a_chain_into_another_source(tmp_path):
    """Codex on #403: the brief walked Read-with limits on the NARROWED desk,
    which holds only the printed paragraph's source, so a chain crossing into
    another source stopped at its first link."""
    c, _ = _cross_source(tmp_path)
    src = (c / "SOURCES.md").read_text(encoding="utf-8")
    (c / "SOURCES.md").write_text(src.replace(
        "**Read with:** 26 CFR 1.162-21 — 26 CFR 1.162-21(g)\n",
        "**Read with:** 26 CFR 1.162-21 — 26 CFR 1.162-21(g)\n"
        "26 CFR 1.162-21(g) — 26 CFR 1.162-21(f)(10) Example 10\n"), encoding="utf-8")
    whole = record.load(c)
    got = ask.brief("x", whole.narrowed_to(["26 USC 274(e)(1)"]), whole=whole)
    assert "`26 CFR 1.162-21(f)(10) Example 10`" in got


def test_a_frame_paragraph_a_position_rests_on_is_still_proved():
    """Codex on #403: (f)(1)(ii)(B) of § 1.263(a)-1 is served in the frame of
    (A) as stored text, but authority_for resolves it to the firm's POS3, so
    the proof skipped it -- a changed (B) was served on a TIED proof."""
    desk = record.load(CORPUS)
    a = "26 CFR 1.263(a)-1(f)(1)(ii)(A)"
    b = "26 CFR 1.263(a)-1(f)(1)(ii)(B)"
    assert b in desk.frame(a) and desk.authority_for(b)[0] == "position"
    served = engine.Served(position="x", citation=a, tier="primary", checked=None)
    assert proving.prove(served, desk, _live(desk)).verdict == proving.TIED
    got = proving.prove(served, desk, _live(desk, moved={b}))
    assert got.verdict == proving.DIFFERS and b in got.note


def test_the_judge_keeps_the_stored_text_when_the_cited_fetch_failed(tmp_path):
    """Codex on #403: with the cited publisher down and another source fetched,
    the judge was checked against the OTHER document alone, so quoting the
    cited paragraph -- which was served -- was refused."""
    c, desk = _cross_source(tmp_path)
    whole = _live(desk)

    def transport(source, citation):
        if source.id == "S41":
            raise ConnectionResetError("the publisher hung up")
        return whole(source, citation)

    words = desk.passage("26 USC 274(e)(1)").text.split("(1)", 1)[-1].strip()[:40]
    out = ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                     citation="26 USC 274(e)(1)", corpus=c, keep=False,
                     prove=transport,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because=words))
    assert isinstance(out, engine.Served), out
    assert out.judged.stands


def test_a_caption_ending_in_a_full_stop_is_still_a_heading():
    """Codex on #403: § 1.162-21(b)(2)(iii) is "Payment amount not identified."
    and its full stop hid that it is a caption, so (A) and (B) -- the tests for
    an unidentified amount -- were left out, cited directly or through (b)."""
    desk = record.load(CORPUS)
    assert desk._opens(desk.passage("26 CFR 1.162-21(b)(2)(iii)"))
    # A short sentence with no clauses under it is a sentence, not a caption.
    assert not record.is_heading("It is not deductible.")
    out = _served("26 CFR 1.162-21(b)(2)(iii)", "Payment amount not identified")
    for c in ("(b)(2)(iii)(A)", "(b)(2)(iii)(B)"):
        assert f"26 CFR 1.162-21{c}:" in out.passage, c
    whole = _served("26 CFR 1.162-21(b)", "Exception for restitution")
    assert "26 CFR 1.162-21(b)(2)(iii)(A):" in whole.passage


def test_a_carried_paragraph_brings_its_own_limits():
    """Codex on #403: citing § 274(e) carried (e)(1) in its frame but not what
    (e)(1) is read with, so a 2026 answer was served the exception without
    § 274(o) or its date. And the proof must check that same set."""
    out = _served("26 USC 274(e)", "Subsection (a) shall not apply to-")
    assert "26 USC 274(o):" in out.passage
    assert f"{U.O_DATE}:" in out.passage
    desk = record.load(CORPUS)
    served = engine.Served(position="x", citation="26 USC 274(e)",
                           tier="primary", checked=None)
    assert proving.prove(served, desk, _live(desk)).verdict == proving.TIED
    moved = proving.prove(served, desk, _live(desk, moved={U.O_DATE}))
    assert moved.verdict == proving.DIFFERS


def test_a_leaf_of_the_restitution_exception_carries_its_general_rule():
    """Codex on #403: citing § 1.162-21(b)(2)(iii)(A) carried nothing of (b)(1),
    which makes the exception need BOTH the identification and establishment
    tests. (b) and (b)(2) are headings, and a heading above a clause is not
    pulled in -- so the record says it: everything under (b) is read with
    (b)(1)."""
    leaf = "26 CFR 1.162-21(b)(2)(iii)(A)"
    words = " ".join(record.load(CORPUS).passage(leaf).text.split()[:6])
    out = _served(leaf, words)
    assert isinstance(out, engine.Served), out
    assert "26 CFR 1.162-21(b)(1):" in out.passage


def test_a_position_backed_answer_still_proves_what_is_served_with_it():
    """Codex on #403: citing § 1.263(a)-1(f)(1)(ii)(B) resolves to the firm's
    POS3, and the proof returned COULD NOT before looking at the six regulation
    paragraphs served with it -- so a changed one was served unchecked. A
    position has no publisher; what is served beside it does."""
    desk = record.load(CORPUS)
    b = "26 CFR 1.263(a)-1(f)(1)(ii)(B)"
    assert desk.authority_for(b)[0] == "position"
    appended = desk.served_with(b)
    assert appended
    served = engine.Served(position="x", citation=b, tier="primary", checked=None)
    assert proving.prove(served, desk, _live(desk)).verdict == proving.COULD_NOT
    got = proving.prove(served, desk, _live(desk, moved={appended[-1]}))
    assert got.verdict == proving.DIFFERS and appended[-1] in got.note


# Codex on #403: § 274(e)(3) excepts a nonemployee's reimbursed expenses only
# "to the extent provided by subsection (d)", § 274(d) is not on file, and the
# reader counted only section numbers -- so nothing said it was missing.
@pytest.mark.parametrize("text, within, want", [
    ("(to the extent provided by subsection (d)) to such person.",
     "26 USC 274(e)(3)", ["26 USC 274(d)"]),
    ("as provided in paragraph (2)", "26 USC 274(n)(1)", ["26 USC 274(n)(2)"]),
    ("subsections (a) and (c)(1)", "26 USC 162(b)", ["26 USC 162(a)", "26 USC 162(c)(1)"]),
    ("subsection (a)(1), (3), or (4)", "26 USC 274(e)(3)",
     ["26 USC 274(a)(1)", "26 USC 274(a)(3)", "26 USC 274(a)(4)"]),
    # Somebody else's subsection is not this section's.
    ("under subsection (a) of section 162", "26 USC 274(e)(3)", ["26 USC 162"]),
    ("under subsection (a)(1) of section 162", "26 USC 274(e)(3)", ["26 USC 162"]),
    ("paragraph (1) of this subsection", "26 USC 274(n)(2)", ["26 USC 274(n)(1)"]),
    # No Code paragraph to resolve against: a regulation, a note, or nothing.
    ("see paragraph (e)(5) of this section", "26 CFR 1.162-21(a)(1)", []),
    ("subsection (a) shall apply", "26 USC 274 note, Pub. L. 115-97 § 13304(e)(2)", []),
    ("subsection (d)", "", []),
])
def test_a_relative_reference_is_read_against_its_own_section(text, within, want):
    assert record.code_references(text, within=within) == want


def test_a_labelled_paragraph_is_read_against_its_own_label():
    """A served passage and an `ask.read` carry each paragraph under its own
    citation; "subsection (d)" in (e)(3)'s block is § 274's."""
    text = ("26 USC 274(o): denies it.\n\n"
            "26 USC 274(e)(3): as provided by subsection (d).\n\n"
            "### 26 CFR 1.162-21(a)\n\n> subsection (q)")
    assert record.code_references(text) == ["26 USC 274(d)"]


def test_reimbursed_expenses_say_the_substantiation_rule_is_not_on_file():
    desk = record.load(CORPUS)
    assert "26 USC 274(d)" in desk.unheld(desk.passage("26 USC 274(e)(3)").text,
                                          within="26 USC 274(e)(3)")
    words = " ".join(desk.passage("26 USC 274(e)(3)").text.split()[:6])
    out = _served("26 USC 274(e)(3)", words)
    assert isinstance(out, engine.Served), out
    assert "26 USC 274(d)" in out.unheld
    assert "26 USC 274(d)" in ask.read("26 USC 274(e)(3)")


def test_a_leaf_of_a_list_of_alternatives_is_not_served_its_siblings():
    """Codex on #403: citing § 274(e)(8) framed it with every exception in (e),
    and (e)(1)'s § 274(o) chain came with them -- eleven sections called missing
    that the answer never turned on. (e)'s items are each a whole exception;
    only a list joined by "and" is one rule that needs all of it."""
    desk = record.load(CORPUS)
    assert desk.frame("26 USC 274(e)(8)") == ["26 USC 274(e)"]
    assert "26 USC 274(o)" not in desk.served_with("26 USC 274(e)(8)")
    # Nor through a limit: (o)(1) is read with (e)(8), and (e)(8) with (e).
    assert "26 USC 274(e)(9)" not in desk.served_with("26 USC 274(o)(1)")
    assert desk.unheld(desk.limits_text("26 USC 274(e)(8)")) == []
    # The control: § 1.162-21(a)'s clauses end "; and", and are one rule.
    assert all(f"26 CFR 1.162-21(a)({i})" in desk.frame(FINE) for i in (1, 2, 3))


def test_a_page_that_is_not_the_publishers_does_not_replace_the_served_text():
    """Codex on #403: a 200 that is a bot interstitial, not the page, proves
    COULD NOT -- and was still handed to the judge as the publisher's document,
    so a judgment quoting what was actually served was refused."""
    desk = record.load(CORPUS)
    whole = _live(desk)

    def transport(source, citation):
        if source.id == "S41":
            return _LivePage("Please verify you are a human to continue.")
        return whole(source, citation)

    words = desk.passage("26 USC 274(e)(1)").text.split("(1)", 1)[-1].strip()[:40]
    out = ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                     citation="26 USC 274(e)(1)", keep=False, prove=transport,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because=words))
    assert isinstance(out, engine.Served), out
    assert out.proof.verdict == proving.COULD_NOT
    assert out.judged.stands
    assert out.judged.against != "the document fetched from the publisher"


def test_a_read_does_not_carry_the_siblings_of_a_limit_it_follows():
    """Codex on #403: reading § 274(o) follows (e)(8) up to (e), and ask.read's
    own copy of the expansion then printed all of (e)(1)-(9), naming §§ 274(d),
    267, 414, 501 and 74 as missing. The read now carries `served_with`'s set."""
    got = ask.read("26 USC 274(o)")
    assert "### 26 USC 274(e)(8)\n" in got and "### 26 USC 274(e)\n" in got
    assert "### 26 USC 274(e)(9)\n" not in got
    assert "26 USC 74`" not in got and "26 USC 274(d)" not in got
    # And the clauses of a limit that is not above anything still come.
    assert "### 26 USC 274(o)(2)\n" in ask.read("26 USC 274(e)(1)")


def test_a_read_of_a_leaf_does_not_expand_its_alternative_parent():
    """Codex on #403: ask.read("26 USC 274(e)(8)") printed (e) as its frame,
    then expanded (e) as if it were cited -- sixteen paragraphs, and §§ 274(d),
    267, 414, 501 and 74 called missing."""
    got = ask.read("26 USC 274(e)(8)")
    assert "### 26 USC 274(e)\n" in got
    assert "### 26 USC 274(e)(9)\n" not in got and "26 USC 74`" not in got


def test_a_dependency_that_could_not_be_checked_stays_before_the_judge(tmp_path):
    """Codex on #403: the cited page tied and a Read-with dependency on another
    source came back a bot page; the judge was checked against the cited page
    alone, so quoting the dependency -- which was served -- was refused."""
    c, desk = _cross_source(tmp_path)
    whole = _live(desk)

    def transport(source, citation):
        if source.id == "S40":
            return _LivePage("Please verify you are a human to continue.")
        return whole(source, citation)

    words = " ".join(desk.passage("26 CFR 1.162-21(g)").text.split()[2:9])
    out = ask.answer(EMPLOYER_MEALS_2026, position=DEDUCTIBLE,
                     citation="26 USC 274(e)(1)", corpus=c, keep=False,
                     prove=transport,
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because=words))
    assert isinstance(out, engine.Served), out
    assert out.judged.stands


def test_the_restitution_exception_carries_both_of_its_tests():
    """Codex on #403: § 1.162-21(b)(1) allows the exception only when the
    identification AND establishment requirements are met, and states
    neither -- they are (b)(2) and (b)(3). Cited alone it was served with
    (g) and nothing else."""
    desk = record.load(CORPUS)
    carried = desk.served_with("26 CFR 1.162-21(b)(1)")
    for c in ("(b)(2)", "(b)(2)(i)", "(b)(2)(iii)(A)", "(b)(3)", "(b)(3)(ii)"):
        assert f"26 CFR 1.162-21{c}" in carried, c
    got = ask.read("26 CFR 1.162-21(b)(1)")
    assert "### 26 CFR 1.162-21(b)(2)\n" in got and "### 26 CFR 1.162-21(b)(3)\n" in got


def test_every_paragraph_invoking_the_restitution_tests_carries_them():
    """Codex on #403: § 1.162-21(e)(4)(i)(B) and (C) condition restitution
    treatment on the identification and establishment tests, and eight worked
    examples apply them -- and each was served with (e) and (g) alone. Read off
    the words, so a paragraph stored later that invokes them is held to it too."""
    desk = record.load(CORPUS)
    invoking = [p.citation for p in desk.passages
                if p.citation.startswith("26 CFR 1.162-21(")
                and re.search(r"paragraphs? \(b\)\((?:2|3)\)|\(b\)\(2\) and \(3\)"
                              r"|identification requirement|establishment requirement",
                              p.text)]
    assert len(invoking) >= 16, invoking
    for c in invoking:
        carried = [c, *desk.served_with(c)]
        for test in ("26 CFR 1.162-21(b)(2)", "26 CFR 1.162-21(b)(3)"):
            assert test in carried, (c, test)
