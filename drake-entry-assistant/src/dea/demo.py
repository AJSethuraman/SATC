"""Demo/sample workbook generation helpers."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from dea.excel_loader import REQUIRED_CLIENT_COLUMNS, REQUIRED_W2_COLUMNS


def _id_from_parts(*parts: str) -> str:
    return "".join(parts)


def create_sample_workbook(path: str | Path) -> Path:
    """Create a deterministic synthetic intake workbook for local demos."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    tp_ssn = _id_from_parts("123", "45", "6789")
    sp_ssn = _id_from_parts("111", "22", "3333")
    employer_ein = _id_from_parts("12", "345", "6789")

    wb = Workbook()
    clients = wb.active
    clients.title = "Clients"
    clients.append(REQUIRED_CLIENT_COLUMNS)
    clients.append(
        [
            "DEMO-001",
            2025,
            "MFJ",
            "Avery",
            "Monroe",
            tp_ssn,
            "1988-04-14",
            "Engineer",
            "Casey",
            "Monroe",
            sp_ssn,
            "1990-11-30",
            "Teacher",
            "100 Demo St",
            "Springfield",
            "IL",
            "62701",
            "",
            "",
        ]
    )

    w2s = wb.create_sheet("W2s")
    w2s.append(REQUIRED_W2_COLUMNS)
    w2s.append(
        [
            "DEMO-001",
            "W2-001",
            "tp",
            employer_ein,
            "Demo Manufacturing LLC",
            "500 Market Ave",
            "Springfield",
            "IL",
            "62702",
            "72000",
            "8500",
            "72000",
            "4464",
            "72000",
            "1044",
            "D",
            "3000",
            "IL",
            "IL-ID",
            "72000",
            "3200",
        ]
    )

    wb.save(output)
    return output
