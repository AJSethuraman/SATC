"""The notification the firm asked for, and the things it must never carry.

THE FIRM, 8 September 2026: *"Nothing stops if it isn't a blocker. I'm addition,
I want a good way for me to be directly notified so I can answer as quickly as I
can"*. The channel was proved the same evening -- a test push reached their
phone -- so what is left is what the desk is allowed to put on it.
"""
import pytest

import notifying


def test_the_question_leads_because_it_is_what_gets_answered():
    out = notifying.line("Are unidentified deposits gross receipts?", ref="q-0007")
    assert out.startswith("Desk parked: Are unidentified deposits")
    assert out.endswith("[q-0007]")


def test_the_reference_survives_a_question_too_long_to_fit():
    """A truncated reference cannot be quoted back, so it is never the thing cut."""
    out = notifying.line("x" * 400, ref="q-0008")
    assert len(out) <= notifying.LIMIT
    assert out.endswith("[q-0008]")


def test_a_long_unbroken_token_does_not_gut_the_line():
    """THE BUG THIS FILE WAS WRITTEN AGAINST. The first version cut at the last
    space it could find, so `"x" * 400` came back as `"Desk parked… [q-0008]"` --
    21 characters of a 200-character budget, because the only space was the one
    after "parked:". A question carrying a url or a pasted blob is exactly the
    one that would do it."""
    out = notifying.line("x" * 400, ref="q-0008")
    assert len(out) > notifying.LIMIT * 0.9, (
        f"the budget is being thrown away: {out!r}")


def test_markdown_is_stripped_because_a_notification_does_not_render_it():
    out = notifying.line("Is **this** a `deduction`?", ref="q-1")
    for ch in "*_`#>":
        assert ch not in out


def test_a_multi_line_question_becomes_one_line():
    out = notifying.line("First line\nsecond line", ref="q-1")
    assert "\n" not in out and "First line second line" in out


# --- the guard, broken on purpose ------------------------------------------
# CLAUDE.md: "Only masked/last-4 values belong in artifacts, logs, and
# workbooks -- never real taxpayer PII." A push is the most escaping artifact
# in the system: it leaves the machine and lands on a lock screen.

@pytest.mark.parametrize("bad, what", [
    ("client ssn 123-45-6789 on the return", "social security number"),
    ("the ein is 12-3456789 per the notice", "employer identification number"),
    ("wire hit account 402213897755 today", "account number"),
])
def test_it_refuses_rather_than_sending_something_shaped_like_an_identifier(bad, what):
    with pytest.raises(ValueError) as e:
        notifying.line(bad, ref="q-9")
    assert what in str(e.value)


def test_the_refusal_says_where_the_question_still_is():
    """A refused notification must not read as a lost question."""
    with pytest.raises(ValueError) as e:
        notifying.line("ssn 123-45-6789", ref="q-77")
    assert "q-77" in str(e.value)


def test_the_refusal_does_not_repeat_the_thing_it_refused_to_send():
    """An exception is written to a log. Echoing the number there would move the
    leak rather than stop it."""
    with pytest.raises(ValueError) as e:
        notifying.line("ssn 123-45-6789", ref="q-77")
    assert "123-45-6789" not in str(e.value)


def test_the_reason_is_checked_too_not_only_the_question():
    with pytest.raises(ValueError):
        notifying.line("what do we do here?", ref="q-1", why="ein 12-3456789")


def test_a_question_with_no_way_to_answer_it_is_refused():
    with pytest.raises(ValueError):
        notifying.line("a real question", ref="")
    with pytest.raises(ValueError):
        notifying.line("   ", ref="q-1")


def test_ordinary_numbers_still_get_through():
    """Over-eager is the intended tuning, but a close is full of amounts and
    years, and a guard that ate all of them would be a guard nobody kept on."""
    for ok in ("is $4,215.60 deductible?", "for tax year 2025?",
               "the 1099-NEC threshold of 600", "invoice 20458 from March"):
        assert notifying.line(ok, ref="q-1")


def test_a_reason_code_is_not_mangled_on_the_way_out():
    """CAUGHT BY RUNNING THE REAL PATH, not by a unit test. The markdown
    stripper took the underscore with it and `authority_absent` reached the firm
    as `authorityabsent` -- the one word in the line they would recognise."""
    out = notifying.line("what now?", ref="U1", why="authority_absent")
    assert "authority_absent" in out


def test_for_entry_reads_the_queue_entry_the_engine_filed():
    class Entry:
        id, question, failed_because = "U7", "is this deductible?", "authority_absent"
    out = notifying.for_entry(Entry())
    assert out.startswith("Desk parked: is this deductible?")
    assert "authority_absent" in out and out.endswith("[U7]")
