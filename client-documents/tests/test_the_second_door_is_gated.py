"""`render` and `event` pass the pre-send gate too.

**THEY DID NOT, AND TWO GOVERNING DOCUMENTS SAID THEY DID.** `presend.gate` had
exactly two callers — `sending.build` and `previewing.preview` — and neither is
on the path `cli.py event` takes. So five documents a client actually receives
reached them unchecked:

    delivery letter · organizer cover · extension notice ·
    disengagement letter · the invoice, via `render`

The delivery letter is the one that travels *with the return*.

`docs/WHERE-THINGS-STAND.md` had the gap recorded as "the biggest hole still
open". Meanwhile `CLAUDE.md` — the file loaded into every agent session on this
machine — and `docs/REPO-INVENTORY.md` both asserted that **every** document a
client receives passes a blocking gate. **The false claim was the more dangerous
half**: a gap invites a look, and a claim forecloses one. Both sentences were
corrected on 4 September 2026; the firm asked for the gap itself closed next.

STAGED, GATED, THEN PLACED — the shape `package` always had. A refused set
leaves `outdir` untouched, because a half-made pack is worse than none: somebody
sends it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

import cli
import engagements
import sending


ROOT = Path(__file__).resolve().parents[1]


def _record():
    """A real opening-package record, from the repository's own sample."""
    raw = json.loads((ROOT / "samples" / "tax-opening-package.json")
                     .read_text(encoding="utf-8"))
    return cli.build_record(raw)


def _args(out: Path, **over):
    a = argparse.Namespace(
        record=None, engagement=None, store=None, docs=["fee-estimate"],
        out=str(out), no_pdf=True, draft=False, invoice=None,
        _record_override=_record(), force=False, reason="", skip_render=True)
    for k, v in over.items():
        setattr(a, k, v)
    return a


# ── the door is gated at all ─────────────────────────────────────────────────

def test_render_runs_the_gate(tmp_path, capsys):
    """The claim in one test: the pre-send gate is reached from this door.

    Before 5 September 2026 nothing on this path called it, and the output said
    nothing about a gate because there was none.
    """
    cli.cmd_render(_args(tmp_path / "out"))
    out = capsys.readouterr().out
    assert "pre-send gate" in out, (
        f"render produced documents and never mentioned a gate:\n{out}")


def test_a_passing_render_still_places_the_documents(tmp_path, capsys):
    """A gate that also breaks the ordinary case is a gate that gets removed."""
    outdir = tmp_path / "out"
    rc = cli.cmd_render(_args(outdir))
    assert rc == 0, capsys.readouterr().out
    written = sorted(p.name for p in outdir.iterdir() if p.is_file())
    assert any(n.endswith(".html") for n in written), written


def test_the_manifest_does_not_follow_the_documents_out(tmp_path):
    """`MANIFEST.json` exists so the GATE can tell which template a document
    came from — a rendered file is named for the client and says nothing about
    its own origin. It is not part of what a client receives."""
    outdir = tmp_path / "out"
    cli.cmd_render(_args(outdir))
    assert not (outdir / "MANIFEST.json").exists()


def test_the_staging_directory_is_not_left_behind(tmp_path):
    """A temp directory holding rendered CLIENT DOCUMENTS — real name, real
    address — is not a thing to leave lying in the system temp folder. The
    repository has been here before: the PDF renderer used to write into the
    tracked template library, and the guard that caught it is still there."""
    import tempfile
    before = set(Path(tempfile.gettempdir()).glob("satc-stage-*"))
    cli.cmd_render(_args(tmp_path / "out"))
    after = set(Path(tempfile.gettempdir()).glob("satc-stage-*"))
    assert after <= before, f"left behind: {sorted(after - before)}"


# ── a page is not a pack ─────────────────────────────────────────────────────

def test_a_chosen_document_is_not_judged_on_what_a_whole_pack_would_hold(
        tmp_path, capsys):
    """THE THING THAT NEARLY MADE THIS GATE USELESS.

    The first version applied the pack gate wholesale, and it refused an
    ordinary `render --docs fee-estimate` — the estimate promises the
    engagement letter as an enclosure, and a one-document render does not hold
    one. That is the estimate being correct, not a fault.

    **A gate that refuses correct everyday use is a gate everybody learns to
    `--force` past, and then it protects nothing.** Caught by running it rather
    than by any test: the test above only said "a gate was mentioned".
    """
    rc = cli.cmd_render(_args(tmp_path / "out", docs=["fee-estimate"]))
    assert rc == 0, capsys.readouterr().err


def test_the_skipped_check_is_named_rather_than_dropped(tmp_path, capsys):
    """It is SKIPPED, not silently absent. A check that quietly does not run is
    the failure this whole module is built against — so the counts differ, and
    the difference is visible.
    """
    cli.cmd_render(_args(tmp_path / "out", docs=["fee-estimate"]))
    subset = capsys.readouterr().out
    cli.cmd_render(_args(tmp_path / "whole", docs=None))
    whole = capsys.readouterr().out

    def n(text):
        import re
        m = re.search(r"pre-send gate: (\d+) check", text)
        assert m, text
        return int(m.group(1))

    assert n(whole) == n(subset) + 1, (
        f"a whole pack must run exactly one more check than a chosen "
        f"document — the enclosure check. Got {n(subset)} and {n(whole)}")


def test_a_whole_package_render_still_gets_the_enclosure_check(tmp_path,
                                                               monkeypatch):
    """The skip must apply ONLY to a subset. `render` with no `--docs` is the
    whole opening package and is a real pack."""
    seen = {}
    real = sending.presend.gate

    def spy(*a, **k):
        seen["whole_pack"] = k.get("whole_pack")
        return real(*a, **k)

    monkeypatch.setattr(sending.presend, "gate", spy)
    cli.cmd_render(_args(tmp_path / "out", docs=None))
    assert seen["whole_pack"] is True
    cli.cmd_render(_args(tmp_path / "sub", docs=["fee-estimate"]))
    assert seen["whole_pack"] is False


# ── and it can actually refuse ───────────────────────────────────────────────

class _Blocked:
    """A gate result with one blocking finding, shaped like the real one."""

    class _F:
        check = "the compliance floor is on the page"
        document = "fee-estimate"
        detail = "the paragraph is not present"

    checked = ["a", "b", "c"]
    blocking = [_F()]


def test_a_blocked_render_writes_nothing_at_all(tmp_path, monkeypatch, capsys):
    """THE ONE THAT MATTERS. A refusal must leave `outdir` untouched.

    Not "leaves a warning", not "writes them and returns 1" — nothing. The
    failure this prevents is a preparer finding four files in a folder, not
    reading the terminal, and sending them.
    """
    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: _Blocked())
    outdir = tmp_path / "out"
    rc = cli.cmd_render(_args(outdir))
    assert rc == 1
    assert not outdir.exists() or not list(outdir.iterdir()), (
        f"a refused render left files in {outdir}: "
        f"{sorted(p.name for p in outdir.iterdir())}")


def test_the_refusal_names_the_check_and_the_way_out(tmp_path, monkeypatch,
                                                     capsys):
    """A gate that only says no is a gate people learn to --force past without
    reading. S3: an error is the interface."""
    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: _Blocked())
    cli.cmd_render(_args(tmp_path / "out"))
    err = capsys.readouterr().err
    assert "compliance floor" in err, err
    assert "--force" in err and "--reason" in err, err


def test_force_without_a_reason_is_refused(tmp_path, monkeypatch, capsys):
    """An override with no reason recorded is a quieter way of sending a pack
    that failed."""
    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: _Blocked())
    outdir = tmp_path / "out"
    rc = cli.cmd_render(_args(outdir, force=True))
    assert rc == 1
    assert not outdir.exists() or not list(outdir.iterdir())
    assert "--reason" in capsys.readouterr().err


def test_force_with_no_engagement_cannot_be_logged_so_is_refused(
        tmp_path, monkeypatch, capsys):
    """A one-off render from a record file has nothing to log an override
    against. Forcing past a gate with no trace is exactly what the log exists to
    prevent, so it is refused rather than quietly allowed."""
    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: _Blocked())
    outdir = tmp_path / "out"
    rc = cli.cmd_render(_args(outdir, force=True, reason="the client is waiting"))
    assert rc == 1
    err = capsys.readouterr().err
    assert "could not be recorded" in err or "no engagement" in err, err
    assert not outdir.exists() or not list(outdir.iterdir())


def test_a_logged_override_lets_it_through_and_leaves_a_trace(
        tmp_path, monkeypatch, capsys):
    """The override is the record. It has to work, or everybody stops at a
    blocking gate they cannot get past and the gate comes out."""
    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: _Blocked())
    store = tmp_path / "engagements"
    engagements.save({"EngagementRef": "2026-0001",
                      "ClientFullName": "Walkthrough Fixture"},
                     "2026-0001", store)

    outdir = tmp_path / "out"
    rc = cli.cmd_render(_args(outdir, force=True, reason="signed off by phone",
                              _gate_ref="2026-0001", _gate_store=store))
    assert rc == 0, capsys.readouterr().err
    assert list(outdir.iterdir()), "forced past the gate but wrote nothing"

    logged = engagements.overrides("2026-0001", store)
    assert logged, "the override was allowed and never recorded"
    assert logged[-1]["reason"] == "signed off by phone"
    assert logged[-1]["failed"][0]["check"] == "the compliance floor is on the page"


# ── check the checker ────────────────────────────────────────────────────────

def test_the_gate_this_calls_is_the_same_one_package_calls():
    """One implementation, not two.

    `package` had the whole discipline already — manifest before gate, blocking
    refusal, an override that must carry a reason and must be logged or it does
    not happen. A second copy in `cli` would be two implementations of one
    policy, drifting from the day it was written, which is exactly how the two
    price lists happened.
    """
    import inspect
    src = inspect.getsource(cli.cmd_render)
    assert "sending.gate_staged" in src, (
        "cmd_render does not go through sending; if it grew its own gate call, "
        "there are now two implementations of one policy")
    assert "presend.gate(" not in src, (
        "cmd_render calls the gate directly instead of going through the "
        "shared discipline that logs overrides")


def test_every_document_the_event_command_makes_goes_through_this_door():
    """`event` renders through `cmd_render`, so gating that door gates all four
    lifecycle documents. If `event` ever grows its own renderer, this fails and
    the gap reopens silently — which is how it existed in the first place."""
    import inspect
    src = inspect.getsource(cli.cmd_event)
    assert "cmd_render(" in src, (
        "cmd_event no longer renders through cmd_render, so the pre-send gate "
        "this file asserts no longer covers the lifecycle documents")


def test_the_blocked_gate_stub_would_pass_if_it_were_not_blocking(
        tmp_path, monkeypatch):
    """MUTATION on the fixture itself. If `_Blocked` stopped being blocking,
    every refusal test above would pass for the wrong reason — they would be
    asserting that a passing render refuses.
    """
    class NotBlocked(_Blocked):
        blocking = []

    monkeypatch.setattr(sending.presend, "gate", lambda *a, **k: NotBlocked())
    outdir = tmp_path / "out"
    assert cli.cmd_render(_args(outdir)) == 0
    assert list(outdir.iterdir()), (
        "with nothing blocking the documents must be placed — so the refusals "
        "above are caused by the blocking finding and not by the stub itself")
