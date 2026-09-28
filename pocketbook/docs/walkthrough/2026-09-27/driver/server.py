"""The launcher window, held open on a virtual display, taking one action at a time.

    xvfb-run -a -s "-screen 0 1000x760x24" venv/bin/python server.py

It builds the real window (launcher.build, from the frozen build in wc/) exactly as PocketBook.pyw does, then
every 200 ms looks for drv/cmd.py. A command is a few lines of Python run against the open window; its
printed output goes to drv/out.txt and drv/done appears. `send.py` is the other end.
Helpers in the command's namespace:
    shot(name)            photograph the window (walk27/shots/NAME.png)
    press(key)            click a button by its name in the window's widgets (Button-1, as a mouse does)
    tick(col, which)      click the box on a column's row in Choose tests (which: a, b or c)
    words()               every piece of text on the page, top to bottom
    busy()                True while the window says it is working
    later(fn)             run fn from the event loop (for anything that opens a dialog)
"""
import io
import os
import sys
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path

W = Path(__file__).resolve().parents[1]
os.environ["HOME"] = str(W / "home")
os.environ["POCKETBOOK_MEMORY"] = str(W / "home" / "memory.yaml")
sys.path.insert(0, str(W / "wc/pocketbook/src"))
DRV = W / "drv"
SHOTS = W / "shots"

import tkinter as tk  # noqa: E402

from pocketbook import launcher  # noqa: E402

# the shuffle test starts worker processes by importing this file again (as PocketBook.pyw guards against):
# the window is only built when this file is the program itself
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    root = tk.Tk()
    w = launcher.build(root)
    flow = w["flow"]
else:
    root = w = flow = None
NS = {"w": w, "flow": flow, "root": root, "launcher": launcher, "W": W, "tk": tk}


def settle(n=6):
    for _ in range(n):
        root.update()
        time.sleep(0.08)


def shot(name):
    settle()
    import subprocess
    g = f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_rootx()}+{root.winfo_rooty()}"
    subprocess.run(["import", "-window", "root", "-crop", g, "+repage", str(SHOTS / f"{name}.png")], check=False)
    print("shot", name)


def shot_screen(name):
    settle()
    import subprocess
    subprocess.run(["import", "-window", "root", str(SHOTS / f"{name}.png")], check=False)
    print("screen", name)


def press(key):
    b = w[key]
    print("press", key, "state", b.cget("state"), "text", b.cget("text") if hasattr(b, "cget") else "")
    b.event_generate("<Button-1>", x=5, y=5)
    settle(3)


def tick(col, which):
    b = w[f"box_{col}_{which}"]
    b.event_generate("<Button-1>", x=8, y=8)
    settle(3)


def words(widget=None):
    out = []

    def walk(x):
        try:
            t = x.cget("text")
            if t:
                out.append(str(t))
        except Exception:
            pass
        if isinstance(x, tk.Canvas):
            for i in x.find_all():
                if x.type(i) == "text":
                    t = x.itemcget(i, "text")
                    if t:
                        out.append(t)
        for c in x.winfo_children():
            walk(c)
    walk(widget or root)
    return out


def busy():
    return bool(flow.busy)


def later(fn, ms=50):
    root.after(ms, fn)


NS.update(shot_screen=shot_screen, shot=shot, press=press, tick=tick, words=words, busy=busy, later=later, settle=settle)


def poll():
    cmd = DRV / "cmd.py"
    if cmd.exists() and not (DRV / "done").exists():
        src = cmd.read_text()
        cmd.unlink()
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(src, NS)
        except Exception:
            buf.write(traceback.format_exc())
        (DRV / "out.txt").write_text(buf.getvalue())
        (DRV / "done").write_text("")
    root.after(200, poll)


if __name__ == "__main__":
    root.after(500, poll)
    root.mainloop()
