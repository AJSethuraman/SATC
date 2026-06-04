"""Loader for year- and status-specific federal tax constants.

Tax tables live as JSON files under ``twe/data/<year>.json`` so a new year can
be added by dropping in a file — no code changes required. The loader exposes a
typed :class:`TaxTables` view and resolves the appropriate year (falling back to
the latest available table with a note when the requested year is missing).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from importlib import resources
from typing import Any


class TaxDataError(Exception):
    """Raised when tax tables cannot be loaded for the requested year."""


@dataclass(slots=True)
class Bracket:
    rate: Decimal
    up_to: Decimal | None  # None = no upper bound (top bracket)


@dataclass(slots=True)
class TaxTables:
    tax_year: int
    raw: dict[str, Any]

    # -- deductions -----------------------------------------------------
    def standard_deduction(self, filing_status: str) -> Decimal:
        return _dec(self.raw["standard_deduction"][filing_status])

    def extra_standard_deduction(self, filing_status: str) -> Decimal:
        return _dec(self.raw["additional_standard_deduction_aged_or_blind"][filing_status])

    # -- ordinary income brackets --------------------------------------
    def ordinary_brackets(self, filing_status: str) -> list[Bracket]:
        return [
            Bracket(rate=_dec(b["rate"]), up_to=_opt(b["up_to"]))
            for b in self.raw["ordinary_brackets"][filing_status]
        ]

    # -- preferential capital-gains thresholds -------------------------
    def capital_gains_thresholds(self, filing_status: str) -> tuple[Decimal, Decimal]:
        cg = self.raw["capital_gains_brackets"][filing_status]
        return _dec(cg["zero_rate_up_to"]), _dec(cg["fifteen_rate_up_to"])

    # -- payroll / surtaxes --------------------------------------------
    @property
    def ss_wage_base(self) -> Decimal:
        return _dec(self.raw["social_security"]["wage_base"])

    @property
    def ss_employee_rate(self) -> Decimal:
        return _dec(self.raw["social_security"]["employee_rate"])

    @property
    def medicare_base_rate(self) -> Decimal:
        return _dec(self.raw["medicare"]["base_rate"])

    @property
    def additional_medicare_rate(self) -> Decimal:
        return _dec(self.raw["medicare"]["additional_rate"])

    def additional_medicare_threshold(self, filing_status: str) -> Decimal:
        return _dec(self.raw["medicare"]["additional_threshold"][filing_status])

    @property
    def niit_rate(self) -> Decimal:
        return _dec(self.raw["net_investment_income_tax"]["rate"])

    def niit_threshold(self, filing_status: str) -> Decimal:
        return _dec(self.raw["net_investment_income_tax"]["threshold"][filing_status])

    # -- self-employment ------------------------------------------------
    @property
    def se_net_earnings_factor(self) -> Decimal:
        return _dec(self.raw["self_employment"]["net_earnings_factor"])

    @property
    def se_social_security_rate(self) -> Decimal:
        return _dec(self.raw["self_employment"]["social_security_rate"])

    @property
    def se_medicare_rate(self) -> Decimal:
        return _dec(self.raw["self_employment"]["medicare_rate"])

    # -- safe harbor ----------------------------------------------------
    def safe_harbor(self) -> dict[str, Any]:
        return self.raw["safe_harbor"]

    @property
    def source(self) -> str:
        return self.raw.get("source", "")


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _opt(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def available_years() -> list[int]:
    """Return tax years that ship with the package, ascending."""

    years: list[int] = []
    for entry in resources.files("twe.data").iterdir():
        name = entry.name
        if name.endswith(".json"):
            stem = name[:-5]
            if stem.isdigit():
                years.append(int(stem))
    return sorted(years)


def load_tax_tables(tax_year: int | None) -> tuple[TaxTables, list[str]]:
    """Load tables for ``tax_year``.

    Returns the tables and a list of advisory notes (e.g. when a fallback year
    is used). When ``tax_year`` is ``None`` the latest available year is used.
    """

    years = available_years()
    if not years:
        raise TaxDataError("no tax tables are bundled with this package")

    notes: list[str] = []
    if tax_year is None:
        resolved = years[-1]
        notes.append(f"No tax year specified; using latest available tables ({resolved}).")
    elif tax_year in years:
        resolved = tax_year
    else:
        resolved = years[-1]
        notes.append(
            f"Tax tables for {tax_year} are not bundled; using {resolved} tables instead. "
            f"Available years: {years}."
        )

    raw = _read_year(resolved)
    return TaxTables(tax_year=resolved, raw=raw), notes


def _read_year(year: int) -> dict[str, Any]:
    try:
        text = resources.files("twe.data").joinpath(f"{year}.json").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:  # pragma: no cover - defensive
        raise TaxDataError(f"could not read tax tables for {year}: {exc}") from exc
    return json.loads(text)
