"""Photograph the launcher window in each state, on a virtual display.

    xvfb-run -a -s "-screen 0 1024x768x24" python3.12 tools/shoot_launcher.py OUT_DIR

Writes a synthetic extract into OUT_DIR, then presses the buttons the way a
person would and saves one PNG per state of the redesign (L1 to L5, with the
Choose tests step in both modes and the page between Next and Run). Needs
tkinter, the cube's add-ons and ImageMagick's `import`. A harness, not a test:
the thing worth checking is what a person sees.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
os.environ["CUBE_MEMORY"] = str(out / "memory.yaml")            # never the machine's own memory

import tkinter as tk  # noqa: E402

from origination_cube import book, deps, launcher, synth  # noqa: E402

launcher.PREFS = out / "launcher.json"
extract = synth.write_extract(out / "extract", n=8000)
root = tk.Tk()
w = launcher.build(root)
flow = w["flow"]


def shot(name):
    for _ in range(5):
        root.update()
        time.sleep(0.1)
    subprocess.run(["import", "-window", str(root.winfo_id()), str(out / f"{name}.png")], check=False)
    subprocess.run(["import", "-window", "root", "-crop", "722x562+0+0", str(out / f"{name}-screen.png")],
                   check=False)


def wait():
    for _ in range(1200):
        root.update()
        if not flow.busy:
            return
        time.sleep(0.1)
    raise SystemExit("the window never finished")


w["extract"].set("")
shot("L1-opened")
w["extract"].set(str(extract))
shot("L1-extract-picked")
w["setup"].invoke()
wait()
shot("L2-choose-tests-bleed")
flow.click("REV_DEBT", "c")                  # split by revolving debt, as in the spec's picture
w["render"]()
shot("L2-choose-tests-bleed-split")
flow.set_mode("new")
for c in ("CHANNEL", "ORIG_BAL", "ASSET_CLASS", "REV_DEBT"):
    flow.click(c, "b")
flow.click("FICO", "c")
w["render"]()
shot("L2-choose-tests-new-variables")
flow.set_mode("bleed")
w["render"]()
w["next"].invoke()
wait()
shot("L2b-answer-in-workbook")
w["run"].invoke()
wait()
shot("L3-answers-needed")
lock = book.book_for(extract).with_name("~$" + book.book_for(extract).name)
lock.write_text("")                          # what Excel leaves beside a workbook it has open
flow.refresh()
w["render"]()
shot("L3-answers-needed-workbook-open")
lock.unlink()
flow.refresh()

from test_book import _answer  # noqa: E402

_answer(book.book_for(extract))
w["render"]()
w["run"].invoke()
wait()
shot("L5-run-finished")

real = deps.missing
deps.missing = lambda: ["numpy"]
flow.gate.missing = ["numpy"]
w["render"]()
shot("L4-add-on-missing")
deps.missing = real
root.destroy()
