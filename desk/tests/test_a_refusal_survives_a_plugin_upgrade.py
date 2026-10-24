"""A refusal is not filed inside the release that refused it.

THE SAME BUG AS `test_the_parked_queue_survives_a_plugin_upgrade`, in the store
next door, and it outlived that fix by seventeen days. `default_queue` moved the
PARKED-QUESTION queue out of the plugin tree on 8 September. The REFUSAL store --
what `ask.answer` writes every time the engine declines to serve -- kept deriving
its path from `ask.CORPUS`, which is `HERE / "corpus"`, which installed is
`~/.claude/plugins/cache/satc/desk/<version>/corpus/`.

MEASURED BEFORE IT WAS FIXED, on the machine this was found on, 25 September 2026:

    0.27.0/corpus/unsupported/forge.md       18 refusals
    0.27.0/corpus/unsupported/frontier.md     4 refusals
    0.28.0/corpus/unsupported/                does not exist
    0.34.0/corpus/unsupported/                does not exist

22 findings in a release nobody runs, invisible to the desk that is installed,
and no error anywhere. `tools/holes.py` reported zero and the zero read as a
clean result.

WHY THIS IS A SEPARATE FILE rather than more cases in the sibling's. The sibling
pins the queue. This pins the store. Folding them together would make one fixture
speak for two locations, which is the shape of the mistake being fixed: the fix
was applied to a location instead of to a rule.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

import unsupported

HERE = Path(__file__).resolve().parent.parent


@pytest.fixture
def unredirected(monkeypatch):
    """The suite redirects the store so tests cannot touch the firm's own.

    These tests are ABOUT the default, so they have to see it. Every other test
    in the suite must not — `conftest.never_the_real_store` is autouse for that
    reason, and this is the one place that steps back out of it.
    """
    monkeypatch.delenv(unsupported.STORE_ENV, raising=False)


def test_the_default_is_outside_any_plugin_cache(unredirected):
    p = unsupported.default_store()
    parts = [s.lower() for s in p.parts]
    for forbidden in ("cache", "plugins", "site-packages"):
        assert forbidden not in parts, (
            f"the refusal store resolves inside {forbidden!r} ({p}), so every "
            f"finding dies with the release that recorded it")


def test_the_default_carries_no_version_in_its_path(unredirected):
    for part in unsupported.default_store().parts:
        assert not re.fullmatch(r"v?\d+\.\d+(\.\d+)?", part), (
            f"{part!r} looks like a release, so the store moves on upgrade — "
            f"which is how 22 refusals ended up stranded in 0.27.0")


def test_it_is_not_inside_the_plugin_checkout_either(unredirected):
    """A refusal carries the question that was asked, and mid-close a question
    can name anything about a client. CLAUDE.md: a client's affairs inside a
    checkout are one `git add` from being published."""
    assert HERE not in unsupported.default_store().resolve().parents


def test_two_releases_resolve_the_same_store(unredirected, monkeypatch):
    """The property that was broken, stated directly."""
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/x/cache/satc/desk/0.27.0")
    first = unsupported.default_store()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/x/cache/satc/desk/0.34.0")
    assert unsupported.default_store() == first


def test_a_deployment_can_point_it_elsewhere(monkeypatch, tmp_path):
    monkeypatch.setenv(unsupported.STORE_ENV, str(tmp_path / "s.md"))
    assert unsupported.default_store() == tmp_path / "s.md"


def test_an_empty_override_is_not_an_override(unredirected, monkeypatch):
    """A shell that exports the variable blank must not silently relocate the
    store to the current directory — the sibling queue is pinned the same way."""
    monkeypatch.setenv(unsupported.STORE_ENV, "   ")
    assert unsupported.default_store() == (
        Path.home() / ".satc" / "desk" / "unsupported" / "asked.md")


# --- the engine has to actually use it ------------------------------------

def test_a_refusal_lands_in_the_durable_store_and_not_beside_the_corpus(
        monkeypatch, tmp_path):
    """The end the whole thing exists for, through the real front door."""
    import shutil
    import ask
    import engine
    import conftest

    corpus = tmp_path / "corpus"
    shutil.copytree(HERE / "corpus", corpus)
    store = tmp_path / "durable" / "asked.md"
    monkeypatch.setenv(unsupported.STORE_ENV, str(store))

    out = ask.answer("is a brewery tab a business meal?",
                     position="fully deductible", citation="26 CFR 9.9-9",
                     model="a test", corpus=corpus,
                     judged=conftest.a_judgment("some words"))
    assert isinstance(out, engine.Refusal)

    assert store.is_file(), "the refusal was not filed in the durable store"
    kept = unsupported.parse(store.read_text(encoding="utf-8"))
    assert len(kept) == 1 and "brewery" in kept[0].question
    assert not (corpus / "unsupported" / "asked.md").exists(), (
        "the refusal was ALSO written inside the corpus, which installed is "
        "inside the versioned plugin cache")


def test_a_caller_can_still_say_where(monkeypatch, tmp_path):
    """`queue=` is how a run against a copied record keeps its findings with it.

    Without this the argument could be deleted and only the test above would
    notice, which would make the default look like the only behaviour.
    """
    import shutil
    import ask
    import conftest

    corpus = tmp_path / "corpus"
    shutil.copytree(HERE / "corpus", corpus)
    monkeypatch.setenv(unsupported.STORE_ENV, str(tmp_path / "unused" / "asked.md"))
    here = tmp_path / "beside" / "asked.md"

    ask.answer("is a brewery tab a business meal?", position="fully deductible",
               citation="26 CFR 9.9-9", model="a test", corpus=corpus,
               queue=here, judged=conftest.a_judgment("some words"))

    assert here.is_file(), "an explicit queue= was ignored"
    assert not (tmp_path / "unused" / "asked.md").exists()


# --- and the report has to read it ----------------------------------------

def test_the_report_reads_the_durable_store(monkeypatch, tmp_path):
    """Moving the store without moving the reader is worse than the bug: the
    findings would be durable and invisible."""
    sys.path.insert(0, str(HERE / "tools"))
    import holes

    store = tmp_path / "asked.md"
    monkeypatch.setenv(unsupported.STORE_ENV, str(store))
    unsupported.append(store, unsupported.from_question(
        "what proves a deposit is revenue?", why="authority_absent", existing=[]))

    listed = [p for _, _, p in holes.stores()]
    assert store in listed, (
        "the durable refusal store is not among the report's stores, so every "
        "refusal would be filed somewhere nobody reads")


def test_the_report_still_reads_refusals_filed_before_the_move(monkeypatch):
    """Aggregating beats migrating. The 22 stranded in 0.27.0 are not moved by
    this change — nothing here reaches into a plugin cache — but an in-tree
    `corpus/unsupported/` written before the move must not go silent."""
    sys.path.insert(0, str(HERE / "tools"))
    import inspect
    import holes
    src = inspect.getsource(holes.stores)
    assert '"corpus" / "unsupported"' in src, (
        "the in-tree refusal path is no longer read, so anything filed there "
        "before the move has gone silent")
