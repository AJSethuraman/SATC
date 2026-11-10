"""A synthetic master database for the demonstration, so the work list has somewhere real to come from.

Everything here is invented. Two lines are wrong on purpose (a facility type the tool's list does not have, and a
preparer nobody has heard of) so that a load shows what a refusal looks like.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

CREDIT = [  # line_id, borrower, security, new money, tester, reviewer, facilities
    ("L-1001", "Harbor Millwork LLC (synthetic)", "Secured", "Yes", "A. Rivera", "D. Patel",
     [("Term loan", 5, 285000, 285000), ("Line of credit", 5, 75000, 22500)]),
    ("L-1002", "Cedar Ridge Dental PC (synthetic)", "Unsecured", "No", "J. Moss", "D. Patel", [("Line of credit", 4, 50000, 12000)]),
    ("L-1003", "Northfield Grain Co-op (synthetic)", "Secured", "Yes", "A. Rivera", "K. Owens",
     [("Equipment loan", 6, 410000, 398000), ("SBA term loan", 6, 150000, 150000)]),
    ("L-1004", "Bay Street Bakery LLC (synthetic)", "Secured", "No", "J. Moss", "D. Patel", [("Bridge loan", 5, 90000, 90000)]),
    ("L-1005", "Larkspur Freight Inc (synthetic)", "Unsecured", "Yes", "Z. Nobody", "D. Patel", [("Term loan", 4, 60000, 41000)]),
    ("L-1006", "Meadow Lane Vet Clinic (synthetic)", "Secured", "No", "A. Rivera", "D. Patel", [("Term loan", 5, 120000, 96000)]),
]
BANK = [("BR-201", "Operating ··4821", "2026-10-31", "A. Rivera", "D. Patel"),
        ("BR-202", "Payroll ··9921", "2026-10-31", "J. Moss", "D. Patel"),
        ("BR-203", "Sweep ··3310", "2026-10-31", "A. Rivera", "K. Owens")]


def write(data_dir):
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    db_path = d / "master.db"
    if db_path.exists():
        db_path.unlink()
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE credit_lines (line_id TEXT PRIMARY KEY, quarter_end TEXT, borrower_name TEXT, security TEXT, new_money TEXT,
                                   scope TEXT, tester TEXT, reviewer TEXT);
        CREATE TABLE credit_facilities (line_id TEXT, facility_type TEXT, risk_rating INTEGER, commitment REAL, outstanding REAL);""")
    for lid, name, sec, nm, tester, rev, facs in CREDIT:
        db.execute("INSERT INTO credit_lines VALUES (?,?,?,?,?,?,?,?)", (lid, "2026-09-30", name, sec, nm, "Annual review (synthetic)", tester, rev))
        for f in facs:
            db.execute("INSERT INTO credit_facilities VALUES (?,?,?,?,?)", (lid, *f))
    db.commit()
    db.close()
    with (d / "bank-accounts.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["line_id", "account", "statement_date", "preparer", "reviewer"])
        w.writerows(BANK)
    (d / "sources.json").write_text(json.dumps({
        "Credit file review": {"kind": "sqlite", "path": "master.db", "lines": "credit_lines", "tables": {"facilities": "credit_facilities"}},
        "Bank reconciliation": {"kind": "csv", "lines": "bank-accounts.csv"},
    }, indent=1))
    return d
