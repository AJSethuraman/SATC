"""What a second adversarial pass on #403 found, in the fixes for the first
(6d64abca): six findings, nine cases, each red against 92d23be1 and green
now. Each docstring says what it expects and why, in the adversary's words.
Nothing here touches the network.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402


def _passage(citation, source_id, text):
    return record.Passage(citation=citation, source_id=source_id,
                          checked="2026-09-27", text=text)


def _source(id_, prefix, url, read_with=()):
    return record.Source(id=id_, title=id_, tier="primary", access="public_fetch",
                         may_store="full_text", checked="2026-09-27",
                         citation_prefix=prefix, url=url, read_with=read_with)


# ── 1. The range-skip in `_relative` swallows a lead-in's dash (REAL CORPUS) ──

def test_a_dash_that_opens_a_sub_list_is_not_a_range():
    """6d64abca made `_relative` skip a relative reference followed by
    " through" or by "-(" / "–(", so "subsections (a) through (c)" is not read
    as (a) alone. The hyphen test is wider than a range. The statute writes a
    lead-in's dash straight after a reference, and `tools/extract_uscode.py`
    joins the clause that follows on to the same line: § 274(a)(2), stored as
    `26 USC 274(a)(2)`, reads "For purposes of applying paragraph (1)- (A) Dues
    or fees ...". A range never crosses label kinds -- (1) is a paragraph, (A)
    a subparagraph -- and the words cite paragraph (1). At 16ac9f50 the reader
    returned `26 USC 274(a)(1)`; at 6d64abca it returns nothing, so a paragraph
    of the real record now cites one fewer section than its words do. The
    record happens to hold (a)(1), so `unheld` is silent either way; a record
    that did not hold it would not be told (proved on the fake desk below)."""
    whole = record.load(CORPUS)
    p = whole.passage("26 USC 274(a)(2)")
    assert p is not None and "paragraph (1)- (A)" in p.text, \
        "the corpus no longer stores § 274(a)(2) with the dash before (A)"
    assert "26 USC 274(a)(1)" in record.code_references(p.text, within=p.citation)

    # And the failure `unheld` exists to prevent, on a record that lacks (1).
    src = _source("S9", "26 USC 999", "https://publisher.example/999")
    desk = record.Desk(name="x", sources=(src,), passages=(
        _passage("26 USC 999(a)(2)", "S9",
                 "(2) Special rules For purposes of applying paragraph (1)- "
                 "(A) Dues or fees to any club shall be treated as items with "
                 "respect to facilities."),
    ))
    assert desk.unheld(desk.passage("26 USC 999(a)(2)").text,
                       within="26 USC 999(a)(2)") == ["26 USC 999(a)(1)"]


# ── 2. A member listed before a range is dropped with the range (made up) ────

def test_a_listed_member_before_a_range_is_still_read():
    """The same skip drops the WHOLE match when " through" follows it. The
    relative regex matches a list -- "subsections (a) and (b)" -- as one
    reference, so "subsections (a) and (b) through (d)" is skipped entire and
    (a), which the words name outright and which is the first end of nothing,
    is lost without a word. The rule the first pass asked for was "either the
    range is listed in full or it is not read as its first end"; (a) is
    neither the range nor its first end. At 16ac9f50 the reader returned (a)
    and (b). No stored passage writes a list before a range today (checked:
    none of the 1,257), so this is the edge and not the corpus."""
    got = record.code_references("subsections (a) and (b) through (d) shall apply",
                                 within="26 USC 999(a)")
    assert "26 USC 999(a)" in got, got


# ── 3. A Code paragraph whose text opens like a label loses its owner (made up)

@pytest.mark.parametrize("text", [
    "Notice of the election is filed under subsection (d) of this section.",
    "IRS forms prescribed under subsection (d) of this section are used.",
    "Treas. Reg. section 1.999-1 applies; see subsection (d) of this section.",
    "Announcement of the rate is made under subsection (d) of this section.",
])
def test_a_code_paragraphs_own_words_are_not_read_as_a_label(text):
    """6d64abca widened `_LABELLED` from `26 USC`/`26 CFR` to lines opening
    `IRS `, `Instr. `, `Rev. Rul. `, `Rev. Proc. `, `PLR `, `Announcement `,
    `Notice `, `TAM ` or `Treas. `, so a publication's label starts a new owner.
    The label's tail is `[^\\n:]+?` then `:\\s` or end of line -- so ANY line
    that begins with one of those words and holds no ": " is a label to the
    end of the line, and the owner is reset to a string that resolves nothing.
    Ordinary English begins lines that way: "Notice of the election ...",
    "IRS forms ...", "Announcement of ...". At 16ac9f50 each of these read its
    "subsection (d)" against `within`; at 6d64abca it reads nothing. The
    corpus already holds a paragraph that opens "Notice by district director"
    (`26 CFR 1.6001-1(d)`) -- a regulation, so nothing is lost there yet; the
    first Code paragraph stored that way loses every relative reference it
    makes, silently, which is the failure `unheld` exists to prevent (proved
    end to end on the fake desk below: (d) is not held and is not reported)."""
    assert record.code_references(text, within="26 USC 999(a)") == ["26 USC 999(d)"]

    src = _source("S9", "26 USC 999", "https://publisher.example/999")
    desk = record.Desk(name="x", sources=(src,), passages=(
        _passage("26 USC 999(a)", "S9", text),))
    assert desk.unheld(text, within="26 USC 999(a)") == ["26 USC 999(d)"]


# ── 4 & 5. `is_under` reads the suffix on one side only (REAL CORPUS) ────────

_LEAD = "26 CFR 1.262-1(b) — how the examples are introduced"
_LEAF = "26 CFR 1.262-1(b)(1) — life insurance premiums"


def test_a_lead_in_cited_with_a_which_rule_suffix_is_served_with_its_clauses():
    """6d64abca made `is_under` read through the record's " — which rule"
    suffix on the CITATION so that § 1.262-1's paragraphs are under their
    section. It did not touch `_clauses`, `_opens`, `frame` or `ask.read`'s
    "under" test on the KEY side, and § 1.262-1 stores a lead-in that carries
    the suffix: `26 CFR 1.262-1(b) — how the examples are introduced` is
    "Personal, living, and family expenses are illustrated in the following
    examples:", `is_lead_in` says so, and its clauses are stored as
    `26 CFR 1.262-1(b)(1) — life insurance premiums` and eight more. By
    #403's own rule a lead-in "states nothing until its clauses finish it",
    and `frame` promises "when `citation` is itself a lead-in, its own
    clauses". `frame(_LEAD)` is `[]`, so `served_with` is `[]`, `limits_text`
    is `""`, and an answer citing it is served -- and the second reader is
    handed -- a colon and nothing after it. `ask.read(_LEAD)` prints the same.
    Pre-existing in shape, but 6d64abca is the commit that decided the suffix
    is "the same paragraph" and applied that to one side of the containment
    test only."""
    whole = record.load(CORPUS)
    lead = whole.passage(_LEAD)
    assert lead is not None and record.is_lead_in(lead.text), \
        "the corpus no longer stores § 1.262-1(b)'s lead-in with a suffix"
    assert whole.passage(_LEAF) is not None
    assert _LEAF in whole.frame(_LEAD), whole.frame(_LEAD)
    assert _LEAF in whole.served_with(_LEAD)


def test_a_clause_cited_with_a_which_rule_suffix_carries_its_lead_in():
    """The other direction of the same gap. `26 CFR 1.262-1(b)(1) — life
    insurance premiums` is a clause of the lead-in above; `frame` promises
    "every stored ancestor that is a lead-in", and § 274(e)(8) is framed with
    (e) on exactly that promise. `is_under(_LEAF, _LEAD)` is False because the
    suffix is stripped from the citation and not from the key, so the ancestor
    is not found and `frame(_LEAF)` is `[]`. The record can key a Read-with
    line on the bare `26 CFR 1.262-1(b)` and reach the clauses -- 6d64abca's
    own test proves that -- but the frame is read off the stored passages, not
    off a Read-with line, and no line can add an ancestor to it."""
    whole = record.load(CORPUS)
    assert whole.passage(_LEAD) is not None and whole.passage(_LEAF) is not None
    assert _LEAD in whole.frame(_LEAF), whole.frame(_LEAF)


# ── 6. `unheld` on a record holding nothing reads past a blank line (edge) ───

def test_unheld_on_a_record_that_holds_nothing_still_reads_the_whole_text():
    """`Desk.unheld` now compiles every held citation into a label regex,
    `^(?:###\\s+)?(A|B|...)(?::\\s|\\s*$)`. On a desk holding no passage the
    alternation is EMPTY, `^()(?:\\s*$)` matches every blank line, and each
    blank line becomes a label "" that resets the owner: everything after the
    first paragraph break is read against nothing. At 16ac9f50 the same call
    returned (d) and (e); at 6d64abca it returns (d) alone. A desk with no
    passages is an edge -- a citation-only source, or a desk built in a test
    -- but `unheld`'s contract is the same there, and this is the one input on
    which the new regex is not the regex the author meant."""
    desk = record.Desk(name="x")
    text = ("The election under subsection (d) applies.\n\n"
            "The limit in subsection (e) applies too.")
    assert record.code_references(text, within="26 USC 999(a)") == [
        "26 USC 999(d)", "26 USC 999(e)"], "the reader itself changed"
    assert desk.unheld(text, within="26 USC 999(a)") == [
        "26 USC 999(d)", "26 USC 999(e)"]
