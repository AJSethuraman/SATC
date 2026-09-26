"""Photograph the launcher window in each state, on a virtual display.

    xvfb-run -a python3.12 tools/shoot_launcher.py OUT_DIR EXTRACT

Presses the buttons the way a person would and saves one PNG per state:
opened, after Set up, after Run with nothing answered. Needs tkinter and
ImageMagick's `import`. A harness, not a test: the thing worth checking is
what a person sees.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import tkinter as tk  # noqa: E402

from origination_cube import launcher  # noqa: E402

out, extract = Path(sys.argv[1]), sys.argv[2]
out.mkdir(parents=True, exist_ok=True)
root = tk.Tk()
w = launcher.build(root)
w["extract"].set(extract)


def shot(name):
    root.update()
    time.sleep(0.3)
    subprocess.run(["import", "-window", root.winfo_id() and str(root.winfo_id()), str(out / f"{name}.png")],
                   check=False)
    subprocess.run(["import", "-window", "root", str(out / f"{name}-screen.png")], check=False)


def wait_idle():
    for _ in range(600):
        root.update()
        if str(w["run"].cget("state")) == "normal":
            return
        time.sleep(0.1)


shot("launcher-01-opened")
w["setup"].invoke()
wait_idle()
shot("launcher-02-after-set-up")
w["run"].invoke()
wait_idle()
shot("launcher-03-run-before-answering")
root.destroy()
