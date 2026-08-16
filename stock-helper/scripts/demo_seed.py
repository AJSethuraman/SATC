"""Seed a synthetic multi-sector universe into a demo database, plus fake price
caches, so the UI can be demonstrated without live SEC/Stooq access.

NOT real data — every company here is invented to exercise the engine across
archetypes (quality compounder, fair, deep value, distressed, manipulator) and
industry buckets. Run with DATA_DIR pointed at a throwaway directory:

    DATA_DIR=demo_data ENABLE_PRICE_DATA=true uv run python scripts/demo_seed.py
"""

from __future__ import annotations

import csv
import math
from datetime import UTC, date, datetime, timedelta

from stock_helper.core.config import get_settings
from stock_helper.industry.sic_buckets import sic_to_bucket
from stock_helper.normalization.xbrl_mapping import CANONICAL_METRICS
from stock_helper.storage.db import get_session, init_db
from stock_helper.storage.models import CompanyFact, Company, SecurityIdentifier

YEARS = [date(y, 12, 31) for y in (2021, 2022, 2023, 2024)]


def _series(start: float, growth: float) -> list[float]:
    return [round(start * (1 + growth) ** i, 1) for i in range(len(YEARS))]


def build_financials(
    *, revenue0: float, rev_growth: float, op_margin: float, ni_margin: float,
    ocf_mult: float, capex_pct: float, assets_mult: float, equity_frac: float,
    debt_frac: float, shares: float, accrual_bloat: float = 0.0,
    receivable_pct: float = 0.10, inventory_pct: float = 0.08,
) -> dict[str, list[tuple[date, float]]]:
    """Turn a few knobs into a full canonical financial history."""
    rev = _series(revenue0, rev_growth)
    op = [round(r * op_margin, 1) for r in rev]
    ni = [round(r * ni_margin, 1) for r in rev]
    # accrual_bloat pushes OCF below NI (earnings-quality stress) in the last year.
    ocf = [round(n * ocf_mult, 1) for n in ni]
    ocf[-1] = round(ocf[-1] * (1 - accrual_bloat), 1)
    capex = [round(r * capex_pct, 1) for r in rev]
    assets = [round(r * assets_mult, 1) for r in rev]
    equity = [round(a * equity_frac, 1) for a in assets]
    debt = [round(a * debt_frac, 1) for a in assets]
    liabilities = [round(a - e, 1) for a, e in zip(assets, equity, strict=False)]
    cogs = [round(r * (1 - op_margin - 0.15), 1) for r in rev]
    gross = [round(r - c, 1) for r, c in zip(rev, cogs, strict=False)]
    da = [round(r * 0.05, 1) for r in rev]
    sga = [round(r * 0.15, 1) for r in rev]
    pretax = [round(o * 0.95, 1) for o in op]
    tax = [round(p * 0.21, 1) for p in pretax]
    recv = [round(r * receivable_pct, 1) for r in rev]
    recv[-1] = round(recv[-1] * (1 + accrual_bloat * 2), 1)  # receivables balloon
    inv = [round(r * inventory_pct, 1) for r in rev]
    cash = [round(a * 0.10, 1) for a in assets]
    ppe = [round(a * 0.35, 1) for a in assets]
    retained = [round(e * 0.7, 1) for e in equity]
    cur_assets = [round(a * 0.4, 1) for a in assets]
    cur_liab = [round(a * 0.2, 1) for a in assets]
    interest = [round(d * 0.05, 1) for d in debt]
    dps = [round(n / shares * 0.3, 2) for n in ni]

    def z(v):
        return list(zip(YEARS, v, strict=False))

    return {
        "revenue": z(rev), "cost_of_revenue": z(cogs), "gross_profit": z(gross),
        "operating_income": z(op), "net_income": z(ni), "pretax_income": z(pretax),
        "tax_expense": z(tax), "operating_cash_flow": z(ocf), "capex": z(capex),
        "depreciation_amortization": z(da), "sga_expense": z(sga),
        "total_assets": z(assets), "total_liabilities": z(liabilities),
        "equity": z(equity), "long_term_debt": z(debt), "cash": z(cash),
        "current_assets": z(cur_assets), "current_liabilities": z(cur_liab),
        "retained_earnings": z(retained), "ppe_net": z(ppe),
        "accounts_receivable": z(recv), "inventory": z(inv),
        "interest_expense": z(interest), "dividends_per_share": z(dps),
        "shares_outstanding": [(YEARS[-1], shares)],
        "diluted_shares": z([shares] * len(YEARS)),
    }


# (ticker, name, sic, archetype-knobs, price_vs_fair) --------------------------
# price_vs_fair < 1 => trades below intrinsic (looks cheap); > 1 => expensive.
UNIVERSE = [
    # Technology (SIC 7372 software, 3674 semis)
    ("NOVA", "Nova Compute", "7372", dict(revenue0=8000, rev_growth=0.18, op_margin=0.30, ni_margin=0.24, ocf_mult=1.2, capex_pct=0.05, assets_mult=1.4, equity_frac=0.65, debt_frac=0.12, shares=500), 1.35),
    ("VRTX", "Vertex Silicon", "3674", dict(revenue0=12000, rev_growth=0.12, op_margin=0.34, ni_margin=0.27, ocf_mult=1.15, capex_pct=0.10, assets_mult=1.6, equity_frac=0.60, debt_frac=0.18, shares=900), 0.72),
    ("BYTE", "Byteworks", "7372", dict(revenue0=3000, rev_growth=0.06, op_margin=0.12, ni_margin=0.07, ocf_mult=0.9, capex_pct=0.06, assets_mult=1.8, equity_frac=0.40, debt_frac=0.35, shares=300), 0.55),
    ("GLOW", "Glow Analytics", "7372", dict(revenue0=1500, rev_growth=0.25, op_margin=0.05, ni_margin=0.02, ocf_mult=0.6, capex_pct=0.08, assets_mult=2.2, equity_frac=0.30, debt_frac=0.45, shares=220, accrual_bloat=0.35), 1.10),
    # Banking (SIC 6022)
    ("FNBK", "First National Bank", "6022", dict(revenue0=6000, rev_growth=0.05, op_margin=0.38, ni_margin=0.28, ocf_mult=1.05, capex_pct=0.02, assets_mult=9.0, equity_frac=0.11, debt_frac=0.10, shares=400), 0.68),
    ("KEYB", "Keystone Bancorp", "6022", dict(revenue0=2500, rev_growth=0.03, op_margin=0.30, ni_margin=0.20, ocf_mult=1.0, capex_pct=0.02, assets_mult=10.0, equity_frac=0.09, debt_frac=0.08, shares=250), 0.85),
    ("TRST", "Trust Financial", "6022", dict(revenue0=9000, rev_growth=0.07, op_margin=0.42, ni_margin=0.31, ocf_mult=1.1, capex_pct=0.02, assets_mult=8.5, equity_frac=0.12, debt_frac=0.11, shares=600), 1.20),
    # Consumer (SIC 5331 retail, 2080 beverage)
    ("SHOP", "ShopRight Stores", "5331", dict(revenue0=20000, rev_growth=0.08, op_margin=0.08, ni_margin=0.05, ocf_mult=1.3, capex_pct=0.04, assets_mult=0.9, equity_frac=0.45, debt_frac=0.30, shares=800), 0.78),
    ("BREW", "Craft Beverage Co", "2080", dict(revenue0=5000, rev_growth=0.10, op_margin=0.22, ni_margin=0.15, ocf_mult=1.1, capex_pct=0.07, assets_mult=1.5, equity_frac=0.55, debt_frac=0.25, shares=350), 1.05),
    ("MART", "MegaMart", "5331", dict(revenue0=45000, rev_growth=0.04, op_margin=0.06, ni_margin=0.035, ocf_mult=1.25, capex_pct=0.03, assets_mult=0.8, equity_frac=0.38, debt_frac=0.40, shares=1200), 0.60),
    # Industrials (SIC 3559 machinery, 3711 autos)
    ("FORG", "Forge Industrial", "3559", dict(revenue0=7000, rev_growth=0.07, op_margin=0.16, ni_margin=0.10, ocf_mult=1.05, capex_pct=0.08, assets_mult=1.3, equity_frac=0.50, debt_frac=0.30, shares=400), 0.82),
    ("MOTR", "Motorline", "3711", dict(revenue0=30000, rev_growth=0.03, op_margin=0.07, ni_margin=0.04, ocf_mult=0.95, capex_pct=0.09, assets_mult=1.1, equity_frac=0.35, debt_frac=0.45, shares=900, accrual_bloat=0.20), 0.90),
    ("AERO", "AeroDynamics", "3559", dict(revenue0=11000, rev_growth=0.09, op_margin=0.19, ni_margin=0.13, ocf_mult=1.1, capex_pct=0.07, assets_mult=1.4, equity_frac=0.48, debt_frac=0.32, shares=500), 1.15),
    # Healthcare (SIC 2834 pharma, 3841 devices)
    ("CURE", "CureGen Pharma", "2834", dict(revenue0=9000, rev_growth=0.14, op_margin=0.32, ni_margin=0.24, ocf_mult=1.15, capex_pct=0.06, assets_mult=1.5, equity_frac=0.62, debt_frac=0.15, shares=450), 0.75),
    ("MEDX", "MedDevice X", "3841", dict(revenue0=4000, rev_growth=0.11, op_margin=0.20, ni_margin=0.14, ocf_mult=1.05, capex_pct=0.06, assets_mult=1.6, equity_frac=0.55, debt_frac=0.22, shares=300), 1.25),
    ("BIOS", "Biosphere Labs", "2834", dict(revenue0=1200, rev_growth=0.30, op_margin=-0.05, ni_margin=-0.10, ocf_mult=0.5, capex_pct=0.10, assets_mult=2.5, equity_frac=0.25, debt_frac=0.50, shares=180), 1.40),
]

# Roughly how the archetype should look — feeds the synthetic price target so the
# screener shows a spread. Keyed by price_vs_fair (already per row).


def seed_prices(settings, ticker: str, last_price: float) -> None:
    """Write ~2 years of synthetic daily closes ending at last_price into cache."""
    settings.price_cache_dir.mkdir(parents=True, exist_ok=True)
    path = settings.price_cache_dir / f"{ticker.lower()}.csv"
    n = 520
    start = date.today() - timedelta(days=int(n * 1.4))
    rows = [("Date", "Open", "High", "Low", "Close", "Volume")]
    d = start
    written = 0
    i = 0
    while written < n:
        if d.weekday() < 5:  # business days only
            # gentle drift toward last_price + a deterministic wobble
            frac = written / n
            base = last_price * (0.7 + 0.3 * frac)
            wobble = 1 + 0.06 * math.sin(written / 9.0)
            close = round(base * wobble, 2)
            rows.append((d.isoformat(), close, close, close, close, 1_000_000))
            written += 1
        d += timedelta(days=1)
        i += 1
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)


def _cik(i: int) -> int:
    return 900000 + i


def insert_company(session, i: int, ticker, name, sic, metrics) -> None:
    now = datetime.now(UTC)
    company = Company(
        cik=_cik(i), name=name, sic=sic, sic_description=f"SIC {sic}",
        industry_bucket=sic_to_bucket(sic), fiscal_year_end="1231",
        source="demo", source_url="demo", retrieved_at=now,
    )
    session.add(company)
    session.flush()
    session.add(SecurityIdentifier(
        company_id=company.id, ticker=ticker, exchange="NASDAQ",
        source="demo", retrieved_at=now,
    ))
    for key, points in metrics.items():
        spec = CANONICAL_METRICS[key]
        taxonomy, tag = spec.candidates[0]
        for pe, value in points:
            session.add(CompanyFact(
                company_id=company.id, metric_key=key, taxonomy=taxonomy, tag=tag,
                unit=spec.unit, value=float(value), period_end=pe, fiscal_year=pe.year,
                fiscal_period="FY", form="10-K", accession=f"{_cik(i)}-{pe.year}",
                filed_date=pe, source="demo", source_url="demo", retrieved_at=now,
            ))


def approx_fair_value_per_share(metrics) -> float:
    """A rough intrinsic anchor so the synthetic price can be set relative to it:
    a crude levered-FCF perpetuity on the latest year."""
    ocf = metrics["operating_cash_flow"][-1][1]
    capex = metrics["capex"][-1][1]
    fcf = max(ocf - capex, 1.0)
    shares = metrics["shares_outstanding"][-1][1]
    return (fcf / 0.09) / shares  # ~9% discount, no growth — just an anchor


def main() -> None:
    settings = get_settings()
    init_db(settings)
    # SPY proxy for beta regressions.
    seed_prices(settings, "SPY", 500.0)
    with get_session(settings) as session:
        for i, (ticker, name, sic, knobs, price_vs_fair) in enumerate(UNIVERSE):
            metrics = build_financials(**knobs)
            insert_company(session, i, ticker, name, sic, metrics)
            fair = approx_fair_value_per_share(metrics)
            seed_prices(settings, ticker, round(fair * price_vs_fair, 2))
        session.commit()
    print(f"Seeded {len(UNIVERSE)} synthetic companies + price caches into "
          f"{settings.data_dir} (DEMO DATA — not real).")


if __name__ == "__main__":
    main()
