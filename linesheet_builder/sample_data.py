from __future__ import annotations
from pathlib import Path
import pandas as pd
from .db import init_db, get_connection, create_or_get_client, create_engagement, seed_template

ROOT=Path(__file__).resolve().parents[1]

def demo_rows():
    return [
        ["L1001","Acme Manufacturing LLC","Commercial Secured",1000000,750000,"2022-01-15","2027-01-15",4,"J. Smith","Equipment","Acme Holdings","2022-01-05","Senior Loan Committee","2025-12-31",1.45,65,"Current",0,False,False,"S001"],
        ["L1002","Baker Retail Group","Commercial Secured",850000,620000,"2021-06-10","2026-06-10",5,"A. Lee","Inventory","Baker Family Trust","2021-05-28","Regional Manager","2025-09-30",1.32,72,"Current",0,False,False,"S002"],
        ["L1003","Cedar Logistics Inc","Commercial Secured",1500000,1200000,"2020-03-20","2028-03-20",6,"J. Smith","Vehicles","Cedar Parent Co","2020-03-01","Senior Loan Committee","2025-12-31",1.25,79,"Current",0,False,False,"S003"],
        ["L1004","Delta Medical Properties","CRE",2200000,1800000,"2019-11-01","2029-11-01",3,"M. Patel","Real Estate","Delta Partners","2019-10-10","Board","2025-12-31",1.55,70,"Current",0,False,False,"S004"],
        ["L1005","Evergreen Farms","Agriculture",640000,510000,"2023-04-01","2028-04-01",4,"A. Lee","Farm Equipment","Evergreen Owners","2023-03-20","Regional Manager","2025-10-31",1.40,60,"Current",0,False,False,"S005"],
        ["L1006","Fountain Hospitality","CRE",3000000,2650000,"2021-08-01","2031-08-01",7,"M. Patel","Hotel Real Estate","Fountain Holdings","2021-07-15","Board","2025-12-31",1.10,83,"Waived",15,False,True,"S006"],
        ["L1007","Granite Tooling Co","Commercial Secured",450000,390000,"2024-02-15","2029-02-15",5,"J. Smith","Equipment","","2024-02-01","Regional Manager","2025-11-30",None,77,"Current",0,False,False,"S007"],
        ["L1008","Harbor Marine LLC","Commercial Secured",700000,690000,"2020-05-01","2026-05-01",8,"A. Lee","Vessels","Harbor Owners","2020-04-22","Senior Loan Committee","2025-12-31",1.22,74,"Current",30,True,False,"S008"],
        ["L1009","","Commercial Secured",900000,820000,"2022-09-01","2027-09-01",4,"M. Patel","Equipment","Ivy Holdings","2022-08-20","Regional Manager","2025-12-31",1.30,68,"Current",0,False,False,"S009"],
        ["L1010","Juniper Foods Inc","Commercial Secured",500000,450000,"2024-01-01","2023-01-01",4,"J. Smith","Inventory","Juniper Owners","2023-12-15","Regional Manager","2025-12-31",1.35,62,"Current",0,False,False,"S010"],
        ["L1001","Kestrel Plastics","Commercial Secured",760000,710000,"2021-02-01","2026-02-01",5,"A. Lee","Equipment","Kestrel Holdings","2021-01-20","Regional Manager","2025-12-31",1.28,69,"Current",0,False,False,"S011"],
    ]

def create_demo_loan_tape(path: str | Path = ROOT / "data" / "demo_loan_tape.xlsx"):
    cols=["Loan Number","Borrower","Product","Commitment","Balance","Origination Date","Maturity Date","Risk Rating","Officer","Collateral","Guarantor","Approval Date","Approval Authority","Financial Statement Date","DSCR","LTV","Covenant Status","Past Due Days","Nonaccrual","Policy Exception","Sample ID"]
    df=pd.DataFrame(demo_rows(), columns=cols); Path(path).parent.mkdir(parents=True, exist_ok=True); df.to_excel(path, index=False); return str(path)

def seed_demo(db_path=ROOT/"data"/"app.db"):
    init_db(db_path); create_demo_loan_tape()
    conn=get_connection(db_path)
    client_id=create_or_get_client(conn,"Demo Bank")
    if not conn.execute("SELECT engagement_id FROM engagements WHERE client_id=?",(client_id,)).fetchone():
        create_engagement(conn, client_id, "Q4 2025", "Commercial Loan Review", "commercial_linesheet_v1", "Demo Reviewer", "Demo QC")
    seed_template(conn,"commercial_linesheet_v1","Commercial Linesheet v1","1.0",str(ROOT/"configs"/"templates"/"commercial_linesheet_v1.yaml"))
    conn.close()

if __name__ == "__main__": seed_demo()
