"""The Choose table tints the row you are in (the firm, 30 Sep 2026: "In setup screens it would be nice if it
highlighted the row you're clicking in when the button is far away from the column names")."""

import time
from pathlib import Path

import pytest

from pocketbook import house, launcher, synth


def _colours(w):
    """Every background in a row, the row's own frame and everything inside it."""
    out, todo = set(), [w]
    while todo:
        x = todo.pop()
        todo.extend(x.winfo_children())
        out.add(str(x.cget("bg")).lower())
    return out


def test_row_highlight_follows_the_pointer_then_the_last_click():
    """Without a window, so it runs everywhere (CI has no display): which row is tinted, and what is repainted."""
    assert launcher.relight(None, None, None) == (None, {})
    assert launcher.relight(None, "FICO", None) == ("FICO", {"FICO": True})
    assert launcher.relight("FICO", "LTV", None) == ("LTV", {"FICO": False, "LTV": True})   # the old one goes white
    assert launcher.relight("LTV", None, None) == (None, {"LTV": False})                    # nothing clicked
    assert launcher.relight("LTV", None, "FICO") == ("FICO", {"LTV": False, "FICO": True})  # back to the click
    assert launcher.relight("FICO", "LTV", "FICO") == ("LTV", {"FICO": False, "LTV": True}) # pointing wins
    assert launcher.relight("FICO", None, "FICO") == ("FICO", {"FICO": True})


def test_row_highlight_pointing_in_a_row_tints_that_whole_row_and_only_it(tmp_path, monkeypatch):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display to open a window on")
    monkeypatch.setattr(launcher, "PREFS", tmp_path / "launcher.json")
    monkeypatch.setattr(launcher, "open_file", lambda p: None)
    lit, white = house.tk(house.CANVAS).lower(), house.tk(house.PAPER).lower()
    try:
        w = launcher.build(root)
        flow = w["flow"]
        w["extract"].set(str(synth.write_extract(tmp_path, n=1500)))
        root.update()
        w["setup"].invoke()
        for _ in range(1200):
            root.update()
            if not flow.busy:
                break
            time.sleep(0.05)
        assert flow.screen() == "L2"
        names = [r["name"] for r in flow.rows()]
        a, b = names[0], names[3]
        row = lambda n: w[f"row_{n}"]
        assert _colours(row(a)) == {white} and _colours(row(b)) == {white}

        # pointing at the far-right box of row a tints all of row a, its name included
        box_a = next(w[k] for k in (f"box_{a}_{x}" for x in "dcba") if k in w)
        box_a.event_generate("<Enter>")
        root.update()
        assert _colours(row(a)) == {lit}
        # pointing at row b's name moves the tint: row b lit, row a white again
        box_a.event_generate("<Leave>")
        name_b = row(b).winfo_children()[0].winfo_children()[0]
        name_b.event_generate("<Enter>")
        root.update()
        assert _colours(row(b)) == {lit} and _colours(row(a)) == {white}
        name_b.event_generate("<Leave>")
        root.update()
        assert _colours(row(b)) == {white}                  # nothing clicked yet: leaving un-tints it

        # a click keeps its row tinted once the pointer has gone
        w["box_REV_DEBT_c"].event_generate("<Button-1>")    # the split radio, as the window test clicks it
        root.update()
        assert flow.split == "REV_DEBT"
        assert _colours(row("REV_DEBT")) == {lit}
        w["box_REV_DEBT_c"].event_generate("<Leave>")
        root.update()
        assert _colours(row("REV_DEBT")) == {lit}
        # and clicking in another row moves it there
        other = next(n for n in names if n != "REV_DEBT")
        row(other).winfo_children()[0].winfo_children()[0].event_generate("<Button-1>")
        root.update()
        assert _colours(row(other)) == {lit} and _colours(row("REV_DEBT")) == {white}
    finally:
        root.destroy()
