"""What an adversarial pass on #403 found: a different model, told to break
the desk by writing tests only, while Codex was out of quota (27 September
2026). Every test here was red against 16ac9f50 and is green now; each
docstring says what it expects and why, in the adversary's words. Nothing
here touches the network -- fake desks are built in memory and the one test
that loads a record loads a copy under `tmp_path`.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402


def _passage(citation, source_id, text):
    return record.Passage(citation=citation, source_id=source_id,
                          checked="2026-09-27", text=text)


def _source(id_, prefix, url, read_with=()):
    return record.Source(id=id_, title=id_, tier="primary", access="public_fetch",
                         may_store="full_text", checked="2026-09-27",
                         citation_prefix=prefix, url=url, read_with=read_with)


# ── 1. The brief and the served answer disagree on what § 274(e) carries ─────

def test_a_brief_printing_274e_names_the_limit_a_served_answer_carries():
    """`served_with` is "one definition, because the served passage, the second
    reader and the live proof must all check the same set". An answer citing
    § 274(e) is served with § 274(o) and its date note (proved by
    `test_a_carried_paragraph_brings_its_own_limits`), and `ask.read` prints
    them. The brief names only what `frame` and `limits_on` return for (e)
    itself: the nine clauses, and no limit at all -- (o) hangs off (e)(1), a
    framed paragraph, and the brief never asks what the framed paragraphs are
    read with. So an answerer briefed on (e) is told to read (e)(1)-(9) as one
    with it and is not told that from 2026 (o) takes (e)(1)'s exception away.
    The brief must name every paragraph the served answer will carry that it
    does not itself print."""
    whole = record.load(CORPUS)
    got = ask.brief("x", whole.narrowed_to(["26 USC 274(e)"]), whole=whole)
    assert "### 26 USC 274(e)\n" in got
    tail = got[got.index("### 26 USC 274(e)\n"):]
    tail = tail[:tail.find("\n### ", 5)] if "\n### " in tail[5:] else tail
    carried = whole.served_with("26 USC 274(e)")
    assert "26 USC 274(o)" in carried, "the served set no longer carries (o)"
    assert "`26 USC 274(o)`" in tail
    assert "`26 USC 274 note, Pub. L. 115-97 § 13304(e)(2)`" in tail


# ── 2. A limit that is a bare clause is served without the words that give it effect

def test_a_limit_that_is_a_clause_is_carried_with_its_lead_in():
    """#403's rule, read off the words: "cited alone, (o)(1) is 'any expense for
    the operation of a facility' -- the denial is in (o)'s lead-in". `frame`
    applies that to the CITED paragraph. It is not applied to a paragraph the
    record reads the citation WITH: `served_with` appends a limit "with its
    clauses" and never with its frame. The real record dodges this by reading
    every § 274 subsection with itself, so (o)'s limit (n)(2)(C) reaches (n)(2)
    through that self-line -- a convention each future source has to remember.
    A source without it serves "(2) any expense for a club." as the whole
    limit, and the second reader is handed a clause with no "shall not apply
    to-" above it. The lead-in a limit completes is part of what is served."""
    src = _source("S3", "26 USC 999", "https://publisher.example/999",
                  read_with=(("26 USC 999(a)", ("26 USC 999(b)(2)",)),))
    desk = record.Desk(name="x", sources=(src,), passages=(
        _passage("26 USC 999(a)", "S3",
                 "(a) General rule. A deduction is allowed for any expense."),
        _passage("26 USC 999(b)", "S3",
                 "(b) Exceptions. Subsection (a) shall not apply to-"),
        _passage("26 USC 999(b)(1)", "S3", "(1) any expense for a yacht, or"),
        _passage("26 USC 999(b)(2)", "S3", "(2) any expense for a club."),
    ))
    assert desk.frame("26 USC 999(b)(2)") == ["26 USC 999(b)"], \
        "the frame of the clause itself is known"
    assert "26 USC 999(b)" in desk.served_with("26 USC 999(a)")
    assert "shall not apply to-" in desk.limits_text("26 USC 999(a)")


# ── 3. A publication's label does not start a new owner for "subsection (q)" ─

def test_a_publications_label_starts_a_new_owner_for_relative_references():
    """`_LABELLED` says "every label starts a new owner; only a Code paragraph's
    resolves anything". The regex matches only `26 USC` and `26 CFR` labels, so
    a paragraph of a publication, a revenue ruling or a PLR served after a Code
    paragraph is read as the CODE paragraph's continuation, and its "subsection
    (q)" becomes § 274(q) -- a section that does not exist, named to the
    answerer as authority not on file, with an instruction to escalate. The
    fixtures only ever put Code and regulation labels side by side."""
    text = ('26 USC 274(e)(1): Expenses for food.\n\n'
            'IRS Pub. 463 (2025), "Meals": See subsection (q) for the worksheet.')
    assert record.code_references(text) == []
    # And end to end, through what `engine.serve` reads off the served passage.
    s1 = _source("S1", "26 USC 274", "https://publisher.example/274",
                 read_with=(("26 USC 274(e)(1)", ('IRS Pub. 463 (2025), "Meals"',)),))
    s2 = _source("S2", "IRS Pub. 463 (2025)", "https://publisher.example/463")
    desk = record.Desk(name="x", sources=(s1, s2), passages=(
        _passage("26 USC 274(e)(1)", "S1", "(1) Expenses for food."),
        _passage('IRS Pub. 463 (2025), "Meals"', "S2",
                 "You can deduct meals. See subsection (q) for the worksheet."),
    ))
    served = ("(1) Expenses for food.\n\nREAD WITH IT -- the record says these "
              "change what it says:\n\n" + desk.limits_text("26 USC 274(e)(1)"))
    assert desk.unheld(served, within="26 USC 274(e)(1)") == []


# ── 4 & 5. A paragraph cited with the record's own " — which rule" suffix ───

def test_a_paragraph_cited_with_a_which_rule_suffix_is_under_its_section():
    """The record cites one paragraph as several rules by suffixing the citation
    with ` — <which rule>` (`_stem`, `alongside`); every stored paragraph of
    § 1.262-1 and § 1.162-1 is cited that way. `ask.read("26 CFR 1.262-1")`
    lists them all as under the section. `is_under` -- the containment rule
    #403 built `limits_on`, `frame`, `unheld` and `load`'s Read-with check on --
    says none of them is. Two readings of "under", and nothing comparing them."""
    whole = record.load(CORPUS)
    suffixed = [p.citation for p in whole.passages
                if p.citation.startswith("26 CFR 1.262-1(") and " — " in p.citation]
    assert suffixed, "the corpus no longer cites § 1.262-1 with suffixes"
    listed = ask.read("26 CFR 1.262-1")
    assert all(f"`{c}`" in listed for c in suffixed), "ask.read lists them as under"
    for c in suffixed:
        assert record.is_under(c, "26 CFR 1.262-1"), c


def test_a_section_wide_read_with_reaches_paragraphs_cited_with_a_suffix(tmp_path):
    """S40 dates the whole of § 1.162-21 with one line, `26 CFR 1.162-21 —
    26 CFR 1.162-21(g)`, and `load` accepts a section as a key when the source
    holds anything under it. The same line for § 1.262-1 -- whose paragraphs
    are all cited with a ` — which rule` suffix -- is refused at load as
    holding nothing under the key, and were it to load, `limits_on` would reach
    none of them. A section-wide limit must reach every paragraph of the
    section the record stores, however the record labels which rule it is."""
    c = tmp_path / "corpus"
    shutil.copytree(CORPUS, c)
    s = (c / "SOURCES.md").read_text(encoding="utf-8")
    anchor = "**Url:** https://www.ecfr.gov/current/title-26/section-1.262-1\n"
    assert anchor in s
    (c / "SOURCES.md").write_text(s.replace(
        anchor, anchor + "\n**Read with:** 26 CFR 1.262-1 — "
                         "26 CFR 1.262-1(a) — the general rule\n"),
        encoding="utf-8")
    desk = record.load(c)
    assert desk.limits_on("26 CFR 1.262-1(b)(5) — travelling away from home") == [
        "26 CFR 1.262-1(a) — the general rule"]


# ── 6. A question is a sentence, not a caption ──────────────────────────────

def test_a_question_is_a_sentence_not_a_caption():
    """`is_heading` is "read off the words: no closing punctuation, and not a
    lead-in". Its list of closing punctuation has no "?" (nor "!"), so a whole
    sentence that asks something is a caption. The corpus already holds one:
    `Rev. Rul. 2005-28, ISSUE` is 288 characters ending "...under § 162 of the
    Internal Revenue Code?" and `_opens` calls it a heading. Nothing is stored
    under it today, so the mis-reading has no effect yet; the first source
    that stores a question with clauses beneath it will serve them as the
    whole of what the question says."""
    assert not record.is_heading("Is it deductible?")
    whole = record.load(CORPUS)
    issue = whole.passage("Rev. Rul. 2005-28, ISSUE")
    assert issue is not None and issue.text.rstrip().endswith("?")
    assert not record.is_heading(issue.text)


# ── 7-10. The reader, on spellings the fixtures never used ──────────────────

def test_a_section_sign_without_a_space_is_still_a_citation():
    """`code_references` reads '"section", "Sections", "§" or "§§", then one
    number'. It requires whitespace between the sign and the number, so "§274(o)"
    -- how the sign is set in a great deal of IRS and Treasury prose -- cites
    nothing, and a served paragraph written that way names no missing authority.
    No stored passage spells it so today; the guard is silent rather than wrong
    on the corpus, and silent is the failure `unheld` exists to prevent."""
    assert record.code_references("under §274(o) generally") == ["26 USC 274(o)"]
    assert record.code_references("§§162 and 212") == ["26 USC 162", "26 USC 212"]


def test_an_inline_list_after_a_citation_is_not_a_shared_label():
    """The shared-label rule reads "section 1221(a)(1), (3), (4), or (5)" as four
    paragraphs, and refuses a label that opens a CAPITALISED item ("or (4) Any
    listed property"). Regulations write inline lists in lower case -- "under
    section 274(d), (i) the taxpayer must ..." -- and the reader turns the
    list's "(i)" into a citation to § 274(i), which is a real subsection about
    something else and is then reported as not on file. The guard was proved
    to fire; it was never proved to stay quiet on the ordinary lower-case list."""
    assert record.code_references(
        "under section 274(d), (i) the taxpayer must substantiate the amount, "
        "and (ii) the time") == ["26 USC 274(d)"]


@pytest.mark.parametrize("text", [
    "section 162 of the Protecting Americans from Tax Hikes Act of 2015",
    "section 101 of the Ticket to Work and Work Incentives Improvement Act of 1999",
])
def test_an_act_named_with_a_lowercase_word_still_owns_its_section(text):
    """`_OWNED_AFTER` excludes "section N of the <Capitalised Words> Act", letting
    only "and", "of", "for", "on" and "the" through in lower case. The PATH Act
    has "from" in its name and the Ticket to Work Act has "to"; both are cited
    routinely in the regulations this desk stores, and each is read as a
    citation to the Code section of the same number."""
    assert record.code_references(text) == []


def test_a_relative_range_is_not_read_as_its_first_member_alone():
    """For section numbers the rule is explicit: a range "names sections the
    reader cannot list", so "sections 261-276" and "sections 1 through 5" cite
    nothing. The relative reader has no such rule: "subsections (a) through (c)"
    in a § 274 paragraph is read as § 274(a) alone, and (b) and (c) -- which the
    text names just as much -- are dropped without a word. Either the range is
    listed in full or, as for sections, it is not read as its first end."""
    got = record.code_references("subsections (a) through (c) shall apply",
                                 within="26 USC 274(e)(3)")
    assert got in ([], ["26 USC 274(a)", "26 USC 274(b)", "26 USC 274(c)"]), got
