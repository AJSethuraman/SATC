"""A test that asserts something is ABSENT must first show the code ran at all.

THE GENERAL FORM OF FOUR SELF-PROVING TESTS IN ONE WEEK, named by the Forge desk
on 8 September 2026 after the fourth:

    "A CONTROL THAT IS REFUSED BEFORE IT REACHES THE CODE UNDER TEST CANNOT
     DISTINGUISH 'absent because correct' FROM 'absent because unreachable.'
     […] engine.serve is an ORDERED chain of refusals — domain gate, ratified
     position, subject/source, judgment. EVERY NEGATIVE ASSERTION ABOUT A LATER
     STAGE IS AT RISK IF THE FIXTURE TRIPS AN EARLIER ONE."

The instance that produced it: a control asserting the straddle note was absent
on a question the DOMAIN GATE refuses. The note is a field of `Served`; the
answer was a `Refusal`; the assertion could not have failed under any mutation,
and a mutation firing the note on every straddle passed all sixteen tests.

THE FIX IS MECHANICAL, WHICH IS WHY IT IS A TEST AND NOT A NOTE IN A README:

    "Before asserting the note is absent, assert the answer was Served — i.e.
     that the stage ran at all. A test that says 'not present' without saying
     'and we got far enough for it to be present' is the self-proving control,
     in general form."

WHAT THIS SCANS FOR, AND WHY IT IS THE NARROW FORM. `out.straddle == ""` on a
`Refusal` raises `AttributeError` — Python already fails that loudly, and most
of the suite is protected by it without knowing. The form that passes SILENTLY
is `getattr(out, "field", <default>)`, because the default is exactly the value
being asserted. So that is what is banned inside a negative assertion, and the
sweep that wrote this found the whole suite clean but for the one instance that
prompted it.
"""
import ast
import pathlib
import re

import engine

HERE = pathlib.Path(__file__).resolve().parent

#: Fields that exist on `Served` and not on `Refusal`. A `getattr` default on
#: one of these is a test quietly agreeing with a refusal it never asked about.
ONLY_WHEN_SERVED = tuple(
    f for f in engine.Served.__dataclass_fields__
    if f not in engine.Refusal.__dataclass_fields__)

#: The shape of an assertion about absence.
ABSENT = re.compile(r"""== ?["']{2}|== ?\(\)|\bis None\b|\bnot \b""")


def _functions(path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield node, "\n".join(lines[node.lineno - 1: node.end_lineno or node.lineno])


def test_no_field_lives_on_both_branches_at_once():
    """THE SEAM IN THIS FILE'S OWN DEFINITION, found by the Forge desk reading
    the guard rather than the code it guards — which is the thing mutation
    cannot do.

    `ONLY_WHEN_SERVED` is the DIFFERENCE of the two dataclasses. Today the
    intersection is empty, so it happens to be all of `Served`, and the coverage
    is complete: `AttributeError` catches every cross-branch access loudly and
    the scan below catches the silent one. **Correct, and correct by a
    coincidence of the current shape.**

        "THE DAY A FIELD LANDS ON BOTH DATACLASSES, THREE THINGS HAPPEN AT ONCE
         AND ALL SILENTLY:
           1. AttributeError stops firing for that field — a Refusal now has it.
           2. ONLY_WHEN_SERVED silently DROPS it, because it is no longer
              Served-only.
           3. `getattr(out, "<that field>", "")` becomes legal again, and means
              nothing again.
         The guard narrows itself precisely when the risk appears. Nothing goes
         red."

    So this is prevention rather than detection, and it fails on the commit that
    creates the risk — the only moment anyone will be thinking about it.
    `working` on a `Served` is the obvious future candidate; if the firm wants
    it, this goes red, it moves to an explicit list, and the scan keeps covering
    it. That is the decision being forced, not forbidden."""
    both = set(engine.Served.__dataclass_fields__) & set(
        engine.Refusal.__dataclass_fields__)
    assert not both, (
        f"{sorted(both)} live on both branches: `AttributeError` no longer "
        f"protects them and ONLY_WHEN_SERVED no longer covers them. Decide "
        f"here, not later — add them to an explicit list the scan reads.")


def test_the_fields_this_guards_actually_exist():
    """DERIVED FROM THE DATACLASSES, not listed here. A field added to `Served`
    is covered the day it is added; a hand-typed list would cover whatever was
    true when somebody last remembered."""
    assert "straddle" in ONLY_WHEN_SERVED
    assert "judged" in ONLY_WHEN_SERVED
    assert "reason" not in ONLY_WHEN_SERVED, "reason is on Refusal too"


def test_no_test_asserts_a_served_field_is_absent_through_a_getattr_default():
    offences = []
    for path in sorted(HERE.glob("test_*.py")):
        if path.name == pathlib.Path(__file__).name:
            continue
        for fn, body in _functions(path):
            for line in body.splitlines():
                stripped = line.strip()
                if not stripped.startswith("assert") or not ABSENT.search(stripped):
                    continue
                for field in ONLY_WHEN_SERVED:
                    if f'getattr(' in stripped and f'"{field}"' in stripped:
                        offences.append(f"{path.name}::{fn.name}: {stripped[:90]}")
    assert not offences, (
        "these assert a Served-only field is absent through a `getattr` "
        "default, so they pass unchanged when the answer was REFUSED and the "
        "code under test never ran. Assert `isinstance(out, engine.Served)` "
        "first — 'not present' means nothing without 'and we got far enough "
        "for it to be present':\n  " + "\n  ".join(offences))


def test_the_scan_can_actually_fail():
    """THE GUARD ON THE GUARD, and this file would be self-proving without it —
    which would be the defect wearing the costume of its own fix."""
    fake = 'def t():\n    assert getattr(out, "straddle", "") == ""\n'
    tree = ast.parse(fake)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    line = fake.splitlines()[1].strip()
    assert line.startswith("assert") and ABSENT.search(line)
    assert any(f'"{f}"' in line for f in ONLY_WHEN_SERVED)
    assert fn.name == "t"
