"""Enterprise value and market-multiples valuation (pure calculation core).

Research flags, NOT price targets or advice. Every multiple falls out of an
explicit numerator / denominator pair carried with full provenance (the values
used, the source XBRL tags, the filing accessions, and the period ends), so any
number here is fully auditable.

Money-critical invariant enforced throughout: a multiple is only defined when it
would be *positive*. Any non-positive denominator — and, for EV multiples, a
non-positive enterprise value in the numerator — yields ``value=None`` with an
``undefined_reason`` instead of a misleading negative "cheap" figure. A negative
P/E or EV/EBIT read as cheapness is a real-money error, so we never emit one.

Yields (earnings yield, FCF yield, dividend yield) are the one place a negative
numerator is *kept*: a negative earnings yield is meaningful and honest, so we
surface it with a ``caveat`` rather than hiding it — but the denominator still
must be positive.

EBIT is pinned to ``operating_income``. This mirrors the EBITDA definition in
features/metrics.py (``operating_income + depreciation_amortization``), so
EV/EBIT and EV/EBITDA share a consistent operating-earnings base rather than
mixing a pre-tax "income before tax + interest" reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from stock_helper.features.metrics import DerivedMetric
from stock_helper.industry.sic_buckets import is_financial
from stock_helper.normalization.facts import MetricSeries
from stock_helper.valuation import VALUATION_VERSION
from stock_helper.valuation.stats import mad, median, robust_zscore, winsorize

if TYPE_CHECKING:  # avoid importing the heavy (pandas/sqlmodel) context module
    from stock_helper.features.context import MarketContext


# Classification of the multiple keys, used by the relative-valuation bridges.
EQUITY_MULTIPLE_KEYS = frozenset({"pe", "p_b", "p_tbv", "p_fcf"})
EV_MULTIPLE_KEYS = frozenset({"ev_ebit", "ev_ebitda", "ev_sales"})
YIELD_KEYS = frozenset({"earnings_yield", "fcf_yield", "dividend_yield"})

# Minimum defined peers before a cross-sectional median is trustworthy enough to
# imply a value from; below this we decline rather than anchor on 1-2 names.
_MIN_PEERS = 3
# Minimum own-history points before a robust z-score of the current level means
# anything (median/MAD need a few observations to define a scale).
_MIN_HISTORY = 4
# |z| beyond this reads as cheap/rich vs the company's own history; within is
# "in-line". Deliberately loose — this is a research flag, not a signal.
_Z_VERDICT = 1.0


# --------------------------------------------------------------------------- #
# Provenance-carrying result dataclasses
# --------------------------------------------------------------------------- #


@dataclass
class EnterpriseValue:
    """EV = market cap + total debt + preferred + minority - cash - marketable.

    Fully auditable: every component keeps the value used, and the object keeps
    the union of source tags / accessions and each component's period end.
    ``enterprise_value`` may be <= 0 for a net-cash company; that is returned
    honestly (with a caveat), and downstream EV multiples treat it as undefined
    rather than emitting a negative multiple.
    """

    enterprise_value: float
    market_cap: float
    total_debt: float
    cash: float
    preferred: float
    minority: float
    marketable: float
    net_debt: float  # total_debt - cash (marketable excluded, per definition)
    components: dict[str, float]
    formula: str
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    period_ends: dict[str, date] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


@dataclass
class Multiple:
    """One valuation multiple or yield with its numerator/denominator provenance.

    ``value is None`` <=> ``undefined_reason`` is set. A populated ``caveat`` on a
    defined value flags something the reader must weigh (e.g. a negative-numerator
    yield, or an EV multiple applied to a financial firm)."""

    key: str
    label: str
    value: float | None
    numerator_label: str
    denominator_label: str
    numerator_value: float | None = None
    denominator_value: float | None = None
    formula: str = ""
    undefined_reason: str | None = None
    caveat: str | None = None
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    period_ends: dict[str, date] = field(default_factory=dict)


@dataclass
class PeerRelativeValue:
    """Implied per-share value from a robust peer-median multiple.

    Equity multiples imply price directly from a per-share metric; EV multiples
    imply an enterprise value, then bridge to equity by subtracting net debt and
    dividing by shares. ``upside_pct`` is vs the current price (None if unknown).
    A scenario, not a target."""

    key: str
    peer_median: float
    n_peers: int
    implied_price: float | None
    upside_pct: float | None
    method: str = ""


@dataclass
class SelfHistoryValue:
    """Current multiple vs the company's own history (robust z, median/MAD).

    ``verdict`` is 'cheap' / 'rich' / 'in-line'. For yields the sign is inverted
    (a high yield relative to history reads as *cheap*)."""

    key: str
    current: float
    history_median: float
    zscore: float | None
    verdict: str
    n_history: int = 0


# --------------------------------------------------------------------------- #
# Latest-value lookup with provenance (derived preferred, series fallback)
# --------------------------------------------------------------------------- #


@dataclass
class _Source:
    value: float
    tags: list[str]
    accessions: list[str]
    period_end: date | None


def _from_derived(derived: dict[str, DerivedMetric], key: str) -> _Source | None:
    dm = derived.get(key)
    if dm is None or dm.latest is None:
        return None
    period_end = dm.points[-1][0] if dm.points else None
    return _Source(dm.latest, list(dm.input_tags), list(dm.input_accessions), period_end)


def _from_series(series: dict[str, MetricSeries], key: str) -> _Source | None:
    s = series.get(key)
    if s is None or not s.points:
        return None
    return _Source(s.latest.value, [s.tag], s.accessions(), s.latest.period_end)


def _latest(
    series: dict[str, MetricSeries], derived: dict[str, DerivedMetric], key: str
) -> _Source | None:
    """Latest scalar for ``key``: the derived metric if present, else the raw
    canonical series. Both carry the same provenance shape."""
    return _from_derived(derived, key) or _from_series(series, key)


def _total_debt_source(
    series: dict[str, MetricSeries], derived: dict[str, DerivedMetric]
) -> _Source | None:
    """derived['total_debt'] when available, else the sum of the tagged debt
    components (long-term + short-term + short-term borrowings)."""
    src = _latest(series, derived, "total_debt")
    if src is not None:
        return src
    parts = [
        _from_series(series, k)
        for k in ("long_term_debt", "short_term_debt", "short_term_borrowings")
    ]
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    tags = sorted({t for p in parts for t in p.tags})
    accns = sorted({a for p in parts for a in p.accessions})
    ends = [p.period_end for p in parts if p.period_end is not None]
    return _Source(sum(p.value for p in parts), tags, accns, max(ends) if ends else None)


# --------------------------------------------------------------------------- #
# Enterprise value bridge
# --------------------------------------------------------------------------- #


def compute_enterprise_value(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    *,
    include_marketable: bool = True,
) -> EnterpriseValue | None:
    """Bridge market cap to enterprise value.

    EV = market_cap + total_debt + preferred + minority - cash - marketable.

    ``market_cap`` is taken as-is from ``market.market_cap`` (which already uses
    ``market.shares`` — we never recompute a different share count). Returns None
    only when there is no market context or no market cap; every other component
    defaults to 0 when untagged (with a caveat), since a debt-free or
    security-free balance sheet is legitimate.
    """
    if market is None or getattr(market, "market_cap", None) is None:
        return None

    market_cap = float(market.market_cap)
    caveats: list[str] = [
        "Market cap uses non-canonical price data (see MarketContext source).",
    ]

    debt_src = _total_debt_source(series, derived)
    cash_src = _latest(series, derived, "cash")
    preferred_src = _latest(series, derived, "preferred_equity")
    minority_src = _latest(series, derived, "minority_interest")
    marketable_src = _latest(series, derived, "marketable_securities")

    total_debt = debt_src.value if debt_src else 0.0
    cash = cash_src.value if cash_src else 0.0
    preferred = preferred_src.value if preferred_src else 0.0
    minority = minority_src.value if minority_src else 0.0
    marketable = marketable_src.value if (marketable_src and include_marketable) else 0.0

    if debt_src is None:
        caveats.append("Total debt not tagged; treated as 0.")
    if cash_src is None:
        caveats.append("Cash not tagged; treated as 0.")

    enterprise_value = market_cap + total_debt + preferred + minority - cash - marketable
    net_debt = total_debt - cash

    if enterprise_value <= 0:
        caveats.append(
            "Net-cash position: enterprise value <= 0, so EV multiples are undefined."
        )

    tags: list[str] = []
    accns: list[str] = []
    period_ends: dict[str, date] = {}
    for name, src in (
        ("total_debt", debt_src),
        ("cash", cash_src),
        ("preferred", preferred_src),
        ("minority", minority_src),
        ("marketable", marketable_src if include_marketable else None),
    ):
        if src is not None:
            tags.extend(src.tags)
            accns.extend(src.accessions)
            if src.period_end is not None:
                period_ends[name] = src.period_end
    if getattr(market, "price_date", None) is not None:
        period_ends["market_cap"] = market.price_date

    return EnterpriseValue(
        enterprise_value=enterprise_value,
        market_cap=market_cap,
        total_debt=total_debt,
        cash=cash,
        preferred=preferred,
        minority=minority,
        marketable=marketable,
        net_debt=net_debt,
        components={
            "market_cap": market_cap,
            "total_debt": total_debt,
            "preferred": preferred,
            "minority": minority,
            "cash": cash,
            "marketable": marketable,
        },
        formula="market_cap + total_debt + preferred + minority - cash - marketable",
        input_tags=sorted(set(tags)),
        input_accessions=sorted(set(accns)),
        period_ends=period_ends,
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# Market multiples
# --------------------------------------------------------------------------- #


def _multiple(
    key: str,
    label: str,
    num_src: _Source | None,
    den_src: _Source | None,
    num_label: str,
    den_label: str,
    formula: str,
    *,
    kind: str,  # "multiple" | "yield"
    extra_caveat: str | None = None,
) -> Multiple:
    """Build one multiple/yield, enforcing the positivity invariant.

    kind="multiple": defined only when BOTH numerator and denominator are > 0
    (a negative multiple is never emitted as if 'cheap').
    kind="yield": denominator must be > 0; a negative numerator is kept but
    flagged with a caveat.
    """
    num = num_src.value if num_src else None
    den = den_src.value if den_src else None

    tags = sorted(
        set((num_src.tags if num_src else []) + (den_src.tags if den_src else []))
    )
    accns = sorted(
        set(
            (num_src.accessions if num_src else [])
            + (den_src.accessions if den_src else [])
        )
    )
    period_ends: dict[str, date] = {}
    if num_src and num_src.period_end is not None:
        period_ends["numerator"] = num_src.period_end
    if den_src and den_src.period_end is not None:
        period_ends["denominator"] = den_src.period_end

    value: float | None = None
    reason: str | None = None
    caveat = extra_caveat

    if num is None or den is None:
        missing = num_label if num is None else den_label
        reason = f"missing input: {missing}"
    elif kind == "multiple":
        if num <= 0:
            reason = f"non-positive {num_label}"
        elif den <= 0:
            reason = f"non-positive {den_label}"
        else:
            value = num / den
    else:  # yield
        if den <= 0:
            reason = f"non-positive {den_label}"
        else:
            value = num / den
            if num < 0:
                neg = f"negative {num_label}"
                caveat = f"{caveat}; {neg}" if caveat else neg

    return Multiple(
        key=key,
        label=label,
        value=value,
        numerator_label=num_label,
        denominator_label=den_label,
        numerator_value=num,
        denominator_value=den,
        formula=formula,
        undefined_reason=reason,
        caveat=caveat,
        input_tags=tags,
        input_accessions=accns,
        period_ends=period_ends,
    )


def compute_multiples(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    ev: EnterpriseValue | None,
    *,
    bucket: str,
) -> dict[str, Multiple]:
    """All computable EV / equity multiples and yields, keyed by metric key.

    EBIT is pinned to operating_income (see module docstring). Missing inputs or
    non-positive denominators/EV yield an undefined Multiple with a reason; a
    negative multiple is never produced.
    """
    out: dict[str, Multiple] = {}

    ebit_src = _latest(series, derived, "operating_income")
    ebitda_src = _latest(series, derived, "ebitda")
    rev_src = _latest(series, derived, "revenue")
    ni_src = _latest(series, derived, "net_income")
    fcf_src = _latest(series, derived, "free_cash_flow")
    eq_src = _latest(series, derived, "equity")
    tbv_src = _latest(series, derived, "tangible_book")
    dps_src = _latest(series, derived, "dividends_per_share")
    eps_src = _latest(series, derived, "eps_diluted")

    ev_src = (
        _Source(ev.enterprise_value, list(ev.input_tags), list(ev.input_accessions), None)
        if ev is not None
        else None
    )
    mc_src = (
        _Source(float(market.market_cap), [], [], getattr(market, "price_date", None))
        if market is not None and getattr(market, "market_cap", None) is not None
        else None
    )
    price_src = (
        _Source(float(market.price), [], [], getattr(market, "price_date", None))
        if market is not None and getattr(market, "price", None) is not None
        else None
    )

    ev_caveat = (
        "EV multiples are not meaningful for financial firms (leverage is operating)."
        if is_financial(bucket)
        else None
    )

    # --- Enterprise-value multiples (numerator = EV; must be > 0) ---
    out["ev_ebit"] = _multiple(
        "ev_ebit", "EV / EBIT", ev_src, ebit_src,
        "enterprise value", "EBIT (operating income)",
        "enterprise_value / operating_income", kind="multiple", extra_caveat=ev_caveat,
    )
    out["ev_ebitda"] = _multiple(
        "ev_ebitda", "EV / EBITDA", ev_src, ebitda_src,
        "enterprise value", "EBITDA",
        "enterprise_value / ebitda", kind="multiple", extra_caveat=ev_caveat,
    )
    out["ev_sales"] = _multiple(
        "ev_sales", "EV / Sales", ev_src, rev_src,
        "enterprise value", "revenue",
        "enterprise_value / revenue", kind="multiple", extra_caveat=ev_caveat,
    )

    # --- Equity (price) multiples (numerator = market cap, always > 0) ---
    if ni_src is not None or eps_src is None or price_src is None:
        out["pe"] = _multiple(
            "pe", "P/E", mc_src, ni_src, "market cap", "net income",
            "market_cap / net_income", kind="multiple",
        )
    else:
        # Fall back to price / diluted EPS when aggregate net income is untagged.
        out["pe"] = _multiple(
            "pe", "P/E", price_src, eps_src, "price", "diluted EPS",
            "price / eps_diluted", kind="multiple",
        )
    out["p_fcf"] = _multiple(
        "p_fcf", "P/FCF", mc_src, fcf_src, "market cap", "free cash flow",
        "market_cap / free_cash_flow", kind="multiple",
    )
    out["p_b"] = _multiple(
        "p_b", "P/B", mc_src, eq_src, "market cap", "equity",
        "market_cap / equity", kind="multiple",
    )
    out["p_tbv"] = _multiple(
        "p_tbv", "P/TBV", mc_src, tbv_src, "market cap", "tangible book value",
        "market_cap / tangible_book", kind="multiple",
    )

    # --- Yields (negative numerator kept + flagged; denominator must be > 0) ---
    out["earnings_yield"] = _multiple(
        "earnings_yield", "Earnings yield (EBIT/EV)", ebit_src, ev_src,
        "EBIT (operating income)", "enterprise value",
        "operating_income / enterprise_value", kind="yield", extra_caveat=ev_caveat,
    )
    out["fcf_yield"] = _multiple(
        "fcf_yield", "FCF yield", fcf_src, mc_src, "free cash flow", "market cap",
        "free_cash_flow / market_cap", kind="yield",
    )
    out["dividend_yield"] = _multiple(
        "dividend_yield", "Dividend yield", dps_src, price_src,
        "dividends per share", "price",
        "dividends_per_share / price", kind="yield",
    )

    return out


# --------------------------------------------------------------------------- #
# Peer-relative valuation
# --------------------------------------------------------------------------- #


def peer_relative_valuation(
    company_multiples: dict[str, Multiple],
    peer_multiples_by_key: dict[str, list[float]],
    *,
    company_metrics: dict[str, float],
    net_debt: float,
    shares: float | None,
) -> dict[str, PeerRelativeValue]:
    """Imply per-share value from robust peer-median multiples.

    ``peer_multiples_by_key`` maps a multiple key to peers' observed values.
    ``company_metrics`` supplies the company's underlying figure per key —
    per-share for equity multiples (eps, book/share, tbv/share, fcf/share) and
    aggregate for EV multiples (EBIT, EBITDA, sales) — plus an optional "price"
    entry used for ``upside_pct``.

    A key is skipped unless it has >= 3 defined (positive) peers. Peers are
    winsorized then reduced to a median (both from valuation.stats). Equity
    multiples imply price directly; EV multiples imply EV, subtract net debt, and
    divide by shares.
    """
    out: dict[str, PeerRelativeValue] = {}
    price = company_metrics.get("price")

    for key, peers in peer_multiples_by_key.items():
        is_equity = key in EQUITY_MULTIPLE_KEYS
        is_ev = key in EV_MULTIPLE_KEYS
        if not (is_equity or is_ev):
            continue

        # A negative/undefined multiple is not a valid comparable.
        clean = [float(v) for v in peers if v is not None and v > 0]
        if len(clean) < _MIN_PEERS:
            continue
        peer_median = median(winsorize(clean))
        if peer_median is None:
            continue

        metric = company_metrics.get(key)
        if metric is None:
            continue

        if is_equity:
            implied_price: float | None = peer_median * metric
            method = f"peer_median({key}) * {key}_per_share"
        else:
            if shares is None or shares <= 0:
                continue
            implied_ev = peer_median * metric
            implied_equity = implied_ev - net_debt
            implied_price = implied_equity / shares
            method = f"(peer_median({key}) * metric - net_debt) / shares"

        upside = (
            (implied_price - price) / price
            if price not in (None, 0) and implied_price is not None
            else None
        )

        out[key] = PeerRelativeValue(
            key=key,
            peer_median=peer_median,
            n_peers=len(clean),
            implied_price=implied_price,
            upside_pct=upside,
            method=method,
        )

    return out


# --------------------------------------------------------------------------- #
# Self-history valuation
# --------------------------------------------------------------------------- #


def self_history_valuation(
    current_by_key: dict[str, float],
    history_by_key: dict[str, list[float]],
) -> dict[str, SelfHistoryValue]:
    """Score each current multiple against the company's own history.

    Robust z-score (median / scaled MAD) of the current level vs its history
    (>= 4 points). Verdict thresholds at |z| = 1: above -> 'rich', below ->
    'cheap', within -> 'in-line'. For yields the sign is inverted, since a high
    yield relative to history is *cheap*."""
    out: dict[str, SelfHistoryValue] = {}

    for key, current in current_by_key.items():
        history = history_by_key.get(key)
        if history is None:
            continue
        clean = [float(v) for v in history if v is not None]
        if len(clean) < _MIN_HISTORY:
            continue

        hist_median = median(clean)
        z = robust_zscore(current, hist_median, mad(clean))

        if z is None:
            verdict = "insufficient"
        else:
            base = -z if key in YIELD_KEYS else z  # invert yields: high yield = cheap
            if base > _Z_VERDICT:
                verdict = "rich"
            elif base < -_Z_VERDICT:
                verdict = "cheap"
            else:
                verdict = "in-line"

        out[key] = SelfHistoryValue(
            key=key,
            current=current,
            history_median=hist_median if hist_median is not None else float("nan"),
            zscore=z,
            verdict=verdict,
            n_history=len(clean),
        )

    return out
