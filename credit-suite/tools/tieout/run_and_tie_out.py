"""Build the deliverable, and tie it out. One command, in that order.

The firm's instruction: "when it's ran, it should be tied out." So this is the
front door for a run. It builds the delivered files, then checks them against
the filings, and **refuses to declare success if anything moved** -- the tie-out
is not a report printed beside the build, it is a gate the build has to pass.

    python tools/tieout/run_and_tie_out.py

Order matters and is the whole point. The tie-out reads the DELIVERED files, so
it has to run after they are written: a check against the intermediate proves
the intermediate, and the last hop is the one the reader depends on.

What runs, and why each is here:

    build_export.py --deep   writes verified-data/ from the verified rows
    prove_delivered_..       every delivered value is the value that was
                             checked -- the hop that was described for weeks
                             and never executed
    tieout_on_run.py         every bank, every series, every field that has a
                             filed line, against the filings themselves, with
                             a planted control
    check_fdic_ratios.py     the FDIC's own arithmetic against our lines
    build_workbook.py        the workbook, LAST, so it is only built from a
                             set that passed

A stage that fails stops the run. A workbook that was never built is obviously
missing; a workbook built from a feed that failed its tie-out is not.
"""
import pathlib
import subprocess
import sys
import time

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
HERE = CS / "tools" / "tieout"
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

STAGES = [
    ("build the delivered files", ["build_export.py", "--deep"]),
    ("the delivered values are the values that were checked",
     ["prove_delivered_is_what_was_checked.py"]),
    ("tie out against the filings", ["tieout_on_run.py"]),
    ("the FDIC's ratios against our own verified lines",
     ["check_fdic_ratios.py"]),
    ("build the workbook", ["build_workbook.py"]),
]

started = time.time()
passed = []
for label, argv in STAGES:
    print("\n=== %s" % label)
    result = subprocess.run([sys.executable, str(HERE / argv[0])] + argv[1:],
                            cwd=str(CS))
    if result.returncode != 0:
        print("\nSTOPPED at: %s (exit %d)" % (label, result.returncode))
        print("%d of %d stages passed. Nothing downstream was built, so there "
              "is no workbook standing on a feed that failed its tie-out."
              % (len(passed), len(STAGES)))
        raise SystemExit(result.returncode)
    passed.append(label)

print("\n%d of %d stages passed in %.0f min."
      % (len(passed), len(STAGES), (time.time() - started) / 60))
print("The feed was built and tied out in the same run.")
