from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "app.db"

SCHEMA = [
"""CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, active_flag INTEGER DEFAULT 1)""",
"""CREATE TABLE IF NOT EXISTS engagements (engagement_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, review_period TEXT, review_type TEXT, template_id TEXT, reviewer_name TEXT, qc_reviewer_name TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS templates (template_id TEXT PRIMARY KEY, template_name TEXT, version TEXT, yaml_path TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS import_batches (import_batch_id INTEGER PRIMARY KEY AUTOINCREMENT, engagement_id INTEGER, original_filename TEXT, raw_file_path TEXT, row_count INTEGER, column_count INTEGER, import_status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS field_mappings (mapping_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, template_id TEXT, incoming_column TEXT, standard_field TEXT, confirmed_flag INTEGER, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS loan_records (loan_record_id INTEGER PRIMARY KEY AUTOINCREMENT, engagement_id INTEGER, import_batch_id INTEGER, loan_id TEXT, borrower_name TEXT, product_type TEXT, commitment_amount REAL, outstanding_balance REAL, origination_date TEXT, maturity_date TEXT, risk_rating TEXT, officer TEXT, collateral_type TEXT, guarantor_name TEXT, approval_date TEXT, approval_authority TEXT, financial_statement_date TEXT, dscr REAL, ltv REAL, covenant_status TEXT, past_due_days INTEGER, nonaccrual_flag TEXT, policy_exception_flag TEXT, review_sample_id TEXT, raw_payload_json TEXT, validation_status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS validation_issues (issue_id INTEGER PRIMARY KEY AUTOINCREMENT, loan_record_id INTEGER, severity TEXT, status TEXT, issue_code TEXT, issue_message TEXT, field_name TEXT, created_at TEXT, resolved_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS review_cases (review_case_id INTEGER PRIMARY KEY AUTOINCREMENT, engagement_id INTEGER, loan_record_id INTEGER, status TEXT, assigned_reviewer TEXT, qc_reviewer TEXT, started_at TEXT, submitted_at TEXT, approved_at TEXT, finalized_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS review_answers (answer_id INTEGER PRIMARY KEY AUTOINCREMENT, review_case_id INTEGER, question_id TEXT, section_id TEXT, answer_value TEXT, source_field TEXT, source_value TEXT, answer_status TEXT, severity TEXT, reviewer_comment TEXT, evidence_required INTEGER, evidence_status TEXT, answered_by TEXT, answered_at TEXT, updated_at TEXT, UNIQUE(review_case_id, question_id))""",
"""CREATE TABLE IF NOT EXISTS exceptions (exception_id INTEGER PRIMARY KEY AUTOINCREMENT, review_case_id INTEGER, loan_record_id INTEGER, question_id TEXT, section_id TEXT, issue_text TEXT, severity TEXT, status TEXT, reviewer_comment TEXT, evidence_status TEXT, created_at TEXT, updated_at TEXT, UNIQUE(review_case_id, question_id))""",
"""CREATE TABLE IF NOT EXISTS evidence_items (evidence_id INTEGER PRIMARY KEY AUTOINCREMENT, review_case_id INTEGER, question_id TEXT, evidence_name TEXT, evidence_status TEXT, evidence_note TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS exports (export_id INTEGER PRIMARY KEY AUTOINCREMENT, engagement_id INTEGER, review_case_id INTEGER, export_type TEXT, file_path TEXT, generated_by TEXT, generated_at TEXT, export_status TEXT)""",
"""CREATE TABLE IF NOT EXISTS audit_log (audit_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, action_type TEXT, entity_type TEXT, entity_id TEXT, before_value TEXT, after_value TEXT, reason TEXT, engagement_id INTEGER, review_case_id INTEGER, loan_id TEXT, template_id TEXT, template_version TEXT)""",
"""CREATE TABLE IF NOT EXISTS dti_inputs (dti_id INTEGER PRIMARY KEY AUTOINCREMENT, review_case_id INTEGER, line_key TEXT, amount REAL, note TEXT, updated_at TEXT, UNIQUE(review_case_id, line_key))""",
"""CREATE TABLE IF NOT EXISTS cash_flow_inputs (cf_id INTEGER PRIMARY KEY AUTOINCREMENT, review_case_id INTEGER, line_key TEXT, period1 REAL, period2 REAL, basis TEXT, method TEXT, note TEXT, updated_at TEXT, UNIQUE(review_case_id, line_key))""",
]

def now() -> str: return datetime.utcnow().isoformat(timespec="seconds")

def get_connection(db_path: str | Path = DEFAULT_DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str | Path = DEFAULT_DB_PATH):
    conn = get_connection(db_path)
    try:
        for stmt in SCHEMA: conn.execute(stmt)
        conn.commit()
    finally: conn.close()

def seed_template(conn, template_id: str, template_name: str, version: str, yaml_path: str):
    conn.execute("INSERT OR REPLACE INTO templates VALUES (?, ?, ?, ?, ?)", (template_id, template_name, version, yaml_path, now()))
    conn.commit()

def create_or_get_client(conn, client_name: str) -> int:
    row = conn.execute("SELECT client_id FROM clients WHERE client_name=?", (client_name,)).fetchone()
    if row: return int(row[0])
    cur = conn.execute("INSERT INTO clients (client_name, created_at, active_flag) VALUES (?, ?, 1)", (client_name, now()))
    conn.commit(); return int(cur.lastrowid)

def create_engagement(conn, client_id: int, review_period: str, review_type: str, template_id: str, reviewer_name: str, qc_reviewer_name: str) -> int:
    cur = conn.execute("INSERT INTO engagements (client_id, review_period, review_type, template_id, reviewer_name, qc_reviewer_name, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (client_id, review_period, review_type, template_id, reviewer_name, qc_reviewer_name, "Active", now()))
    conn.commit(); return int(cur.lastrowid)
