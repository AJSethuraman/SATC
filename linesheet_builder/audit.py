from __future__ import annotations
import pandas as pd
from pathlib import Path
from .db import now

def append_audit_event(conn, user: str, action_type: str, entity_type: str, entity_id=None, before_value=None, after_value=None, reason=None, engagement_id=None, review_case_id=None, loan_id=None, template_id=None, template_version=None):
    conn.execute("""INSERT INTO audit_log (timestamp, user, action_type, entity_type, entity_id, before_value, after_value, reason, engagement_id, review_case_id, loan_id, template_id, template_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (now(), user, action_type, entity_type, str(entity_id) if entity_id is not None else None, before_value, after_value, reason, engagement_id, review_case_id, loan_id, template_id, template_version))
    conn.commit()

def export_audit_log(conn, output_path: str | Path):
    df = pd.read_sql_query("SELECT * FROM audit_log ORDER BY audit_id", conn)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return str(output_path)
