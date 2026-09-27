"""An answerer can find every section on file, not only the eight it was shown.

26 September 2026, Sarcia pilot 4. Five sections were admitted because pilot 3's
refusals named them; asked again, the paragraph carrying the rule reached the
eight passages a brief prints for ONE of them. § 1.6001-1(a) ranked 442nd and
§ 1.263(a)-4(f)(1) 622nd of 1,171 -- measured here, and matching the desk's own
report. Three of the nine served answers cited a paragraph retrieval never
surfaced, because the desk already knew where it was, while the brief told
every answerer that a citation to anything not printed would be refused.

That sentence was false. The engine checks the whole corpus. So the brief now
says what is true, lists every section on file, and `ask.read` opens one.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

COMMINGLED = ("A single account carries both purchases made for customers' "
              "jobs and purchases made for the account holder's household. "
              "What does the recordkeeping authority require in that "
              "situation, and does commingling of that kind affect whether "
              "the trade-related amounts can be taken into account?")


def test_the_brief_does_not_say_what_the_engine_does_not_do():
    got = ask.consult(COMMINGLED)
    assert "not printed" not in got
    assert "anything NOT on file is refused" in got


def test_every_section_on_file_is_listed_in_the_brief():
    """Every source holding a stored paragraph. S34, the firm's own policy,
    holds none -- its positions are printed where they apply."""
    got = ask.consult(COMMINGLED)
    index = got[got.index("## Everything on file"):]
    desk = record.load(CORPUS)
    held = {p.source_id for p in desk.passages}
    for source in desk.sources:
        assert (f"`{source.citation_prefix}`" in index) == (source.id in held), \
            source.id


def test_the_rule_retrieval_missed_is_one_read_away():
    """The pilot-4 case: 1.6001-1(a) is not in this brief, and it is listed."""
    got = ask.consult(COMMINGLED)
    assert "### 26 CFR 1.6001-1(a)" not in got
    assert "`26 CFR 1.6001-1`" in got
    section = ask.read("26 CFR 1.6001-1")
    assert "`26 CFR 1.6001-1(a)`" in section
    assert "shall keep such permanent books of account or records" in \
        ask.read("26 CFR 1.6001-1(a)")


def test_a_lead_in_is_printed_with_the_limits_that_finish_it():
    """(f)(1) ends "the earlier of--" and states no rule without (i) and (ii)."""
    got = ask.read("26 CFR 1.263(a)-4(f)(1)")
    assert got.index("does not extend beyond the earlier of") \
        < got.index("12 months after the first date") \
        < got.index("The end of the taxable year following")


def test_under_means_under():
    """§ 1.274-5T is not under § 1.274-5, and § 1.61-10 is not under § 1.61-1."""
    got = ask.read("26 CFR 1.274-5")
    assert "1.274-5T" not in got
    assert "26 CFR 1.274-5(c)" in got


def test_nothing_on_file_says_so_rather_than_offering_the_nearest():
    got = ask.read("26 CFR 1.6001-9")
    assert got.startswith("Nothing on file under 26 CFR 1.6001-9")
    assert "1.6001-1" not in got


def test_every_listed_section_opens():
    """Independent review of #401: five sources whose citations run
    "IRS Pub. 463 (2025), ..." were refused by `read`, though the brief told
    the answerer to read them; and a source holding no paragraphs was listed."""
    got = ask.consult(COMMINGLED)
    index = got[got.index("## Everything on file"):]
    for source in record.load(CORPUS).sources:
        listed = f"`{source.citation_prefix}`" in index
        opens = not ask.read(source.citation_prefix).startswith("Nothing on file")
        assert listed == opens, (source.id, listed, opens)


def test_an_exact_read_prints_its_own_clauses_and_lists_the_rest():
    """Codex on #401: reading a parent printed every descendant --
    § 1.263(a)-3(k) came back as 55 passages and 52,915 characters, past the
    8,192-token window before the brief was counted. Direct sub-paragraphs
    finish a lead-in and are printed; anything deeper is listed by citation,
    one `read` away."""
    got = ask.read("26 CFR 1.263(a)-3(k)")
    assert len(got) < 16_000, len(got)
    assert "`26 CFR 1.263(a)-3(k)(1)(i)`" in got or "### 26 CFR 1.263(a)-3(k)(1)" in got
    deeper = [line for line in got.splitlines() if line.startswith("### ")]
    assert all(line.count("(") - "26 CFR 1.263(a)-3(k)".count("(") <= 1
               for line in deeper), deeper


def test_a_paragraph_with_worked_examples_lists_them():
    """Codex on #401: § 1.263(a)-3(e)(6) printed its lead-in, which ends in a
    colon, and none of its 19 examples was printed or listed."""
    got = ask.read("26 CFR 1.263(a)-3(e)(6)")
    assert "`26 CFR 1.263(a)-3(e)(6) Example 1`" in got
    assert got.count("Example ") >= 19
