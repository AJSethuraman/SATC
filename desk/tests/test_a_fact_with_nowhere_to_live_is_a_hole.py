"""A fact the caller has and the record cannot hold is a HOLE, not litter.

THE INCIDENT, 8 September 2026, on the first run where the follow-up loop
worked end to end. A desk was handed four facts, three of which matched no
field any desk declares. They were dropped — no line in the brief, no warning,
no error. The desk then served an answer that turned on one of them.

Its own account:

    "It did not error and it did not reject a name. It SWALLOWED three of the
     four [...] I went on to serve an answer built on three facts the desk had
     already discarded."

    "An error would have been fine. A `no_field_for_this_fact` refusal would
     have been excellent. Silence is the one outcome that teaches a caller its
     facts landed when they did not."

THE VOCABULARY ALREADY EXISTED AND NEVER FIRED. `no_field_for_this_fact` is
annotated *"nobody ever decided this should be written down"* — precisely this
case. The path that raises it is on the ANSWERING side, where a POSITION names a
fact the file lacks. Nothing looked the other way: a fact the CALLER holds and
the record cannot. That is a preparer discovering, by doing the work, that the
firm tracks nowhere to put something, and it was being thrown away.
"""
import re
from pathlib import Path

import pytest

import ask
import record

HERE = Path(__file__).resolve().parents[1]
Q = "we bought a forklift, deducted or capitalized"


@pytest.fixture
def caps():
    return record.load(HERE / "corpus")


@pytest.fixture
def assets(tmp_path):
    """A record that declares NO facts, CONSTRUCTED.

    It was `desks/fixed-assets`, which happened to declare none. `dec-kill`
    merged the seven and the corpus declares all three, so there is no record on
    disk left to point at — and a property proved on whichever directory
    happened to satisfy it was always the weaker version: it goes green the day
    that directory declares a fact, having checked nothing.

    Stripping `Records:` out of the real corpus does not work either, and the
    reason is a guard doing its job: `record.load` refuses a position that needs
    a field nothing declares, so the corpus without its `Records:` line is not a
    legal record at all. So this is built from nothing — one source, one
    passage, one problem, no positions, no facts.
    """
    d = tmp_path / "corpus"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** primary · **Access:** public_fetch · "
        "**May store:** full_text · **Checked:** 2026-09-10\n\n"
        "**Citation prefix:** 26 CFR\n\n**Why:** 17 U.S.C. § 105 places a work "
        "of the United States Government in the public domain.\n",
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1\n\n**Answer:** must capitalize"
        "\n\n**Facts:** f\n", encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-10 · "
        "**Kind:** rule\n\n> must capitalize\n", encoding="utf-8")
    (d / "SUBJECTS.md").write_text(
        "## corpus · A record that records nothing\n\n"
        "**Answered from S1:** widgets\n", encoding="utf-8")
    desk = record.load(d)
    assert desk.records == (), "the fixture declares a fact after all"
    return desk


# ------------------------------------------------------------- the record

def test_a_declared_fact_is_not_unrecorded(caps):
    ctx = record.Context(facts={"capitalization_rule": "the firm's default"})
    assert ctx.unrecorded(caps.records) == ()


def test_an_undeclared_one_is_named(caps):
    ctx = record.Context(facts={"invoice_amount": "18,400"})
    assert ctx.unrecorded(caps.records) == ("invoice_amount",)


def test_a_record_declaring_nothing_can_hold_nothing(assets):
    """A record declaring no facts has a hole for every fact."""
    assert assets.records == ()
    ctx = record.Context(facts={"capitalization_rule": "x", "invoice_amount": "y"})
    assert ctx.unrecorded(assets.records) == ("capitalization_rule",
                                              "invoice_amount")


def test_a_blank_value_is_not_a_hole(caps):
    """Nothing was told to us, so nothing has nowhere to go."""
    assert record.Context(facts={"invoice_amount": "  "}).unrecorded(
        caps.records) == ()


def test_the_made_up_field_that_proved_it(caps, assets):
    """The desk session's own probe, kept as the test."""
    ctx = record.Context(facts={"totally_made_up_field": "banana"})
    assert ctx.unrecorded(caps.records) == ("totally_made_up_field",)
    assert ctx.unrecorded(assets.records) == ("totally_made_up_field",)


# ---------------------------------------------------- what the answerer sees

def test_the_brief_names_it_instead_of_dropping_it(assets):
    ctx = record.Context(facts={"invoice_amount": "18,400"})
    brief = ask.brief(Q, assets, ctx)
    assert "invoice_amount" in brief
    assert "NOWHERE to record it" in brief


def test_it_is_not_printed_as_a_fact_on_file(caps):
    """THE FAILURE THIS MUST NOT BECOME. Printed under "What the file already
    says", a fact with no field reads as verified and retained. It is neither."""
    ctx = record.Context(facts={"invoice_amount": "18,400",
                                "capitalization_rule": "the firm's default"})
    brief = ask.brief(Q, caps, ctx)
    on_file = brief.split("## What the file already says")[1].split("##")[0]
    assert "capitalization_rule" in on_file
    assert "invoice_amount" not in on_file


def test_the_answerer_is_told_not_to_answer_from_it(assets):
    ctx = record.Context(facts={"invoice_amount": "18,400"})
    brief = ask.brief(Q, assets, ctx)
    assert "not facts you may answer from" in brief
    assert "no_field_for_this_fact" in brief


def test_and_is_told_it_will_not_survive(assets):
    """The half a caller most needs: this does not persist. The next agent
    asked the same question starts without it."""
    brief = ask.brief(Q, assets, record.Context(facts={"invoice_amount": "1"}))
    assert "nothing will retain it" in brief


def test_nothing_is_added_when_every_fact_has_a_home(caps):
    """THE CONTROL. A section that appears always says nothing ever."""
    brief = ask.brief(Q, caps, record.Context(
        facts={"capitalization_rule": "the firm's default"}))
    assert "NOWHERE to record it" not in brief


def test_nor_when_no_facts_were_given_at_all(caps):
    assert "NOWHERE to record it" not in ask.brief(Q, caps,
                                                   record.NOTHING_ON_FILE)


# ------------------------------------- the default caveat stops lying

def test_the_default_caveat_asks_while_the_fact_is_silent(caps):
    brief = ask.brief(Q, caps, record.NOTHING_ON_FILE)
    assert "nothing here says whether this one is" in brief


def test_and_stops_saying_that_once_the_file_says(caps):
    """FOUND ON THE FIRST RUN WHERE THE FOLLOW-UP LOOP WORKED. *"'Nothing here
    says whether this one is' is false in that exact brief. The brief says [...]
    Since 0.9.2 exists to make that loop work, this is the sentence it breaks."*
    """
    brief = ask.brief(Q, caps, record.Context(
        facts={"capitalization_rule": "the firm's default; no client rule"}))
    assert "nothing here says whether this one is" not in brief
    assert "The file says this client is on the firm's default" in brief


def test_and_still_says_to_read_what_was_recorded(caps):
    """Knowing a rule is recorded is not knowing what it says."""
    brief = ask.brief(Q, caps, record.Context(
        facts={"capitalization_rule": "expense everything under $2,500"}))
    assert "read it before relying on this" in brief
