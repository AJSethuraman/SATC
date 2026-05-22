from __future__ import annotations
import shutil
from pathlib import Path
import pandas as pd
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]

def load_loan_tape(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() in [".xlsx", ".xls"]: return pd.read_excel(path)
    if path.suffix.lower() == ".csv": return pd.read_csv(path)
    raise ValueError(f"Unsupported loan tape type: {path.suffix}")

def save_raw_import(uploaded_file, raw_dir: str | Path = ROOT / "data" / "raw_imports") -> str:
    raw_dir = Path(raw_dir); raw_dir.mkdir(parents=True, exist_ok=True)
    name = getattr(uploaded_file, "name", None) or Path(str(uploaded_file)).name
    dest = raw_dir / f"{now().replace(':','').replace('-','')}_{name}"
    if hasattr(uploaded_file, "getbuffer"):
        dest.write_bytes(uploaded_file.getbuffer())
    else:
        shutil.copy2(uploaded_file, dest)
    return str(dest)

def create_import_batch(conn, engagement_id: int, original_filename: str, raw_file_path: str, df: pd.DataFrame, user: str = "system") -> int:
    cur = conn.execute("INSERT INTO import_batches (engagement_id, original_filename, raw_file_path, row_count, column_count, import_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (engagement_id, original_filename, raw_file_path, len(df), len(df.columns), "Imported", now()))
    batch_id = int(cur.lastrowid); conn.commit()
    append_audit_event(conn, user, "import_created", "import_batch", batch_id, after_value=f"{len(df)} rows/{len(df.columns)} cols", engagement_id=engagement_id)
    return batch_id

def import_preview(file_path: str | Path, rows: int = 10):
    df = load_loan_tape(file_path)
    return {"preview": df.head(rows), "rows": len(df), "columns": list(df.columns)}
