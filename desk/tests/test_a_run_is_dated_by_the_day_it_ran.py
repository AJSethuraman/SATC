"""A folder named for a date must hold what happened on that date.

THE DEFECT, 7 SEPTEMBER 2026. `tools/ask_the_desks.py` wrote its briefs to
`runs/asked-2026-09-05`, hardcoded. Running it two days later did not create a
new run -- it overwrote the old one in place, and seventeen briefs silently
gained POS3 and the marked omission while the directory went on claiming to be
the 5 September evidence. Nothing failed. `git status` was the only witness.

WHY THIS IS THE SAME BUG AS THE TYPED CORPUS FIGURE, which has its own test in
this directory. Both are a fact written by hand next to a fact that moves. The
corpus figure went stale in prose; this one went stale in a path, and the path
version is worse, because prose that disagrees with the record can at least be
read and doubted -- a directory whose name is wrong reads as evidence.

AND IT UNDERMINES AN EXEMPTION THIS SUITE GRANTS. `runs/` and `tie-outs/` are
excused from the corpus-figure sweep because they are DATED ARTIFACTS: "when the
record moves, the exhibits are RE-RUN and re-dated, never patched." That
exemption is only safe while the date is true. A tool that can only ever write
into one day makes patching the default and re-dating impossible, so the
exemption was quietly protecting a lie rather than a record.

THE PATTERN ALREADY EXISTED. `tools/scoreboard_run.py` derives `runs/<today>`
and carries a docstring about what to do when two runs land on the same day.
This is not a new idea being introduced; it is one tool being brought back to
the convention its sibling already followed.
"""
from __future__ import annotations

import pathlib
import re
import sys
from datetime import date

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import ask_the_desks                                       # noqa: E402

#: A run directory under `runs/`, with the date typed into the literal. The
#: shape the defect had, and the shape a reviewer would not look twice at.
_TYPED_RUN = re.compile(r'"runs"\s*/\s*"[^"]*\d{4}-\d{2}-\d{2}[^"]*"'
                        r'|"runs/[^"]*\d{4}-\d{2}-\d{2}[^"]*"')


def test_the_brief_directory_names_the_day_it_is_written():
    assert ask_the_desks.BRIEFS.name == f"asked-{date.today().isoformat()}", (
        f"briefs would be written to {ask_the_desks.BRIEFS.name!r} on "
        f"{date.today().isoformat()}. A run that lands in another day's folder "
        f"overwrites that day's evidence and inherits its date.")
    assert ask_the_desks.BRIEFS.parent.name == "runs"


def test_no_tool_types_a_date_into_a_run_directory():
    """The general rule, so the next tool does not repeat it.

    Only the OUTPUT path is covered. A tool may name a dated run in its prose --
    `extract_ecfr.py` and `scoreboard_run.py` both cite `runs/2026-09-04` as
    evidence for a decision, and citing an artifact is the opposite of the bug.
    So this reads code, not comments.
    """
    offenders = []
    for path in sorted((HERE / "tools").glob("*.py")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#")[0]
            if _TYPED_RUN.search(code):
                offenders.append(f"tools/{path.name}:{n}  {line.strip()[:70]}")
    assert not offenders, (
        "a run directory with the date typed into it. The run will overwrite "
        "whatever is already there and take that day's name:\n  "
        + "\n  ".join(offenders))


def test_the_corpus_keeps_its_own_date():
    """Narrowing, and it matters. The QUESTIONS were asked by the close on
    5 September; that date is a fact about the input and must not float to
    today. Only the day the desks ANSWERED them varies."""
    assert ask_the_desks.CORPUS.name == "CLOSE-QUESTIONS-2026-09-05.md"
    assert ask_the_desks.CORPUS.is_file(), "the close's questions moved"


def test_the_guard_can_actually_fail():
    """A pattern that matches nothing passes over anything."""
    assert _TYPED_RUN.search('BRIEFS = HERE / "runs" / "asked-2026-09-05"')
    assert _TYPED_RUN.search('p = Path("runs/2026-09-04")')
    assert not _TYPED_RUN.search('d = ROOT / "runs" / today.isoformat()')
    assert not _TYPED_RUN.search('f"asked-{RUN_DAY}"')


# ---------------------------------------------------------------------------
# THE SAME BUG, ONE DIRECTORY OVER. The briefs learned to write to the day they
# ran on; `serve_answers` went on writing to `runs/asked-<today>` whatever
# answers file it was handed. So re-serving the 5 September answers on the 7th
# put the result in a run it did not come from, and the evening's re-ask had to
# be lifted into its own directory by hand.
#
# A record of what the desks DID belongs beside the input that produced it. Any
# other rule makes the two drift, and neither one says which.


def test_a_served_run_lands_beside_the_answers_it_served(tmp_path, monkeypatch):
    answers = tmp_path / "somewhere-else" / "answers.json"
    answers.parent.mkdir()
    real = HERE / "runs" / "reasked-2026-09-07-evening" / "answers.json"
    answers.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")

    assert ask_the_desks.serve_answers(answers) == 0
    assert (answers.parent / "served.json").is_file()
    # AND NOT IN TODAY'S RUN, which is the half that was wrong.
    assert not (ask_the_desks.BRIEFS / "served.json").exists() or (
        ask_the_desks.BRIEFS / "served.json").read_text(encoding="utf-8") != (
        answers.parent / "served.json").read_text(encoding="utf-8")


def test_a_refusal_records_the_fact_and_the_position_that_asked(tmp_path):
    """THE CHAIN THE FIRM MADE A CONDITION. `engine.Refusal` sets `fact` and
    `by_position` together on the refusals that turn on a fact, because the firm
    approved a desk asking for a field -- *"that seems low stakes and required
    and i would approve it fairly easily"* -- only on the ask arriving with
    which position wanted it. This writer kept the reason and the prose and
    dropped both, so `tools/holes.py` printed a run's holes unable to name
    either, and the only route back was parsing a sentence."""
    import json

    answers = tmp_path / "answers.json"
    real = HERE / "runs" / "reasked-2026-09-07-evening" / "answers.json"
    answers.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    assert ask_the_desks.serve_answers(answers) == 0

    rows = json.loads((tmp_path / "served.json").read_text(encoding="utf-8"))
    named = [r for r in rows if r.get("fact")]
    assert named, "no refusal named a fact; the close run has five"
    for r in named:
        assert r["by_position"], (
            f"Q{r['q']} asks for {r['fact']!r} with no position behind it — "
            "a field request with no chain is what the condition forbids")
    assert all(not r["fact"] and not r["by_position"]
               for r in rows if r["served"]), "a served answer carried a chain"
