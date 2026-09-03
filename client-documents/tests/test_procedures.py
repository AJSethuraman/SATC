"""The operating procedures, generated from the software that performs them.

The firm asked for these — *"i will eventually want operating procedures and
stuff so it's integral everything works and can be demonstrated"* — and the
whole design decision is that they are GENERATED. A procedure written by hand
beside software is wrong within a month, and nobody finds out until somebody
follows it.

So the claims under test are not about the prose. They are that the document
**cannot** say something untrue: it cannot name a command that does not exist,
list a document a return type does not get, or claim a check the gate does not
perform. And that the committed copy is what the software generates today —
which is the one assertion that stops all of the above from rotting.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import closeout  # noqa: E402
import packaging  # noqa: E402
import procedures  # noqa: E402


def test_the_committed_copy_is_what_the_software_generates_today():
    """THE ASSERTION THAT KEEPS THE REST TRUE. Everything else here proves the
    generator is honest; this proves the file on disk came from it."""
    assert procedures.is_current(), (
        f"{procedures.OUT.name} has drifted from the software. Regenerate it: "
        f"cd client-documents && python cli.py procedures")


def test_every_command_it_names_exists():
    """A document that tells someone to run a command that does not exist is
    worse than no document."""
    have = set(procedures.commands())
    assert have, "no subcommands were found at all — the parser scan is broken"

    text = procedures.render()
    named = set()
    for line in text.splitlines():
        if line.startswith("python cli.py "):
            named.add(line.split()[2])
    assert named, "the procedures name no commands, which cannot be right"
    assert named <= have, sorted(named - have)


def test_it_cannot_name_a_command_that_was_renamed(monkeypatch):
    """`_require` is the guard. Proved by taking a command away."""
    monkeypatch.setattr(procedures, "commands", lambda: ["package"])
    with pytest.raises(RuntimeError, match="no longer offers"):
        procedures.render()


def test_the_pack_table_comes_from_packaging():
    text = procedures.render()
    for key, label, form in procedures.RETURN_TYPES:
        docs = packaging.documents_for({"_return_type": key})
        row = f"| {label} ({form}) | " + ", ".join(f"`{d}`" for d in docs)
        assert row in text, f"{key}: {row}"


def test_a_new_document_in_a_pack_shows_up_without_anyone_writing_it(monkeypatch):
    """The test that proves this is generated rather than transcribed."""
    original = packaging.documents_for

    def one_more(record, **kw):
        return original(record, **kw) + ["records-release"]

    monkeypatch.setattr(packaging, "documents_for", one_more)
    assert "`records-release` |" in procedures.render()


def test_the_gate_checks_come_from_the_gate():
    text = procedures.render()
    for check in procedures.gate_checks():
        assert check in text, check


# THREE TESTS WERE DELETED FROM HERE, under S30: a check for something that
# cannot happen is worse than no check.
#
#   test_the_gate_list_is_not_empty            — `render()` calls `_require`
#     and raises on an empty parse, and `test_the_gate_checks_come_from_the_gate`
#     already compares the list to the gate's own.
#   test_a_runtime_count_does_not_reach_the_procedure — a count cannot reach the
#     page: `presend.Result.add` keeps the check's literal name in `checked` and
#     the count in a separate `Counted` (`presend.py:118`), and `gate_checks`
#     returns `result.checked` verbatim. The reason is already written at
#     `procedures.py:78`, which is where a reader meets it.
#   test_no_advisory_is_listed_among_the_gate_checks — the two lists are built in
#     different modules in different shapes; `advisory_checks` synthesises
#     `f"{key} ({tenet}) — {what}"`, which no `presend.gate` literal can equal.
#
# None of them protected anything. All three cost maintenance and taught a
# reader that the suite is full of things that might happen.


def test_the_advisories_are_listed_and_named_as_advisory():
    """Separately from the blocking checks, and said out loud to be advisory.

    A procedure that ran the two lists together would teach a preparer that a
    note is a failure, and the next thing to happen is that the blocking eight
    get ignored too.
    """
    import notes
    text = procedures.render()
    listed = procedures.advisory_checks()
    assert len(listed) == len(notes.ADVISORIES) == 10
    for line in listed:
        assert line in text, line
    assert "never block and never change the exit code" in text


def test_the_close_out_questions_come_from_the_registry():
    text = procedures.render()
    for key, label, form in procedures.RETURN_TYPES:
        asked = closeout.questions_for(key)
        assert f"**{label} ({form})** — {len(asked)} questions" in text
        for q in asked:
            assert f"`{q['id']}`" in text


def test_a_skipped_check_is_named_as_skipped():
    """A procedure that lists only what ran reads like a procedure where
    everything ran."""
    assert "only when the caller supplies the rendered text" in procedures.render()


def test_judgement_is_marked_and_not_filled_in():
    """Whether to override a hard-no, and what a divergence means, belong to a
    person. The document says where those are rather than deciding them."""
    text = procedures.render()
    assert text.count("**Judgement, not procedure:**") >= 2


def test_the_check_flag_fails_on_a_drifted_copy(tmp_path, monkeypatch, capsys):
    drifted = tmp_path / "OPERATING-PROCEDURES.md"
    drifted.write_text(procedures.render() + "\nsomebody edited this\n",
                       encoding="utf-8")
    monkeypatch.setattr(procedures, "OUT", drifted)

    assert cli.main(["procedures", "--check"]) == 1
    assert "out of date" in capsys.readouterr().out


def test_the_check_flag_passes_on_a_current_copy(tmp_path, monkeypatch):
    current = tmp_path / "OPERATING-PROCEDURES.md"
    current.write_text(procedures.render(), encoding="utf-8")
    monkeypatch.setattr(procedures, "OUT", current)
    assert cli.main(["procedures", "--check"]) == 0


def test_generating_is_idempotent(tmp_path, monkeypatch):
    out = tmp_path / "OPERATING-PROCEDURES.md"
    monkeypatch.setattr(procedures, "OUT", out)
    procedures.write(out)
    once = out.read_text(encoding="utf-8")
    procedures.write(out)
    assert out.read_text(encoding="utf-8") == once


# ── the reading copy ──────────────────────────────────────────────────────

def test_the_reading_copy_loses_nothing():
    """The markdown is the source of truth; the rendering may not quietly
    shed a step of it."""
    import procedures_html
    md = procedures.OUT.read_text(encoding="utf-8")
    doc = procedures_html.render(procedures.OUT)
    assert procedures_html.dropped(md, doc) == {}


def test_the_reading_copy_needs_nothing_beside_it():
    """A file that only renders while its siblings happen to sit next to it
    is the bug this exists to avoid. `render` refuses rather than writing one,
    so this asserts the refusal is reachable as well as the happy path."""
    import procedures_html
    doc = procedures_html.render(procedures.OUT)
    assert procedures_html.external_references(doc) == []
    broken = doc.replace("</head>", "<link rel=stylesheet href=\"next-door.css\">"
                                    "</head>")
    assert procedures_html.external_references(broken) == ["next-door.css"]


def test_a_wrapped_list_item_stays_one_item(tmp_path):
    """THE DEFECT THIS TEST EXISTS FOR. The generator wraps at about seventy
    columns, so half its bullets continue on an indented line. Reading only
    the first line split them: "the hard-no list in" became a bullet and
    "firm-settings.yaml, refused before anything is composed" a loose
    paragraph under it. Every word survived, in the wrong shape."""
    import procedures_html
    src = tmp_path / "p.md"
    src.write_text("# T\n\n## 1 · S\n\n- **work we do not take** — the list in\n"
                   "  `firm-settings.yaml`, refused before anything is made;\n"
                   "- a decision that is not yes — nothing is created;\n",
                   encoding="utf-8")
    _title, body = procedures_html.blocks(src.read_text(encoding="utf-8"))
    html = "".join(body)
    assert html.count("<li>") == 2
    assert "firm-settings.yaml" in html.split("</li>")[0]
    assert "<p>" not in html          # nothing fell out of the list


def test_the_documents_own_angle_brackets_survive():
    """`<REF>` appears eleven times. Marking up before escaping turns it into
    a tag and it vanishes from the page."""
    import procedures_html
    _t, body = procedures_html.blocks("# T\n\nRun it with <REF> in place.\n")
    assert "&lt;REF&gt;" in "".join(body)
