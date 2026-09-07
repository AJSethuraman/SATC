"""Time recorded by the software, because the firm will not record it by hand.

Their words, and they decide the whole design: *"I want it as I work and to
automate everything possible about recording time because I am bad at doing
so."* Anything with a start button is a chore, and a chore this firm does not
do is a feature that reports nothing.
"""

from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stderr, redirect_stdout, suppress
from datetime import datetime, timedelta

import pytest

import timelog


def _engagement(tmp_path, ref="2026-0001", **record):
    d = tmp_path / ref
    d.mkdir(parents=True, exist_ok=True)
    base = {"ClientFullName": "Maplewood Dental LLC", "TaxYear": 2026}
    base.update(record)
    (d / "record.json").write_text(json.dumps(base, indent=2), encoding="utf-8")
    return tmp_path


T0 = datetime(2027, 2, 18, 9, 0)


# -- it records without being asked ------------------------------------------

def test_touches_close_together_are_one_sitting(tmp_path):
    """Three commands over twenty minutes is one piece of work, not three."""
    store = _engagement(tmp_path)
    # All three must be WORK commands — `price` sits in REPORTING and the first
    # draft of this test used it, so it recorded two touches and failed. That is
    # the feature working; the fixture was wrong.
    for minutes, what in [(0, "interview"), (6, "render"), (20, "package")]:
        timelog.record(store, "2026-0001", what, when=T0 + timedelta(minutes=minutes))

    got = timelog.spent(store, "2026-0001")
    assert len(got.sittings) == 1
    assert got.sittings[0].touches == 3
    assert got.measured == pytest.approx(20 / 60, abs=0.01)


def test_a_long_gap_starts_a_new_sitting(tmp_path):
    """Yesterday evening is not this morning. Joining them would invent hours."""
    store = _engagement(tmp_path)
    timelog.record(store, "2026-0001", "package", when=T0)
    timelog.record(store, "2026-0001", "sign", when=T0 + timedelta(hours=4))

    assert len(timelog.spent(store, "2026-0001").sittings) == 2


def test_one_touch_alone_is_the_firms_own_minimum_and_not_zero(tmp_path):
    """A single command has no span. Recording it as nothing says the work did
    not happen. It counts as `minimum_increment` from the fee schedule — the
    firm's existing answer to "how short is the shortest job" — because
    inventing a second answer here would be a number nobody chose."""
    store = _engagement(tmp_path)
    timelog.record(store, "2026-0001", "package", when=T0)

    assert timelog.spent(store, "2026-0001", floor=0.25).measured == 0.25


# -- what it must never claim -------------------------------------------------

def test_measured_and_stated_are_never_added(tmp_path):
    """THE ONE THAT MATTERS. `measured` is a floor — it sees the software and
    not Drake, where the return is actually prepared. `stated` is somebody's
    recollection. A single total would look more certain than either, which is
    the failure this repository keeps having."""
    store = _engagement(tmp_path)
    timelog.record(store, "2026-0001", "package", when=T0)
    timelog.add(store, "2026-0001", 3.0, "Drake preparation", when=T0)

    got = timelog.spent(store, "2026-0001")
    assert got.measured == 0.25 and got.stated == 3.0
    assert not hasattr(got, "total"), "a single total is the thing to not have"


def test_stated_time_needs_to_say_what_it_was(tmp_path):
    """A number with no work against it cannot be checked by anybody later,
    including the person who wrote it."""
    store = _engagement(tmp_path)
    with pytest.raises(ValueError, match="say what it was"):
        timelog.add(store, "2026-0001", 2.0, "   ")


def test_no_rows_is_not_the_same_as_no_time(tmp_path):
    """S2. "0.00 hours" beside a budget reads as a job that took no time, which
    is a claim. "Nothing recorded" is the truth."""
    store = _engagement(tmp_path)
    assert timelog.spent(store, "2026-0001").examined_nothing


# -- it must never break real work -------------------------------------------

def test_recording_never_raises_even_when_the_write_itself_fails(tmp_path):
    """This runs beside a pack being rendered for a client. A failure to write a
    time row must not stop a document going out — the cost is a low measured
    figure, and a low floor is the honest failure for a floor to have.

    THE FIRST VERSION OF THIS TEST PROVED NOTHING. It pointed at a folder that
    did not exist, which `record` refuses before it ever opens a file — so the
    error handling it claimed to cover was never reached, and mutation testing
    caught it. This makes the log path a DIRECTORY, so the open genuinely
    raises.
    """
    store = _engagement(tmp_path)
    (store / "2026-0001" / timelog.LOG).mkdir()      # a directory where a file goes

    timelog.record(store, "2026-0001", "package")    # must not raise
    assert timelog.spent(store, "2026-0001").examined_nothing


def test_a_missing_engagement_is_simply_not_recorded(tmp_path):
    """Nothing to attach a touch to, and creating the folder would invent an
    engagement out of a mistyped ref."""
    timelog.record(tmp_path / "nowhere", "2026-9999", "package")
    assert not (tmp_path / "nowhere").exists()


def test_a_corrupt_row_loses_one_touch_and_not_the_file(tmp_path):
    store = _engagement(tmp_path)
    timelog.record(store, "2026-0001", "package", when=T0)
    with (store / "2026-0001" / timelog.LOG).open("a", encoding="utf-8") as fh:
        fh.write("{not json at all\n")
    timelog.record(store, "2026-0001", "sign", when=T0 + timedelta(minutes=5))

    assert timelog.spent(store, "2026-0001").touches == 2


def test_stated_time_does_raise(tmp_path):
    """The asymmetry is deliberate. `record` is bookkeeping beside real work and
    must never interrupt it; `add` is somebody deliberately writing down two
    hours in Drake, and losing that silently is the worst of both worlds."""
    with pytest.raises(FileNotFoundError):
        timelog.add(tmp_path / "nowhere", "2026-9999", 2.0, "Drake")


# -- looking is not working ---------------------------------------------------

def test_a_reporting_command_does_not_record_itself(tmp_path):
    """`spent` recorded itself the first time it ran — a quarter-hour of "work"
    for opening the report. Asking how long something took must not add to how
    long it took."""
    store = _engagement(tmp_path)
    timelog.record(store, "2026-0001", "spent", when=T0)
    timelog.record(store, "2026-0001", "season", when=T0)

    assert timelog.spent(store, "2026-0001").examined_nothing


def test_every_command_is_classified_as_work_or_as_looking():
    """PREVENT, DO NOT DETECT. A deny-list lets the NEXT reporting command
    forget, and it would forget silently — inflating the measured figure with
    time spent looking. This fails until somebody decides which a new command
    is, which is the whole point.

    Where a command genuinely does both — `sign` lists signatures and records
    one — it counts as work. Under-recording is the safer failure: the measured
    figure is already a floor and is presented as one.
    """
    import cli

    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        with pytest.raises(SystemExit):
            cli.main(["--help"])
    found = re.search(r"\{([a-z,\-]+)\}", buf.getvalue())
    assert found, "could not read the subcommand list — this check examined nothing"
    commands = set(found.group(1).split(","))
    assert len(commands) > 10, f"only {len(commands)} subcommands found"

    stale = timelog.REPORTING - commands
    assert not stale, (
        f"REPORTING names commands that do not exist: {sorted(stale)}. "
        f"A stale entry silently stops recording a command that never ran.")

    work = commands - timelog.REPORTING
    assert work, "every command counted as looking — nothing would ever record"


def test_the_command_line_records_without_anyone_asking_it_to(tmp_path):
    """THE WIRING, END TO END, and nothing tested it until mutation testing
    removed the hook and every test still passed.

    This is the whole feature: the firm runs an ordinary command and time
    appears. A unit test that calls `timelog.record` directly proves the
    bookkeeping and not the automation, and the automation is the point.
    """
    import cli

    store = _engagement(tmp_path)
    buf = io.StringIO()
    # The command itself may refuse on a fixture this thin — irrelevant here.
    # The touch is recorded BEFORE dispatch, which is the behaviour under test.
    with redirect_stdout(buf), redirect_stderr(buf), suppress(Exception):
        cli.main(["sign", "--engagement", "2026-0001", "--store", str(store)])

    got = timelog.spent(store, "2026-0001")
    assert not got.examined_nothing, "an ordinary command recorded nothing"
    assert got.sittings[0].what == ["sign"]


def test_it_records_even_when_the_command_refuses(tmp_path):
    """BEFORE the command runs, not after. A pack blocked by the pre-send gate
    is often exactly where the work went, and a command that refuses still took
    the time it took."""
    import cli

    store = _engagement(tmp_path)
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        code = cli.main(["spent", "--engagement", "no-such-ref",
                         "--store", str(store)])
    assert code == 1, "the fixture must be a command that actually refuses"

    # `spent` is a reporting command, so it records nothing — but a WORK command
    # that refuses does. Prove the refusing half with one that is work.
    (store / "2026-0002").mkdir()
    with redirect_stdout(buf), redirect_stderr(buf), suppress(Exception):
        cli.main(["sign", "--engagement", "2026-0002", "--store", str(store)])
    assert not timelog.spent(store, "2026-0002").examined_nothing


def test_stated_time_cannot_smuggle_an_identification_number(tmp_path):
    """`--what` is free text a person types, and free text is where TINs get in.
    This file sits in the engagement folder, which is in OneDrive."""
    store = _engagement(tmp_path)
    with pytest.raises(Exception) as caught:
        timelog.add(store, "2026-0001", 2.0,
                    "called the client about SSN 123-45-6789")
    assert "123-45-6789" not in str(caught.value), (
        "the refusal repeated the number it objected to")
    assert timelog.spent(store, "2026-0001").examined_nothing, (
        "it wrote the row before refusing")
