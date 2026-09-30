"""What went wrong is said on the window, never in Notepad (at the bank, 30 Sep 2026).

Pressing Run with the extract open in Excel (or with OneDrive still syncing it), a PermissionError traceback from
Run's fingerprint check ended up in Notepad: the launcher wrote it to last-error.txt and pointed there. PocketBook
checked whether the *workbook* was open, never the *extract*. The firm: "It would be a lot easier if these kinds of
errors just displayed on screen in the huge white space allotted".

So: an extract that can't be read is a plain refusal naming the file, from every place that reads it; and anything
PocketBook didn't expect is shown on the page, with its type and message and a Copy details button, and the window
stays usable."""

from pathlib import Path

import pytest
from openpyxl import Workbook

from pocketbook import book, launcher, synth
from test_book import _answer
from test_launcher import _flow, _read

BANK = ("Test_Pop_DC.xlsx can't be read: it's open in Excel, or OneDrive is still syncing it. Close it in Excel "
        "(check for a hidden Excel window), or right-click it in File Explorer and choose Always keep on this device. "
        "Then press {again} again.")


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    """last-error.txt and the launcher's choices land in the test's own folder, never the real home."""
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(launcher, "PREFS", tmp_path / "launcher.json")


def _bank_extract(tmp_path, n=1500) -> Path:
    """The synthetic book, saved as the bank's file was: Test_Pop_DC.xlsx."""
    csv_ = synth.write_extract(tmp_path, n=n)
    wb = Workbook()
    ws = wb.active
    import csv
    with csv_.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            ws.append([float(v) if v.replace(".", "", 1).replace("-", "", 1).isdigit() else v for v in row])
    x = tmp_path / "Test_Pop_DC.xlsx"
    wb.save(x)
    csv_.unlink()
    return x


def _locked(monkeypatch, path: Path) -> None:
    """The extract held by Excel, or online-only in OneDrive: every read of it raises, as on the bank's machine."""
    real_bytes, real_open = Path.read_bytes, open

    def read_bytes(self):
        if Path(self).resolve() == path.resolve():
            raise PermissionError(13, "Permission denied", str(path))
        return real_bytes(self)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)

    def open_(file, *a, **k):
        if isinstance(file, (str, Path)) and Path(file).resolve() == path.resolve():
            raise PermissionError(13, "Permission denied", str(path))
        return real_open(file, *a, **k)
    monkeypatch.setattr("builtins.open", open_)


def _ready_to_run(tmp_path) -> launcher.Flow:
    """Set up, the tests chosen, the workbook answered: the next press is Run."""
    f = _flow(_bank_extract(tmp_path))
    f.set_up()
    assert f.screen() == "L2", f.message
    f.next()
    assert f.page == "answer", f.message
    _answer(launcher.book_for(f.extract))
    return f


# ---- an extract that can't be read


def test_run_with_the_extract_open_in_excel_says_so_on_screen(tmp_path, monkeypatch):
    """The bank's case: the workbook is closed and answered, the extract isn't readable."""
    f = _ready_to_run(tmp_path)
    x = Path(f.extract)
    _locked(monkeypatch, x)
    f.run()                                                     # never raises
    assert f.screen() == "L3" and not f.answers and f.crash is None
    assert [n.says for n in f.needs] == [BANK.format(again="Run")]
    assert f.needs_head()[0] == "Run stopped"
    assert not (tmp_path / "home" / ".pocketbook" / "last-error.txt").exists()   # nothing unexpected: no log
    # book.run itself, without the launcher, refuses in the same words
    out = book.run(launcher.book_for(x), x)
    assert not out.ok and out.lines == [BANK.format(again="Run")] and not out.problems
    # fixed (closed in Excel): Run again from the same window works
    monkeypatch.undo()
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path / "home")
    f.run()
    assert f.screen() == "L5", [n.says for n in f.needs]


def test_set_up_with_the_extract_open_in_excel_says_press_set_up_again(tmp_path, monkeypatch):
    x = _bank_extract(tmp_path, n=300)
    _locked(monkeypatch, x)
    f = _flow(x)
    f.set_up()                                                  # step 2: reading what each column is
    assert f.screen() == "L1" and f.message == [BANK.format(again="Set up")] and f.crash is None
    got = book.set_up(x)                                        # Next: writing the workbook
    assert not got.ok and got.lines == [BANK.format(again="Set up")]
    assert book.read_extract(x).problem == BANK.format(again="Set up")
    assert not launcher.book_for(x).exists()


def test_an_extract_that_is_gone_says_where_it_was_looked_for(tmp_path, monkeypatch):
    f = _ready_to_run(tmp_path)
    x = Path(f.extract)
    x.rename(tmp_path / "moved.xlsx")
    gone = (f"Couldn't find Test_Pop_DC.xlsx. PocketBook looked for it in {tmp_path}. Put it back there, or pick it "
            f"again with Browse, then press {{again}} again.")
    f.run()
    assert [n.says for n in f.needs] == [gone.format(again="Run")] and f.crash is None
    assert book.set_up(x).lines == [gone.format(again="Set up")]
    assert book.read_extract(x).problem == gone.format(again="Set up")
    g = _flow(x)
    g.set_up()
    assert g.message == [gone.format(again="Set up")]


def test_the_extract_is_read_once_per_run_and_its_fingerprint_comes_from_that_read(tmp_path, monkeypatch):
    """Run read the extract twice, the fingerprint first: that second read is where the bank's traceback came from.
    A changed extract is still noticed."""
    f = _ready_to_run(tmp_path)
    x = Path(f.extract)
    reads = []
    real = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: (reads.append(Path(self).name), real(self))[1])
    out = book.run(launcher.book_for(x), x)
    assert out.ok and reads.count(x.name) == 1
    assert not any("has changed since Set up" in ln for ln in out.lines)
    wb = __import__("openpyxl").load_workbook(x)
    wb.properties.title = "saved again"                        # the same loans, saved again: new bytes
    wb.save(x)
    again = book.run(launcher.book_for(x), x)
    assert any("Test_Pop_DC.xlsx has changed since Set up" in ln for ln in again.lines)


# ---- anything PocketBook didn't expect


def test_an_unexpected_error_in_run_is_shown_on_the_page_with_its_details(tmp_path, monkeypatch):
    f = _ready_to_run(tmp_path)

    def boom(*a, **k):
        raise KeyError("GCO_AMT")
    monkeypatch.setattr(book, "run", boom)
    f.run()                                                     # never raises out of the launcher
    assert f.screen() == "L3" and not f.answers and f.needs_head()[0] == "Run stopped"
    c = f.crash
    assert c is not None and c.heading == "Run stopped" and c.kind == "KeyError" and c.said == "'GCO_AMT'"
    log = tmp_path / "home" / ".pocketbook" / "last-error.txt"
    assert [n.says for n in f.needs] == [
        "Something went wrong that PocketBook didn't expect.",
        "KeyError: 'GCO_AMT'",
        "Press Copy details and send what it copies, to get it fixed.",
        f"A copy is kept in {log}."]
    assert "Traceback" in c.details and "boom" in c.details and 'raise KeyError("GCO_AMT")' in c.details
    assert log.read_text(encoding="utf-8") == c.details            # the file copy is still kept
    assert not any("The details are in" in n.says for n in f.needs)  # not pointed at a file to open in Notepad
    # the window is still usable: fixed, Run again works and the page moves on
    monkeypatch.undo()
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path / "home")
    f.run()
    assert f.screen() == "L5" and f.crash is None


def test_an_unexpected_error_in_set_up_or_next_is_shown_not_raised(tmp_path, monkeypatch):
    x = synth.write_extract(tmp_path, n=300)
    f = _flow(x)

    def boom(*a, **k):
        raise ValueError("a column with no name")
    monkeypatch.setattr(book, "read_extract", boom)
    f.set_up()
    assert f.screen() == "L1" and f.crash.heading == "Set up stopped"
    assert f.message[:2] == ["Something went wrong that PocketBook didn't expect.", "ValueError: a column with no name"]
    monkeypatch.undo()
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path / "home")
    g = _read(tmp_path / "b")
    monkeypatch.setattr(book, "set_up", boom)
    g.next()
    assert g.screen() == "L2" and g.crash.heading == "Writing the workbook stopped"
    assert g.message == g.crash.lines() and "ValueError: a column with no name" in g.message
    # the old button words, for the command-line helpers, say the same
    lines = launcher.do_set_up(str(x))
    assert lines[1] == "ValueError: a column with no name" and "Traceback" not in "".join(lines)


def test_a_run_that_stopped_on_the_tie_out_still_offers_the_details(tmp_path, monkeypatch):
    """The failed tie-out keeps its own plain words (walk of 27 Sep 2026) and gains Copy details."""
    from pocketbook import engine
    f = _ready_to_run(tmp_path)

    def fails(grid, total, measures, n):
        raise engine.TieOutError("grid x: rows adds up to 7999 across the cells, but the book says 8000")
    monkeypatch.setattr(engine, "tie_out", fails)
    f.run()
    assert f.needs[0].says.startswith("Run stopped: the grids didn't add up to the book")
    assert f.needs[1].says.endswith("Press Copy details and send what it copies, to get it fixed.")
    assert f.crash is not None and f.crash.kind == "TieOutError" and "Traceback" in f.crash.details


# ---- on a real window, where there is a display


def test_the_window_shows_the_error_in_the_page_and_copy_details_copies_the_traceback(tmp_path, monkeypatch):
    from test_deps import _window
    root = _window()
    try:
        w = launcher.build(root)
        flow = w["flow"]
        f = _ready_to_run(tmp_path)
        flow.extract, flow.read, flow.written, flow.page = f.extract, f.read, f.written, "answer"
        w["extract"].set(f.extract)

        def boom(*a, **k):
            raise KeyError("GCO_AMT")
        monkeypatch.setattr(book, "run", boom)
        w["render"]()
        root.update()
        w["run"].invoke()
        for _ in range(200):
            root.update()
            if not flow.busy:
                break
            __import__("time").sleep(0.05)
        root.update()
        shown = w["crash"].cget("text")
        assert "Something went wrong that PocketBook didn't expect." in shown and "KeyError: 'GCO_AMT'" in shown
        assert w["crash"].winfo_manager() == "pack" and w["crash"].winfo_toplevel() == root   # drawn in the page
        w["copy_details"].invoke()
        assert root.clipboard_get() == flow.crash.details and "Traceback" in root.clipboard_get()
        assert w["copy_details"].cget("text") == "Copied"
        assert str(w["run"].cget("state")) == "normal"                 # the window is still usable
        # the extract locked: the plain refusal, on the same page, with nothing to copy
        monkeypatch.undo()
        monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path / "home")
        _locked(monkeypatch, Path(f.extract))
        w["run"].invoke()
        for _ in range(200):
            root.update()
            if not flow.busy:
                break
            __import__("time").sleep(0.05)
        root.update()
        assert flow.crash is None and "copy_details" not in w
        assert flow.needs[0].says == BANK.format(again="Run")
    finally:
        root.destroy()


def test_the_set_up_page_shows_an_unexpected_error_in_its_space(tmp_path, monkeypatch):
    from test_deps import _window
    root = _window()
    try:
        w = launcher.build(root)
        flow = w["flow"]
        w["extract"].set(str(synth.write_extract(tmp_path, n=300)))

        def boom(*a, **k):
            raise ValueError("a column with no name")
        monkeypatch.setattr(book, "read_extract", boom)
        root.update()
        w["setup"].invoke()
        for _ in range(200):
            root.update()
            if not flow.busy:
                break
            __import__("time").sleep(0.05)
        root.update()
        assert flow.screen() == "L1" and "ValueError: a column with no name" in w["crash"].cget("text")
        w["copy_details"].invoke()
        assert "ValueError: a column with no name" in root.clipboard_get()
        assert str(w["setup"].cget("state")) == "normal"
    finally:
        root.destroy()


def test_the_window_catches_what_a_step_itself_did_not(tmp_path, monkeypatch):
    """The last net: an error raised out of a step (here the Run step itself) still lands on the page."""
    from test_deps import _window
    root = _window()
    try:
        w = launcher.build(root)
        flow = w["flow"]
        f = _ready_to_run(tmp_path)
        flow.extract, flow.read, flow.written, flow.page = f.extract, f.read, f.written, "answer"
        w["extract"].set(f.extract)

        def boom():
            raise OSError(22, "Invalid argument")
        flow.run = boom
        w["render"]()
        root.update()
        w["run"].invoke()
        for _ in range(200):
            root.update()
            if not flow.busy:
                break
            __import__("time").sleep(0.05)
        root.update()
        assert flow.crash.heading == "Run stopped" and "OSError: [Errno 22] Invalid argument" in w["crash"].cget("text")
        assert "copy_details" in w and str(w["run"].cget("state")) == "normal"
    finally:
        root.destroy()
