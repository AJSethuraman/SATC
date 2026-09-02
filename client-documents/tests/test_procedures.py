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
import pathlib
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


# ── every template is an appendix to its process ──────────────────────────

def test_every_template_belongs_to_a_procedure_or_is_named_as_not_belonging():
    """The firm's general rule, 2 September 2026: "each relevant template is
    included as an appendix item to the process it belongs to".

    Checked BOTH ways, because one direction passes trivially: a document set
    with no procedures has no orphans. So this asserts what the audit examined
    as well as what it found (S2)."""
    audit = procedures.template_audit()
    assert audit["missing"] == [], (
        "a procedure names a document with no template behind it: "
        + "; ".join(audit["missing"]))
    assert audit["templates_examined"] >= 12, (
        "the audit read fewer templates than this set has, so 'no orphans' "
        "means nothing")
    assert audit["documents_examined"] >= 10

    # An orphan is REPORTED, not failed: a finished letter with no process
    # behind it is work waiting on a decision. But it must reach the page.
    doc = procedures.render()
    for orphan in audit["orphans"]:
        assert orphan in doc, (
            f"{orphan} belongs to no procedure and the document does not say so")


def test_each_procedure_that_produces_a_document_carries_it_as_an_appendix():
    doc = procedures.render()
    for procedure, docs in procedures.templates_by_procedure().items():
        if not docs or procedure.startswith("Lifecycle"):
            continue
        for doc_id in docs:
            entry = procedures.document_files()[doc_id]
            assert entry[0] in doc, (
                f"{procedure} produces {entry[1]} and the procedures never "
                f"name its template")


def test_the_reading_copy_carries_the_document_itself_not_a_description():
    """The firm, asked what "template" meant: "by template i do not mean an
    example, i want it printed in such a way that it is the actual format we'd
    give a client but it has the <<placeholder>> values."

    So each appendix embeds the template's own client-facing block, with its
    merge tokens left unfilled. Two things this pins: the document is there,
    and the placeholders are still visible in it."""
    import procedures_html
    html = procedures_html.render()
    # EVERY bullet that names a template, not "at least one". The guard used to
    # fire only at zero, so when the conditional Records Release bullet stopped
    # matching, eight of nine embedded and the ninth fell through as plain
    # text — silently, and it is the one the appendix rule most needed to show.
    bullets = procedures_html._appendix_bullets(
        "\n".join(procedures_html.blocks(
            pathlib.Path(procedures_html.SOURCE).read_text(encoding="utf-8"))[1]))
    embedded = html.count('class="tpl"')
    assert embedded == bullets, (
        f"{bullets} appendix bullets name a template and {embedded} embedded")
    assert bullets >= 10, "the appendices name fewer templates than this set has"
    assert "&lt;&lt;ClientFullName&gt;&gt;" in html, (
        "the placeholders were filled in or stripped — this is an example now, "
        "not a template")
    # The authoring notes are NOT the document. Embedding the whole file put
    # the merge-field table into the firm's operating procedures.
    assert "THE FEE IS NOT A FIELD" not in html.upper()


def test_a_template_with_no_client_document_is_refused_not_embedded():
    """Check the checker. A template whose client-facing block cannot be found
    must stop the build rather than have its whole file — authoring notes and
    all — inlined into the procedures."""
    import procedures_html, pytest as _pytest
    # A real one would be caught the same way; none exists, so this builds the
    # shape on purpose rather than asserting against a file that happens to be
    # fine today. `_SKELETON.html` DOES carry `.letter` and is embedded
    # correctly — asserting it was refused would have passed for the wrong
    # reason and proved nothing.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "Broken.html").write_text(
            "<html><body><div class='wrapper'>no document block here"
            "</div></body></html>", encoding="utf-8")
        real = procedures_html.TEMPLATE_DIR
        procedures_html.TEMPLATE_DIR = d
        try:
            with _pytest.raises(RuntimeError) as exc:
                procedures_html.template_body("Broken.html")
            assert "neither" in str(exc.value)
            with _pytest.raises(RuntimeError) as missing:
                procedures_html.template_body("NotThere.html")
            assert "not in" in str(missing.value)
        finally:
            procedures_html.TEMPLATE_DIR = real


def test_the_scoped_stylesheet_is_balanced():
    """The first scoper split on '}' and mangled every @media block, coming out
    one brace short — so a browser dropped every rule after the break and the
    appendix silently lost its containment. Found by reading `overflow-x:
    visible` off an element that had been told to scroll."""
    import procedures_html
    css = procedures_html.template_css()
    assert css.count("{") == css.count("}")
    assert ".tpl{" in css, "the scope never reached the frame itself"


def test_every_command_line_the_document_prints_would_actually_run():
    """THE CHECK THAT WAS MISSING, and the document's own preamble is why it
    was needed. `_require` verifies a command NAME exists, and the preamble
    then promises the document "cannot name a command that does not exist" —
    true of names, and of nothing else. Every flag, argument and value in every
    code block was typed by hand into `render()` and checked by nothing.

    So `python cli.py from-lead --lead lead.json` sat on the front page from
    the day it was written: `lead` is a positional and argparse refuses the
    flag. The first command in the first procedure, under a guarantee that it
    could not be wrong.

    This parses every line the document prints with the CLI's real parser."""
    bad = procedures.unrunnable()
    assert not bad, "\n\n".join(bad)
    # S2: the denominator. "Nothing would fail" across zero lines is not news.
    assert len(procedures.invocations(procedures.render())) >= 15


def test_the_invocation_check_would_notice_a_wrong_flag():
    """Check the checker, on the exact shape that shipped."""
    ok = procedures.unrunnable("python cli.py from-lead lead.json --out r.json")
    assert ok == []
    caught = procedures.unrunnable("python cli.py from-lead --lead lead.json")
    assert len(caught) == 1 and "--lead" in caught[0]
    # A command that does not exist at all, and a choice that is not a choice.
    assert procedures.unrunnable("python cli.py invent --thing 1")
    assert procedures.unrunnable("python cli.py event --kind nonsense "
                                 "--engagement 2026-0001")


def test_the_carry_count_is_asked_not_remembered():
    """It read "Nine carry", which was true of one individual sample. Five of
    the carried answers are entity-only, so a preparer rolling a partnership
    forward and counting nine would conclude six answers had been lost."""
    import interview
    text = procedures.render()
    assert f"Up to {len(interview.CARRIES)} carry" in text
    assert "Nine carry" not in text


def test_the_document_does_not_still_say_the_invoice_is_unknowable():
    """`signing._unsettled` blocks on an unsettled invoice and has since
    payments were wired. This paragraph said the opposite for as long, because
    it was transcribed from that function's own stale docstring."""
    text = procedures.render()
    assert "writes the bill and stops" not in text
    assert "BLOCKER here, not a silence" in text
    import signing, inspect
    assert "Nothing in this repository records" not in inspect.getsource(signing), (
        "the docstring this was transcribed from is still wrong, so it will "
        "be transcribed again")


def test_every_document_producing_procedure_is_a_real_section():
    """Four of the eleven client documents are produced by `event`, and the
    index listed them against procedure names that existed nowhere in the
    document. An index entry pointing at no section is worse than none."""
    text = procedures.render()
    headings = {line.lstrip("# ").strip().lower()
                for line in text.splitlines() if line.startswith("#")}
    for procedure in procedures.templates_by_procedure():
        assert any(procedure.lower() in h for h in headings), (
            f"{procedure!r} is in the index and reaches no heading in the "
            f"document, so a reader following the index arrives nowhere")


def test_sign_does_not_claim_to_produce_the_delivery_letter():
    """`cmd_sign` renders nothing. The delivery letter comes from
    `event --kind delivery`. This was a hardcoded tuple inside the function
    whose own comment says DERIVED, NEVER TYPED."""
    by_procedure = procedures.templates_by_procedure()
    assert "Getting it signed" not in by_procedure
    assert by_procedure["When the return is ready to go back"] == ["delivery-letter"]
