"""Drake INPUT generator — emits a Drake-ready intake workbook for keying.

Produces a workbook with the ``Clients`` / ``W2s`` sheets and column order the Drake
data-entry keying expects, so the preparer types as little as possible. SATC owns the
workpapers, the data mart, and reconciliation back to Drake's output; the keystrokes
into Drake are done by the preparer (or a separate automation tool not part of this
repo).

IMPORTANT — this intake is the ONE artifact that necessarily carries real identity
data (it is what gets typed into Drake), so it is an EPHEMERAL key-time export
assembled from the identity vault + confirmed source data, written to a transient,
git-ignored location and deleted after keying. It is NOT the durable, de-identified
workpaper workbook and is never committed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook

# Column order matches the Clients / W2s intake schema Drake keying expects.
CLIENT_COLUMNS = [
    "ClientID", "TaxYear", "FilingStatus",
    "TP_First", "TP_Last", "TP_SSN", "TP_DOB", "TP_Occupation",
    "SP_First", "SP_Last", "SP_SSN", "SP_DOB", "SP_Occupation",
    "Address", "City", "State", "ZIP", "Phone", "Email",
]
W2_COLUMNS = [
    "ClientID", "W2_ID", "Employee", "Employer_EIN", "Employer_Name",
    "Employer_Address", "Employer_City", "Employer_State", "Employer_ZIP",
    "Box1", "Box2", "Box3", "Box4", "Box5", "Box6",
    "Box12_Code_1", "Box12_Amount_1", "Box15_State", "Box15_Employer_State_ID",
    "Box16", "Box17",
]


@dataclass(slots=True)
class IntakeW2:
    w2_id: str
    employee: str                      # "taxpayer" | "spouse"
    employer_ein: str
    employer_name: str
    employer_address: str = ""
    employer_city: str = ""
    employer_state: str = ""
    employer_zip: str = ""
    box1: float = 0
    box2: float = 0
    box3: float = 0
    box4: float = 0
    box5: float = 0
    box6: float = 0
    box12_code_1: str = ""
    box12_amount_1: float | str = ""
    box15_state: str = ""
    box15_employer_state_id: str = ""
    box16: float | str = ""
    box17: float | str = ""


@dataclass(slots=True)
class IntakeClient:
    client_id: str
    tax_year: int
    filing_status: str                 # Drake codes: S / MFJ / MFS / HOH / QSS
    tp_first: str
    tp_last: str
    tp_ssn: str
    tp_dob: str                        # ISO YYYY-MM-DD
    tp_occupation: str = ""
    sp_first: str = ""
    sp_last: str = ""
    sp_ssn: str = ""
    sp_dob: str = ""
    sp_occupation: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    phone: str = ""
    email: str = ""
    w2s: list[IntakeW2] = field(default_factory=list)

    def client_row(self) -> list:
        return [
            self.client_id, self.tax_year, self.filing_status,
            self.tp_first, self.tp_last, self.tp_ssn, self.tp_dob, self.tp_occupation,
            self.sp_first, self.sp_last, self.sp_ssn, self.sp_dob, self.sp_occupation,
            self.address, self.city, self.state, self.zip, self.phone, self.email,
        ]

    def w2_rows(self) -> list[list]:
        rows = []
        for w in self.w2s:
            rows.append([
                self.client_id, w.w2_id, w.employee, w.employer_ein, w.employer_name,
                w.employer_address, w.employer_city, w.employer_state, w.employer_zip,
                w.box1, w.box2, w.box3, w.box4, w.box5, w.box6,
                w.box12_code_1, w.box12_amount_1, w.box15_state, w.box15_employer_state_id,
                w.box16, w.box17,
            ])
        return rows


def generate_drake_intake_workbook(out_path: str | Path, clients: list[IntakeClient]) -> Path:
    """Write a Drake-ready intake workbook. Returns the path.

    The output carries identity data and must be treated as transient/secure —
    write it to a git-ignored location and delete it after keying into Drake.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    clients_ws = wb.active
    clients_ws.title = "Clients"
    clients_ws.append(CLIENT_COLUMNS)
    for c in clients:
        clients_ws.append(c.client_row())

    w2_ws = wb.create_sheet("W2s")
    w2_ws.append(W2_COLUMNS)
    for c in clients:
        for row in c.w2_rows():
            w2_ws.append(row)

    wb.save(out)
    return out
