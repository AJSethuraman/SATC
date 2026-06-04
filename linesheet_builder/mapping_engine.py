from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import yaml
from .db import now
from .audit import append_audit_event

STANDARD_FIELDS = ['loan_id','borrower_name','product_type','commitment_amount','outstanding_balance','origination_date','maturity_date','risk_rating','officer','collateral_type','guarantor_name','approval_date','approval_authority','financial_statement_date','dscr','ltv','covenant_status','past_due_days','nonaccrual_flag','policy_exception_flag','review_sample_id']

def _norm(s): return ''.join(ch for ch in str(s).lower() if ch.isalnum())
ALIASES = {"loannumber":"loan_id","loanid":"loan_id","borrower":"borrower_name","borrowername":"borrower_name","product":"product_type","balance":"outstanding_balance","commitment":"commitment_amount","nonaccrual":"nonaccrual_flag","policyexception":"policy_exception_flag","sampleid":"review_sample_id","collateral":"collateral_type","guarantor":"guarantor_name"}

def suggest_mappings(incoming_columns, standard_schema=None):
    fields = standard_schema or STANDARD_FIELDS
    suggestions = {}
    for col in incoming_columns:
        n = _norm(col)
        target = ALIASES.get(n)
        if not target:
            for f in fields:
                if n == _norm(f) or n in _norm(f) or _norm(f) in n:
                    target = f; break
        suggestions[col] = target or ""
    return suggestions

def apply_mapping(df: pd.DataFrame, mapping_profile: dict) -> pd.DataFrame:
    mappings = mapping_profile.get("mappings", mapping_profile)
    rows = []
    for _, row in df.iterrows():
        raw = dict(row)
        rec = {field: None for field in STANDARD_FIELDS}
        for incoming, standard in mappings.items():
            if standard and incoming in df.columns:
                rec[standard] = raw.get(incoming)
        rec["raw_payload_json"] = json.dumps(raw, default=str)
        rows.append(rec)
    return pd.DataFrame(rows, columns=STANDARD_FIELDS + ["raw_payload_json"])

def save_mapping_profile(mapping_profile: dict, path: str | Path, conn=None, client_id=None, template_id=None, user="system"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(mapping_profile, sort_keys=False))
    if conn and client_id and template_id:
        conn.execute("DELETE FROM field_mappings WHERE client_id=? AND template_id=?", (client_id, template_id))
        for incoming, standard in mapping_profile.get("mappings", mapping_profile).items():
            conn.execute("INSERT INTO field_mappings (client_id, template_id, incoming_column, standard_field, confirmed_flag, created_at) VALUES (?, ?, ?, ?, 1, ?)", (client_id, template_id, incoming, standard, now()))
        conn.commit(); append_audit_event(conn, user, "mapping_saved", "field_mapping", template_id, engagement_id=None, template_id=template_id)
    return str(path)

def load_mapping_profile(path: str | Path): return yaml.safe_load(Path(path).read_text())

def _sqlite_value(v):
    """Coerce pandas/numpy scalars to native types sqlite3 can bind."""
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)): return None
    if hasattr(v, "isoformat"): return v.isoformat()  # Timestamp/datetime/date
    if hasattr(v, "item"):  # numpy scalar
        try: return v.item()
        except Exception: return v
    return v

def persist_loan_records(conn, engagement_id: int, import_batch_id: int, mapped_df: pd.DataFrame, user="system"):
    ids = []
    cols = STANDARD_FIELDS + ["raw_payload_json"]
    for _, row in mapped_df.iterrows():
        vals = [_sqlite_value(row[c]) for c in cols]
        cur = conn.execute(f"INSERT INTO loan_records (engagement_id, import_batch_id, {','.join(cols)}, validation_status, created_at) VALUES (?, ?, {','.join(['?']*len(cols))}, ?, ?)", [engagement_id, import_batch_id] + vals + ["Needs Review", now()])
        ids.append(int(cur.lastrowid))
    conn.commit(); append_audit_event(conn, user, "loan_records_normalized", "loan_records", import_batch_id, after_value=f"{len(ids)} records", engagement_id=engagement_id)
    return ids
