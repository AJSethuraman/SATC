"""The desk holds the rules, not only the answers.

The first record stored the 21 worked examples it also scored on, and nothing
else: 21 passages for 21 problems, the same citation on each pair, not one
operative rule. Shown to a model the corpus leaked its conclusions; hidden, there
was nothing to retrieve from, and the frontier row solved the citation as an
assignment puzzle. No citation score on that desk was interpretable, including
the good ones (`runs/2026-09-04/SCOREBOARD.md`).

So four things are asserted here, each over the COMMITTED record and each
proved capable of failing by mutation before it was kept:

  1. the paragraph outline is reconstructed from the source without judgement,
     and the section's own cross-references corroborate it;
  2. the stored authority is the rules and holds no worked example;
  3. a problem's citation is read verbatim from its own withheld analysis, and
     an example whose analysis does not name a single rule is excluded by name;
  4. the index is no longer a bijection.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

import pytest

import record
from conftest import DESKS, ROOT

sys.path.insert(0, str(ROOT / "tools"))
import extract_ecfr as ex          # noqa: E402

XML = ROOT / "tools" / "fixtures" / "1.263a-3.xml"
DESK = DESKS / "fixed-assets"
PREFIX = "26 CFR 1.263(a)-3"


def _p(xml: str):
    return ET.fromstring(xml)


# ── 1 · the outline is read, not guessed ─────────────────────────────────────

def test_a_run_in_heading_opens_every_paragraph_it_names():
    """"(c) Coordination ...—(1) In general. Nothing ..." is one element opening
    two paragraphs. Reading only the leading label never sees (c)(1) -- or
    (e)(2)(ii), which four of the first 21 problems turned on."""
    got = ex.labels(_p("<P>(c) <I>Coordination with the Code</I>—(1) "
                       "<I>In general.</I> Nothing changes.</P>"))
    assert got == [("c", False, "Coordination with the Code"),
                   ("1", False, "In general. Nothing changes.")]
    # Three levels in one element, as (g) does in the real section.
    got = ex.labels(_p("<P>(g) <I>Special rules</I>—(1) <I>Certain costs</I>—(i) "
                       "<I>In general.</I> A taxpayer must.</P>"))
    assert [l for l, _, _ in got] == ["g", "1", "i"]
    # An italic run that is NOT followed by a dash is a defined term, not a
    # heading opening a deeper paragraph.
    got = ex.labels(_p("<P>(2) <I>Personal property</I> means tangible.</P>"))
    assert got == [("2", False, "Personal property means tangible.")]


def test_an_italic_numeral_is_the_fifth_level_and_a_plain_one_is_not():
    """The XML writes the second level as `(1)` and the fifth as `(<I>1</I>)`.
    That typesetting is what places "(3) Property other than building" at
    (e)(3) rather than under (e)(2)(v)(B), where a plain deepest-first walk
    put it. Without it the numeral is ambiguous and nothing else settles it."""
    assert ex.labels(_p("<P>(<I>1</I>) <I>Entire building.</I> Text.</P>")) == [
        ("1", True, "Entire building. Text.")]
    chain = [[("e", False)], [("1", False)], [("i", False)], [("A", False)]]
    italic = ex.placements(chain + [[("1", True)]])
    assert italic == [[("e",), ("e", "1"), ("e", "1", "i"), ("e", "1", "i", "A"),
                       ("e", "1", "i", "A", "1")]]
    # A plain (1) after (e)(1)(i)(A) has nowhere to go: it is not the successor
    # of (1) and it may not open the italic level. No reading, rather than a
    # wrong one.
    assert ex.placements(chain + [[("1", False)]]) == []
    # And an italic (1) cannot open the SECOND level.
    assert ex.placements([[("e", False)], [("1", True)]]) == []


def test_the_letter_i_is_placed_by_the_sequence_around_it():
    """(i) is the ninth letter at one depth and the first roman at another.
    After (h)(1), "(i) ...—(1) In general." can only be the letter, because a
    plain (1) cannot follow (h)(1)(i); after (h)(1) a bare (i) followed by (A)
    is the roman. The label alone never settles it; the sequence does."""
    letter = ex.placements([[("h", False)], [("1", False)],
                            [("i", False), ("1", False)]])
    assert letter == [[("h",), ("h", "1"), ("i", "1")]]
    roman = ex.placements([[("h", False)], [("1", False)], [("i", False)],
                           [("A", False)]])
    assert roman == [[("h",), ("h", "1"), ("h", "1", "i"), ("h", "1", "i", "A")]]
    # THE SUCCESSOR RULE UNDER LOAD. On the committed section every wrong
    # branch dies at the next label, so a mutant that dropped the rule
    # survived both tests above. Here nothing follows the (i): only the rule
    # that a letter must succeed the letter on the stack -- (a) then (b), not
    # (a) then (i) -- makes the roman reading the single one.
    assert ex.placements([[("a", False)], [("1", False)], [("i", False)]]) == [
        [("a",), ("a", "1"), ("a", "1", "i")]]
    # And a level cannot skip: (1) then (3) is not a sequence.
    assert ex.placements([[("a", False)], [("1", False)], [("3", False)]]) == []


def test_an_underdetermined_element_is_excluded_and_named_not_placed(tmp_path):
    """Where two readings are consistent, the element is not placed by
    preference. A stored citation that might be the wrong paragraph is worse
    than none, and an answer key resting on it would be a guess."""
    xml = tmp_path / "s.xml"
    xml.write_text('<DIV8><P>(h) <I>Safe harbor.</I> Text.</P>'
                   '<P>(1) <I>In general.</I> Text.</P>'
                   '<P>(i) Could be either.</P></DIV8>', encoding="utf-8")
    paragraphs, underdetermined = ex.outline(xml)
    assert [p.label for p in paragraphs] == ["(h)", "(h)(1)"]
    assert len(underdetermined) == 1
    assert "(h)(1)(i)" in underdetermined[0] and "(i)" in underdetermined[0]


def test_an_element_with_no_label_is_an_error_not_a_skip(tmp_path):
    xml = tmp_path / "s.xml"
    xml.write_text('<DIV8><P>(a) Fine.</P><P>No label here.</P></DIV8>',
                   encoding="utf-8")
    with pytest.raises(ValueError, match="no paragraph label"):
        ex.outline(xml)


def test_the_committed_section_admits_exactly_one_reading():
    """The whole reconstruction rests on this. Were it two, `outline` would
    exclude the elements that differ, and this asserts it never had to."""
    facts = ex.corpus(XML)
    assert facts["readings"] == 1
    assert facts["underdetermined"] == []
    held = {p.label for p in facts["paragraphs"]}
    assert "(e)(3)" in held and "(e)(3)(i)" in held, "the (e)(3) placement"
    assert "(e)(2)(v)(B)(3)" not in held, "the deepest-first walk's error"
    assert "(e)(2)(v)(B)(2)" in held, "the italic fifth level"
    assert {"(c)", "(c)(1)", "(g)", "(g)(1)", "(g)(1)(i)"} <= held, "run-ins"
    assert {"(e)(2)(ii)", "(i)(1)(ii)", "(j)(1)(iii)", "(k)(1)(vi)", "(l)(1)"} <= held


def test_the_section_corroborates_the_outline_with_its_own_cross_references():
    """The regulation cites its own paragraphs in full 109 times. A wrong
    outline would leave many of those pointing at nothing. Every one that does
    not resolve names a paragraph the section's text does not contain -- and
    the parent of each IS held, so the reader reached the right neighbourhood
    and found the hole the regulation itself left."""
    facts = ex.corpus(XML)
    cited, held = facts["cited"], {p.label for p in facts["paragraphs"]}
    assert len(cited) > 100, "the cross-reference reader found almost nothing"
    assert facts["resolved"] == cited & held
    assert facts["dangling"] == cited - held
    assert len(facts["dangling"]) <= 2, sorted(facts["dangling"])
    for path in facts["dangling"]:
        parent = "".join(f"({x})" for x in ex._parts(path)[:-1])
        assert parent in held, f"{path} dangles and so does its parent {parent}"


def test_the_extracted_file_states_the_corroboration_it_was_built_with():
    """The header prints numbers about itself. They are asserted against a
    rebuild, both directions, so the file cannot outlive the facts."""
    facts = ex.corpus(XML)
    text = (DESK / "extracted" / "treas-reg-1-263a-3.md").read_text(encoding="utf-8")
    head = " ".join(text.split("\n---\n", 1)[0].split())     # it is line-wrapped
    assert f"{facts['elements']} elements opening {len(facts['paragraphs'])} paragraphs" in head
    assert f"cites {len(facts['cited'])} of its own paragraph paths" in head
    assert f"{len(facts['resolved'])} resolve" in head
    assert f"{len(facts['dangling'])} do not — {', '.join(sorted(facts['dangling']))}" in head
    assert f"admits {facts['readings']} consistent" in head


def test_cross_references_into_other_sections_are_not_ours():
    got = ex.cited_paths(
        "Under paragraphs (e)(4), and (e)(5)(ii) of this section, and paragraph "
        "(c)(1)(i) of § 1.162-3, and this paragraph (j), and paragraph (3), "
        "and paragraphs (d)(1) and (j) of this section.")
    assert got == {"(e)(4)", "(e)(5)(ii)", "(j)", "(d)(1)"}


# ── 2 · the stored authority is the rules and holds no worked example ────────

def _rules_text() -> str:
    root = ET.parse(XML).getroot()
    return " ".join(" ".join("".join(c.itertext()).split())
                    for c in root if c.tag in ("P", "PSPACE"))


def test_every_stored_passage_is_verbatim_from_outside_the_examples():
    """Asserted over the committed record. The stems are not the point here;
    the source is: a passage that cannot be found in the section's text outside
    its <EXAMPLE> elements is either retyped or a worked example."""
    desk = record.load(DESK)
    assert len(desk.passages) > 100, "the corpus is not the section's rules"
    rules = _rules_text()
    for p in desk.passages:
        assert p.text in rules, (
            f"{p.citation} is not verbatim from the section's rules: "
            f"{p.text[:80]!r}")


def test_the_stored_authority_holds_no_problems_worked_example():
    """The leak, at its new boundary. Written against every example in the
    section and every problem's facts, not against the extractor's own view of
    what it stored."""
    desk = record.load(DESK)
    corpus = " ".join(p.text for p in desk.passages).casefold()
    for e in ex.examples(XML):
        opening = " ".join(e["text"].split())[:120].casefold()
        assert opening not in corpus, (
            f"({e['para']})({e['sub']}) Example {e['n']} is in the authority")
    for q in desk.problems:
        probe = max(re.split(r"(?<=\.)\s+", q.facts), key=len).casefold()
        assert probe not in corpus, f"{q.id}'s facts are in the authority"


def test_checked_on_a_rule_passage_is_the_fetch_date_never_the_run():
    _, _, _, _, passages = ex.build(XML, DESK, checked="2019-01-02")
    assert passages, "no passages built"
    assert all("**Checked:** 2019-01-02" in p for p in passages)


# ── 3 · the citation is read from the analysis, never assigned ───────────────

HELD = {"(i)(1)", "(i)(1)(ii)", "(i)(3)", "(j)", "(j)(1)", "(j)(1)(iii)",
        "(j)(2)(ii)", "(j)(10)", "(k)(1)(iv)", "(k)(2)", "(d)(1)"}


@pytest.mark.parametrize("withheld,family,expect", [
    ("within the safe harbor under paragraph (i)(1)(ii) of this section. "
     "Accordingly, not required under paragraph (d).", "i", "(i)(1)(ii)"),
    # the named ancestor covers the steps beneath it
    ("under paragraphs (e)(2)(ii) and (j)(2)(ii); a betterment under paragraph "
     "(j)(1)(iii). Therefore, under paragraphs (d)(1) and (j).", "j", "(j)"),
    # references outside the family the examples illustrate are not the rule
    ("Therefore, must capitalize under paragraphs (d)(1) and (j).", "j", "(j)"),
])
def test_the_governing_rule_is_the_one_named_path_that_covers_the_rest(
        withheld, family, expect):
    assert ex.governing(withheld, family, HELD) == (expect, "")


@pytest.mark.parametrize("withheld,family,why", [
    ("Therefore, not required to be capitalized under paragraph (d).", "i",
     "analysis names no paragraph of the rules it illustrates"),
    ("Under paragraph (k)(2) and paragraph (k)(1)(iv) of this section.", "k",
     "analysis names more than one paragraph and none contains the rest"),
    # two siblings at one level; neither is beneath the other
    ("Under paragraphs (j)(1) and (j)(10) of this section.", "j",
     "analysis names more than one paragraph and none contains the rest"),
    ("Under paragraph (i)(1)(iii) of this section.", "i",
     "analysis names a paragraph the section does not contain"),
])
def test_an_analysis_with_no_single_governing_rule_is_a_named_exclusion(
        withheld, family, why):
    assert ex.governing(withheld, family, HELD) == ("", why)


def test_a_sentence_applying_a_rule_by_name_is_withheld_and_a_stipulation_is_not():
    """"A's ESVs are within the routine maintenance safe harbor under paragraph
    (i)(1)(ii)" carries no connective and no banned stem, so the first boundary
    kept it as a fact. Once the citation IS that paragraph, that sentence hands
    the model its citation the way the conclusion used to hand it the answer."""
    facts, withheld, answer = ex.split_conclusion(
        "Assume that none of the exceptions in paragraph (i)(3) apply. A pays "
        "for work. The work is within the safe harbor under paragraph (i)(1)(ii) "
        "of this section. Therefore, A is not required to capitalize it.")
    assert answer == "not required to capitalize"
    assert facts == ("Assume that none of the exceptions in paragraph (i)(3) "
                     "apply. A pays for work.")
    assert withheld == ("The work is within the safe harbor under paragraph "
                        "(i)(1)(ii) of this section. Therefore, A is not "
                        "required to capitalize it.")


def test_build_refuses_a_problem_whose_stipulation_names_its_own_rule(tmp_path):
    """The stipulation exception cannot reopen the leak: a fact pattern that
    names its governing paragraph is refused at the boundary every problem
    passes, and counted by name. § 1.263(a)-3(j)(3) Example 10 is the real case
    -- its stipulation says the work "is for a betterment ... under paragraph
    (j)(1)(ii)", which stipulates the outcome of the very test."""
    xml = tmp_path / "s.xml"
    xml.write_text(
        '<DIV8><P>(j) <I>Betterments</I>—(1) <I>In general.</I> A rule.</P>'
        '<P>(2) Examples. The following examples illustrate the application of '
        'this paragraph (j):</P>'
        '<EXAMPLE><HED>Example 1. Leaks.</HED><PSPACE>Assume that the work is a '
        'betterment under paragraph (j)(1) of this section. A pays for work on '
        'a machine. Therefore, A must capitalize the amount under paragraph (j) '
        'of this section.</PSPACE></EXAMPLE>'
        '<EXAMPLE><HED>Example 2. Clean.</HED><PSPACE>B pays for work on a '
        'machine. The work is a betterment under paragraph (j)(1) of this '
        'section. Therefore, B must capitalize the amount under paragraph (j) '
        'of this section.</PSPACE></EXAMPLE></DIV8>', encoding="utf-8")
    _, kept, dropped, problems, passages = ex.build(xml, tmp_path, checked="2026-09-04")
    assert [(e["title"], why) for e, why in dropped] == [
        ("Leaks.", "facts name the governing paragraph")]
    assert [(e["title"], e["rule"]) for e, _ in kept] == [("Clean.", "(j)")]
    assert "**Citation:** 26 CFR 1.263(a)-3(j)\n" in problems[0]
    assert "(j)(1)" not in problems[0].split("**Facts:**")[1]
    assert len(passages) == 3, "(j), (j)(1) and (j)(2), never the examples"


def _kept_by_facts() -> dict:
    _, kept, _, _, _ = ex.build(XML, DESK, checked="2026-09-04")
    return {e["facts"]: e for e, _ in kept}


def test_every_problems_citation_is_named_in_its_own_withheld_analysis():
    """Verbatim by construction, asserted over the committed record: rebuild,
    find each problem's example by its facts, and check the cited path appears
    in the sentences that were withheld from those facts."""
    desk = record.load(DESK)
    kept = _kept_by_facts()
    root = ET.parse(XML).getroot()
    assert desk.problems, "would pass vacuously"
    for p in desk.problems:
        assert p.facts in kept, f"{p.id} is not a rebuild of the fixture"
        e = kept[p.facts]
        _, withheld, _ = ex.split_conclusion(e["text"])
        path = p.citation[len(PREFIX):]
        assert path and re.search(r"paragraphs? [^.]*" + re.escape(path), withheld), (
            f"{p.id} cites {path}, which its withheld analysis never names")
        assert path == e["rule"]


def test_no_problems_facts_name_its_own_citation_or_apply_a_rule_by_name():
    """The leak one boundary down, with the patterns written here rather than
    imported: a fact may cite a paragraph only inside a stipulation, and never
    the paragraph the problem is scored on finding."""
    desk = record.load(DESK)
    assert desk.problems, "would pass vacuously"
    applies = re.compile(r"paragraphs? \(")
    for p in desk.problems:
        path = p.citation[len(PREFIX):]
        assert path not in p.facts, f"{p.id}'s facts name its citation {path}"
        for s in re.split(r"(?<=\.)\s+(?=[A-Z(])", p.facts):
            if applies.search(s):
                assert re.match(r"^\(?[ivx]*\)?\s*Assume\b", s), (
                    f"{p.id} applies a rule by name in its facts: {s[:90]!r}")


def test_every_example_left_out_at_the_citation_step_is_counted_by_name():
    """Three exclusions that did not exist in the first record. Each names the
    example and what its analysis actually named, so a reader of the 4 September
    scoreboard can see where each of its 21 problems went."""
    _, kept, dropped, _, _ = ex.build(XML, DESK, checked="2026-09-04")
    text = (DESK / "PROBLEMS.md").read_text(encoding="utf-8")
    named = [(e, why) for e, why in dropped if "named" in e]
    assert named, "no example was excluded at the citation step; check the reasons"
    for e, why in named:
        row = f"| ({e['para']})({e['sub']}) Example {e['n']} · {e['title']} | {why} |"
        assert row in text, f"not counted by name: {row}"
    rows = text.split("### Left out at the citation step, by name", 1)[1]
    rows = rows.split("## What a model gets for free", 1)[0]
    assert rows.count("\n| (") == len(named), "the by-name table and the build disagree"


# ── 4 · the index is not a bijection ─────────────────────────────────────────

def test_the_index_is_not_a_bijection():
    """The structure that made 17/21 an upper bound: 21 strings for 21 problems,
    one each, solvable as an assignment puzzle. Three things must all hold: the
    count of citable rules differs from the count of problems, problems share
    citations, and every problem's citation still resolves."""
    desk = record.load(DESK)
    index = {p.citation for p in desk.passages}
    keys = [p.citation for p in desk.problems]
    assert len(index) != len(keys)
    assert len(index) > len(keys) * 5, "the index barely exceeds the problems"
    assert len(set(keys)) < len(keys), "no two problems share a rule"
    assert set(keys) <= index, sorted(set(keys) - index)


def test_problems_md_states_the_citation_spread_and_its_baseline():
    desk = record.load(DESK)
    text = (DESK / "PROBLEMS.md").read_text(encoding="utf-8")
    stated = {m.group(1): int(m.group(2)) for m in
              re.finditer(r"^\| (26 CFR [^|]+?) \| (\d+) \|$", text, re.M)}
    assert stated == dict(Counter(p.citation for p in desk.problems))
    top = max(stated.values())
    assert (f"Always citing the most common one matches {top} of "
            f"{len(desk.problems)} ({top * 100 // len(desk.problems)}%)") in text
    assert f"holds **{len(desk.passages)}** paragraphs for **{len(desk.problems)}** problems" in text
