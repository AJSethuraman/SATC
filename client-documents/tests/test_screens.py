"""The vocabulary the preparer's screens are written in, held in place.

The design that arrived on 2 September 2026
(`satc-handoff/06-APP/00 Patterns and cuts.html`) named six things the app had
no visual language for. Three of them are rules rather than decoration, and a
rule with nothing enforcing it is a rule that holds until the next busy week:

  * **every number says what it counted** -- S2, on a screen. A bare count is
    the shape that let two blocking checks report `ok` while examining nothing;
  * **examined nothing never looks like passed** -- the same failure, one layer
    up, where a person reads it;
  * **a filename on a screen is the software talking about itself** -- S35, the
    rule the firm stated in their own words on 2 September and which
    `plainspoken.py` enforces over *literals*. The gate names a failing
    document by the file it rendered to, which is a runtime value and slips
    straight past a source scan.

Each test below was made to fail on purpose before it was kept. What each one
would notice is written in its own docstring, in the words of the thing that
would break.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import presend  # noqa: E402
import sending  # noqa: E402
import web  # noqa: E402

SOURCE = (ROOT / "web.py").read_text(encoding="utf-8")


def _page_strings() -> list[tuple[int, str]]:
    """Every literal inside a function that builds a page.

    The same seam `plainspoken` reads, and for the same reason: a string in a
    helper is not a string a person sees.
    """
    import ast

    out: list[tuple[int, str]] = []
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not re.search(r"_body$|^body_|_page$|^_checks_block$", node.name):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                out.append((sub.lineno, sub.value))
    return out


# ── every number says what it counted ─────────────────────────────────────

def test_no_screen_prints_a_bracket_s_plural():
    """`11 check(s)` is a machine talking to a person.

    It shipped on four screens -- the gate, both pack pages, the payments
    list -- and on the one where it mattered most it sat beside a number that
    is the whole point of the check. `web.tally` does the plural in one line.

    WOULD NOTICE: any `(s)` written back into a page builder.
    """
    bad = [(line, text) for line, text in _page_strings() if "(s)" in text]
    assert not bad, "\n".join(f"web.py:{n}  {t[:90]}" for n, t in bad)


def test_a_tally_cannot_be_written_without_the_noun():
    """The count and what it counted are one element, so there is no way to
    render the number on its own through this.

    WOULD NOTICE: `tally()` growing a path that emits a bare figure.
    """
    with pytest.raises(TypeError):
        web.tally(11)                                       # type: ignore[call-arg]
    assert web.tally(11, "check") == "<span class=tally><b>11</b> checks</span>"
    assert web.tally(1, "check") == "<span class=tally><b>1</b> check</span>"
    assert "1,249" in web.tally(1249, "word"), "a four-figure count is unreadable"


def test_nothing_to_count_is_said_in_words_and_never_as_a_zero():
    """"0 checks" and "we did not look" are the same words for two different
    worlds. S2 is the reason this project has the rule at all.

    WOULD NOTICE: the empty case falling through to the plural.
    """
    said = web.tally(0, "clause", nothing="no clause was cited")
    assert "0" not in said
    assert "no clause was cited" in said and "tally empty" in said


# ── examined nothing is not a pass ────────────────────────────────────────

def _result(*rows) -> presend.Result:
    """A gate result built the way `presend` builds one."""
    res = presend.Result()
    for what, counted in rows:
        res.add(what, counted)
    return res


def test_a_check_that_examined_nothing_does_not_wear_the_pass_mark():
    """`ok` and `NONE` were two shades of one grey. This is the pair that must
    never be confused: one looked and was satisfied, the other examined nothing
    and knows nothing.

    WOULD NOTICE: the `not got.examined` branch being dropped, which is exactly
    how `cited_clauses` reported `ok` on all 29 packs while reading zero
    citations.
    """
    html = web._checks_block(_result(
        ("every cited clause name is a real section",
         presend.Counted([], 0, "citation")),
        ("every referenced file is in the pack",
         presend.Counted([], 8, "referenced file")),
    ))
    # The whole row, from its own `<tr>` -- the mark is BEFORE the name.
    at = html.index("every cited clause")
    empty = html[html.rindex("<tr>", 0, at):html.index("</tr>", at)]
    assert "mk none" in empty and "nothing to look at" in empty, empty
    assert "mk pass" not in empty and ">fine<" not in empty, empty

    assert "8 referenced files read" in html


def test_a_failing_check_says_what_happens_to_you_not_what_it_did():
    """"Fail" describes the check. "Stops it" describes the consequence, which
    is the half the person holding the screen needs (S35).

    WOULD NOTICE: the blocking branch losing its mark, or the mark going back
    to naming the check's own state.
    """
    stopped = presend.Counted(
        [presend.Finding("plain", "x.html", "uses 'pursuant'")], 4, "word")
    html = web._checks_block(_result(("no banned legalese", stopped)))
    assert "mk stop" in html and "stops it" in html
    assert ">FAIL<" not in html


def test_the_gate_reports_how_many_checks_it_ran():
    """A page that says "checks ran" without a number is the denominator
    failure with better manners.

    WOULD NOTICE: the header line losing its count.
    """
    html = web._checks_block(_result(
        ("a", presend.Counted([], 1, "thing")),
        ("b", presend.Counted([], 2, "thing")),
    ))
    assert "<b>2</b> checks" in html


# ── a filename is not a document ──────────────────────────────────────────

FILE = "SAT-C Engagement Letter - Reyes - 2026.html"


def _refused_pack(tmp_path: Path) -> sending.Pack:
    """A pack the gate stopped, shaped the way `sending.build` returns one.

    `written` is filled in BEFORE the gate runs, which is why the refusal
    screen can name the document rather than the file -- and why this fixture
    has to carry it.
    """
    check = presend.Result()
    # `presend` tags a finding with its own short key -- "plain" -- and lists
    # the check under its sentence. Both, the way it really arrives.
    check.add("no banned legalese and no British spelling",
              presend.Counted(
                  [presend.Finding("plain", FILE,
                                   "uses 'pursuant', which the firm has "
                                   "ruled out of anything a client reads.")],
                  96, "word-in-document pair"))
    return sending.Pack(
        status="refused-gate", outdir=tmp_path / "pack",
        documents=["tax-letter"],
        written={"tax-letter": [tmp_path / FILE]},
        check=check)


def test_the_gate_names_the_document_not_the_file_it_rendered_to(tmp_path):
    """The firm, 2 September 2026, on a screen that named a config key:
    *"what software says stuff like that to its user?"*

    A filename is the same shape. It is on that screen precisely because
    something is wrong with the letter, and the file it names is the one thing
    on the page they cannot do anything about.

    `plainspoken.py` cannot see this: the filename is a runtime value, not a
    literal, so a source scan reads the f-string and finds nothing.

    WOULD NOTICE: `esc(f.document)` going back into the refusal list.
    """
    pack = _refused_pack(tmp_path)
    html = web.packed_body("2026-0001", {"ClientFullName": "Mr. and Mrs. Reyes"},
                           pack, False)
    assert FILE not in html, "a filename reached the gate screen"
    assert ".html" not in html
    assert "Engagement Letter" in html, "and the document is not named either"


def test_a_document_a_finding_cannot_be_placed_in_is_left_unnamed(tmp_path):
    """Dropping it is the failure mode to prefer: the row simply names no
    document, and the detail beside it still says what happened. Printing a
    filename nobody asked for is the one outcome that is worse than saying
    less.

    WOULD NOTICE: the fallback returning the raw value.
    """
    assert web._document_named("Some Letter - 2026.pdf", {}) == ""
    assert web._document_named("MANIFEST.json", {}) == ""
    # A sentinel is the software's word for a scope, and has a plain one.
    assert web._document_named("(all)") == "every document in the pack"


# ── the third colour means one thing ──────────────────────────────────────

def test_an_unwritten_sentence_on_the_record_is_not_dressed_as_an_error():
    """`[CONFIRM: ...]` is the software declining to write a sentence that is
    the firm's to write. It sat in the same ink as twenty-five settled facts,
    so the one row on the page that needs a person looked like the rest of it.

    WOULD NOTICE: the `[CONFIRM:` branch in `engagement_body` going away, or
    the panel losing the placeholder it exists to quote.
    """
    held = "[CONFIRM: what the firm does if an extension is refused]"
    html = web.engagement_body("2026-0001", {
        "ClientFullName": "Mr. and Mrs. Daniel Reyes",
        "PeriodLabel": "2026 tax year",
        "ExtensionRefusedNote": held,
        "TaxYear": "2026",
    }, [])
    assert "class=ask" in html, "nothing on the page says a person is needed"
    assert "class=said" in html
    # Quoted EXACTLY as it will print, because that is the string somebody has
    # to go and replace.
    assert held.replace("[", "[") in html.replace("&lt;", "<")
    assert "class=hardno" not in html, "a decision was dressed as a refusal"


def test_a_record_with_nothing_outstanding_shows_no_panel():
    """A panel that is always there is a panel nobody reads.

    WOULD NOTICE: the panel being rendered unconditionally.
    """
    html = web.engagement_body("2026-0001", {
        "ClientFullName": "Mr. and Mrs. Daniel Reyes", "TaxYear": "2026"}, [])
    assert "class=ask" not in html


def test_the_third_colour_is_used_for_one_meaning_and_no_other():
    """Navy is the firm acting, oxblood is a refusal, and burnt orange is the
    software waiting on the firm. A third colour that comes to mean two things
    is a third colour that means nothing.

    The focus ring is the one honest overlap and is named here rather than
    excepted silently: a focus ring means *the software is waiting on you
    here*, which is the same sentence.

    WOULD NOTICE: `--await` being reached for by any other rule -- an error
    style, a hover, a heading.
    """
    css = web.CSS
    allowed = {".mk.wait", ".ask", ".ask h2", ".ask .said", ".said",
               ":focus-visible"}
    used = set()
    for rule in re.findall(r"([^{}/]+)\{([^}]*)\}", css):
        selector, body = rule[0].strip(), rule[1]
        if "--await" not in body or selector.startswith(":root"):
            continue
        used |= {s.strip() for s in selector.split(",")}
    assert used <= allowed, f"the third colour has grown a second meaning: {used - allowed}"
    assert used, "the third colour is declared and used nowhere"


# ── one palette, and it lives in one place ────────────────────────────────

def test_no_screen_paints_a_colour_of_its_own():
    """The payments list carried `style='color:#2F6B4F'` -- a green declared
    nowhere, meaning "paid", which is what an outlined mark already means. A
    colour typed into markup is a colour no palette can move.

    WOULD NOTICE: any inline `color:` or `background` in a page builder.
    """
    bad = [(n, t) for n, t in _page_strings()
           if re.search(r"style\s*=\s*['\"]?[^'\"]*(color|background)", t)]
    assert not bad, "\n".join(f"web.py:{n}  {t[:90]}" for n, t in bad)


def test_every_mark_in_the_vocabulary_is_styled():
    """Six marks, one vocabulary, and a class with no rule behind it renders
    as unstyled text -- which is how a refusal ends up looking like a note.
    The same failure is already commented in `price_body`.

    WOULD NOTICE: a mark used on a screen that the stylesheet does not know.
    """
    used = {m for _, text in _page_strings()
            for m in re.findall(r"class='mk (\w+)'", text)}
    assert used, "no mark reaches any screen"
    for mark in used:
        assert f".mk.{mark}{{" in web.CSS, f".mk.{mark} is used and unstyled"


def test_the_keyboard_can_see_where_it_is():
    """Only text inputs had a focus style. A button or a link reached by Tab
    showed whatever the browser chose, which on a navy button is nearly
    nothing -- on a tool driven from a keyboard with a client in the chair.

    WOULD NOTICE: the ring being removed, or narrowed back to inputs.
    """
    assert ":focus-visible{outline:2px solid var(--await)" in web.CSS


def test_the_app_asks_for_no_font_it_cannot_have():
    """No webfont is loaded and none ever was, so every screen has always
    rendered in whatever the machine had. Naming a face that is not there is a
    design that works by accident.

    THE DOCUMENTS ARE A DIFFERENT SURFACE and keep IBM Plex: `presend` opens
    each one in a browser and fails it when the type is not the firm's.

    WOULD NOTICE: a font name creeping back into the app's stylesheet, or a
    `<link>` to a font host appearing in the page shell.
    """
    import re as _re
    rules = _re.sub(r"/\*.*?\*/", "", web.CSS, flags=_re.S)
    assert "IBM Plex" not in rules, "a face nothing loads is named in a rule"
    shell = web.page("x", "<p>y</p>")
    assert "fonts.googleapis" not in shell and "@import" not in rules


def test_the_thing_that_stopped_the_pack_is_called_what_the_table_calls_it(tmp_path):
    """One check, two names, on one page. The table said "no banned legalese
    and no British spelling"; the failure above it said **plain**, which is the
    key `presend` tags its findings with and is not a sentence anybody could
    match to the row below.

    S3 on a screen -- two halves of one report disagreeing about what a thing
    is called, on the morning a pack is blocked.

    WOULD NOTICE: the refusal list going back to printing `f.check`.
    """
    pack = _refused_pack(tmp_path)
    html = web.packed_body("2026-0001", {"ClientFullName": "Reyes"}, pack, False)
    top = html[:html.index("Before sending")]
    assert "no banned legalese and no British spelling" in top, top
    assert "<b>plain</b>" not in top


def test_a_finding_from_a_check_that_reported_no_count_keeps_its_own_name():
    """The map is derived, so a finding the counts do not cover has no entry.
    Falling back to the finding's own key is right -- inventing a sentence for
    it would be worse -- and this is here so the fallback is deliberate rather
    than discovered.
    """
    assert web._check_labels(presend.Result()) == {}
    orphan = presend.Result()
    orphan.findings.append(presend.Finding("renders", "(all)", "boom"))
    assert web._check_labels(orphan) == {}


def test_a_tally_is_never_escaped_on_its_way_to_the_page():
    """It shipped, and only a photograph found it.

    `waiting_body` built `waited = tally(days, "day")` and then wrote
    `{esc(waited)}` into the cell, so the signature chase column printed
    `<span class=tally><b>0</b> days</span>` as WORDS -- the markup, on screen,
    in front of a preparer. Every test in the suite read the page as a string
    and every one of them was satisfied: the tokens were all there. S16, from
    the inside.

    So the rule is checked where it can be checked -- in the source, on the
    join that broke: a name bound to `tally()` must not reach `esc()`.

    WOULD NOTICE: `esc()` going back around anything a tally produced.
    """
    import ast

    tree = ast.parse(SOURCE)
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        made: set[str] = set()
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Assign):
                continue
            calls = [c for c in ast.walk(sub.value)
                     if isinstance(c, ast.Call)
                     and getattr(c.func, "id", "") == "tally"]
            if calls:
                made |= {tgt.id for tgt in sub.targets
                         if isinstance(tgt, ast.Name)}
        if not made:
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call)
                    and getattr(sub.func, "id", "") == "esc"
                    and sub.args
                    and isinstance(sub.args[0], ast.Name)
                    and sub.args[0].id in made):
                bad.append(f"web.py:{sub.lineno}  {node.name}() escapes "
                           f"{sub.args[0].id!r}, which is a tally, so the page "
                           f"prints its markup as words")
    assert not bad, "\n".join(bad)


def test_the_chase_column_shows_a_number_and_not_a_span():
    """The other half of the same guard, from the page's side rather than the
    source's -- because a rule about `esc` cannot see an f-string that inlines
    the call.
    """
    class Waiting:
        ref, client, overdue, examined = "2026-0001", "Reyes", False, 6
        missing = ["Form 8879 — Spouse"]

        def waiting_days(self):
            return 11

    html = web.waiting_body([Waiting()])
    assert "&lt;span" not in html, "a tally reached the page escaped"
    assert "<b>11</b> days" in html
