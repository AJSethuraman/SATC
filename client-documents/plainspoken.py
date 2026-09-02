"""Does the software talk to its user, or about itself?

THE FIRM, 2 September 2026, looking at a screenshot of the refusal screen:

    like in the attached it says something about the yaml. why would that be
    in our software? what software says stuff like that to its user?

The screen had read: *"This is work the firm does not take. firm-settings.yaml
lists it under `hard_no` and the interview schema marks the options
themselves."* A filename and two code identifiers, on a screen a preparer sees
mid-call with a client in the room.

It was not a slip. It was written by whoever built the thing, for whoever
builds the thing, and then rendered to whoever uses it -- which is the same
failure `CLAUDE.md` records about the price page ("A requirement written for
whoever builds the thing is not copy"), one surface over.

WHAT THIS CHECKS AND WHAT IT DOES NOT. A terminal command may name a file and
print the next command to type: its reader is already at a terminal, and
"run this next" is the most useful thing a CLI can say. A BROWSER SCREEN may
not. Its reader is doing tax work, not running software, and every filename on
it is a thing they now have to know about and cannot act on.

So this reads the strings that reach a browser screen, and nothing else.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# What a screen must not say, and why each one is here.
TELLS: list[tuple[str, str]] = [
    (r"\b[\w-]+\.(?:yaml|yml|py|json)\b",
     "names a file the reader cannot open from here"),
    (r"\bpython cli\.py\b|\bcli\.py \w+",
     "tells someone in a browser to run a terminal command"),
    (r"\bschema\b",
     "'schema' is a word about the software, not about the work"),
    (r"\bthe registry's\b|\bfrom the registry\b",
     "'the registry' names something the reader cannot see"),
    (r"`_[a-z]\w*`|`[a-z]+_[a-z_]+`",
     "a code identifier in backticks"),
    (r"\bmerge field\b",
     "'merge field' is the builder's name for a blank"),
]

# Functions in `web.py` that BUILD a page. Everything else there -- helpers,
# converters, the CSS -- is not read by a person.
BODY = re.compile(r"_body$|^body_|_page$")


def _rendered_strings(path: Path) -> list[tuple[int, str]]:
    """Every literal inside a page-building function, with its line."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not BODY.search(node.name):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if len(sub.value) > 20:
                    out.append((sub.lineno, sub.value))
    return out


def _reasons(path: Path) -> list[tuple[int, str]]:
    """Refusal text -- it is built away from the browser and rendered by it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Outcome":
            for kw in node.keywords:
                if kw.arg == "reason":
                    for sub in ast.walk(kw.value):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            out.append((sub.lineno, sub.value))
    return out


def _help_text() -> list[tuple[str, str]]:
    """The `help:` a preparer reads under each interview question."""
    import yaml
    spec = yaml.safe_load(
        (ROOT / "registry" / "interview.yaml").read_text(encoding="utf-8")) or {}
    out = []
    for section in spec.get("sections") or []:
        for q in section.get("questions") or []:
            if q.get("help"):
                out.append((q["id"], q["help"]))
    return out


def findings() -> tuple[list[str], int]:
    """`(what reads wrong, how many strings were examined)`.

    THE SECOND NUMBER IS HALF THE ANSWER (S2). "Nothing reads wrong" across
    four strings is not the same report as across four hundred, and this check
    is one refactor away from silently examining nothing.
    """
    bad: list[str] = []
    examined = 0

    def look(where: str, line, text: str) -> None:
        nonlocal examined
        examined += 1
        flat = " ".join(text.split())
        for pattern, why in TELLS:
            m = re.search(pattern, flat)
            if m:
                bad.append(f"{where}:{line}  {why}  ({m.group()!r})\n"
                           f"      {flat[:96]}")
                return

    web = ROOT / "web.py"
    if web.exists():
        for line, text in _rendered_strings(web):
            look("web.py", line, text)
    intake = ROOT / "intake.py"
    if intake.exists():
        for line, text in _reasons(intake):
            look("intake.py", line, text)
    for qid, text in _help_text():
        look(f"interview.yaml[{qid}]", "help", text)

    return bad, examined
