"""A desk reply is readable whatever a console did to its punctuation.

SARCIA PILOT 2, 25 SEPTEMBER 2026. Three questions went to the desk, three
answers came back, and `relay.read` -- the tool the asking skill mandates so that
"did it answer or refuse" is never a reading task -- RAISED on all three. The
replies were right. Their punctuation was not: every em dash and middle dot had
become a hyphen.

WHERE IT HAPPENED, MEASURED rather than guessed. Occam's requests crossed the
same trigger transport with their em dashes intact (12 in each); all three desk
replies contained none. So the characters were lost on the ANSWERING side -- its
console mangles UTF-8, which Forge-Desk itself reported while transcribing a
brief. The transport is innocent and the fix does not depend on it.

TWO HALVES, BOTH HERE:
  1. The engine now writes the two lines `read` parses in plain ASCII -- `:` and
     `|` -- so there is nothing left on them for a console to break.
  2. `read` accepts every spelling a reply can arrive in: the new one, the old
     em-dash one, and whatever a console turned either into. Not guessing: the
     reason is a closed set of snake_case codes and "confirmed" anchors the end
     of a grade line, so the meaning is recoverable whichever characters survived.

A PIPE, NOT A HYPHEN. A served answer's grade line can already carry a dash
INSIDE a value ("not binding — read the note below"). Mangled, that is a hyphen
indistinguishable from a hyphen separator, so a separator had to be something a
value never contains.
"""
from __future__ import annotations

import re

import pytest

import engine
import relay

#: THE THREE BANNERS EXACTLY AS THEY ARRIVED in pilot 2, copied from the stored
#: trigger records. No client data: a reason code and the word "corpus".
PILOT_2 = [
    "THE DESK DID NOT ANSWER - authority_permits_choice  -  corpus",
    "THE DESK DID NOT ANSWER - facts_not_established  -  corpus",
    "THE DESK DID NOT ANSWER - context_not_on_file  -  corpus",
]


@pytest.mark.parametrize("banner", PILOT_2)
def test_the_three_replies_that_failed_now_read(banner):
    got = relay.read(banner + "\n    the detail line\n")
    assert got.answered is False
    assert got.reason == banner.split()[6]


@pytest.mark.parametrize("dash,sep", [
    (":", "|"),       # what the engine writes now
    ("—", "·"),       # what it wrote before
    ("-", "-"),       # pilot 2
    ("--", "."),      # the other console manglings the two sessions reported
    ("-", "."),
])
def test_every_spelling_of_a_refusal_reads_the_same(dash, sep):
    body = f"THE DESK DID NOT ANSWER {dash} facts_not_established  {sep}  corpus\n    detail\n"
    got = relay.read(body)
    assert (got.answered, got.reason) == (False, "facts_not_established")


@pytest.mark.parametrize("line,binding", [
    ("primary | the firm treats as binding | confirmed 2026-09-05", True),
    ("primary | not binding: read the note below | confirmed 2026-09-05", False),
    ("primary · the firm treats as binding · confirmed 2026-09-05", True),
    ("primary · not binding — read the note below · confirmed 2026-09-05", False),
    # the mangled old form: a hyphen INSIDE the value AND as every separator
    ("primary - not binding - read the note below - confirmed 2026-09-05", False),
    ("secondary . the firm treats as binding . confirmed 2026-09-05", True),
])
def test_every_spelling_of_a_served_answer_reads_the_same(line, binding):
    body = f"an answer\n\n    26 CFR 1.162-3(c)(1)(iv)\n    {line}\n"
    got = relay.read(body)
    assert got.answered is True
    assert got.citation == "26 CFR 1.162-3(c)(1)(iv)"
    assert got.binding is binding
    assert got.checked == "2026-09-05"
    assert got.tier in ("primary", "secondary")


# --- prevent rather than detect: nothing left for a console to break --------

def test_the_engine_writes_the_parsed_lines_in_plain_ascii():
    served = str(engine.Served(position="p", citation="26 CFR 1.162-3(a)",
                               tier="primary", binding=False, checked="2026-09-05"))
    refused = str(engine.Refusal(reason="facts_not_established", detail="d",
                                 desk="corpus"))
    grade = next(l for l in served.splitlines() if "confirmed" in l)
    banner = refused.splitlines()[0]
    for line in (grade, banner):
        assert line.isascii(), (
            f"{line!r} carries non-ASCII characters, and a reply is parsed off "
            f"exactly this line on the far side of a console that mangles them")


def test_what_the_engine_writes_is_what_the_reader_reads():
    """The round trip, without a console in the middle: if the writer and the
    reader ever drift apart, this is the test that says so."""
    refused = engine.Refusal(reason="context_not_on_file", detail="d", desk="corpus")
    got = relay.read(str(refused))
    assert (got.answered, got.reason) == (False, "context_not_on_file")


def test_every_reason_code_is_one_the_reader_can_match():
    """The reader matches a reason as `[a-z_]+`. A code added later with a
    hyphen or a capital in it would be silently unreadable."""
    bad = [r for r in engine.REASONS if not re.fullmatch(r"[a-z_]+", r)]
    assert not bad, f"reason codes the reader cannot match: {bad}"


def test_something_that_is_neither_still_raises():
    """Tolerance must not turn into guessing: a reply with no banner and no
    grade line is still refused loudly rather than read as a no."""
    with pytest.raises(relay.RelayError):
        relay.read("DESK ANSWER abc\n\nI think it is probably deductible.\n")
