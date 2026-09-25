"""The control center: generated from settings.yaml, read back from the
cells a person edits, and refusing rather than defaulting."""

import pytest
from openpyxl import load_workbook

from origination_cube import control


@pytest.fixture
def book(tmp_path):
    return control.build_control_book(tmp_path / "control.xlsx")


def _row(ws, key):
    for r in ws.iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == key:
            return r[0].row
    raise KeyError(key)


JUDGMENT = {"min_age_months", "min_loans", "min_events", "materiality", "compare_to", "worse_at", "better_at",
            "confidence"}


def test_judgment_settings_recommend_nothing_and_method_settings_recommend_one():
    """The firm: what is material, what is enough loans, what counts as worse
    is the professional's judgment, never the tool's."""
    settings = control.load_settings()
    assert {s.key for s in settings if s.judgment} == JUDGMENT
    for s in settings:
        assert sum(o.recommended for o in s.options) == (0 if s.judgment else 1), s.key


def test_every_setting_has_options_and_short_explanations():
    for s in control.load_settings():
        assert len(s.options) >= 2, s.key
        assert len({o.label for o in s.options}) == len(s.options), s.key
        assert s.takes_effect in ("live", "re-run"), s.key
        for o in s.options:
            # the firm's tell: a sentence past ~25 words was written to be complete, not read
            assert len(o.explains.split()) <= 30, (s.key, o.label)


def _answer_judgment(book, choices=None):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    for s in control.load_settings():
        if s.judgment:
            pick = (choices or {}).get(s.key, s.options[0].shown)
            ws.cell(row=_row(ws, s.key), column=control.CHOOSE_COL).value = pick
    wb.save(book)


def test_a_fresh_tab_waits_for_every_judgment_and_names_each(book):
    with pytest.raises(control.ControlError) as exc:
        control.read_control(book)
    assert len(exc.value.problems) == len(JUDGMENT)
    assert all("needs an answer" in p for p in exc.value.problems)
    assert not any("judgment" in p.lower() for p in exc.value.problems)


def test_unanswered_cells_are_shaded_by_a_rule_not_labelled(book):
    """The firm: no "your judgment" labels; shade what still needs entering."""
    ws = load_workbook(book)[control.SHEET]
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
    assert "judgment" not in text.lower() and "whose call" not in text.lower()
    rules = [r for rng in ws.conditional_formatting for r in rng.rules]
    assert len(rules) == len(control.load_settings())
    r = _row(ws, "materiality")
    ranges = [str(rng.sqref) for rng in ws.conditional_formatting]
    assert f"C{r}:D{r}" in ranges


def test_method_settings_open_on_their_recommendation(book):
    _answer_judgment(book)
    got = control.read_control(book)
    for s in control.load_settings():
        if not s.judgment:
            assert got[s.key] == s.recommended().value


def test_your_own_value_wins(book):
    _answer_judgment(book)
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "worse_at"), column=control.OWN_COL).value = 1.4
    wb.save(book)
    assert control.read_control(book)["worse_at"] == 1.4


def test_picking_another_option(book):
    _answer_judgment(book)
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "confidence"), column=control.CHOOSE_COL).value = "99%"
    wb.save(book)
    assert control.read_control(book)["confidence"] == 0.99


def test_nothing_chosen_is_refused_by_name(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "band_count"), column=control.CHOOSE_COL).value = None
    wb.save(book)
    _answer_judgment(book)
    with pytest.raises(control.ControlError, match="How many bands"):
        control.read_control(book)


def test_text_where_a_number_is_needed_is_refused(book):
    _answer_judgment(book)
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "materiality"), column=control.OWN_COL).value = "lots"
    wb.save(book)
    with pytest.raises(control.ControlError, match="dollar amount"):
        control.read_control(book)


def test_a_setting_missing_from_the_tab_is_refused(book):
    _answer_judgment(book)
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "many_tests"), column=control.KEY_COL).value = None
    wb.save(book)
    with pytest.raises(control.ControlError, match="`many_tests` is not on the Control tab"):
        control.read_control(book)


def test_in_use_and_meaning_are_formulas_over_the_options_tab(book):
    ws = load_workbook(book)[control.SHEET]
    r = _row(ws, "confidence")
    assert str(ws.cell(row=r, column=5).value).startswith("=IF(")
    assert "_options" in ws.cell(row=r, column=6).value
    assert ws.data_validations.dataValidation, "every Choose cell carries a dropdown"
