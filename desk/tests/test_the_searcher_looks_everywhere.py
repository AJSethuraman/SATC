"""The searcher has no allow-list, and that was the firm's call.

THE ARGUMENT THAT ENDED THE OTHER DESIGN, in one question: *"how would you know
you need to access a site not on the whitelist before being asked?"* An
allow-list can only contain publishers somebody already thought of, so a
discovery tool wearing one discovers only what the record already knows — the
one thing it is not needed for. The gate moved to the record instead: look
anywhere, store only what a declared publisher backs, and bring everything else
to the firm as a proposal about a publisher.

That decision is a paragraph in `searching.py` and a paragraph is not a
constraint. These tests are: a hit from a host nobody has ever declared comes
back from `look`, and the searcher cannot answer anything because it cannot
reach the thing that answers.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                               # noqa: E402
import searching                                            # noqa: E402


class _Refusal:
    def __init__(self, reason, detail=""):
        self.reason, self.detail = reason, detail


def _gap():
    return searching.Gap.from_refusal(
        _Refusal(searching.ABSENT, "nothing in the record covers it"),
        "fixed-assets", "may a roof replacement be expensed?")


# ── search everywhere ─────────────────────────────────────────────────────────

def test_a_hit_from_a_host_no_desk_has_declared_still_comes_back():
    """THE WHOLE DECISION, mechanically. If this ever filters, discovery dies."""
    def some_engine(q):
        return [{"url": "https://tax-blog.example/roofs", "title": "Roofs"},
                {"url": "https://www.ecfr.gov/current/title-26/section-1.263(a)-3"}]

    hits = searching.look(_gap(), ["roof replacement capitalize"], some_engine)
    assert {h.host for h in hits} == {"tax-blog.example", "ecfr.gov"}


def test_look_holds_no_list_of_hosts_at_all():
    """Not "the list is empty" — there is no list, so none can be filled in."""
    src = (HERE / "searching.py").read_text()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "look")
    hosts = [n.value for n in ast.walk(fn)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and "." in n.value and " " not in n.value]
    assert hosts == [], f"look() names hosts: {hosts}"


def test_every_hit_remembers_which_query_found_it():
    hits = searching.look(_gap(), ["one", "two"],
                          lambda q: [{"url": f"https://e.example/{q}"}])
    assert sorted(h.query for h in hits) == ["one", "two"]


def test_the_same_url_found_twice_is_one_hit():
    hits = searching.look(_gap(), ["a", "b"],
                          lambda q: [{"url": "https://e.example/same"}])
    assert len(hits) == 1


def test_a_query_that_returns_nothing_is_not_an_error():
    assert searching.look(_gap(), ["nothing"], lambda q: None) == ()


# ── a gap opens only on a refusal, and only on one of them ────────────────────

def test_only_an_absent_authority_opens_a_gap():
    gap = _gap()
    assert gap.reason == searching.ABSENT and gap.desk == "fixed-assets"
    assert gap.opened_at, "a gap records when it opened"


@pytest.mark.parametrize("reason", [
    r for r in engine.REASONS if r != searching.ABSENT])
def test_no_other_refusal_sends_the_searcher_out(reason):
    """Searching does not fix a licence, a missing fact, or the firm's choice.

    Each of these has its own next step and none of them is a web search. A
    searcher that ran on `authority_permits_choice` would go looking for someone
    on the internet to make the firm's decision for them.
    """
    with pytest.raises(searching.SearchError, match=reason):
        searching.Gap.from_refusal(_Refusal(reason), "fixed-assets", "q?")


def test_there_is_no_way_to_open_a_gap_without_a_refusal():
    """No constructor takes a bare question. The searcher is a repair path."""
    with pytest.raises(searching.SearchError):
        searching.Gap.from_refusal(_Refusal(""), "fixed-assets", "q?")


def test_the_reason_the_searcher_watches_for_is_one_the_engine_counts():
    """`searching` may not import `engine`, so the two constants could drift.

    This is the seam where a rename would silently switch the searcher off:
    every refusal would stop opening a gap and nothing would fail.
    """
    assert searching.ABSENT in engine.REASONS


# ── it cannot answer, and the import graph is why ─────────────────────────────

def test_searching_imports_neither_the_engine_nor_the_front_door():
    tree = ast.parse((HERE / "searching.py").read_text())
    named = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    named |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
              for a in n.names}
    assert not named & {"engine", "ask"}, f"searching imports {named}"


def test_importing_searching_does_not_drag_in_anything_that_can_answer():
    """Transitively, in a fresh interpreter — the direct check is not enough.

    `proving` imports cleanly today. If it ever grew an `engine` import, the AST
    test above would still pass while the property it protects was gone.
    """
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import searching; "
         "print(','.join(sorted({'engine','ask'} & set(sys.modules))))" % str(HERE)],
        capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "", f"searching pulled in {out.stdout.strip()}"


def test_the_only_thing_this_module_ever_builds_out_of_the_record_is_a_passage():
    """The handover to the rest of the plugin is a `record.Passage`, full stop.

    Not a stylistic point. A searcher that could construct a `Position` would be
    writing the firm's judgement from something it read on the internet, and the
    two-store split — `extracted/` an agent may write, `positions/` it may only
    propose — would have a hole in it the guards do not watch.
    """
    tree = ast.parse((HERE / "searching.py").read_text())
    built = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "record"
             and n.func.attr[:1].isupper()}
    assert built == {"Passage"}, f"searching also builds record.{built}"
