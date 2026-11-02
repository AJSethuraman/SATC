"""Build the demonstration workbooks: each pack in packs/, once blank and once filled with its example.

    python3 workpaper-studio/excel/build_tool_workbook.py
    python3 workpaper-studio/excel/check_tool_workbooks.py

The generator itself lives in the application (src/workpaper_studio/workbook.py); a case exported from the app and these
demonstrations come from the same code.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from workpaper_studio.workbook import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
