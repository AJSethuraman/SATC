"""Shared valuation contracts: assumptions and the top-level composed result.

The per-engine result dataclasses (DcfResult, EnterpriseValue, Multiple,
FactorResult, QualityFactors) live in their owning modules. This module holds
only what several engines share, plus ValuationResult which composes them.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

# FCF basis (which cash flow the DCF discounts). Levered/owner-earnings flows
# already belong to EQUITY holders -> discount at cost of equity, NO net-debt
# subtraction. Only UNLEVERED (FCFF) discounts at WACC then subtracts net debt.
LEVERED = "levered"  # OCF - capex (interest already deducted in OCF) -> equity
OWNER_EARNINGS = "owner_earnings"  # NI + D&A + SBC - maintenance capex -> equity
UNLEVERED = "unlevered"  # FCFF; discount at WACC, subtract net debt (deferred)

# Terminal value method.
GORDON = "gordon"  # perpetuity: FCF_{n+1} / (r - g_terminal)
EXIT_MULTIPLE = "exit_multiple"  # terminal EV/EBITDA * terminal EBITDA

EQUITY_BASES = (LEVERED, OWNER_EARNINGS)


@dataclass(frozen=True)
class Assumptions:
    """Editable DCF assumptions. Defaults are deliberate, conservative, and
    labeled — the discount rate is a flat cost-of-equity assumption (no CAPM/beta
    is derivable here), so intrinsic value is a scenario, not a target."""

    discount_rate: float = 0.09  # cost of equity for LEVERED/OWNER_EARNINGS bases
    terminal_growth: float = 0.025  # long-run growth; must be < discount_rate
    stage1_years: int = 5
    fcf_basis: str = LEVERED
    terminal_method: str = GORDON
    exit_multiple: float | None = None  # for EXIT_MULTIPLE terminal
    growth_rate: float | None = None  # explicit stage-1 growth; None -> estimate
    fade_to_terminal: bool = False  # linearly fade stage-1 growth toward terminal
    mid_year_convention: bool = False


@dataclass
class ValuationResult:
    """Everything the report/UI/extras need for one company. Any sub-result may
    be None when its inputs are unavailable — the surface reports that honestly
    and never fabricates a number."""

    ticker: str
    bucket: str
    as_of: date | None
    price: float | None
    price_date: date | None

    dcf: Any | None = None  # DcfResult
    reverse: Any | None = None  # ReverseDcfResult
    sensitivity: Any | None = None  # SensitivityTable
    enterprise_value: Any | None = None  # EnterpriseValue
    multiples: dict[str, Any] = field(default_factory=dict)  # key -> Multiple
    peer_relative: dict[str, Any] = field(default_factory=dict)
    self_history: dict[str, Any] = field(default_factory=dict)
    quality: Any | None = None  # QualityFactors
    beneish: Any | None = None  # BeneishResult
    stress: Any | None = None  # StressReport

    fair_value_per_share: float | None = None
    margin_of_safety: float | None = None  # (fair - price)/fair; None if no price
    implied_growth: float | None = None  # reverse-DCF headline
    metric_set: str = ""  # "industrial" | "financial"
    flags: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    engine_version: str = ""
