import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from queue import Queue
import threading

from openpyxl import load_workbook

from create_demo_data import make_demo_tree
from scanner import ScanConfig, run_scan


def _collect_events(q: Queue) -> list[dict]:
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


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
    summary = wb["Summary"]

    headers = [c.value for c in review[1]]
    assert headers[0] == "Client Decision"
    assert "Duplicate Group ID" in headers
    groups = [row[0].value for row in dup.iter_rows(min_row=2) if row[0].value]
    assert groups

    rows = list(review.iter_rows(min_row=2, values_only=True))
    by_name = [r for r in rows if r[6] == "samefile.txt"]
    assert len(by_name) == 2
    assert all((r[2] or "") == "" for r in by_name)

    metrics = {r[0].value: r[1].value for r in summary.iter_rows(min_row=2, max_col=2) if r[0].value}
    assert metrics["Scan Status"] == "Completed"


def test_extension_filters(tmp_path: Path) -> None:
    root = make_demo_tree(tmp_path / "demo")
    out_inc = tmp_path / "inc.xlsx"
    run_scan(ScanConfig(root_path=root, output_file=out_inc, filter_mode="include", extension_text="txt", detect_duplicates=False), Queue())
    exts = {r[7].value for r in load_workbook(out_inc)["Review"].iter_rows(min_row=2)}
    assert exts == {".txt"}

    out_exc = tmp_path / "exc.xlsx"
    run_scan(ScanConfig(root_path=root, output_file=out_exc, filter_mode="exclude", extension_text="txt", detect_duplicates=False), Queue())
    exts2 = {r[7].value for r in load_workbook(out_exc)["Review"].iter_rows(min_row=2)}
    assert ".txt" not in exts2


def test_empty_scan_exports_workbook_and_progress(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    out = tmp_path / "empty.xlsx"
    q = Queue()
    run_scan(ScanConfig(root_path=root, output_file=out, filter_mode="all", extension_text="", detect_duplicates=True), q)
    assert out.exists()
    events = _collect_events(q)
    assert any(e.get("type") == "progress" and e.get("phase") == "Metadata Scan" for e in events)


def test_hash_progress_and_cancellation(tmp_path: Path) -> None:
    root = make_demo_tree(tmp_path / "demo")
    out = tmp_path / "cancel.xlsx"
    cancel = threading.Event()
    cancel.set()
    q = Queue()
    run_scan(ScanConfig(root_path=root, output_file=out, filter_mode="all", extension_text="", detect_duplicates=True), q, cancel)
    assert out.exists()
    wb = load_workbook(out)
    summary = wb["Summary"]
    metrics = {r[0].value: r[1].value for r in summary.iter_rows(min_row=2, max_col=2) if r[0].value}
    assert metrics["Scan Status"] == "Cancelled"

    events = _collect_events(q)
    assert any(e.get("type") == "progress" and e.get("phase") == "Metadata Scan" for e in events)
    assert any(e.get("type") == "done" for e in events)


def test_hashing_progress_emitted(tmp_path: Path) -> None:
    root = make_demo_tree(tmp_path / "demo")
    out = tmp_path / "hash.xlsx"
    q = Queue()
    run_scan(ScanConfig(root_path=root, output_file=out, filter_mode="all", extension_text="", detect_duplicates=True), q)
    events = _collect_events(q)
    assert any(e.get("type") == "progress" and e.get("phase") == "Hashing" for e in events)
