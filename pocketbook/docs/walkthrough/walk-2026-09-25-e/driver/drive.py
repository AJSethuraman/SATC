"""Drive the launcher window the way a person would, and photograph it.

    HOME=... CUBE_MEMORY=... xvfb-run -a -s "-screen 0 800x600x24" python3.12 drive.py OUTPNG EXTRACT ACTION...

ACTION is one of: open (just photograph), browse (open the file dialog, photograph it, pick EXTRACT),
setup, run, openbook, scroll (scroll the message box to the end and photograph). The extract box is set to EXTRACT unless it is '-' (then left as the window remembers it).
After each action the window is photographed as OUTPNG with -<n>-<action> appended.
"""
import subprocess, sys, time
from pathlib import Path

import os
# the build under walk: commit 5ef61df, frozen with `git archive` into scratch (CUBE_SRC) so another session
# editing src/ mid-walk cannot change what is walked
sys.path.insert(0, os.environ["CUBE_SRC"])
import tkinter as tk
from origination_cube import launcher

out, extract, actions = sys.argv[1], sys.argv[2], sys.argv[3:]
root = tk.Tk()
w = launcher.build(root)
if extract != "-" and "browse" not in actions:
    w["extract"].set(extract)


def shot(name):
    for _ in range(5):
        root.update(); time.sleep(0.1)
    # the window alone, as the person sees it (the virtual screen is bigger than the window)
    g = f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_rootx()}+{root.winfo_rooty()}"
    subprocess.run(["import", "-window", "root", "-crop", g, "+repage", f"{out}-{name}.png"], check=False)


def wait_idle():
    for _ in range(1200):
        root.update()
        if str(w["run"].cget("state")) == "normal":
            return
        time.sleep(0.1)


for i, a in enumerate(actions, 1):
    if a == "open":
        shot(f"{i}-opened")
    elif a == "browse":
        def pick():
            shot(f"{i}-file-dialog")
            d = ".__tk_filedialog"
            try:
                root.tk.eval(f"{d}.contents.f2.ent delete 0 end")
                root.tk.eval(f"{d}.contents.f2.ent insert 0 {{{extract}}}")
                shot(f"{i}-file-dialog-typed")
                root.tk.eval(f"{d}.contents.f2.ok invoke")
            except tk.TclError as e:
                print("dialog:", e)
        root.after(800, pick)
        # press the Browse button the way a person would
        from tkinter import ttk
        btn = [c for c in w["setup"].master.master.winfo_children() if isinstance(c, ttk.Button)][0]
        btn.invoke()
        shot(f"{i}-picked")
    elif a == "setup":
        w["setup"].invoke(); wait_idle(); shot(f"{i}-after-set-up")
    elif a == "run":
        w["run"].invoke(); wait_idle(); shot(f"{i}-after-run")
    elif a == "scroll":
        w["status"].see("end"); shot(f"{i}-scrolled")
    elif a == "openbook":
        w["open"].invoke(); shot(f"{i}-after-open")
    print(f"--- {a}:")
    print(w["status"].get("1.0", "end").rstrip())
root.destroy()
