"""Routing: a lookup, never a judgement — and canon's rule, not a copy of it.

The reliable path in is not the doer remembering to ask. It is the engine
refusing an out-of-authority act and NAMING the desk, because that does not
depend on a model recognising its own ignorance. This session watched the weaker
mechanism fail in this very repository: canon installed successfully and its
standing behaviour still did not load.
"""
from __future__ import annotations

import pytest

import _canon
import routing
from conftest import DESKS, ROOT
from record import RecordError

SUBJECTS = """## demo · A demo desk

**Fires on:** alpha, beta, gamma
"""


@pytest.fixture
def regs():
    return routing.registry(DESKS)


# ── canon's rule, borrowed rather than rewritten ─────────────────────────────

def test_the_matching_rule_comes_from_canon_not_from_here():
    """Copying `touches` here would be writing it a third time. Canon's own note
    records what happened the second time: two rules that agreed until they did
    not, with nothing comparing them."""
    assert _canon.load_record().touches is not None
    import pathlib
    for f in ROOT.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert "def touches" not in src or f.name == "_canon.py", (
            f"{f.name} defines its own touches(); use canon's"
        )


def test_matching_is_whole_word_only():
    """Substring matching once made "extension" fire on "extensive"."""
    touches = _canon.load_record().touches
    assert touches("a repair to the roof", "repair")
    assert not touches("the repairman called", "repair")


def test_a_missing_canon_raises_rather_than_falling_back(monkeypatch, tmp_path):
    """A quiet reimplementation is the failure canon's note describes. A broken
    install should say so, not limp."""
    monkeypatch.setenv("CANON_ROOT", str(tmp_path / "nowhere"))
    monkeypatch.setattr(_canon, "_candidates", lambda: [tmp_path / "nowhere"])
    monkeypatch.delitem(__import__("sys").modules, "canon_record", raising=False)
    with pytest.raises(_canon.CanonMissing, match="dependency"):
        _canon.load_record()


def test_canon_is_found_in_the_marketplace_cache_layout(monkeypatch, tmp_path):
    """The layout the repository never exercises, and the one #230 turns on.

    Installed from a marketplace, plugins are cached as
    `<cache>/<marketplace>/<plugin>/<version>` — so canon's root is
    `.../satc/canon/1.4.0` while desk's is `.../satc/desk/0.1.0`. A sibling
    lookup from desk resolves to `.../satc/desk/canon`, which never exists.

    Written sibling-only first and it passed everything, because the repository
    is the only place the tests ran and there both rules agree. Found by opening
    the real plugin cache. The fixture below is built here rather than read from
    this machine, so the test proves the shape rather than the installation.
    """
    import sys

    cache = tmp_path / "cache" / "satc"
    canon = cache / "canon" / "1.4.0"
    desk = cache / "desk" / "0.1.0"
    canon.mkdir(parents=True)
    desk.mkdir(parents=True)
    real = (ROOT.parent / "canon" / "record.py").read_text(encoding="utf-8")
    (canon / "record.py").write_text(real, encoding="utf-8")

    monkeypatch.delenv("CANON_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(desk))
    monkeypatch.setattr(_canon, "__file__", str(desk / "_canon.py"))
    monkeypatch.delitem(sys.modules, "canon_record", raising=False)

    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found, (
        "canon is not findable in the marketplace cache layout; a sibling "
        "lookup from desk resolves to .../desk/canon, which never exists"
    )
    assert found[0] == canon


def test_the_newest_installed_version_wins(monkeypatch, tmp_path):
    """Two versions can sit in the cache at once. Take the later one."""
    cache = tmp_path / "cache" / "satc"
    desk = cache / "desk" / "0.1.0"
    desk.mkdir(parents=True)
    for v in ("1.3.0", "1.4.0"):
        d = cache / "canon" / v
        d.mkdir(parents=True)
        (d / "record.py").write_text("touches = None\n", encoding="utf-8")
    monkeypatch.delenv("CANON_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(desk))
    monkeypatch.setattr(_canon, "__file__", str(desk / "_canon.py"))
    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found[0].name == "1.4.0"


def test_the_repository_layout_still_resolves():
    """The layout that already worked must keep working — this is how the suite
    finds canon on every other test in this file."""
    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found, "canon is not findable from the repository checkout"


# ── the wrapped-field regression ─────────────────────────────────────────────

def test_a_wrapped_subject_list_is_read_in_full():
    """Written with a single-line read first, this parsed 5 subjects out of 24
    and reported success. A silent partial read is worse than an error, because
    routing then works for some questions and quietly misses others."""
    wrapped = ("## demo · A demo desk\n\n"
               "**Fires on:** alpha, beta,\ngamma, delta,\nepsilon\n")
    r = routing.parse_subjects(wrapped, "demo")
    assert r.fires_on == ("alpha", "beta", "gamma", "delta", "epsilon")


def test_the_shipped_desk_declares_more_subjects_than_one_line_would_hold(regs):
    assert len(regs[0].fires_on) > 10, (
        "if this drops sharply, the wrapped-field read has regressed"
    )


def test_a_desk_with_no_subjects_is_an_error():
    """A desk nothing routes to is a desk nobody asks."""
    with pytest.raises(RecordError, match="Fires on"):
        routing.parse_subjects("## demo · x\n\n**Other:** y\n", "demo")


# ── routing itself ───────────────────────────────────────────────────────────

def test_a_question_on_subject_reaches_the_desk(regs):
    assert [r.desk for r in routing.route("is a new roof an improvement?", regs)] \
        == ["fixed-assets"]


def test_route_itself_matches_whole_words_not_substrings(regs):
    """Testing canon's `touches` is not the same as testing that route() USES it.

    Found by a mutation run: swapping route() to `term in question` left the
    suite green, because the whole-word test above exercised canon directly.
    That is canon's own recorded failure -- the rule written twice, once
    whole-word and once not, with nothing comparing them -- reproduced here.

    "repair" is one of this desk's subjects, so a substring matcher fires on
    "repairman" and a whole-word one does not.
    """
    assert any("repair" in r.fires_on for r in regs), "fixture no longer proves it"
    assert routing.route("the repairman called about parking", regs) == [], (
        "route() is matching substrings; it must use canon's whole-word rule"
    )


def test_silence_is_a_result(regs):
    """A question matching nothing returns nothing — not a nearest guess. A
    router that always answers is one whose answer means nothing."""
    assert routing.route("what is the weather today", regs) == []
    assert routing.refusal_naming_the_desk("what is the weather today", regs) == ""


def test_routing_involves_no_model(regs):
    """"Does this question touch the subject this desk is about" is a comparison,
    not a judgement. That is C8's test and the reason this stays deterministic."""
    out = [routing.route("capitalize the HVAC?", regs) for _ in range(5)]
    assert all(o == out[0] for o in out)


def test_a_refusal_names_the_desk_and_the_next_step(regs):
    """On a small model a bare "no" ends the run; a refusal naming the next step
    self-corrects it."""
    msg = routing.refusal_naming_the_desk("should I capitalize this?", regs)
    assert "fixed-assets" in msg
    assert "ask_desk" in msg
    assert "citation" in msg


def test_the_caller_holds_one_schema_not_one_per_desk(regs):
    """Rule 1: an 8,192-token window against ~11k of tool schemas silently
    truncates the model's own instructions. The router resolves desks
    server-side, where it costs the caller nothing."""
    import inspect
    sig = inspect.signature(routing.route)
    assert list(sig.parameters) == ["question", "registrations"], (
        "route() must take a question and the registry, not a desk name — the "
        "caller must not have to know which desks exist"
    )
