"""The scorer that measures the classifier against real IRS forms.

Its whole job is to be honest about a number, so the tests are about the ways a
score can flatter itself.
"""

from __future__ import annotations

import pytest

from satc.ingest.corpus import BLANKS, Score, Verdict, report, score


def _v(**kw):
    base = dict(stem="fw2", expected="W-2", got="W-2", method="text", confidence="HIGH")
    base.update(kw)
    return Verdict(**base)


# -- the distinction that matters ---------------------------------------------

def test_right_by_filename_is_not_counted_as_right_by_content():
    """`fw2.pdf` classifies as a W-2 because of its NAME. A client's upload is
    called IMG_4471.pdf. On the first real run three of eight "right" answers
    were filename saves, so the honest content score was five of thirteen."""
    s = Score([_v(method="filename")])
    assert s.by_content == 0
    assert s.by_name == 1


def test_a_content_verdict_counts():
    assert Score([_v(method="text")]).by_content == 1


def test_wrong_is_distinguished_from_unclassified():
    """A wrong answer files the document under another form and closes that
    form's request. Unclassified leaves it open and asks a human. They are not
    the same failure and must never be summed."""
    s = Score([_v(stem="a", expected="1099-G", got="1099-NEC"),
               _v(stem="b", expected="1098", got="Unclassified")])
    assert s.wrong == 1 and s.unknown == 1


def test_an_unconfigured_type_is_not_scored_at_all():
    """Schedule C has no entry in classification.yaml, so Unclassified is the
    correct and honest answer -- not a miss to be counted against anything."""
    s = Score([_v(stem="f1040sc", expected=None, got="Unclassified")])
    assert s.total == 0 and s.wrong == 0


# -- S2: a check that examined nothing ----------------------------------------

def test_an_empty_folder_reports_nothing_to_score_rather_than_a_clean_sheet(tmp_path):
    """corpus/blanks/ ships empty. A run with no forms in it must not look like
    a pass -- a green check that examined nothing is worse than a red one."""
    (tmp_path / "expected.yaml").write_text("expect:\n  fw2: \"W-2\"\n")
    s = score(tmp_path)
    assert s.total == 0
    assert "NOTHING TO SCORE" in report(s)


def test_a_form_that_was_never_fetched_is_skipped_not_failed(tmp_path):
    """Thirteen of fifteen fetched is a normal outcome. An absent file is not a
    wrong answer."""
    (tmp_path / "expected.yaml").write_text('expect:\n  f1099b: "1099-B"\n')
    assert score(tmp_path).total == 0


# -- against the real forms, when they are present ----------------------------

@pytest.mark.skipif(not list(BLANKS.glob("*.pdf")),
                    reason="corpus/blanks is empty — see its README")
def test_the_real_blanks_do_not_get_worse():
    """THE BASELINE, a ceiling on WRONG and a floor on right-by-content.

    Measured on the fourteen real blanks the firm fetched, 31 Aug 2026:

        before the page fix   5 of 13 by content · +3 by filename · 4 WRONG · 1 unknown
        after                13 of 13 by content · 0 by filename  · 0 WRONG · 0 unknown

    All four wrong answers were one bug: page 1 of a real IRS document is a
    notice, every rung read page 1, and the notice's worked example is 1099-NEC.

    ZERO WRONG IS NOW THE CEILING, and that is the point of writing it down. A
    change that improves one form by breaking another is caught here rather than
    celebrated, and the floor stops a "fix" that buys correctness by refusing to
    answer.
    """
    s = score()
    assert s.total >= 13, f"expected the full set, scored {s.total}"
    assert s.wrong == 0, (
        f"the classifier got {s.wrong} form(s) confidently wrong:\n" + report(s))
    assert s.by_content >= 13, (
        f"content-only accuracy fell ({s.by_content} < 13):\n" + report(s))
    assert s.by_name == 0, (
        "a form is being saved by its filename again — a client's upload is "
        "called IMG_4471.pdf:\n" + report(s))
