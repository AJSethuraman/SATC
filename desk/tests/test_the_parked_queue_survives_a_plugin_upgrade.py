"""The queue of parked questions is not inside the release that parked them.

FOUND BY A REVIEW of the commit that built the notification path, and it is that
commit which made it matter: parking a question is only worth doing if somebody
comes back to it.

`be-the-desk` told the reader to write the queue to `ROOT/unfiled/CLOSE.md`, and
in an installed layout the skill resolves `ROOT` by picking the highest version
directory under `~/.claude/plugins/cache/satc/desk/`. So the supposedly durable
store lived inside ONE release. Update the plugin and `ROOT` moves; the skill and
`tools/holes.py` both look at the new root, find nothing, and every unanswered
question is gone with no error raised anywhere. Cache cleanup could delete it.
"""
from __future__ import annotations

import os
from pathlib import Path

import unsupported


def test_the_default_is_outside_any_plugin_cache():
    p = unsupported.default_queue()
    parts = [s.lower() for s in p.parts]
    for forbidden in ("cache", "plugins", "site-packages"):
        assert forbidden not in parts, (
            f"the queue resolves inside {forbidden!r} ({p}), so it dies with "
            f"the release that wrote it")


def test_the_default_carries_no_version_in_its_path():
    """A version anywhere in the path is the bug wearing a different directory."""
    import re
    for part in unsupported.default_queue().parts:
        assert not re.fullmatch(r"v?\d+\.\d+(\.\d+)?", part), (
            f"{part!r} looks like a release, so the path moves when the plugin "
            f"is upgraded")


def test_it_is_not_inside_the_plugin_checkout_either():
    """A parked question is written mid-close and can name anything about a
    client. CLAUDE.md: a client's affairs in a checkout are one `git add` from
    being published."""
    here = Path(__file__).resolve().parent.parent
    assert here not in unsupported.default_queue().resolve().parents


def test_a_deployment_can_point_it_elsewhere(monkeypatch, tmp_path):
    monkeypatch.setenv(unsupported.QUEUE_ENV, str(tmp_path / "q.md"))
    assert unsupported.default_queue() == tmp_path / "q.md"


def test_an_empty_override_is_not_an_override(monkeypatch):
    """An unset variable and one set to "" must behave the same, or a shell that
    exports it blank silently relocates the queue to the current directory."""
    monkeypatch.setenv(unsupported.QUEUE_ENV, "   ")
    assert unsupported.default_queue() == Path.home() / ".satc" / "desk" / "unfiled" / "CLOSE.md"


def test_the_override_expands_a_home_relative_path(monkeypatch):
    monkeypatch.setenv(unsupported.QUEUE_ENV, "~/somewhere/q.md")
    assert unsupported.default_queue() == Path.home() / "somewhere" / "q.md"


def test_two_releases_resolve_the_same_queue(monkeypatch):
    """The property that was broken, stated directly: the answer to "where is
    the queue" does not depend on which release is installed."""
    monkeypatch.delenv(unsupported.QUEUE_ENV, raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/x/cache/satc/desk/0.17.0")
    first = unsupported.default_queue()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/x/cache/satc/desk/0.18.0")
    assert unsupported.default_queue() == first


# --- and the report has to actually read it -------------------------------
# Moving the store without moving the reader would be worse than the bug: the
# queue would be durable and invisible.

def _holes():
    import sys
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tools"))
    import holes
    return holes


def test_the_report_reads_the_stable_queue(monkeypatch, tmp_path):
    q = tmp_path / "CLOSE.md"
    monkeypatch.setenv(unsupported.QUEUE_ENV, str(q))
    entry = unsupported.from_question(
        "a deposit nobody can identify", why="authority_absent", existing=[])
    unsupported.append(q, entry)

    holes = _holes()
    listed = [p for _, _, p in holes.stores()]
    assert q in listed, (
        "the durable queue is not in the report's stores, so a parked question "
        "would be filed somewhere nobody reads")


def test_the_report_still_reads_a_queue_written_before_the_move(monkeypatch, tmp_path):
    """Aggregating beats migrating: a queue written to the old in-tree path is
    exactly the one somebody is still waiting on an answer for."""
    monkeypatch.setenv(unsupported.QUEUE_ENV, str(tmp_path / "nothing-here.md"))
    holes = _holes()
    root = Path(__file__).resolve().parent.parent
    where = [w for _, w, _ in holes.stores(root)]
    assert any(w.startswith("unfiled/") for w in where), (
        "the in-tree queue is no longer read, so entries filed before the "
        "move have gone silent")


def test_a_path_outside_the_tree_is_still_named_for_a_person(monkeypatch):
    """`_where` raises for anything outside root, which is now the normal case
    for the durable queue — so the report needs the other spelling."""
    holes = _holes()
    shown = holes._outside(Path.home() / ".satc" / "desk" / "unfiled" / "CLOSE.md")
    assert shown.startswith("~/") and "\\" not in shown
