"""The prose reader renders, and it renders its denominators.

FOUR DEFECTS FOUND BY WALKING THE ENGAGEMENT BROWSER, 5 September 2026.

E1 -- THE CRASH. Ticking "Also read the prose and tell me what it notices" and
pressing Build the pack returned **HTTP 500**. `web.packed_body` iterated
`pack.readings` reading `f.document`, `f.check` and `f.detail` -- the fields of
`presend.Finding`. `pack.readings` holds `notes.Checked`, which has `key`,
`findings`, `examined`, `unit` and `scope`:

    AttributeError: 'Checked' object has no attribute 'document'

Two types, and the wrong one assumed. The documents had already rendered -- about
forty seconds of work, every one opened in a browser to prove it was readable --
and the whole lot was thrown away by the code that DISPLAYS the result. The
option's own label promises "nothing here can stop a pack". It stopped the pack.

**And the obvious fix would have been wrong.** Iterating `c.findings` and
printing those alone renders a tidy list from an advisory that read zero
sentences -- which is the sentence this project exists to stop producing. A
`Checked` carries what was LOOKED AT, so the screen shows it, and one that
examined nothing says "skipped" rather than passing quietly.

E6 -- THE UNCLOSED SCRIPT TAG. `web.py` emitted `<\\/script>` -- an escaped
slash, which is how you close a script tag from inside a JavaScript string. This
was not inside one; it was the tag itself, in HTML being written directly. The
browser never saw a closing tag, swallowed `</main></body></html>` as script
source, and the script failed to parse -- so the "Building - about a minute"
label it exists to show has never once appeared. It also raised a SyntaxWarning
on every single start, because `\\/` is not a Python escape either.

E5 -- A CONTROL THAT COULD NOT SUCCEED. "Put the invoice in too" was offered
unconditionally. On an engagement with no bill it failed the entire atomic build
-- no letter, no estimate, no onboarding letter -- on an optional extra, and the
resulting page had no way back.

E3 -- THE RAW FIELD NAME. Pressing Next with nothing chosen said
`federal_form is required`, the internal id, while the question it belongs to --
"Which federal return?" -- sat directly above it.
"""
from __future__ import annotations

import pathlib
import re

import pytest

import interview
import notes
import presend
import web
from presend import Finding

HERE = pathlib.Path(__file__).resolve().parent.parent


class _Pack:
    """The parts of `sending.Packed` that `packed_body` reads."""

    def __init__(self, readings):
        self.status = "written"
        self.outdir = pathlib.Path(".")
        self.documents = ["tax-letter"]
        self.written = {}
        self.refused = []
        self.check = presend.Result()
        self.readings = readings
        self.manifest = None
        self.manifest_json = ""
        self.stale = ""
        self.override = ""
        self.detail = ""
        self.ok = True


def _render(readings):
    return web.packed_body("2026-0001", {"ClientFullName": "A Client"},
                           _Pack(readings), False)


# ── E1 ────────────────────────────────────────────────────────────────────────

def test_a_reading_renders_instead_of_raising():
    """THE CRASH. `Checked` has no `.document`, and the renderer asked for one."""
    checked = notes.Checked(key="A1", findings=[], examined=91, unit="sentence",
                            scope="the pack")
    html = _render([checked])                      # raised AttributeError before
    assert "What the prose reads like" in html


def test_a_reading_says_what_it_looked_at():
    """The denominator is the whole reason `Checked` exists (S2).

    Rendering only the findings would turn an advisory that read nothing into a
    clean-looking line, which is precisely the failure this project is built to
    stop.
    """
    checked = notes.Checked(key="A1", findings=[], examined=91, unit="sentence",
                            scope="the pack")
    html = _render([checked])
    assert "91 sentences" in html
    assert "the pack" in html


def test_an_advisory_that_read_nothing_says_skipped_not_clean():
    checked = notes.Checked(key="A1", findings=[], examined=0, unit="sentence")
    html = _render([checked])
    assert "skipped" in html
    assert "nothing is known" in html
    assert "nothing to flag" not in html, "a check that read nothing reads as a pass"


def test_the_findings_underneath_are_still_shown():
    """Fixing the crash must not lose what the advisory actually found."""
    finding = Finding(check="A3", document="Engagement Letter.html",
                      detail="34 words: “Where the law is unclear…”", blocking=False)
    checked = notes.Checked(key="A3", findings=[finding], examined=91,
                            unit="sentence", scope="the pack")
    html = _render([checked])
    assert "1 to look at" in html
    assert "34 words" in html
    assert "Engagement Letter.html" in html


# ── E6 ────────────────────────────────────────────────────────────────────────

def test_the_script_tag_in_the_page_actually_closes():
    """An escaped slash is the JavaScript-string trick, not an HTML closing tag.

    ASSERTED ON THE RENDERED PAGE, NOT ON THE SOURCE. The first draft of this
    test read `web.py` and asserted the sequence was absent -- and failed,
    because the fix's own comment quotes the bad sequence in order to explain
    it. A source-level check here polices the prose about the bug rather than
    the bug. What matters is what the browser receives.
    """
    html = web.package_body("2026-0001", {"ClientFullName": "A Client"},
                            ["tax-letter"], has_bill=True)
    assert "<" + chr(92) + "/script>" not in html, (
        "the closing tag is escaped, so the script element never closes and the "
        "markup after it is swallowed as script source")
    if "<script>" in html:
        assert "</script>" in html


def test_web_py_imports_without_a_syntax_warning():
    """It printed one on every start, and a warning nobody can fix is a warning
    everybody learns to scroll past."""
    import py_compile
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        py_compile.compile(str(HERE / "web.py"), doraise=True, cfile=None)
    bad = [w for w in caught if issubclass(w.category, SyntaxWarning)]
    assert not bad, f"web.py still warns: {[str(w.message) for w in bad]}"


# ── E5 ────────────────────────────────────────────────────────────────────────

def _package_screen(has_bill):
    return web.package_body("2026-0001", {"ClientFullName": "A Client"},
                            ["tax-letter"], has_bill=has_bill)


def test_the_invoice_box_is_dead_when_there_is_no_bill():
    html = _package_screen(has_bill=False)
    assert "disabled" in html
    assert "no bill has been raised" in html
    assert "name=invoice" not in html, "the box can still be ticked"


def test_the_invoice_box_works_when_there_is_one():
    """The control. Disabling it always would remove a real feature."""
    html = _package_screen(has_bill=True)
    assert "name=invoice" in html
    assert "no bill has been raised" not in html


# ── E3 ────────────────────────────────────────────────────────────────────────

def test_a_required_question_is_named_by_its_question():
    """"federal_form is required" is the field id, not the thing on screen."""
    session = interview.Interview()
    with pytest.raises(interview.InterviewError) as exc:
        session.answer("federal_form", "")
    message = str(exc.value)
    assert "Which federal return?" in message, "it still names only the field id"
    assert "federal_form" in message, "the id is gone, and `--set` takes it"
