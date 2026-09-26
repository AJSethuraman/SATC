# Double-click to open the Origination Cube window (Windows runs .pyw files with
# Python and no console). Everything is decided in the workbook; this runs it.
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

# The shuffle test deals its shuffles across the machine's cores (design.md OC-41). Windows starts each worker
# by running this file again under another name, so the window opens only when this file is the program itself.
if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()        # a no-op unless the cube is ever packaged as one .exe
    from origination_cube.launcher import main

    main()
