"""The file an engagement's facts live in, and everything it refuses.

WHY IT EXISTS, measured rather than assumed. On 7 September 2026 the close's
eighteen questions were put through the production path and five refused with
`context_not_on_file` — the desks asking for `trade`, `taxpayer` and
`capitalization_rule`. `engine.serve()` takes all three. Nothing produced them:
the only thing carrying facts was a worked example's own `On file` line, which
is a test fixture. The refusals were correct and unanswerable.

These tests are mostly about what the reader REFUSES, because that is where a
file of facts goes wrong: a fact nobody recorded reads exactly like one somebody
did.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engagements                                          # noqa: E402
import record                                               # noqa: E402
import ask                                                  # noqa: E402


GOOD = """# Engagement · alpha-2026

## trade

**Value:** general contractor
**Recorded by:** AJS
**Recorded on:** 2026-09-07
**From:** the interview's business-activity answer

## capitalization_rule

**Value:** none
**Recorded by:** AJS
**Recorded on:** 2026-09-07
**From:** asked at the interview; the client has no threshold of their own
"""


@pytest.fixture
def outside(tmp_path):
    """A path the plugin does not contain, which is the only kind it reads."""
    def write(text, name="engagement.md"):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p
    return write


def test_the_vocabulary_is_read_off_the_desks_and_not_listed_anywhere():
    """A list typed into this module would be a second copy of the `Records:`
    lines, and the copy is what goes stale."""
    known = engagements.declared()
    from_desks = {}
    for d in sorted((HERE / "desks").iterdir()):
        if (d / "SOURCES.md").is_file():
            for name in record.load(d).records:
                from_desks.setdefault(name, []).append(d.name)
    assert known == from_desks
    assert known, "no desk declares a fact, so this reader guards nothing"

    src = (HERE / "engagements.py").read_text(encoding="utf-8")
    body = src.split("def declared(")[1].split("\ndef ")[0]
    for name in known:
        assert name not in body, (
            f"{name!r} is written into `declared`; the desks declare the "
            f"vocabulary and this reads it")


def test_a_file_the_desks_can_be_handed(outside):
    eng = engagements.load(outside(GOOD))
    assert eng.ref == "alpha-2026"
    assert [f.name for f in eng.facts] == ["trade", "capitalization_rule"]
    assert eng.by_name("trade").by == "AJS"
    assert eng.by_name("trade").on == "2026-09-07"
    ctx = eng.context()
    assert isinstance(ctx, record.Context)
    assert ctx.facts == {"trade": "general contractor",
                         "capitalization_rule": "none"}


def test_the_context_carries_values_and_never_who_recorded_them(outside):
    """A desk answers from authority and from what the file records. Who wrote
    a fact down is the firm's audit trail, not the desk's input."""
    ctx = engagements.load(outside(GOOD)).context()
    assert "AJS" not in str(ctx.facts)
    assert "2026-09-07" not in str(ctx.facts)
    assert "interview" not in str(ctx.facts)


def test_none_survives_the_round_trip_as_the_third_state(outside):
    """`none` means somebody asked and the answer was no. Collapsed into
    "nothing recorded" it becomes a question nobody asked, which is the thing
    `Context.standing_rule` exists to keep apart."""
    ctx = engagements.load(outside(GOOD)).context()
    assert ctx.standing_rule("capitalization_rule") == record.NONE
    assert ctx.standing_rule("taxpayer") == record.ABSENT


def test_a_fact_no_desk_records_is_refused(outside):
    text = GOOD + "\n## favourite_colour\n\n**Value:** blue\n" \
                  "**Recorded by:** AJS\n**Recorded on:** 2026-09-07\n"
    with pytest.raises(engagements.EngagementError) as e:
        engagements.load(outside(text))
    assert "favourite_colour" in str(e.value)
    assert "trade" in str(e.value), "the refusal does not say what IS recorded"


@pytest.mark.parametrize("drop", ["**Recorded by:** AJS\n",
                                  "**Recorded on:** 2026-09-07\n",
                                  "**Value:** general contractor\n"])
def test_a_fact_nobody_recorded_is_not_a_recorded_fact(outside, drop):
    with pytest.raises(engagements.EngagementError):
        engagements.load(outside(GOOD.replace(drop, "", 1)))


def test_a_day_that_is_not_a_day_is_refused(outside):
    with pytest.raises(engagements.EngagementError):
        engagements.load(outside(GOOD.replace("2026-09-07", "2026-02-31", 1)))


#: EVERY SHAPE THE VAULT EXISTS FOR. Separated and not, both kinds. The value is
#: written under a fact name the desks DO declare, because a guard that only
#: fires on a suspicious field name catches nothing a careless paste does.
@pytest.mark.parametrize("value", ["123-45-6789", "12-3456789", "123456789",
                                   "the EIN is 12-3456789 on the letter"])
def test_anything_shaped_like_a_taxpayer_number_is_refused(outside, value):
    text = GOOD.replace("general contractor", value, 1)
    with pytest.raises(engagements.EngagementError) as e:
        engagements.load(outside(text))
    assert "vault" in str(e.value)


def test_a_number_that_is_not_an_identifier_still_reads(outside):
    """The guard must not eat the facts. A threshold is a number too."""
    text = GOOD.replace("**Value:** none", "**Value:** $2,500 per invoice", 1)
    eng = engagements.load(outside(text))
    assert eng.by_name("capitalization_rule").value == "$2,500 per invoice"


def test_the_file_may_not_live_inside_the_plugin(tmp_path):
    """`desk` is a checkout that gets pushed. A client's affairs in it are one
    `git add -A` from being published, and the reader is where that is stopped
    rather than a line in a README."""
    inside = HERE / "engagement-should-not-be-here.md"
    inside.write_text(GOOD, encoding="utf-8")
    try:
        with pytest.raises(engagements.EngagementError) as e:
            engagements.load(inside)
        assert "inside the desk plugin" in str(e.value)
    finally:
        inside.unlink()


def test_a_reference_is_a_reference_and_not_a_person(outside):
    with pytest.raises(engagements.EngagementError):
        engagements.load(outside(GOOD.replace("alpha-2026", "Smith,", 1)))


def test_a_file_recording_nothing_is_refused(outside):
    with pytest.raises(engagements.EngagementError) as e:
        engagements.load(outside("# Engagement · alpha-2026\n"))
    assert "indistinguishable" in str(e.value)


def test_one_fact_recorded_twice_is_refused(outside):
    dup = GOOD + "\n## trade\n\n**Value:** hairstylist\n" \
                 "**Recorded by:** AJS\n**Recorded on:** 2026-09-07\n"
    with pytest.raises(engagements.EngagementError) as e:
        engagements.load(outside(dup))
    assert "twice" in str(e.value)


def test_what_is_missing_is_reported_by_name(outside):
    """The half that matters. A file listing what it holds leaves a reader to
    assume the rest were not needed."""
    eng = engagements.load(outside(GOOD))
    assert engagements.gaps(eng) == {
        "taxpayer": ["rewards-and-information-returns"]}
    assert set(engagements.gaps(None)) == set(engagements.declared()), \
        "no file at all must answer 'everything', not raise"


def test_the_desks_actually_take_it(outside):
    """END TO END, and the point of the whole file: the same question reaches
    the same desk with and without it, and only one of them can be answered."""
    ctx = engagements.load(outside(GOOD)).context()
    question = "they bought clothing at that store — is it a personal expense?"

    blind = dict(ask.consult(question))
    seeing = dict(ask.consult(question, context=ctx))
    assert blind and seeing, "the question reaches no desk at all"
    assert set(blind) == set(seeing), "the file changed which desk was asked"

    # WHICH DESK RECORDS WHAT IS READ OFF THE DESK, not matched in the brief's
    # prose -- the first version of this looked for "trade" in the text and
    # passed on the capitalisation desk, whose authority is full of "trade or
    # business". A word in a regulation is not a declaration.
    checked = 0
    for name, brief in seeing.items():
        for fact in record.load(HERE / "desks" / name).records:
            value = ctx.facts.get(fact)
            if not value:
                continue
            checked += 1
            assert value in brief, (
                f"{name} records {fact}, the file has it, and the brief does "
                f"not carry it")
            assert value not in blind[name], (
                f"{name}'s brief carries {fact} with no file behind it")
    assert checked, "no desk on this question records a fact this file holds"


# ---------------------------------------------------------------------------
# The blank file the firm starts from. Generated, never kept as a template: a
# template is a second copy of the `Records:` lines, and the copy goes stale the
# first time a desk starts recording something new.


def test_the_blank_file_covers_every_fact_the_desks_record(capsys):
    from tools import engagement as cli
    assert cli.main(["new", "alpha-2026"]) == 0
    blank = capsys.readouterr().out
    for name, desks in engagements.declared().items():
        assert "## %s" % name in blank, "%s has no stub to fill in" % name
        for d in desks:
            assert d in blank, "%s does not say which desk asks for %s" % (name, d)


def test_the_blank_file_becomes_a_real_one_once_it_is_filled(outside, capsys):
    """Round trip. A starter that does not parse once filled is a starter that
    sends the firm to a refusal they cannot read."""
    from tools import engagement as cli
    cli.main(["new", "alpha-2026"])
    filled = capsys.readouterr().out.replace(
        "**Value:** \n", "**Value:** recorded at the interview\n").replace(
        "**Recorded by:** \n", "**Recorded by:** AJS\n").replace(
        "**From:** \n", "**From:** the interview\n")
    eng = engagements.load(outside(filled, "filled.md"))
    assert engagements.gaps(eng) == {}, (
        "the blank file does not cover what the desks record")


def test_the_blank_file_as_printed_is_refused(outside, capsys):
    """It is a form, not a record. Empty values must not read as facts."""
    from tools import engagement as cli
    cli.main(["new", "alpha-2026"])
    with pytest.raises(engagements.EngagementError):
        engagements.load(outside(capsys.readouterr().out, "blank.md"))
