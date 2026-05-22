from __future__ import annotations

from pathlib import Path
import shutil
import time


def make_demo_tree(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    (root / "MachineA" / "docs").mkdir(parents=True)
    (root / "MachineB" / "docs").mkdir(parents=True)
    (root / "archives").mkdir(parents=True)
    (root / "unicode_测试").mkdir(parents=True)

    dup = b"duplicate-content-123\n"
    (root / "MachineA" / "docs" / "same_name.txt").write_bytes(dup)
    (root / "MachineB" / "docs" / "same_name.txt").write_bytes(dup)
    (root / "MachineB" / "docs" / "different_name_copy.txt").write_bytes(dup)

    (root / "MachineA" / "docs" / "report.xlsx").write_text("excel-like")
    (root / "MachineA" / "docs" / "proposal.docx").write_text("word-like")
    (root / "MachineA" / "docs" / "manual.pdf").write_text("pdf-like")
    (root / "MachineA" / "docs" / "image.jpg").write_bytes(b"\xff\xd8\xfffake")
    (root / "archives" / "backup.zip").write_bytes(b"PK\x03\x04fake")
    (root / "unicode_测试" / "noext").write_text("no extension")

    (root / "MachineA" / "docs" / "samefile.txt").write_text("one")
    (root / "MachineB" / "docs" / "samefile.txt").write_text("two")

    old_file = root / "MachineA" / "docs" / "old_log.log"
    old_file.write_text("old")
    old_ts = time.time() - (8 * 365 * 24 * 3600)
    try:
        os_utime = __import__("os").utime
        os_utime(old_file, (old_ts, old_ts))
    except Exception:
        pass

    return root


if __name__ == "__main__":
    target = Path("demo_data")
    out = make_demo_tree(target)
    print(f"Demo data created at: {out.resolve()}")
