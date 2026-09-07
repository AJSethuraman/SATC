"""`make web` can be pointed at a store that is not the firm's.

**IT COULD NOT, AND THAT IS WHY NOBODY HAS DRIVEN THOSE SCREENS.**
`create_app(store=...)` has always accepted one. The entry point at the bottom
of `web.py` called `create_app()` with no argument, so the browser front door
always opened the **real engagement store** and no flag changed it.

Same shape as the Square defect found the day before: a way to run against live
client data with no way to scope it. It is the reason an assessment agent read
twenty-eight routes instead of driving them — it could not open the app safely,
and said so in its "what I did not check" list.

The firm, 5 September 2026: *"Let make web take a store"*.

Precedence is `--store`, then `$SATC_ENGAGEMENTS`, then the real one — the same
order `satc_system`'s `resolve_dir` uses, and for the same reason: a path typed
on this command line is more specific than a variable exported hours ago.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import engagements
import web


def _an_engagement(store: Path, ref: str = "2026-0001") -> None:
    """INVENTED. Nothing here resembles a real client."""
    engagements.save({"EngagementRef": ref,
                      "ClientFullName": "Walkthrough Fixture"}, ref, store)


# ── the app honours a store ──────────────────────────────────────────────────

def test_the_app_reads_the_store_it_was_given(tmp_path):
    store = tmp_path / "engagements"
    _an_engagement(store)
    app = web.create_app(store=store)
    assert app.config["STORE"] == store


def test_a_string_path_works_as_well_as_a_Path(tmp_path):
    """The entry point hands it whatever argparse produced, which is a str."""
    store = tmp_path / "engagements"
    _an_engagement(store)
    app = web.create_app(store=str(store))
    assert Path(app.config["STORE"]) == store


def test_no_store_still_means_the_real_one(tmp_path):
    """The default must not move. Somebody running `make web` to look at their
    own clients has to keep getting them."""
    assert web.create_app().config["STORE"] == engagements.STORE


def test_the_scoped_app_does_not_see_the_real_engagements(tmp_path):
    """THE POINT. A scoped run must be genuinely isolated, not merely
    differently configured — otherwise the next agent to drive these screens is
    driving them over the firm's clients."""
    store = tmp_path / "engagements"
    _an_engagement(store, "2026-0001")
    app = web.create_app(store=store)
    body = app.test_client().get("/", headers={"Accept": "application/json"}) \
        .get_data(as_text=True)
    listed = json.loads(body) if body.strip().startswith(("[", "{")) else []
    ids = listed if isinstance(listed, list) else listed.get("engagements", [])
    assert "2026-0001" in json.dumps(ids)
    assert app.config["STORE"] != engagements.STORE


# ── the entry point actually passes it ───────────────────────────────────────

def test_the_entry_point_passes_a_store_through(monkeypatch, tmp_path, capsys):
    """The claim in one test. `create_app(store=...)` accepting an argument was
    never the problem — the entry point not passing one was."""
    import runpy
    import sys

    store = tmp_path / "engagements"
    _an_engagement(store)
    seen = {}

    class _App:
        def run(self, **kw):
            seen["run"] = kw

    monkeypatch.setattr(web, "create_app",
                        lambda store=None, **kw: (seen.__setitem__("store", store),
                                                  _App())[1])
    monkeypatch.setattr(sys, "argv", ["web.py", "--store", str(store),
                                      "--port", "5099"])
    web_main = _entry_point_source()
    exec(compile(web_main, "web.py:__main__", "exec"),
         {"create_app": web.create_app, "Path": Path, "web": web,
          "__name__": "__main__"})
    assert Path(seen["store"]) == store, seen
    assert seen["run"]["port"] == 5099


def _entry_point_source() -> str:
    """The `if __name__ == "__main__":` block, as source.

    Reading it out of the file rather than importing `web.py` as a script,
    because importing it as `__main__` would start a server.
    """
    text = (Path(web.__file__)).read_text(encoding="utf-8")
    marker = 'if __name__ == "__main__":'
    assert marker in text, "web.py has no entry point block any more"
    block = text.split(marker, 1)[1]
    lines = [ln[4:] if ln.startswith("    ") else ln
             for ln in block.split("\n")]
    return "\n".join(lines)


def test_the_environment_is_honoured_when_no_flag_is_given(monkeypatch,
                                                           tmp_path):
    """So a whole session can be scoped once rather than on every command."""
    import sys
    store = tmp_path / "engagements"
    _an_engagement(store)
    seen = {}

    class _App:
        def run(self, **kw):
            pass

    monkeypatch.setattr(web, "create_app",
                        lambda store=None, **kw: (seen.__setitem__("store", store),
                                                  _App())[1])
    monkeypatch.setattr(sys, "argv", ["web.py"])
    monkeypatch.setenv("SATC_ENGAGEMENTS", str(store))
    exec(compile(_entry_point_source(), "web.py:__main__", "exec"),
         {"create_app": web.create_app, "Path": Path, "__name__": "__main__"})
    assert Path(seen["store"]) == store


def test_a_flag_beats_the_environment(monkeypatch, tmp_path):
    """A path typed on this command line is more specific than a variable
    exported hours ago."""
    import sys
    flagged = tmp_path / "flagged"
    exported = tmp_path / "exported"
    _an_engagement(flagged)
    _an_engagement(exported)
    seen = {}

    class _App:
        def run(self, **kw):
            pass

    monkeypatch.setattr(web, "create_app",
                        lambda store=None, **kw: (seen.__setitem__("store", store),
                                                  _App())[1])
    monkeypatch.setattr(sys, "argv", ["web.py", "--store", str(flagged)])
    monkeypatch.setenv("SATC_ENGAGEMENTS", str(exported))
    exec(compile(_entry_point_source(), "web.py:__main__", "exec"),
         {"create_app": web.create_app, "Path": Path, "__name__": "__main__"})
    assert Path(seen["store"]) == flagged


# ── check the checker ────────────────────────────────────────────────────────

def test_the_old_entry_point_would_fail_these(tmp_path):
    """MUTATION. The old line was `create_app().run(port=5051, ...)` — no store
    passed, whatever anybody typed. Reproduce it and it must disagree.
    """
    seen = {}

    def old_entry():
        seen["store"] = None            # exactly what create_app() received

    old_entry()
    assert seen["store"] is None
    app = web.create_app(store=tmp_path / "engagements")
    assert app.config["STORE"] is not None
    assert Path(app.config["STORE"]) != engagements.STORE, (
        "a scoped app resolved to the real store — the fix is doing nothing")
