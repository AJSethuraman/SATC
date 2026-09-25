"""The launcher's buttons, without the window: every outcome is words."""

from origination_cube import book, launcher, synth


def test_the_workbook_sits_beside_the_extract(tmp_path):
    assert launcher.book_for(tmp_path / "sep loans.csv") == tmp_path / "sep loans - Origination Cube.xlsx"


def test_buttons_pressed_out_of_order_say_what_to_do(tmp_path):
    assert "Pick the extract first" in launcher.do_set_up("")[0]
    x = synth.write_extract(tmp_path, n=500)
    assert "Press 1. Set up" in launcher.do_run(str(x))[0]


def test_set_up_then_run_through_the_buttons(tmp_path):
    x = synth.write_extract(tmp_path, n=2000)
    lines = launcher.do_set_up(str(x))
    assert lines[0].startswith("Set up") and launcher.book_for(x).exists()
    lines = launcher.do_run(str(x))
    assert lines[0].startswith("Couldn't run yet")


def test_an_unexpected_failure_is_a_sentence_not_a_traceback(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher.Path, "home", lambda: tmp_path)

    def boom(*a, **k):
        raise ZeroDivisionError("inside")
    monkeypatch.setattr(book, "set_up", boom)
    x = synth.write_extract(tmp_path, n=100)
    lines = launcher.do_set_up(str(x))
    assert len(lines) == 1 and "send that file over" in lines[0] and "Traceback" not in lines[0]
    assert "ZeroDivisionError" in (tmp_path / ".origination-cube" / "last-error.txt").read_text()


def test_run_hands_the_picked_extract_to_the_workbook(tmp_path, monkeypatch):
    """Second walk, defect 1: the window's extract wins over the path stored at Set up."""
    x = synth.write_extract(tmp_path, n=100)
    launcher.book_for(x).write_bytes(b"")
    seen = {}

    def fake(target, extract=None):
        seen["extract"] = extract
        return book.Outcome(True, target, ["ok"])
    monkeypatch.setattr(book, "run", fake)
    assert launcher.do_run(str(x)) == ["ok"] and seen["extract"] == str(x)
