"""The two column limits, when the extract already has a workbook (HANDOFF.md open item, 4 Oct 2026: "The launcher's
Next overwrites a category limit typed on Control").

Before: the launcher kept its own last choice of the two limits and Next wrote it over Control, so a value typed on
Control was replaced without a word. The firm, 14 Oct 2026, chose the workbook's: picking an extract loads the limits
Control holds into the launcher's two dropdowns, as bands, segments and filters already are, and Next writes back
what the dropdowns show. A value typed on Control survives; a change made in the launcher replaces it.
"""

import json

import pytest
from openpyxl import load_workbook

from pocketbook import book, control, launcher
from test_launcher import _flow, _graded


def _type_on_control(b, key, choose=None, own=None):
    """What an analyst does in Excel: pick an option in C, or type a number of their own in D."""
    wb = load_workbook(b)
    ws = wb[control.SHEET]
    r = control.row_of(ws, key)
    ws.cell(row=r, column=control.CHOOSE_COL).value = choose
    ws.cell(row=r, column=control.OWN_COL).value = own
    wb.save(b)


def _limits(b) -> dict:
    ws = load_workbook(b)[control.SHEET]
    return {k: control.answer_of(k, ws.cell(row=control.row_of(ws, k), column=control.CHOOSE_COL).value,
                                 ws.cell(row=control.row_of(ws, k), column=control.OWN_COL).value)
            for k in ("few_values", "many_values")}


def _written(tmp_path, few=6, many=50):
    """An extract whose workbook the launcher wrote with these limits."""
    x = _graded(tmp_path)
    f = _flow(x, few=few, many=many)
    f.set_up()
    f.next()
    assert f.page == "answer", f.message
    b = launcher.book_for(x)
    assert _limits(b) == {"few_values": few, "many_values": many}
    return x, b


def test_a_limit_picked_on_control_survives_next(tmp_path):
    """The reproduction: 24 picked on Control, the launcher reopened with its own last choice (6), Next pressed."""
    x, b = _written(tmp_path)
    _type_on_control(b, "few_values", choose="24 values")
    f = _flow(x, few=6)                                   # the launcher's saved preference is still 6
    assert (f.few, f.many) == (24, 50)
    f.set_up()
    f.next()
    assert _limits(b) == {"few_values": 24, "many_values": 50}


def test_a_limit_typed_off_the_list_on_control_survives_next(tmp_path):
    """A number of the analyst's own in D (60 is not one of the options), not only an option picked in C."""
    x, b = _written(tmp_path)
    _type_on_control(b, "many_values", own=60)
    f = _flow(x)
    assert (f.few, f.many) == (6, 60)
    f.set_up()
    f.next()
    assert _limits(b) == {"few_values": 6, "many_values": 60}


def test_a_limit_changed_in_the_launcher_after_reopening_is_written(tmp_path):
    x, b = _written(tmp_path)
    _type_on_control(b, "few_values", choose="24 values")
    f = _flow(x)
    assert f.few == 24 and f.limits_said
    f.choose_limit("few", 6)
    assert f.few == 6 and not f.limits_said               # the line no longer describes the dropdowns
    f.set_up()
    f.next()
    assert _limits(b) == {"few_values": 6, "many_values": 50}


def test_the_launcher_says_where_the_limits_came_from(tmp_path):
    x, b = _written(tmp_path)
    f = _flow(x)
    assert f.limits_said == launcher.LIMITS_FROM_BOOK
    (tmp_path / "other").mkdir()
    f.pick(str(_graded(tmp_path / "other")))              # an extract with no workbook beside it
    assert f.limits_said == "" and (f.few, f.many) == (12, 50)   # the launcher's own, not the last workbook's


def test_an_extract_with_no_workbook_keeps_the_launchers_limits(tmp_path):
    x = _graded(tmp_path)
    f = _flow(x, few=24, many=25)
    assert (f.few, f.many, f.limits_said) == (24, 25, "")


def test_the_limits_load_when_the_launcher_opens_on_the_last_extract(tmp_path):
    """The window starts a Flow with the extract from its saved preferences, not through pick."""
    x, b = _written(tmp_path)
    _type_on_control(b, "few_values", choose="24 values")
    f = launcher.Flow(gate=launcher.AddOns(), extract=str(x), few=6)
    assert f.few == 24 and f.limits_said == launcher.LIMITS_FROM_BOOK


def test_a_blank_limit_on_control_leaves_the_launchers(tmp_path):
    x, b = _written(tmp_path, few=6, many=25)
    _type_on_control(b, "few_values")                     # both cells cleared
    f = _flow(x, few=12)
    assert (f.few, f.many) == (12, 25)


def test_an_unreadable_workbook_leaves_the_launchers_limits(tmp_path):
    x = _graded(tmp_path)
    launcher.book_for(x).write_bytes(b"not a workbook")
    assert book.limits_in(x) == {}
    f = _flow(x, few=24)
    assert (f.few, f.limits_said) == (24, "")


def _without_dimension(b):
    """The workbook as a writer that records no sheet size leaves it: openpyxl then reads each row of a read-only sheet
    only as far as its last filled cell (review of #437: with the size recorded, every row is padded to it)."""
    import re
    import zipfile
    parts = {}
    with zipfile.ZipFile(b) as z:
        for i in z.infolist():
            data = z.read(i.filename)
            if i.filename.startswith("xl/worksheets/") and i.filename.endswith(".xml"):
                data = re.sub(rb"<dimension [^>]*/>", b"", data)
            parts[i.filename] = data
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)


def test_read_limits_reads_a_read_only_worksheet(tmp_path):
    """book.limits_in opens the workbook read-only: rows padded to the sheet's recorded size, or, with none recorded,
    rows of different lengths, some shorter than the hidden key column."""
    x, b = _written(tmp_path, few=6, many=25)
    _type_on_control(b, "many_values", own=60)
    for strip in (False, True):
        if strip:
            _without_dimension(b)
        wb = load_workbook(b, read_only=True)
        try:
            ws = wb[control.SHEET]
            if strip:
                assert min(len(r) for r in ws.iter_rows(min_row=control.FIRST_ROW, values_only=True)) < control.KEY_COL
            assert control.read_limits(ws) == {"few_values": 6, "many_values": 60}
        finally:
            wb.close()
        assert book.limits_in(x) == {"few_values": 6, "many_values": 60}


def test_a_limit_typed_on_control_while_the_launcher_left_open_survives_next(tmp_path):
    """The launcher stays open while the analyst edits Control in Excel; Set up and Next read Control again."""
    x, b = _written(tmp_path)
    f = _flow(x)
    f.set_up()
    _type_on_control(b, "few_values", choose="24 values")
    f.next()                                              # straight from Choose tests, no Set up in between
    assert _limits(b) == {"few_values": 24, "many_values": 50}
    _type_on_control(b, "many_values", choose="100 values")
    f.set_up()
    assert (f.few, f.many) == (24, 100)
    f.next()
    assert _limits(b) == {"few_values": 24, "many_values": 100}


def test_a_launcher_change_wins_once_then_control_is_read_again_launcher_left_open(tmp_path):
    x, b = _written(tmp_path)
    f = _flow(x)
    f.choose_limit("few", 24)
    _type_on_control(b, "few_values", choose="12 values")  # Control edited after the launcher's change
    f.set_up()
    f.next()
    assert _limits(b)["few_values"] == 24                 # the launcher's change was made last here, and is written
    _type_on_control(b, "few_values", choose="12 values")  # after that Next, Control is the record again
    f.next()
    assert _limits(b)["few_values"] == 12


def test_a_path_being_typed_never_takes_another_extracts_limits(tmp_path):
    """Typing ".../loans2.csv" passes through ".../loans", whose workbook name is loans.csv's."""
    x, b = _written(tmp_path)
    _type_on_control(b, "few_values", choose="24 values")
    _type_on_control(b, "many_values", choose="25 values")
    other = tmp_path / "loans2.csv"
    other.write_bytes(x.read_bytes())
    stem = str(x.with_suffix(""))
    assert launcher.book_for(stem) == b                   # the trap: a prefix maps to loans.csv's workbook
    f = _flow(few=6, many=50)
    for i in range(len(stem) - 3, len(str(other)) + 1):
        f.pick(str(other)[:i])
        assert (f.few, f.many, f.limits_said) == (6, 50, ""), str(other)[:i]
    assert f.limit_prefs() == {"few": 6, "many": 50}
    f.pick(str(x))                                        # the extract itself does take them
    assert (f.few, f.many) == (24, 25)
    assert f.limit_prefs() == {"few": 6, "many": 50}      # and the launcher keeps its own for the next extract


def test_the_window_shows_the_workbooks_limits_and_drops_the_line_on_a_change(tmp_path, monkeypatch):
    """The dropdowns and the line under them, in the window (needs a display; CI has none, so Flow's tests above
    carry the planted bugs)."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display to open a window on")
    x, b = _written(tmp_path)
    _type_on_control(b, "many_values", own=60)            # off the list: offered beside the options
    monkeypatch.setattr(launcher, "PREFS", tmp_path / "launcher.json")
    monkeypatch.setattr(launcher, "open_file", lambda p: None)
    # the window opens on the last extract, from its prefs: the first drawing, before any pick
    (tmp_path / "launcher.json").write_text(json.dumps({"extract": str(x), "few": 12, "many": 50}))
    try:
        w = launcher.build(root)
        flow = w["flow"]
        root.update()
        assert (w["few"].get(), w["many"].get()) == ("6 values", "60 values")
        assert "60 values" in w["many"].cget("values")
        assert w["limits_said"].winfo_ismapped()
        w["extract"].set(str(x) + "~")                    # a path being typed: no file, the launcher's own
        root.update()
        assert (w["few"].get(), w["many"].get()) == ("12 values", "50 values")
        assert not w["limits_said"].winfo_ismapped()
        w["extract"].set(str(x))
        root.update()
        assert (w["few"].get(), w["many"].get()) == ("6 values", "60 values")
        assert "60 values" in w["many"].cget("values")
        assert w["limits_said"].winfo_ismapped() and w["limits_said"].cget("text") == launcher.LIMITS_FROM_BOOK
        w["few"].set("24 values")
        w["few"].event_generate("<<ComboboxSelected>>")
        root.update()
        assert flow.few == 24 and not w["limits_said"].winfo_ismapped()
        assert json.loads((tmp_path / "launcher.json").read_text())["few"] == 24
    finally:
        root.destroy()
