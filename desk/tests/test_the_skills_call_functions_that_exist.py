"""Every call in a skill binds against the real signature.

WHY THIS EXISTS. `skills/be-the-desk/SKILL.md` told its reader, in two worked
examples, to call:

    ask.answer(question, desk, position="an entry in the books", ...)

There is no such signature. `answer` takes ONE positional parameter and
everything after it is keyword-only — `desk` stopped being an argument when
`dec-kill` deleted the desks on 10 September. The suite was green the whole
time, because a skill is a Markdown file and nothing read it.

A SKILL IS NOT DOCUMENTATION. It is prose an agent executes at runtime, in a
session that has no way to check it and every reason to trust it. A wrong call
here is a live defect that surfaces as a TypeError in front of whoever was
trying to close a set of books — which is where Forge-Occam found it, in the
Sarcia pilot.

WHAT THIS CHECKS AND WHAT IT CANNOT. It parses every fenced `python` block,
which catches a syntax error outright, then binds every call on a module this
repository owns against that function's real signature. It cannot check that the
VALUES are sensible, or that the example is good advice. It checks the one thing
that is mechanically knowable and was mechanically wrong.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
SKILLS = sorted(HERE.glob("skills/*/SKILL.md"))

#: Modules this repository owns. A call on anything else -- `json.dumps`, a
#: local variable, the standard library -- is not ours to police, and pretending
#: otherwise would make the test fail on the next example that uses `pathlib`.
OURS = {"ask", "record", "engine", "unsupported", "judging", "pool",
        "positions", "relay", "domains", "candidates", "proving", "searching"}

_BLOCK = re.compile(r"^```python\n(.*?)^```", re.M | re.S)


def _blocks(path: Path) -> list[tuple[int, str]]:
    """Each fenced python block with the line it starts on, for the message."""
    out = []
    text = path.read_text(encoding="utf-8")
    for m in _BLOCK.finditer(text):
        out.append((text[:m.start()].count("\n") + 1, m.group(1)))
    return out


def test_there_are_skills_with_code_to_check():
    """An empty denominator passes every assertion below it.

    This is the failure the repository has already paid for twice: a guard that
    measured nothing and reported clean. If the skills stop carrying examples,
    this file should be deleted, not left quietly passing.
    """
    assert SKILLS, "no SKILL.md found at all"
    total = sum(len(_blocks(p)) for p in SKILLS)
    assert total >= 5, f"only {total} python blocks across {len(SKILLS)} skills"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_python_block_parses(path):
    for line, src in _blocks(path):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"{path.name} line {line}: {e}\n\n{src}")


def _calls(src: str):
    """Calls of the form `<module>.<name>(...)` on a module we own."""
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)):
            continue
        if f.value.id not in OURS:
            continue
        yield f.value.id, f.attr, node


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_call_binds_against_the_real_signature(path):
    problems = []
    for line, src in _blocks(path):
        for mod_name, attr, node in _calls(src):
            try:
                mod = importlib.import_module(mod_name)
            except ImportError:                       # not on this path; skip
                continue
            fn = getattr(mod, attr, None)
            if fn is None:
                problems.append(
                    f"line {line}: {mod_name}.{attr} does not exist")
                continue
            if not callable(fn):
                continue
            try:
                sig = inspect.signature(fn)
            except (TypeError, ValueError):            # builtins, C types
                continue
            # A splat hides the shape, so there is nothing to check.
            if any(isinstance(a, ast.Starred) for a in node.args) or \
               any(k.arg is None for k in node.keywords):
                continue
            args = [object()] * len(node.args)
            kwargs = {k.arg: object() for k in node.keywords}
            try:
                sig.bind_partial(*args, **kwargs)
            except TypeError as e:
                problems.append(
                    f"line {line}: {mod_name}.{attr}(...) does not fit "
                    f"{mod_name}.{attr}{sig} — {e}")
    assert not problems, (
        "a skill tells its reader to make a call that cannot work. A skill is "
        "prose an agent EXECUTES, so this is a live defect and not a doc lag:\n  "
        + "\n  ".join(problems))


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_no_skill_still_speaks_in_desks(path):
    """`dec-kill` deleted the desks. A skill still naming one is a live defect.

    The plan that killed them said so in as many words: "the skills are prose an
    agent reads at runtime; a skill still saying 'which desk' after S4 is a live
    defect, not a doc lag." Three of these survived to 25 September.
    """
    text = path.read_text(encoding="utf-8")
    gone = ["desk_name", "which desk", "that desk", "routes the question",
            "ask.answer(question, desk", "ask.consult(question, desk"]
    found = [g for g in gone if g in text]
    assert not found, (
        f"{path.parent.name} still speaks in desks: {found}. There is one "
        f"corpus addressed by citation; there is no desk to name.")
