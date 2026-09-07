"""The cash desk's reader: what it splits, and what it refuses.

It exists because `extract_ecfr` refuses § 1.446-1 — the section uses lower-case
letters at a fourth level where the CFR alphabet cycle expects upper-case ones.
This one does less and is tested on the two things it does that a length cap or a
loose match would get silently wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_cash_desk as bcd                              # noqa: E402


def _html(reconciling_body: str, *, other=("Kinds of Records To Keep",
                                           "Supporting Documents",
                                           "Bookkeeping System")) -> str:
    """A page shaped like the publication: contents first, then the body.

    The contents matter. Publication 583 lists every heading before the text, so
    a reader taking the FIRST match gets a link with no body under it.
    """
    toc = "".join(f"<p>{h}</p>" for h in other) + \
        "<p>Reconciling the checking account.</p>"
    body = "".join(f"<p>{h}</p><p>body of {h}</p>" for h in other) + \
        f"<p>Reconciling the checking account.</p><p>{reconciling_body}</p>"
    return f"<html><body>{toc}{body}</body></html>"


def _write(tmp_path, text) -> Path:
    p = tmp_path / "p583.html"
    p.write_text(text, encoding="utf-8")
    return p


GOOD = ("When you receive your bank statement, make sure the statement, your "
        "checkbook, and your books agree. The statement balance may not agree "
        "with the balance in your checkbook and books "
        + bcd.RECONCILING_LEAD
        + " Includes bank charges you did not enter in your books, "
        + bcd.CHARGE_SPLIT + " or checks that did not clear. "
        + bcd.RECONCILING_SPLIT
        + " Update your checkbook and journals for items not recorded.")


def test_the_reconciliation_section_is_split_into_its_three_rules(tmp_path):
    """One citation admits one ratified position, and this section states three
    rules that do not share an answer. Keyed to one citation, two of the desk's
    four problems are refused as contradicting the position whatever a desk
    says."""
    out = dict(bcd.pub583_sections(_write(tmp_path, _html(GOOD))))
    timing = next(c for c in out if c.endswith(bcd.TIMING))
    updating = next(c for c in out if c.endswith(bcd.UPDATING))

    assert "did not clear" in out[timing]
    assert bcd.RECONCILING_SPLIT not in out[timing]
    assert out[updating].startswith(bcd.RECONCILING_SPLIT)
    assert "not recorded" in out[updating]


def test_the_bank_charge_rule_is_not_stored_under_the_timing_citation(tmp_path):
    """THE BUG THIS SPLIT EXISTS FOR, found by Codex on #264.

    Splitting only at `RECONCILING_SPLIT` divides the publication's DIAGNOSIS
    from its PROCEDURE — not its timing rule from its correction rule. So the
    head kept both causes, including "Includes bank charges you did not enter in
    your books", which is CB4. POS1 then ratified that head as "a reconciling
    item, no entry in the books", and the desk's own record held authority
    saying an unentered bank charge is a timing difference.
    """
    out = dict(bcd.pub583_sections(_write(tmp_path, _html(GOOD))))
    timing = next(c for c in out if c.endswith(bcd.TIMING))
    charge = next(c for c in out if c.endswith(bcd.UNENTERED))

    assert "bank charges" not in out[timing], (
        "the timing passage carries POS1, whose answer is 'no entry in the "
        "books'. A bank charge nobody entered is an ENTRY.")
    assert "bank charges" in out[charge]
    assert "did not clear" not in out[charge]

    lead = "The statement balance may not agree"
    assert lead in out[timing] and lead in out[charge], (
        "both causes hang off one sentence stem; a fragment starting 'Includes "
        "bank charges' cannot be checked line by line against the page")
    assert f"{bcd.RECONCILING_LEAD} Does not include" in out[timing], (
        "the conjunction joining the two causes belongs to neither of them: "
        "spliced on, this stores 'if the statement: or Does not include "
        "deposits', which no reader can match against the page")


def test_a_moved_charge_marker_is_refused_rather_than_matched_loosely(tmp_path):
    """The second cut refuses on the same terms as the first. A publication that
    reworded its enumeration would otherwise silently store one rule again."""
    body = GOOD.replace(bcd.CHARGE_SPLIT, "or omits deposits")
    with pytest.raises(ValueError, match="not in the reconciliation section"):
        bcd.pub583_sections(_write(tmp_path, _html(body)))


def test_a_moved_split_marker_is_refused_rather_than_matched_loosely(tmp_path):
    """The publication is revised. A marker that no longer matches has to be
    re-read by a person: matching loosely would store half a rule under a
    citation naming the whole one."""
    body = GOOD.replace(bcd.RECONCILING_SPLIT, "By reconciling, you will:")
    with pytest.raises(ValueError, match="not in the reconciliation section"):
        bcd.pub583_sections(_write(tmp_path, _html(body)))


def test_an_oversized_section_is_refused_rather_than_trimmed(tmp_path):
    """THE BUG THIS REPLACED. The first version capped the body at 2,400
    characters and returned what fitted — which silently dropped "Update your
    checkbook and journals for items shown on the reconciliation as not recorded
    (such as service charges) or recorded incorrectly", the one sentence the
    whole desk turns on. A cap that truncates is a partial read wearing a
    limit's clothes."""
    body = GOOD + " padding." * (bcd.SECTION_LIMIT // 6)
    with pytest.raises(ValueError, match="over the"):
        bcd.pub583_sections(_write(tmp_path, _html(body)))


def test_a_missing_section_is_refused(tmp_path):
    """A heading that has moved must be re-read, never matched loosely."""
    html = _html(GOOD).replace("Bookkeeping System", "Bookkeeping", 2)
    with pytest.raises(ValueError, match="has no section"):
        bcd.pub583_sections(_write(tmp_path, html))


def test_the_body_is_read_and_not_the_table_of_contents(tmp_path):
    """The contents lists every heading first, so the first match is a link with
    nothing under it. Read the last."""
    out = dict(bcd.pub583_sections(_write(tmp_path, _html(GOOD))))
    kinds = next(c for c in out if "Kinds of Records" in c)
    assert out[kinds] == "body of Kinds of Records To Keep"


# ── the CFR reader ───────────────────────────────────────────────────────────

def test_a_run_in_headings_outer_label_is_placed_like_any_other(tmp_path):
    """`(a) General rule. (1) …` opens two levels in one element. Resetting the
    stack to the two labels it read produced a second `26 CFR 1.446-1(d)(1)` out
    of `(e)(2)(ii)(d) Changes involving depreciable assets—(1) Scope.` — a
    lower-case letter at a fourth level, which is the shape that makes
    `extract_ecfr` refuse this section. The record caught the duplicate and the
    factory deleted the desk rather than ship it; this agrees with that refusal
    instead of relying on it."""
    xml = tmp_path / "s.xml"
    xml.write_text(
        "<DIV8>"
        "<P>(a) General rule. (1) First paragraph.</P>"
        "<P>(2) Second paragraph.</P>"
        "<P>(b) Exceptions. (1) Under b.</P>"
        "<P>(d) Deep run-in. (1) Not a top-level d.</P>"
        "</DIV8>", encoding="utf-8")
    kept, excluded = bcd.cfr_paragraphs(xml)
    cites = [c for c, _ in kept]
    assert cites == ["26 CFR 1.446-1(a)(1)", "26 CFR 1.446-1(a)(2)",
                     "26 CFR 1.446-1(b)(1)"]
    assert len(cites) == len(set(cites)), "a citation was produced twice"
    assert any("(d)" in e for e in excluded), (
        "the unplaceable run-in must be named, not silently dropped")
