"""The shared layer must not know what domain it serves.

**Read the rule carefully, because the obvious version of it is wrong.** This is
not "accounting vocabulary is forbidden." The firm, 4 September 2026:

    accounting-specific isn't the problem, it's just like… me saying it
    shouldn't be total jargin

The rule is that a shared **interface or code path** must not be meaningful only
to an accountant. Prose explaining a concept is fine — this file's own docstring
names accounting concepts and must keep passing. A shared function whose name,
parameters, fields or closed vocabulary presupposes a domain is not.

So this checks the **API**, via the syntax tree, and never the comments. A grep
over comment text is easy to write, easy to satisfy, and measures the wrong
thing.

WHY IT GATES THE BUILD RATHER THAN BEING A REVIEW HABIT. v2's whole metric is how
many changes the second desk forces on this layer. If a domain leaks in
gradually, that measurement is destroyed before it is ever taken, and nobody
notices because each individual leak looked reasonable.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from conftest import ROOT

#: The modules every desk shares. Anything under `desks/` is data for one domain
#: and is not covered — that is the whole point of the split.
SHARED = ("record.py", "engine.py", "fetch.py", "guards.py", "unsupported.py",
          "positions.py")

#: Vocabulary that would mean this layer had learned a trade. Kept as stems so
#: inflections are caught: "depreciat" covers depreciate, depreciation,
#: depreciable.
DOMAIN_STEMS = (
    "capitalis", "capitaliz", "depreciat", "amortis", "amortiz", "accrual",
    "accrue", "ledger", "journal", "debit", "gaap", "fasb", "irc", "asc",
    "taxpayer", "audit", "invoice", "expense", "deduct", "restoration",
    "betterment", "improvement", "engagement", "bookkeep", "workpaper",
)


def _api_names(path: Path) -> set[str]:
    """Every identifier a caller could touch, and no prose.

    Docstrings are stripped by construction: `ast` gives them as `Expr` nodes and
    nothing here reads them. Comments never reach the tree at all.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                for a in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                    names.add(a.arg)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)          # dataclass fields
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def _vocabulary_values(path: Path) -> set[str]:
    """The closed vocabularies — tiers, access values, reasons, markers.

    These ARE the interface: a desk declares itself in these words, so a domain
    term here would make every desk speak one trade.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    out.add(sub.value)
        # Enum members: `NAME = "value"` inside a class
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for sub in ast.walk(stmt.value):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            out.add(sub.value)
    return out


def _offending(words: set[str]) -> list[tuple[str, str]]:
    return sorted(
        (w, stem) for w in words for stem in DOMAIN_STEMS
        if stem in w.lower()
    )


@pytest.mark.parametrize("module", SHARED)
def test_no_shared_interface_presupposes_a_domain(module):
    bad = _offending(_api_names(ROOT / module))
    assert not bad, (
        f"{module} exposes {bad} — a caller would have to know accounting to use "
        f"this layer. Move it into a desk, or name it for what it does rather "
        f"than what it is currently used for."
    )


@pytest.mark.parametrize("module", SHARED)
def test_no_closed_vocabulary_speaks_one_trade(module):
    bad = _offending(_vocabulary_values(ROOT / module))
    assert not bad, (
        f"{module}'s vocabulary contains {bad} — every desk declares itself in "
        f"these words, so a domain term here makes them all speak one trade."
    )


def test_prose_naming_a_domain_concept_does_not_fail(tmp_path):
    """The check that proves this is not a grep.

    A module whose docstring, comments and string content are thick with
    accounting must still pass, because explaining a concept is not the same as
    encoding it. If this ever goes red, the test has become the wrong test.
    """
    m = tmp_path / "prose.py"
    m.write_text(
        '"""Grading, explained with an accounting example.\n\n'
        'Whether a roof replacement is a capitalisable improvement or a\n'
        'deductible repair is exactly the kind of judgement a desk escalates.\n'
        'Depreciation, accrual and the ledger are all downstream of it.\n"""\n'
        "# capitalize, depreciate, accrue -- all fine in a comment\n"
        "def grade(answer, known):\n"
        '    """Compare an answer to the one the authority states."""\n'
        "    return answer == known\n",
        encoding="utf-8")
    assert not _offending(_api_names(m))
    assert not _offending(_vocabulary_values(m))


def test_the_check_can_actually_fail(tmp_path):
    """A leak the reviewer would wave through, caught mechanically."""
    m = tmp_path / "leaky.py"
    m.write_text(
        "def is_capitalisable(amount):\n"
        "    return True\n", encoding="utf-8")
    assert _offending(_api_names(m)), "a domain-named public function must be caught"


def test_a_domain_term_in_a_closed_vocabulary_is_caught(tmp_path):
    m = tmp_path / "vocab.py"
    m.write_text('OUTCOMES = ("correct", "must_capitalize")\n', encoding="utf-8")
    assert _offending(_vocabulary_values(m))


def test_desk_data_is_not_covered_by_this_rule():
    """`desks/` is one domain's data and is supposed to be full of its words."""
    problems = (ROOT / "desks" / "fixed-assets" / "PROBLEMS.md").read_text(
        encoding="utf-8")
    assert "capitalize" in problems.lower(), (
        "the desk's own record should speak its trade; if this fails the fixture "
        "changed and the test above is no longer proving a contrast"
    )
