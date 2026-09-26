"""Every position quotes the words of its paragraph that it rests on.

SARCIA PILOT 3, 25 September 2026. The desk's second readers refused seven of
the nine answers it tried to serve, and four of those were ratified positions
pinned to a paragraph that did not carry them. Read against the stored text,
five of twenty were wrong: POS7 cited the paragraph that DEFINES entertainment
for a rule about beverages, POS8 a paragraph with no percentage for a
50-percent rule, POS15 a definition for a $2,000 threshold, POS17 and POS20
definitions for the firm's practice of asking first.

THE FIRM: *"how does this kind of thing keep happening"*. Because every check
here asked whether a citation RESOLVED, never whether the paragraph SAID it. The
second reader was the only thing that read the words, and it runs at answer time
on the positions a question happens to reach. `Rests on:` moves the same reading
to the moment a position is written.

WHERE A POSITION SITS AND WHAT IT RESTS ON ARE SEPARATE. The first fix moved
POS7 to the paragraph that carries it, and this suite refused it at once: a
position answers every question on its citation, so the concession-stand and
stadium-suite problems would have been answered with the brewery rule. POS7
stays where bars are named; `Rests on:` names the paragraph one down.

What this proves and what it does not: the words are real and in order. Whether
they carry the position is still a reading -- but it is now one line, next to
the position, where anybody can see it.
"""
from __future__ import annotations

import pathlib
import re
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                               # noqa: E402
import judging                                              # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

FILE = pathlib.Path("positions") / "POSITIONS.md"


def _copy(tmp_path):
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    return dst


def _edit(corpus, pid, old, new):
    p = corpus / FILE
    text = p.read_text(encoding="utf-8")
    head = re.search(rf"^## {pid} · .*$", text, re.M)
    nxt = re.search(r"^## POS\d+ · ", text[head.end():], re.M)
    end = head.end() + nxt.start() if nxt else len(text)
    block = text[head.start():end]
    assert old in block, f"{old!r} not in {pid}"
    p.write_text(text[:head.start()] + block.replace(old, new, 1) + text[end:],
                 encoding="utf-8")


def _load(corpus):
    return record.load(corpus)


def test_every_cited_position_quotes_its_paragraph():
    d = record.load(CORPUS)
    cited = [q for q in d.positions if not q.is_policy]
    assert len(cited) == 16, [q.id for q in cited]
    assert all(q.rests_on for q in cited), [q.id for q in cited if not q.rests_on]


def test_a_position_that_does_not_say_what_it_rests_on_is_refused(tmp_path):
    c = _copy(tmp_path)
    p = c / FILE
    text = p.read_text(encoding="utf-8")
    p.write_text(re.sub(r'\n\n\*\*Rests on:\*\* "the taxpayer shall allocate[^\n]*',
                        "", text, count=1), encoding="utf-8")
    with pytest.raises(record.RecordError, match="does not say which words"):
        _load(c)


def test_words_the_paragraph_does_not_contain_are_refused(tmp_path):
    """POS8 as it was: a 50-percent rule resting on (a)(1), which holds no
    percentage. Quote the percentage against (a)(1) and it is refused."""
    c = _copy(tmp_path)
    _edit(c, "POS8", '26 CFR 1.274-12(a)(2) — "the amount allowable',
          '"the amount allowable')
    with pytest.raises(record.RecordError, match="does not contain"):
        _load(c)


def test_one_changed_word_inside_a_quote_is_refused(tmp_path):
    c = _copy(tmp_path)
    _edit(c, "POS19", "on the basis of mileage", "on the basis of receipts")
    with pytest.raises(record.RecordError, match="does not contain"):
        _load(c)


def test_resting_on_a_paragraph_nobody_stored_is_refused(tmp_path):
    c = _copy(tmp_path)
    _edit(c, "POS7", "26 CFR 1.274-11(b)(1)(ii) —", "26 CFR 1.274-11(b)(1)(ix) —")
    with pytest.raises(record.RecordError, match="does not store"):
        _load(c)


def test_a_firm_policy_may_not_quote_a_paragraph(tmp_path):
    """A quotation beside a policy reads as authority it does not have."""
    c = _copy(tmp_path)
    _edit(c, "POS15", "**Kind:** firm policy",
          '**Kind:** firm policy\n\n**Rests on:** "Third party payment network"')
    with pytest.raises(record.RecordError, match="is firm policy and quotes"):
        _load(c)


@pytest.mark.parametrize("pid", ["POS15", "POS17", "POS20"])
def test_the_three_no_paragraph_carries_are_marked_as_the_firms(pid):
    q = next(q for q in record.load(CORPUS).positions if q.id == pid)
    assert q.is_policy and q.unreviewed
    assert q.citation.startswith("SATC policy —")


@pytest.mark.parametrize("pid, sits, rests", [
    ("POS7", "26 CFR 1.274-11(b)(1)(i)", ("26 CFR 1.274-11(b)(1)(ii)",)),
    ("POS8", "26 CFR 1.274-12(a)(1)",
     ("26 CFR 1.274-12(a)(1)", "26 CFR 1.274-12(a)(2)")),
])
def test_a_position_stays_where_its_topic_is(pid, sits, rests):
    q = next(q for q in record.load(CORPUS).positions if q.id == pid)
    assert q.citation == sits and q.rests_at == rests


def _served(pid):
    d = record.load(CORPUS)
    q = next(p for p in d.positions if p.id == pid)
    out = engine.serve(engine.Answer(citation=q.citation, position=q.position),
                       d, question="a test question")
    assert isinstance(out, engine.Served), out
    return q, out


@pytest.mark.parametrize("pid", ["POS7", "POS8"])
def test_the_second_reader_is_handed_what_the_position_rests_on(pid):
    """THE PILOT'S REFUSALS, UNDONE FOR THE RIGHT REASON. A reader quoting the
    words the position rests on now finds them in what they are handed."""
    q, out = _served(pid)
    words = " [...] ".join(w for _, w in q.rests_on)
    seen = judging.read(judging.Judgment(by="reader", supports=True,
                                         because=words), out.passage)
    assert seen.verdict == judging.HOLDS, seen
    assert all(w in str(out) for _, w in q.rests_on)


def test_a_position_resting_on_its_own_paragraph_serves_that_paragraph():
    q, out = _served("POS19")
    assert out.passage == record.load(CORPUS).passage(q.citation).text


def test_one_firm_policy_is_never_served_as_anothers_opposite_answer():
    """`SATC policy — <which>` shares its dash with the firm's two-answer
    convention. With four policies, every one became `alongside` every other
    until `record._stem` stopped treating the policy prefix as a section."""
    d = record.load(CORPUS)
    policies = [q for q in d.positions if q.is_policy]
    assert len(policies) == 4
    for q in policies:
        assert d.alongside(q.citation) == (), q.id



def test_applies_at_is_only_for_a_policy(tmp_path):
    c = _copy(tmp_path)
    _edit(c, "POS19", "**Rests on:**",
          "**Applies at:** 26 CFR 1.280F-6(e)(2)\n\n**Rests on:**")
    with pytest.raises(record.RecordError, match="is not firm policy"):
        _load(c)


def test_a_policy_cannot_apply_at_a_paragraph_nobody_stored(tmp_path):
    c = _copy(tmp_path)
    _edit(c, "POS15", "**Applies at:** 26 CFR 1.6050W-1(c)(3)",
          "**Applies at:** 26 CFR 1.6050W-1(c)(9)")
    with pytest.raises(record.RecordError, match="nothing could ever show it"):
        _load(c)


# --- narrowing keeps what a position needs (Codex on #398) -----------------------

def test_narrowing_to_a_position_keeps_the_paragraphs_it_rests_on():
    """A brief is the record narrowed to what the pool returned. Narrowed to
    POS7's own citation, (b)(1)(ii) was dropped, so the served passage fell
    back to (b)(1)(i) and the second reader was handed the wrong paragraph
    again -- the guarantee this file exists for, undone one layer down."""
    d = record.load(CORPUS)
    q = next(p for p in d.positions if p.id == "POS7")
    narrow = d.narrowed_to([q.citation])
    out = engine.serve(engine.Answer(citation=q.citation, position=q.position),
                       narrow, question="a test question")
    assert isinstance(out, engine.Served), out
    assert "26 CFR 1.274-11(b)(1)(ii)" in out.passage
    words = q.rests_on[0][1]
    assert judging.read(judging.Judgment(by="reader", supports=True,
                                         because=words),
                        out.passage).verdict == judging.HOLDS


def test_narrowing_to_where_a_policy_applies_keeps_the_policys_source():
    """Narrowed to § 1.6050W-1(c)(3), POS15 came along through `Applies at:`
    and its source, the firm's policy row, did not -- so serving it raised."""
    d = record.load(CORPUS)
    q = next(p for p in d.positions if p.id == "POS15")
    narrow = d.narrowed_to(["26 CFR 1.6050W-1(c)(3)"])
    assert q in narrow.positions
    out = engine.serve(engine.Answer(citation=q.citation, position=q.position),
                       narrow, question="a test question")
    assert isinstance(out, engine.Served), out


@pytest.mark.parametrize("empty", ['"[...]"', '"  "', '"the"'])
def test_a_quotation_that_carries_no_words_is_refused(tmp_path, empty):
    """Codex on #398: `"[...]"` elides every word, so `elided_match` has no
    segment to look for and passes on any paragraph -- a position resting on
    nothing, checked as resting on something. A quotation has to carry words a
    reader can weigh; one word carries none."""
    c = _copy(tmp_path)
    _edit(c, "POS19", '"the taxpayer shall allocate the use of the property on the basis of mileage."', empty)
    with pytest.raises(record.RecordError):
        _load(c)


def test_a_position_can_rest_on_a_citation_that_carries_a_quoted_title(tmp_path):
    """Codex on #398: the citation half of `Rests on:` refused `"`, so no
    position could rest on `IRS Pub. 463 (2025), "Actual Car Expenses"` or any
    other publication cited by its quoted section title."""
    c = _copy(tmp_path)
    _edit(c, "POS19", '**Rests on:** "the taxpayer shall allocate',
          '**Rests on:** IRS Pub. 463 (2025), "Actual Car Expenses" — "If you '
          'don\'t use the standard mileage rate, you may be able to deduct your '
          'actual car expenses."\n"the taxpayer shall allocate')
    q = next(p for p in _load(c).positions if p.id == "POS19")
    assert q.rests_at == ('IRS Pub. 463 (2025), "Actual Car Expenses"',
                          "26 CFR 1.280F-6(e)(2)")
