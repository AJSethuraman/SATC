# Double-click to open the Thresholds window (Windows runs .pyw files with
# Python and no console). The window builds the workbook; the bank's judgements
# are then made on its red Settings tab.
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

if __name__ == "__main__":
    from threshold_engine.launcher import main

    main()
