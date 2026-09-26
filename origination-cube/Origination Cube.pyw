# Double-click to open the Origination Cube window (Windows runs .pyw files with
# Python and no console). Everything is decided in the workbook; this runs it.
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))
from origination_cube.launcher import main  # noqa: E402

main()
