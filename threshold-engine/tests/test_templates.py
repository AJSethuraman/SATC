"""templates: each template is written, filled with synthetic values, passes
check and builds through workbook.build; every refusal is pinned by its exact
message; a third column (the way account-level data would travel) is refused
and the message says why. Every value here is synthetic: a sine wave, not a
bank's number."""
import math

import pytest

from threshold_engine.scale import scale
from threshold_engine.templates import (
    MIN_QUARTERS, SCALE_REFUSAL, TEMPLATES, check, checklist_path, write_template)
from threshold_engine.workbook import build

ENDS = ("03-31", "06-30", "09-30", "12-31")
SPEC = {   # spec B's table, key -> (title, unit, direction)
    "wapd": ("Weighted average probability of default", "%", "higher_is_worse"),
    "refreshed-score": ("Refreshed credit score (portfolio average)", "score", "lower_is_worse"),
    "epd": ("Early payment default rate", "%", "higher_is_worse"),
    "student-loans": ("Other consumer: student loans only (Laurel Road)", "%", "higher_is_worse"),
    "other-consumer-ex-student": ("Other consumer without student loans", "%", "higher_is_worse"),
    "card-rewards": ("Credit card: rewards cards only", "%", "higher_is_worse"),
    "card-non-rewards": ("Credit card: non-rewards cards only", "%", "higher_is_worse"),
}
HISTORY = "%d quarter(s) of history; at least 9 are needed. scale.py refuses with '%s', and nine " \
          "quarters hold two four-quarter changes end to end"


def dates(n, first_year=2015):
    return ["%d-%s" % (first_year + i // 4, ENDS[i % 4]) for i in range(n)]


def synthetic(unit, n):
    """A made-up cycle: a rate between about 0.5 and 3.5, or a score near 700."""
    if unit == "%":
        return [round(2.0 + 1.2 * math.sin(i / 3.0) + 0.3 * math.sin(i), 4) for i in range(n)]
    return [round(700 - 25 * math.sin(i / 3.0) - 5 * math.sin(i), 2) for i in range(n)]


def answers(key):
    """A synthetic answer for every note the template asks."""
    out = {k: "synthetic test answer for %s" % k for k, _ in TEMPLATES[key].notes}
    if TEMPLATES[key].unit == "score":
        out["scale"] = "300-850"
    return out


def filled(tmp_path, key, n=24, rows=None, notes=None, name="f.csv"):
    """Write the template, answer its notes, add the rows (date, value)."""
    out = tmp_path / ("t-" + name)
    write_template(key, out)
    ans = answers(key) if notes is None else notes
    lines = []
    for line in out.read_text(encoding="utf-8").splitlines():
        k = line[1:].split(":", 1)[0].strip()
        if line.startswith("#") and "[STATE:" in line:
            if k in ans:
                lines.append("# %s: %s" % (k, ans[k]))
        else:
            lines.append(line)
    if rows is None:
        rows = list(zip(dates(n), synthetic(TEMPLATES[key].unit, n)))
    lines += ["%s,%s" % r for r in rows]
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def raw(tmp_path, key, body, notes=None, name="r.csv"):
    """The template line write_template puts first, answered notes, then
    ``body`` exactly as given."""
    ans = answers(key) if notes is None else notes
    p = tmp_path / name
    p.write_text("# template: %s (%s)\n" % (key, TEMPLATES[key].title) + "".join("# %s: %s\n" % kv for kv in ans.items()) + body, encoding="utf-8")
    return p


def rows_text(n=12, unit="%"):
    return "date,value\n" + "".join("%s,%s\n" % r for r in zip(dates(n), synthetic(unit, n)))


# ---- the table and the written template ----

def test_the_templates_are_the_spec_table():
    assert {k: (t.title, t.unit, t.direction) for k, t in TEMPLATES.items()} == SPEC


@pytest.mark.parametrize("key", list(SPEC))
def test_every_template_asks_the_common_notes(key):
    keys = [k for k, _ in TEMPLATES[key].notes]
    for k in ("measure", "as-of", "basis", "source", "prepared-by", "prepared-on"):
        assert k in keys
    if TEMPLATES[key].unit == "%":
        assert "numerator" in keys and "denominator" in keys and "scale" not in keys
    else:
        assert "scale" in keys and "numerator" not in keys
    assert len(keys) == len(set(keys))


def test_epd_asks_the_window():
    assert "window" in dict(TEMPLATES["epd"].notes)


@pytest.mark.parametrize("key", list(SPEC))
def test_write_holds_questions_header_and_no_rows(tmp_path, key):
    csv_path, md = write_template(key, tmp_path / "x.csv")
    assert md == tmp_path / "x.checklist.md" == checklist_path(csv_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[-1] == "date,value"
    for k, q in TEMPLATES[key].notes:
        assert "# %s: [STATE: %s]" % (k, q) in lines
    text = md.read_text(encoding="utf-8")
    for k, _ in TEMPLATES[key].notes:
        assert "`%s`" % k in text
    assert "template check %s x.csv" % key in text
    # An unanswered template is refused: every placeholder, and no history.
    problems = check(key, csv_path)
    for k, q in TEMPLATES[key].notes:
        assert "note '%s' still holds its placeholder; answer it: %s" % (k, q) in problems
    assert HISTORY % (0, SCALE_REFUSAL) in problems


def test_write_refuses_to_write_over_a_file(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("# measure: answered\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        write_template("wapd", p)
    assert str(e.value) == ("%s already exists; it is not written over, so a filled template cannot be "
                            "lost. Choose another name or move it." % p)
    assert p.read_text(encoding="utf-8") == "# measure: answered\n"
    assert not (tmp_path / "x.checklist.md").exists()


def test_write_refuses_a_name_that_is_not_csv(tmp_path):
    with pytest.raises(ValueError) as e:
        write_template("wapd", tmp_path / "x.xlsx")
    assert str(e.value) == "the template is a CSV: name it OUT.csv, not x.xlsx"


def test_an_unknown_key_is_refused(tmp_path):
    keys = ", ".join(SPEC)
    for call in (lambda: write_template("nco", tmp_path / "x.csv"), lambda: check("nco", tmp_path / "x.csv")):
        with pytest.raises(ValueError) as e:
            call()
        assert str(e.value) == "no template 'nco'; the templates are: %s" % keys


# ---- acceptance: filled, checked, built ----

@pytest.mark.parametrize("key", list(SPEC))
def test_filled_template_passes_and_builds(tmp_path, key):
    p = filled(tmp_path, key)
    assert check(key, p) == []
    t = TEMPLATES[key]
    info = build(tmp_path / "w.xlsx", [(t.title, p)], t.title, t.unit, t.direction, "quarterly", 1,
                 t.unit == "%", 0.5, 1.0, 2.5, "worse", (10,), (50, 75, 90, 95), 4, 12)
    assert info["quarters"] == 24 and (tmp_path / "w.xlsx").exists()


def test_every_template_title_can_be_a_product_label():
    """A bank will reach for the title as the workbook label; one holding a
    comma would split in Excel's product dropdown (the Codex review, 12 Oct
    2026, made the build refuse it, and this title was the first caught)."""
    from threshold_engine.series import label_ok
    assert all(label_ok(t.title) for t in TEMPLATES.values())


def test_exactly_nine_quarters_passes_and_builds(tmp_path):
    p = filled(tmp_path, "epd", n=MIN_QUARTERS)
    assert MIN_QUARTERS == 9 and check("epd", p) == []
    info = build(tmp_path / "w.xlsx", [("EPD", p)], "EPD", "%", "higher_is_worse", "quarterly", 1,
                 True, 0.5, 1.0, 2.5, "worse", (10,), (50, 75, 90, 95), 1, 8)
    assert info["quarters"] == 9


# ---- one test per refusal, each with its exact message ----

def test_the_minimum_history_cites_scale_pys_own_refusal():
    # The quoted text must be what scale.py actually says, not a paraphrase.
    assert scale([1.0, 2.0, 3.0, 4.0, 5.0], "higher_is_worse", 0.5, 1.0, 2.5, True)["refused"] \
        == SCALE_REFUSAL


def test_eight_quarters_is_refused(tmp_path):
    p = filled(tmp_path, "epd", n=8)
    assert check("epd", p) == [HISTORY % (8, SCALE_REFUSAL)]


def test_missing_note(tmp_path):
    ans = answers("epd")
    del ans["window"]
    p = raw(tmp_path, "epd", rows_text(), notes=ans)
    assert check("epd", p) == ["missing note: # window: the months on book that define early"]


def test_placeholder_left_in(tmp_path):
    ans = dict(answers("wapd"), source="[STATE: the internal system or report, by name]")
    p = raw(tmp_path, "wapd", rows_text(), notes=ans)
    assert check("wapd", p) == [
        "note 'source' still holds its placeholder; answer it: the internal system or report, by name"]


def test_empty_note(tmp_path):
    ans = dict(answers("wapd"), measure="")
    p = raw(tmp_path, "wapd", rows_text(), notes=ans)
    assert check("wapd", p) == ["note 'measure' is empty; answer it: what is measured, in the bank's words"]


def test_note_given_twice(tmp_path):
    p = raw(tmp_path, "wapd", "# basis: quarter-end\n" + rows_text())
    assert check("wapd", p) == ["line 11: note 'basis' is given twice"]


def test_scale_that_does_not_read(tmp_path):
    ans = dict(answers("refreshed-score"), scale="850-300")
    p = raw(tmp_path, "refreshed-score", rows_text(unit="score"), notes=ans)
    assert check("refreshed-score", p) == [
        "note 'scale' must give the lowest and highest possible scores, low first, e.g. 300-850; "
        "found '850-300'"]


def test_score_outside_the_stated_scale(tmp_path):
    rows = list(zip(dates(12), synthetic("score", 12)))
    rows[3] = (rows[3][0], 851)
    p = raw(tmp_path, "refreshed-score", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("refreshed-score", p) == ["line 14: 851 is outside the stated scale 300-850"]


def test_percent_outside_0_to_100(tmp_path):
    rows = list(zip(dates(12), synthetic("%", 12)))
    rows[0] = (rows[0][0], "-0.5")
    rows[1] = (rows[1][0], "100.01")
    p = raw(tmp_path, "card-rewards", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("card-rewards", p) == ["line 12: -0.5 is outside 0-100, and this measure is a %",
                                        "line 13: 100.01 is outside 0-100, and this measure is a %"]


def test_byte_order_mark(tmp_path):
    p = raw(tmp_path, "wapd", rows_text())
    p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
    assert check("wapd", p) == [
        "the file starts with a byte-order mark (Excel's 'CSV UTF-8'); the workbook reads plain UTF-8: "
        "save it as plain CSV or from a text editor"]


def test_not_utf8(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes(b"# measure: caf\xe9\ndate,value\n")
    assert check("wapd", p) == ["the file is not UTF-8 text"]


def test_no_header(tmp_path):
    p = raw(tmp_path, "wapd", "")
    assert check("wapd", p) == ["no header: the first line after the notes must be exactly 'date,value'"]


def test_header_not_exact(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("date,value", "Date,Value", 1))
    assert check("wapd", p) == ["line 11: the header must be exactly 'date,value'; found 'Date,Value'"]


def test_no_pii_a_third_column_is_refused_and_says_why(tmp_path):
    body = "date,value,account\n" + "".join(
        "%s,%s,%d\n" % (d, v, 1000 + i) for i, (d, v) in enumerate(zip(dates(12), synthetic("%", 12))))
    p = raw(tmp_path, "card-non-rewards", body)
    problems = check("card-non-rewards", p)
    assert problems == [
        "line 11: column(s) 'account' refused: a template holds date and value and nothing else, so no "
        "account-level data or personal information can travel in it"]
    assert "personal information" in problems[0] and "account-level" in problems[0]


def test_a_row_with_an_extra_field_is_refused(tmp_path):
    body = rows_text().replace("2016-06-30,", "2016-06-30,Jane Doe,", 1)
    p = raw(tmp_path, "wapd", body)
    problems = check("wapd", p)
    assert problems[0] == (
        "line 17: 3 fields; a row holds a date and a value and nothing else, so no account-level data or "
        "personal information can travel in it")
    # the dropped row leaves a gap behind it, which is also reported
    assert problems[1:] == ["line 18: 2016-09-30 follows 2016-03-31; the quarters between are missing, "
                            "and a gap is refused, not filled in"]


def test_date_not_a_quarter_end(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2015-03-31", "2015-03-01", 1))
    assert check("wapd", p) == [
        "line 12: date '2015-03-01' is not a quarter-end (YYYY-03-31, YYYY-06-30, YYYY-09-30 or "
        "YYYY-12-31)"]


def test_yyyyqn_is_refused_with_the_date_to_write(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2015-03-31", "2015Q1", 1))
    assert check("wapd", p) == [
        "line 12: date '2015Q1': write it as 2015-03-31; the workbook reads YYYYQn as the wrong quarter"]


def test_yyyyqn_really_does_not_build(tmp_path):
    """Why YYYYQn is refused: the workbook reads it as monthly steps and refuses it."""
    p = tmp_path / "q.csv"
    p.write_text("date,value\n" + "".join("%dQ%d,%s\n" % (2015 + i // 4, i % 4 + 1, v)
                                          for i, v in enumerate(synthetic("%", 12))), encoding="utf-8")
    with pytest.raises(ValueError, match="expected one quarterly step"):
        build(tmp_path / "w.xlsx", [("A", p)], "A", "%", "higher_is_worse", "quarterly", 1, True,
              0.5, 1.0, 2.5, "worse", (10,), (50, 75, 90, 95), 1, 8)


def test_repeated_date(tmp_path):
    p = raw(tmp_path, "wapd", rows_text(12) + "2017-12-31,1.0\n")
    assert check("wapd", p) == ["line 24: 2017-12-31 is repeated"]


def test_dates_out_of_order(tmp_path):
    rows = list(zip(dates(12), synthetic("%", 12)))
    rows[4], rows[5] = rows[5], rows[4]
    p = raw(tmp_path, "wapd", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("wapd", p) == ["line 16: 2016-06-30 follows 2015-12-31; the quarters between are missing, "
                                "and a gap is refused, not filled in",
                                "line 17: 2016-03-31 comes before 2016-06-30; dates run oldest first"]


def test_a_gap(tmp_path):
    rows = list(zip(dates(13), synthetic("%", 13)))
    del rows[6]
    p = raw(tmp_path, "wapd", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("wapd", p) == ["line 18: 2016-12-31 follows 2016-06-30; the quarters between are missing, "
                                "and a gap is refused, not filled in"]


def test_value_not_a_number(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2015-06-30,", "2015-06-30,1.2%", 1))
    v = rows_text().splitlines()[2].split(",")[1]
    assert check("wapd", p) == ["line 13: value '1.2%%%s' is not a number" % v]


def test_value_blank_is_not_a_number(tmp_path):
    rows = list(zip(dates(12), synthetic("%", 12)))
    rows[2] = (rows[2][0], "")
    p = raw(tmp_path, "wapd", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("wapd", p) == ["line 14: value '' is not a number"]


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_value_not_finite(tmp_path, bad):
    rows = list(zip(dates(12), synthetic("%", 12)))
    rows[2] = (rows[2][0], bad)
    p = raw(tmp_path, "wapd", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("wapd", p) == ["line 14: value %r is not a finite number" % bad]


def test_every_problem_is_reported_at_once(tmp_path):
    ans = answers("epd")
    del ans["window"]
    ans["source"] = "[STATE: x]"
    rows = list(zip(dates(5), synthetic("%", 5)))
    rows[1] = (rows[1][0], "nan")
    p = raw(tmp_path, "epd", "date,value\n" + "".join("%s,%s\n" % r for r in rows), notes=ans)
    assert check("epd", p) == [
        "missing note: # window: the months on book that define early",
        "note 'source' still holds its placeholder; answer it: the internal system or report, by name",
        "line 12: value 'nan' is not a finite number",
        HISTORY % (5, SCALE_REFUSAL)]


# ---- the file is checked against the template it was written from ----

SPLITS = ("card-rewards", "card-non-rewards", "student-loans", "other-consumer-ex-student")


@pytest.mark.parametrize("written", SPLITS)
def test_a_split_file_does_not_pass_as_another_split(tmp_path, written):
    """The four two-book splits ask identical notes, so only the template line
    tells a card-rewards file from a card-non-rewards one."""
    p = filled(tmp_path, written)
    assert check(written, p) == []
    for other in SPLITS:
        if other != written:
            assert check(other, p) == [
                "note 'template' says this file was written from %r, not %r; check it as %s, or write "
                "the %s template and fill that" % (written, other, written, other)]


def test_the_template_line_is_required(tmp_path):
    p = raw(tmp_path, "card-rewards", rows_text())
    p.write_text("".join(l for l in p.read_text(encoding="utf-8").splitlines(keepends=True)
                         if not l.startswith("# template:")), encoding="utf-8")
    assert check("card-rewards", p) == [
        "missing note: # template: card-rewards (Credit card: rewards cards only); it names the "
        "template the file was written from, so a file cannot be checked as another book"]


# ---- no account-level data in '#' lines ----

COMMENT_REFUSED = ("line %d: a '#' line must be a note, '# key: answer'; anything else is refused, so "
                   "no account-level data or personal information can travel in one")


def test_account_rows_hidden_as_comments_are_refused(tmp_path):
    """The workbook skips '#' lines, so a row written as a comment would pass the
    column rule; it is refused instead. The card numbers are the standard test
    number, and the rest is made up."""
    body = ("#4111111111111111,Test Person,000-00-0000,balance 1.00\n"
            "#4111111111111112,Test Person,000-00-0000,balance 2.00\n") + rows_text()
    p = raw(tmp_path, "card-rewards", body)
    assert check("card-rewards", p) == [COMMENT_REFUSED % 11, COMMENT_REFUSED % 12]


def test_a_note_the_template_does_not_ask_is_refused(tmp_path):
    p = raw(tmp_path, "wapd", "# contact: 000-00-0000 Test Person\n" + rows_text())
    assert check("wapd", p) == [
        "line 11: note 'contact' is not one this template asks; a '#' line holds only the template's "
        "notes, so no account-level data or personal information can travel in one"]


def test_a_comment_among_the_rows_is_refused(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2016-03-31,", "#4111111111111111\n2016-03-31,", 1))
    assert check("wapd", p) == [COMMENT_REFUSED % 16]


def test_the_written_unit_line_is_one_of_the_notes(tmp_path):
    # filled() keeps the '# unit:' line write_template wrote; it is not refused.
    p = filled(tmp_path, "wapd")
    assert "# unit: %; higher is worse" in p.read_text(encoding="utf-8")
    assert check("wapd", p) == []


# ---- lines split where the workbook splits them ----

def _build(tmp_path, p):
    return build(tmp_path / "w.xlsx", [("A", p)], "A", "%", "higher_is_worse", "quarterly", 1, True,
                 0.5, 1.0, 2.5, "worse", (10,), (50, 75, 90, 95), 1, 8)


def test_a_vertical_tab_before_the_header_is_refused_as_the_build_refuses_it(tmp_path):
    p = raw(tmp_path, "wapd", rows_text())
    p.write_text(p.read_text(encoding="utf-8").replace("\ndate,value\n", "\x0bdate,value\n"),
                 encoding="utf-8", newline="")
    with pytest.raises(ValueError, match=r"must begin with the header line date,value \(it has: 2015-03-31,2.0\)"):
        _build(tmp_path, p)
    # 'date,value' rides on the last note's line, so the first row is read as the header.
    assert check("wapd", p) == [
        "line 11: the header must be exactly 'date,value'; found '2015-03-31,2.0'"]


def test_a_line_separator_inside_a_row_is_refused_as_the_build_refuses_it(tmp_path):
    lines = rows_text().splitlines()
    joined = lines[2] + " " + lines[3]
    p = raw(tmp_path, "wapd", "\n".join(lines[:2] + [joined] + lines[4:]) + "\n")
    with pytest.raises(ValueError):
        _build(tmp_path, p)
    # One physical line holding two rows' worth of fields.
    assert check("wapd", p) == [
        "line 13: 3 fields; a row holds a date and a value and nothing else, so no account-level data "
        "or personal information can travel in it",
        "line 14: 2015-12-31 follows 2015-03-31; the quarters between are missing, and a gap is "
        "refused, not filled in"]


def test_a_line_separator_inside_a_note_answer_passes_as_it_builds(tmp_path):
    p = raw(tmp_path, "wapd", rows_text(), notes=dict(answers("wapd"), measure="synthetic answer"))
    assert check("wapd", p) == []
    assert _build(tmp_path, p)["quarters"] == 12


# ---- line numbers name the line the row is on ----

def test_a_quoted_field_across_lines_does_not_shift_later_line_numbers(tmp_path):
    lines = rows_text(12).splitlines()
    lines[2] = '2015-06-30,"1.2\nX"'      # file lines 13-14
    del lines[4]                          # 2015-12-31 missing: 2016-03-31 on file line 16
    p = raw(tmp_path, "wapd", "\n".join(lines) + "\n")
    assert check("wapd", p) == [
        "line 13: value '1.2\\nX' is not a number",
        "line 16: 2016-03-31 follows 2015-09-30; the quarters between are missing, and a gap is "
        "refused, not filled in"]


def test_a_blank_line_among_the_rows_is_skipped_as_the_build_skips_it(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2016-03-31,", "\n2016-03-31,", 1))
    assert check("wapd", p) == []
    assert _build(tmp_path, p)["quarters"] == 12


def test_a_trailing_comma_on_the_header_is_one_problem_not_one_per_row(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("date,value", "date,value,", 1))
    assert check("wapd", p) == [
        "line 11: column(s) unnamed (a trailing comma?) refused: a template holds date and value and "
        "nothing else, so no account-level data or personal information can travel in it"]


def test_a_row_with_one_field_says_it_needs_a_value(tmp_path):
    lines = rows_text(12).splitlines()
    lines[2] = "2015-06-30"
    p = raw(tmp_path, "wapd", "\n".join(lines) + "\n")
    assert check("wapd", p) == ["line 13: 1 field(s); a row needs a date, a comma and a value",
                                "line 14: 2015-09-30 follows 2015-03-31; the quarters between are "
                                "missing, and a gap is refused, not filled in"]


# ---- guards no test pinned (each survived a mutation) ----

def test_percent_0_and_100_exactly_pass(tmp_path):
    rows = list(zip(dates(12), synthetic("%", 12)))
    rows[0], rows[1] = (rows[0][0], "0"), (rows[1][0], "100")
    p = raw(tmp_path, "wapd", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("wapd", p) == []


def test_a_score_on_either_end_of_the_scale_passes(tmp_path):
    rows = list(zip(dates(12), synthetic("score", 12)))
    rows[0], rows[1] = (rows[0][0], "300"), (rows[1][0], "850")
    p = raw(tmp_path, "refreshed-score", "date,value\n" + "".join("%s,%s\n" % r for r in rows))
    assert check("refreshed-score", p) == []


def test_a_scale_with_no_width_is_refused(tmp_path):
    ans = dict(answers("refreshed-score"), scale="500-500")
    p = raw(tmp_path, "refreshed-score", rows_text(unit="score"), notes=ans)
    assert check("refreshed-score", p) == [
        "note 'scale' must give the lowest and highest possible scores, low first, e.g. 300-850; "
        "found '500-500'"]


def test_a_header_with_a_space_is_refused_because_it_does_not_build(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("date,value", "date, value", 1))
    assert check("wapd", p) == ["line 11: the header must be exactly 'date,value'; found 'date, value'"]
    with pytest.raises(ValueError, match=r"must begin with the header line date,value \(it has: date, value\)"):
        _build(tmp_path, p)


def test_a_date_with_a_time_is_not_a_quarter_end(tmp_path):
    p = raw(tmp_path, "wapd", rows_text().replace("2015-03-31", "2015-03-31T00:00", 1))
    assert check("wapd", p) == [
        "line 12: date '2015-03-31T00:00' is not a quarter-end (YYYY-03-31, YYYY-06-30, YYYY-09-30 or "
        "YYYY-12-31)"]


def test_write_refuses_to_write_over_a_checklist(tmp_path):
    md = tmp_path / "x.checklist.md"
    md.write_text("notes the bank kept\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        write_template("wapd", tmp_path / "x.csv")
    assert str(e.value) == ("%s already exists; it is not written over, so a filled template cannot be "
                            "lost. Choose another name or move it." % md)
    assert md.read_text(encoding="utf-8") == "notes the bank kept\n"
    assert not (tmp_path / "x.csv").exists()
