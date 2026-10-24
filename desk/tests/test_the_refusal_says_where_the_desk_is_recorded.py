"""Refusing without saying where to look made a session do archaeology.

`desk_session()` refuses when `SATC_DESK_SESSION` is unset, and that refusal is
right: `DESIGN-PRINCIPLES.md` says refuse rather than default, and a WRONG id
fails silently — the question goes somewhere, the asker waits, and nothing says
the desk never saw it. That reasoning stands and this test does not weaken it.

WHAT IT MISSED. The message said "export it" and never said what to export. On
8 September 2026 a session with the variable unset reported to the firm that the
round trip "cannot be done from this container" — and then found the id in
ninety seconds by reading `list_triggers`, where every previous round trip had
left one. The firm:

    "How in the world will the skill ever work if you can't even keep it
     straight. Does it need built into the plugin itself?"

Half of it does. The id is RECORDED in the plugin so nobody has to go digging;
it is not TRUSTED by the code, because a committed id travels with the release
and goes stale, and a stale id is the silent-failure case above. So the refusal
now names the file, and the file carries the id, the date it was confirmed, and
how to check it is still alive.
"""
from __future__ import annotations

import pytest

import relay
from relay import RelayError

#: Where the deployment record lives, relative to the plugin root.
RECORD = "WHERE-THE-DESK-IS.md"


def test_the_refusal_names_the_file_that_records_the_id():
    with pytest.raises(RelayError) as e:
        relay.desk_session({})
    assert RECORD in str(e.value), (
        "the refusal does not say where the id is written down, so the next "
        "session has to go archaeology through list_triggers — which is the "
        "step that produced a false 'cannot be done from this container'")


def test_the_refusal_still_refuses():
    """The fix must not turn into a default. A named file is not a fallback."""
    with pytest.raises(RelayError):
        relay.desk_session({})


def test_a_set_variable_still_wins_over_the_record():
    """Deployment state beats the committed note, always — that is the point."""
    live = "session_016cgnNu73t4Y3pGyMYTNExh"
    assert relay.desk_session({relay.DESK: live}) == live


def test_the_recorded_file_exists_and_carries_a_session_id():
    """A refusal pointing at a file that is not there is worse than silence."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "docs" / RECORD
    assert p.exists(), f"{RECORD} is named by the refusal and does not exist"
    text = p.read_text(encoding="utf-8")
    assert relay.SESSION.search(text.replace("`", " ").replace("\n", " ")) or \
        any(relay.SESSION.match(w) for w in text.replace("`", " ").split()), \
        "the record names no session id, so it answers nothing"
