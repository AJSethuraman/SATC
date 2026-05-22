import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from queue import Queue

from openpyxl import load_workbook

from create_demo_data import make_demo_tree
from scanner import ScanConfig, run_scan



def test_end_to_end(tmp_path: Path) -> None:
    root = make_demo_tree(tmp_path / "demo")
    out = tmp_path / "report.xlsx"
    q = Queue()
    cfg = ScanConfig(root_path=root, output_file=out, filter_mode="all", extension_text="", detect_duplicates=True)
    run_scan(cfg, q)
    assert out.exists()

    wb = load_workbook(out)
    assert wb.sheetnames == ["Review", "Duplicate Groups", "Summary", "Errors"]
    review = wb["Review"]
    dup = wb["Duplicate Groups"]

    headers = [c.value for c in review[1]]
    assert headers[0] == "Client Decision"
    assert "Duplicate Group ID" in headers

    groups = [row[0].value for row in dup.iter_rows(min_row=2) if row[0].value]
    assert groups, "Expected at least one duplicate group"

    rows = list(review.iter_rows(min_row=2, values_only=True))
    by_name = [r for r in rows if r[6] == "samefile.txt"]
    assert len(by_name) == 2
    assert all((r[2] or "") == "" for r in by_name)


def test_extension_filters(tmp_path: Path) -> None:
    root = make_demo_tree(tmp_path / "demo")
    out_inc = tmp_path / "inc.xlsx"
    run_scan(ScanConfig(root_path=root, output_file=out_inc, filter_mode="include", extension_text="txt", detect_duplicates=False), Queue())
    wb = load_workbook(out_inc)
    exts = {r[7].value for r in wb["Review"].iter_rows(min_row=2)}
    assert exts == {".txt"}

    out_exc = tmp_path / "exc.xlsx"
    run_scan(ScanConfig(root_path=root, output_file=out_exc, filter_mode="exclude", extension_text="txt", detect_duplicates=False), Queue())
    wb2 = load_workbook(out_exc)
    exts2 = {r[7].value for r in wb2["Review"].iter_rows(min_row=2)}
    assert ".txt" not in exts2