"""Where the tie-out's working data lives is a setting, not a typed-in path.

Fifty-two of the fifty-eight tie-out tools carried the same Windows temp path,
session id and all -- a folder Windows may clear that holds the 760 filed Call
Reports every check runs against. Those are not a cache: most have been amended
since the quarter they report, so fetching them again returns a different
document and a tie-out already done cannot be reproduced.
"""

from __future__ import annotations

import pathlib

import pytest

from credit_suite import workdir as W


def test_the_environment_wins_over_everything(tmp_path, monkeypatch):
    """A run that wants somewhere else says so once, on the command line."""
    monkeypatch.setenv(W.ENV, str(tmp_path))
    assert W.workdir() == tmp_path


def test_a_directory_that_is_not_there_is_refused_by_name(tmp_path, monkeypatch):
    """Not silently fallen back from: an override that points nowhere is a
    typo, and continuing with a different folder answers a question nobody
    asked."""
    monkeypatch.setenv(W.ENV, str(tmp_path / "nope"))
    with pytest.raises(SystemExit) as excinfo:
        W.workdir()
    assert W.ENV in str(excinfo.value)


def test_with_nothing_anywhere_it_refuses_and_says_where_it_looked(monkeypatch):
    """The failure this guards is the one that reads as success: a missing
    folder becoming an empty one gives every tool nothing to read and every
    count an honest-looking zero."""
    monkeypatch.delenv(W.ENV, raising=False)
    monkeypatch.setattr(W, "FORGE", pathlib.Path("/nonexistent-forge"))
    monkeypatch.setattr(W, "LEGACY", pathlib.Path("/nonexistent-legacy"))
    with pytest.raises(SystemExit) as excinfo:
        W.workdir()
    message = str(excinfo.value)
    assert "nonexistent-forge" in message and "nonexistent-legacy" in message
    assert "not a cache" in message


def test_the_forge_is_preferred_over_the_old_temp_folder(tmp_path, monkeypatch):
    """Both can exist during a move. The Forge is the one that survives."""
    forge, legacy = tmp_path / "forge", tmp_path / "legacy"
    forge.mkdir(); legacy.mkdir()
    monkeypatch.delenv(W.ENV, raising=False)
    monkeypatch.setattr(W, "FORGE", forge)
    monkeypatch.setattr(W, "LEGACY", legacy)
    assert W.workdir() == forge


def test_the_purge_list_says_which_half_cannot_be_rebuilt():
    """The firm said they will purge at some point. What must not go is
    recorded here rather than left to a judgement call at the time."""
    assert "banks" in W.IRREPLACEABLE and "filings" in W.IRREPLACEABLE
    assert not set(W.IRREPLACEABLE) & set(W.REBUILDABLE)
    assert "amended" in W.IRREPLACEABLE["banks"]


def test_no_tie_out_tool_carries_the_typed_path_any_more():
    """The point of the setting is that there is one of it."""
    tools = (pathlib.Path(__file__).resolve().parents[1] / "tools" / "tieout")
    carrying = [p.name for p in tools.glob("*.py")
                if "261f7248-3cbc" in p.read_text(encoding="utf-8")]
    assert carrying == [], carrying
