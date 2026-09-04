"""The two Square facts get written down without anyone editing YAML.

THE FIRM, 4 September 2026: *"i can get the location and prod IDs if that's what
we need - i want it to be simple for me to update these figures."*

The failure this exists to stop already happened. On 2 September the firm was
asked for a location id and sent an APPLICATION id -- `sq0idp-...` rather than
`L...` -- because Square's console shows them side by side and nothing said
which was wanted. Square's answer to an application id is a 401, which reads
like a bad token, so the wrong identifier would have been blamed on the right
one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import square_setup as setup


REG = Path(__file__).resolve().parent.parent / "registry" / "payments.yaml"


@pytest.fixture()
def text() -> str:
    return REG.read_text(encoding="utf-8")


# -- the identifier we are actually being handed -------------------------------

def test_an_application_id_is_refused_and_named_as_one():
    """The whole point. It must say WHICH identifier this is, not just 'bad'."""
    why = setup.looks_wrong("sq0idp-AbCdEf123456")
    assert "APPLICATION id" in why
    assert "location" in why.lower()
    assert "LM2T2W21MZ5CY" in why, "say what a right one looks like"


def test_a_sandbox_application_id_is_refused_too():
    assert "APPLICATION id" in setup.looks_wrong("sandbox-sq0idb-AbCdEf123456")


@pytest.mark.parametrize("bad", ["", "   ", "hello", "L", "lm2t2w21mz5cy",
                                 "12345678", "L$$$$$$"])
def test_anything_that_is_not_a_location_id_is_refused(bad):
    assert setup.looks_wrong(bad)


def test_a_real_location_id_passes():
    assert setup.looks_wrong("LM2T2W21MZ5CY") == ""


# -- the write ----------------------------------------------------------------

def test_writing_a_value_as_itself_changes_nothing(text):
    """THE SAFETY PROPERTY, the same one `registry_editor` holds.

    A writer that cannot rewrite a value as itself is quietly reformatting
    something, and in this file the thing it reformats will be a comment
    recording a decision.
    """
    assert setup.set_location("sandbox_location_id", "LM2T2W21MZ5CY",
                              text=text) == text


def test_it_changes_exactly_one_line_and_keeps_every_comment(text):
    out = setup.set_location("location_id", "LPRODABC123", text=text)
    before, after = text.splitlines(), out.splitlines()
    assert len(before) == len(after)
    assert sum(1 for a, b in zip(before, after) if a != b) == 1
    assert text.count("#") == out.count("#"), "a comment was lost"


def test_the_value_written_is_the_value_asked_for(text):
    out = setup.set_location("location_id", "LPRODABC123", text=text)
    line = next(l for l in out.splitlines()
                if l.strip().startswith("location_id:"))
    assert line == '  location_id: "LPRODABC123"'


def test_the_two_location_keys_do_not_overwrite_each_other(text):
    """They are one word apart and both end in `location_id`. A loose match
    writes the production id over the sandbox one, and the next test run bills
    a real client against a test location."""
    out = setup.set_location("location_id", "LPRODABC123", text=text)
    assert '  sandbox_location_id: "LM2T2W21MZ5CY"' in out
    out2 = setup.set_location("sandbox_location_id", "LSANDBOXXYZ", text=text)
    assert 'LSANDBOXXYZ' in out2
    assert "CONFIRM" in next(l for l in out2.splitlines()
                             if l.strip().startswith("location_id:"))


def test_a_bad_id_is_refused_before_anything_is_written(text):
    with pytest.raises(setup.SetupError):
        setup.set_location("location_id", "sq0idp-nope", text=text)
    assert REG.read_text(encoding="utf-8") == text, "the file was touched"


def test_a_key_that_is_not_a_location_is_refused(text):
    """It will not invent a key. One this writes and nothing reads is worse
    than a missing one."""
    with pytest.raises(setup.SetupError):
        setup.set_location("api_host", "LM2T2W21MZ5CY", text=text)


def test_it_writes_inside_the_square_block_not_into_a_comment():
    """`location_id` appears in prose in this file. A bare search finds the
    comment first and edits that."""
    doc = ('# a note mentioning location_id: not a real one\n'
           'processor: square\n'
           'square:\n'
           '  location_id: "[CONFIRM: x]"\n'
           '  sandbox_location_id: "LOLDONE1234"\n'
           'currency: USD\n')
    out = setup.set_location("location_id", "LNEWONE1234", text=doc)
    assert out.splitlines()[0] == doc.splitlines()[0], "the comment was edited"
    assert '  location_id: "LNEWONE1234"' in out


# -- the token ----------------------------------------------------------------

def test_an_empty_token_is_not_stored():
    with pytest.raises(setup.SetupError):
        setup.remember_token("   ", sandbox=True)


@pytest.mark.skipif(setup._dpapi(b"probe") is None,
                    reason="DPAPI unavailable on this platform")
def test_a_remembered_token_round_trips_and_is_not_readable_as_text(tmp_path,
                                                                   monkeypatch):
    monkeypatch.setattr(setup, "TOKEN_FILES", {True: tmp_path / "s", False: tmp_path / "p"})
    secret = "EAAAl-not-a-real-token-000"
    setup.remember_token(secret, sandbox=True)
    assert setup.stored_token(True) == secret
    on_disk = (tmp_path / "s").read_bytes()
    assert secret.encode() not in on_disk, "the token is sitting there in clear"
    assert setup.forget_token(True)
    assert setup.stored_token(True) == ""


def test_no_remembered_token_reads_as_empty_rather_than_raising(tmp_path,
                                                               monkeypatch):
    """The absence of a token is an ordinary state, not an error. It is what
    every machine that has never run --setup looks like."""
    monkeypatch.setattr(setup, "TOKEN_FILES", {True: tmp_path / "no", False: tmp_path / "ne"})
    assert setup.stored_token(True) == ""
    assert setup.forget_token(True) == []


def test_it_refuses_rather_than_storing_a_token_it_cannot_seal(tmp_path,
                                                               monkeypatch):
    """A live payment token written in the clear is worse than typing it again.

    The fallback that would 'helpfully' still store it is the whole risk here,
    so the refusal is the behaviour under test.
    """
    monkeypatch.setattr(setup, "TOKEN_FILES", {True: tmp_path / "s", False: tmp_path / "p"})
    monkeypatch.setattr(setup, "_dpapi", lambda *a, **k: None)
    with pytest.raises(setup.SetupError) as e:
        setup.remember_token("EAAAl-not-a-real-token-000", sandbox=True)
    assert "NOT been written" in str(e.value)
    assert not (tmp_path / "s").exists()


# -- the property has to hold on DISK, not just in memory ---------------------

def test_saving_does_not_rewrite_every_line_ending(tmp_path, monkeypatch):
    """THE ONE THE IN-MEMORY TEST MISSED.

    `set_location` returned a byte-identical string and `save_location` then
    wrote it through Python's text mode, which on Windows turns every `\n` into
    `\r\n`. One value changed and ~100 line endings changed with it: a
    whole-file diff for anyone without `core.autocrlf`, and a promise that was
    true of the function and false of the file.

    Found by `git status` calling the registry modified after a run that had
    put it back exactly as it was.
    """
    src = REG.read_bytes()
    target = tmp_path / "payments.yaml"
    target.write_bytes(src)
    monkeypatch.setattr(setup, "REGISTRY", target)

    setup.save_location("sandbox_location_id", "LM2T2W21MZ5CY")
    assert target.read_bytes() == src, "saving the same value rewrote the file"

    setup.save_location("location_id", "LPRODABC123")
    after = target.read_bytes()
    assert after.count(b"\r\n") == src.count(b"\r\n"), "line endings changed"
    assert b'location_id: "LPRODABC123"' in after
