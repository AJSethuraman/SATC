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


def test_every_setting_has_options_one_recommended_and_short_explanations():
    for s in control.load_settings():
        assert len(s.options) >= 2, s.key
        assert sum(o.recommended for o in s.options) == 1, s.key
        assert len({o.label for o in s.options}) == len(s.options), s.key
        assert s.takes_effect in ("live", "re-run"), s.key
        for o in s.options:
            # the firm's tell: a sentence past ~25 words was written to be complete, not read
            assert len(o.explains.split()) <= 30, (s.key, o.label)


def test_the_tab_opens_on_the_recommended_options(book):
    got = control.read_control(book)
    want = {s.key: s.recommended().value for s in control.load_settings()}
    assert got == want


def test_your_own_value_wins(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "worse_at"), column=control.OWN_COL, value=1.4)
    wb.save(book)
    assert control.read_control(book)["worse_at"] == 1.4


def test_picking_another_option(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "confidence"), column=control.CHOOSE_COL, value="99%")
    wb.save(book)
    assert control.read_control(book)["confidence"] == 0.99


def test_nothing_chosen_is_refused_by_name(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "min_loans"), column=control.CHOOSE_COL).value = None
    wb.save(book)
    with pytest.raises(control.ControlError, match="Fewest loans in a pocket"):
        control.read_control(book)


def test_text_where_a_number_is_needed_is_refused(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "materiality"), column=control.OWN_COL, value="lots")
    wb.save(book)
    with pytest.raises(control.ControlError, match="dollar amount"):
        control.read_control(book)


def test_a_setting_missing_from_the_tab_is_refused(book):
    wb = load_workbook(book)
    ws = wb[control.SHEET]
    ws.cell(row=_row(ws, "proof"), column=control.KEY_COL).value = None
    wb.save(book)
    with pytest.raises(control.ControlError, match="`proof` is not on the Control tab"):
        control.read_control(book)


def test_in_use_and_meaning_are_formulas_over_the_options_tab(book):
    ws = load_workbook(book)[control.SHEET]
    r = _row(ws, "confidence")
    assert str(ws.cell(row=r, column=5).value).startswith("=IF(")
    assert "_options" in ws.cell(row=r, column=6).value
    assert ws.data_validations.dataValidation, "every Choose cell carries a dropdown"
