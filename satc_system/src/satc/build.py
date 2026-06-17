"""Workbook build orchestrator.

Assembles the SATC workbook from its parts: a branded cover, the dated tax-law
reference sheets (which expose the crosswalk parameters as cells), and the
config-driven line sheets prefilled with a client's confirmed values. Output is a
single .xlsx; run ``scripts/recalc.py`` afterward to evaluate formulas and confirm
zero errors.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from satc.config import load_line_sheet, templatize
from satc.crosswalk import CrosswalkLibrary
from satc.fixtures import synthetic_1040_values, synthetic_identities
from satc.workbook.cover import build_cover
from satc.workbook.line_sheet import BuildContext, LineSheetBuilder
from satc.workbook.reference import build_reference_sheet

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "build" / "SATC_Workbook.xlsx"


def _reference_sheets(wb: Workbook, lib: CrosswalkLibrary, tax_year: int,
                      jurisdictions: list[str]) -> dict[str, str]:
    """Build one reference sheet per jurisdiction; return the merged cell registry."""
    registry: dict[str, str] = {}
    for juris in jurisdictions:
        xw = lib.resolve_or_none(tax_year, juris)
        if xw is None:
            continue
        ws = wb.create_sheet(f"Tax Law {juris} {tax_year}")
        registry.update(build_reference_sheet(ws, xw))
    return registry


def build_demo_workbook(out_path: str | Path = DEFAULT_OUT, tax_year: int = 2024) -> Path:
    """Build the demo workbook for synthetic client SATC-001000 (1040, OH)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lib = CrosswalkLibrary().load()
    identities = {r.client_id: r for r in synthetic_identities()}
    client = identities["SATC-001000"].to_public()
    state = client.home_state or "OH"

    wb = Workbook()
    wb.remove(wb.active)

    cover = wb.create_sheet("Cover")
    registry = _reference_sheets(wb, lib, tax_year, ["US", state])

    config = templatize(load_line_sheet("1040"), {"STATE": state})
    config["meta"]["subtitle"] = (
        f"Client {client.client_id} ({client.entity_type})  ·  TY{tax_year}  ·  Federal + {state}"
        "   —   Drake is the system of record."
    )
    ctx = BuildContext(
        xw_registry=registry,
        values=synthetic_1040_values(tax_year),
        default_jurisdiction="US",
    )
    ls = wb.create_sheet(f"1040 — {client.client_id}")
    LineSheetBuilder(ls, config, ctx).build()

    contents = [
        (f"Tax Law US {tax_year}", "Federal parameters in force, with citations"),
        (f"Tax Law {state} {tax_year}", f"{state} parameters in force, with citations"),
        (f"1040 — {client.client_id}", "Individual workpaper: intake, schedules, state, §8867, reconciliation"),
    ]
    build_cover(cover, tax_year=tax_year, contents=contents)

    wb.save(out)
    return out


def main() -> None:
    out = build_demo_workbook()
    print(f"Built {out}")


if __name__ == "__main__":
    main()
