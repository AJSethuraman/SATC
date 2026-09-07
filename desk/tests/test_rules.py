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
import scoreboard_run as sr        # noqa: E402

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


def _examples_text() -> str:
    root = ET.parse(XML).getroot()
    return " ".join(
        " ".join(" ".join("".join(kid.itertext()).split())
                 for kid in c if kid.tag != "HED")
        for c in root if c.tag == "EXAMPLE")


def test_the_marking_is_truthful_against_the_section_itself():
    """Every passage is verbatim from the half of the section its `Kind` claims.

    THE STRONGEST FORM OF THIS CHECK, and it only became available once the
    examples were stored. Before, a passage could only be tested against the
    rules -- "not found outside the <EXAMPLE> elements" meant retyped or leaked.
    Now the record makes a CLAIM about each passage, and the section itself can
    contradict it: a rule must occur in the <P>/<PSPACE> text, an example must
    occur inside an <EXAMPLE>, and a passage in the wrong half is a mismarking
    that no amount of internal consistency would reveal.
    """
    desk = record.load(DESK)
    assert len(desk.passages) > 100, "the corpus is not the section"
    rules, examples_ = _rules_text(), _examples_text()
    for p in desk.passages:
        where, name = ((rules, "the section's rules")
                       if p.kind == record.RULE
                       else (examples_, "the section's worked examples"))
        assert p.text in where, (
            f"{p.citation} is filed as a {p.kind} but is not verbatim from "
            f"{name}: {p.text[:80]!r}")


def test_every_worked_example_is_stored_and_every_one_is_marked():
    """The other direction, and the reason this change was made at all.

    Measured 7 September 2026: this section carries 223,804 characters of worked
    examples across six regulations and the desks held none of them. An example
    silently dropped is the defect now; before, it was an example silently kept.
    """
    desk = record.load(DESK)
    stored = {p.text for p in desk.passages if p.kind == record.EXAMPLE}
    missing = [f"({e['para']})({e['sub']}) Example {e['n']}"
               for e in ex.examples(XML)
               if " ".join(e["text"].split()) not in stored]
    assert not missing, f"the section's examples are not all stored: {missing}"
    assert len(stored) == 117, f"{len(stored)} examples stored, not 117"


def test_no_worked_example_is_filed_among_the_rules():
    """The leak, at the boundary that still matters. An example filed as a RULE
    reaches the prompt with its own conclusion in it -- and `corpus_lines`,
    `citation_index` and `ask.brief_for_grading` all withhold by KIND, so a
    mismarking is the one thing that defeats all three at once."""
    desk = record.load(DESK)
    rules_held = " ".join(p.text for p in desk.passages
                          if p.kind == record.RULE).casefold()
    for e in ex.examples(XML):
        opening = " ".join(e["text"].split())[:120].casefold()
        assert opening not in rules_held, (
            f"({e['para']})({e['sub']}) Example {e['n']} is filed as a rule")
    for q in desk.problems:
        probe = max(re.split(r"(?<=\.)\s+", q.facts), key=len).casefold()
        assert probe not in rules_held, (
            f"{q.id}'s facts are among the rules, so they reach the prompt")


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
    # THREE RULES AND BOTH EXAMPLES. This asserted `== 3, "never the examples"`
    # until 7 September 2026; the examples are stored now and marked, so
    # `ask.brief_for_grading` can withhold them by kind instead of the corpus
    # never having them. What it was really protecting still holds: the passage
    # count has no relation to the problem count -- here five against one.
    assert len(passages) == 5
    rules = [x for x in passages if "**Kind:** rule" in x]
    stored_examples = [x for x in passages if "**Kind:** example" in x]
    assert len(rules) == 3 and len(stored_examples) == 2
    # AND THE ONE THAT COULD NOT BE A PROBLEM IS STILL AUTHORITY. "Leaks." was
    # dropped above because its stipulation names its own governing paragraph --
    # a scoring defect, not a legal one. The government still published it.
    assert any("Example 1" in x for x in stored_examples), (
        "the example dropped as a problem was dropped from the corpus too; "
        "'we cannot grade this' is not 'this is not law'")
    assert all("**Kind:** example" not in x for x in rules)


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
    # READ OFF THE PROMPT PATH, NOT OFF `desk.passages`. Since the corpus began
    # holding the section's 117 worked examples, those two are different
    # numbers: this desk stores 289, of which 172 are the index it cites
    # from. The sentence claims the latter, so the check asks the code that
    # builds the index rather than counting the record.
    shown = len(sr.corpus_lines(desk, "index"))
    assert shown == sum(1 for p in desk.passages if p.kind == record.RULE)
    assert f"holds **{shown}** paragraphs for **{len(desk.problems)}** problems" in text


# -- the two shapes a run-in heading takes ------------------------------------

def test_a_run_in_heading_is_recognised_in_both_shapes():
    """One <P> can open more than one paragraph, and the CFR writes that two ways.

    § 1.263(a)-3 closes every one of its thirty run-ins with an EM-DASH:
    "(c) Coordination with other provisions of the Code—(1) In general." That is
    the only shape the reader knew until 7 September 2026.

    § 1.6050W-1 and § 1.446-1 close theirs with the heading's own FULL STOP,
    inside the italics, followed by a bare space: "(iv) [i]Combinations of the
    foregoing methods.[/i] (a) In accordance with..." The reader saw only the
    leading label, the italic (a) that followed had no level to continue, and
    no consistent reading of the section existed at all -- so `outline()`
    refused it. Correctly, and for a gap in the reader rather than in the
    regulation. § 1.6050W-1 places now, and brought 22 worked examples with it.
    """
    I0, I1 = ex._I0, ex._I1
    dash = f"(c) {I0}Coordination with other provisions of the Code{I1}—(1) In general. Text."
    stop = f"(iv) {I0}Combinations of the foregoing methods.{I1} ({I0}a{I1}) In accordance with."
    for text, expect in ((dash, [("c", False), ("1", False)]),
                         (stop, [("iv", False), ("a", True)])):
        got = [(l, i) for l, i, _ in ex.labels(_elem(text))]
        assert got == expect, f"{text[:40]!r} read as {got}"


def test_only_an_italic_run_touching_the_label_can_be_a_run_in():
    """What actually keeps the second shape safe -- and it is NOT the full stop.

    I CLAIMED IT WAS, AND A MUTATION SAID OTHERWISE. Requiring the heading's own
    full stop looked like the thing separating a run-in heading from an italic
    term inside a sentence, and I wrote that in the comment beside the pattern.
    Dropping the requirement broke nothing, twice, including against a case
    built specifically to catch it.

    The reason is the ANCHOR. `_RUN_IN` is matched against the text immediately
    following the leading label, so an italic run anywhere else in the sentence
    is never even a candidate. A heading touches its label; a term does not.
    That is the property, it is exact, and it is what this asserts.

    The full stop stays because it is the shape § 1.446-1 and § 1.6050W-1
    actually write and narrower costs nothing here -- not because it is load
    bearing. Saying so is the point: a guard believed to be doing work it is
    not is worse than no guard, because it stops anyone looking for the real one.
    """
    I0, I1 = ex._I0, ex._I1
    mid = f"(a) The election under {I0}section 263A.{I1} (1) applies only to."
    got = [(l, i) for l, i, _ in ex.labels(_elem(mid))]
    assert got == [("a", False)], (
        f"an italic run away from the label was read as a run-in: {got}")
    # AND ONE THAT TOUCHES IT IS, so the test is not passing on an inert input.
    head = f"(a) {I0}General rule.{I1} (1) Section 446(a) provides that."
    assert [(l, i) for l, i, _ in ex.labels(_elem(head))] == \
        [("a", False), ("1", False)]


def test_the_section_reads_identically_after_the_second_shape_was_added():
    """The regression harness for that change, kept rather than run once.

    § 1.263(a)-3 uses only em-dashes, so recognising a second shape must leave
    it untouched. It did: same paragraph count, nothing underdetermined, the
    same 117 example citations.
    """
    paragraphs, underdetermined = ex.outline(XML)
    assert (len(paragraphs), len(underdetermined)) == (172, 0)
    assert len(list(ex.examples(XML))) == 117


def _elem(text: str):
    """A <P> whose marked text is `text`, italics already fenced."""
    import xml.etree.ElementTree as _ET
    frag = text.replace(ex._I0, "<I>").replace(ex._I1, "</I>")
    return _ET.fromstring(f"<P>{frag}</P>")


# -- the four sections that still refuse, and what the evidence says ----------

def test_why_four_sections_cannot_be_read_yet():
    """The diagnosis, corrected. I published a wrong one an hour before this.

    I COMMITTED "the CFR does skip a level, and § 1.446-1 says so in its own
    text", on the evidence that it cites `(e)(2)(ii)(a)` — a roman numeral
    followed directly by a lowercase letter. The citation is real. The reading
    of it was wrong, and the mistake was mine twice over.

    § 1.446-1 does not skip a level. It uses a DIFFERENT ALPHABET at the same
    one: under (c)(1)(ii) its fourth level runs (A), (B), (C); under (c)(1)(iv)
    it runs italic (a), (b). Same depth, two alphabets, and `LEVELS` allows one
    per depth. So (e)(2)(ii)(a) is four components at four levels, not three
    with one skipped, and nothing is being skipped anywhere.

    THREE CAUSES, MEASURED RATHER THAN GUESSED, prototyped 7 September 2026:

      1. `LEVELS` has no italic-lowercase alphabet at all. `_fits` places an
         italic "a" at NO depth, so every such label is unreadable wherever it
         appears — independent of everything else.
      2. A depth admits one alphabet. § 1.446-1 needs the fourth to admit
         uppercase OR italic-lowercase, chosen per branch.
      3. A third run-in shape, with no heading between the labels at all:
         "(2)(i) Except as otherwise..." and "(ii) (a) A change in...". The
         reader knows the two heading shapes and not this one.

    ALL THREE TOGETHER GET § 1.446-1 TO ONE CONSISTENT READING, and that is
    still not good enough to ship. Its own text cites 31 paragraph paths and
    only 24 resolve against that reading. § 1.263(a)-3 resolves 107 of 109, so
    24 of 31 is not the ordinary residue of dangling cross-references — it says
    the reading is partly wrong. § 1.62-2, § 1.274-5 and § 1.274-5T still admit
    no reading at all, so at least a fourth cause is unfound.

    THE SELF-CITATIONS ARE THE ACCEPTANCE TEST, and that is the useful thing to
    leave behind. A regulation naming its own paragraphs is external
    corroboration rather than internal consistency: a reading that places every
    cited path is right for a reason that does not come from the reader.
    """
    text = XML.read_text(encoding="utf-8")
    cited = ex.cited_paths(text)
    held = {p.label for p in ex.outline(XML)[0]}
    resolved = sum(1 for c in cited if c in held)
    # THE BAR THE OTHERS MUST CLEAR, taken from the section that reads.
    assert (resolved, len(cited)) == (100, 102), (resolved, len(cited))
    assert sorted(c for c in cited if c not in held) == \
        ["(i)(1)(iii)", "(j)(3)(ii)"]


def test_the_placement_index_is_still_the_thing_that_would_have_to_change():
    """The three places that would have to change, so the note cannot rot.

    Not the index coupling after all — that was part of the wrong diagnosis
    above. `walk()` may keep indexing the stack by depth, because nothing is
    skipped. What must change is `LEVELS` (one alphabet per depth, and no
    italic-lowercase anywhere) and `_RUN_IN` (two shapes, not three).
    """
    src = (ROOT / "tools" / "extract_ecfr.py").read_text(encoding="utf-8")
    body = src.split("def placements(")[1].split("\ndef ")[0]
    assert "stack[depth]" in body and "stack[:depth] + (label,)" in body, (
        "`placements` no longer indexes the stack by depth. If levels and path "
        "positions are tracked separately now, a skipped level may be readable "
        "-- try § 1.446-1 and update the note above.")
