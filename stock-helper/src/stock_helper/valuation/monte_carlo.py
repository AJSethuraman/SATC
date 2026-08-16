"""Monte Carlo DCF — quantify a *single* valuation's input uncertainty.

This does NOT prove a DCF "works" and is NOT a backtest. It answers a narrow,
honest question: given that the base assumptions (growth, discount rate,
terminal growth, FCF base) are themselves uncertain, how wide is the resulting
fair-value distribution? The output is a spread around one scenario, not a
probability the stock goes up.

Design:
- Reuses the pure :func:`stock_helper.valuation.dcf.dcf_value` for every draw —
  the simulation is only a sampler wrapped around the audited core, so the
  point estimate (all sds = 0) collapses exactly onto ``dcf_value``.
- Draws are seeded (``np.random.default_rng(seed)``) for reproducibility.
- Perpetuity validity is enforced per draw (r > g_terminal + 0.005); invalid
  draws are rejected so no bogus Gordon terminal ever enters the distribution.
- Missing/degenerate input (non-positive FCF or shares, too few valid draws)
  yields ``None`` — never a fabricated number.
"""

from dataclasses import dataclass, field

import numpy as np

from stock_helper.valuation import VALUATION_VERSION
from stock_helper.valuation.dcf import dcf_value
from stock_helper.valuation.types import LEVERED

# Perpetuity guard: a draw is only kept if the discount rate clears terminal
# growth by at least this margin, matching dcf_value's Gordon guard with a small
# cushion so near-singular (r - g -> 0) terminal values don't explode the tail.
_MIN_RG_SPREAD = 0.005

# Minimum valid draws before a distribution is trustworthy enough to summarize.
_MIN_VALID_DRAWS = 100

# Bounds for the growth_sd derived from historical FCF-growth volatility.
_GROWTH_SD_FLOOR = 0.02
_GROWTH_SD_CAP = 0.10


@dataclass
class MonteCarloResult:
    """Distribution of fair-value-per-share across randomized input draws.

    Every field describes *input* uncertainty only. ``caveats`` is load-bearing:
    the spread is a sensitivity fan, not a performance claim or a price target.
    """

    median: float
    mean: float
    p10: float
    p90: float
    p25: float
    p75: float
    prob_undervalued: float | None  # share of draws with fair value > price
    n_sims: int  # number of VALID draws actually summarized
    seed: int
    inputs_summary: dict = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


def run_monte_carlo_dcf(
    *,
    fcf_0: float,
    stage1_growth: float,
    stage1_years: int,
    discount_rate: float,
    terminal_growth: float,
    shares: float,
    net_debt: float = 0.0,
    price: float | None = None,
    n: int = 5000,
    seed: int = 42,
    growth_sd: float = 0.03,
    discount_sd: float = 0.01,
    terminal_sd: float = 0.005,
    fcf_sd: float = 0.0,
    fcf_basis: str = LEVERED,
) -> MonteCarloResult | None:
    """Simulate ``n`` DCF scenarios by perturbing the four key assumptions.

    Each draw samples g ~ N(stage1_growth, growth_sd), r ~ N(discount_rate,
    discount_sd), gt ~ N(terminal_growth, terminal_sd), and (if ``fcf_sd`` > 0) a
    multiplicative FCF shock ~ N(1, fcf_sd). Draws where r <= gt + 0.005 are
    rejected (invalid perpetuity). The pure :func:`dcf_value` is called for each
    surviving draw and its ``fair_value_per_share`` collected (None results
    skipped). Returns ``None`` if ``fcf_0 <= 0``, ``shares <= 0``, or fewer than
    100 valid draws survive.

    ``prob_undervalued`` is the share of draws whose fair value exceeds ``price``
    (None when ``price`` is None). With all sds = 0 the distribution collapses to
    the single point estimate — the simulation adds no bias, only spread.
    """
    if fcf_0 <= 0 or shares <= 0 or n <= 0:
        return None

    rng = np.random.default_rng(seed)
    g_draws = rng.normal(stage1_growth, growth_sd, n)
    r_draws = rng.normal(discount_rate, discount_sd, n)
    gt_draws = rng.normal(terminal_growth, terminal_sd, n)
    fcf_mult = rng.normal(1.0, fcf_sd, n) if fcf_sd > 0 else np.ones(n)

    fair_values: list[float] = []
    for g, r, gt, mult in zip(g_draws, r_draws, gt_draws, fcf_mult, strict=True):
        # Reject draws that violate the perpetuity guard rather than clip them,
        # so a near-singular (r - g) never manufactures an extreme fair value.
        if r <= gt + _MIN_RG_SPREAD:
            continue
        res = dcf_value(
            float(fcf_0 * mult), float(g), stage1_years, float(r), float(gt),
            shares, net_debt=net_debt, fcf_basis=fcf_basis,
        )
        fv = res.fair_value_per_share
        if fv is not None:
            fair_values.append(fv)

    if len(fair_values) < _MIN_VALID_DRAWS:
        return None

    arr = np.asarray(fair_values, dtype=float)
    p10, p25, p50, p75, p90 = np.percentile(arr, [10, 25, 50, 75, 90])

    prob_undervalued: float | None = None
    if price is not None:
        prob_undervalued = float(np.mean(arr > price))

    caveats = [
        "Distribution reflects INPUT uncertainty only (growth, discount, "
        "terminal growth, FCF base) — NOT model risk, regime change, or the "
        "chance the base assumptions are simply wrong.",
        "This is NOT a probability the stock goes up and NOT a price target — "
        "it is a sensitivity fan around one editable scenario.",
        "Educational research aid, not investment advice.",
    ]
    if prob_undervalued is not None:
        caveats.append(
            "'prob_undervalued' is the fraction of simulated fair values above "
            "the current price under the assumed input spreads — a diagnostic, "
            "not a forecast."
        )
    n_rejected = n - len(fair_values)
    if n_rejected > 0:
        caveats.append(
            f"{n_rejected} of {n} draws rejected (invalid perpetuity or "
            "uncomputable) — distribution is truncated to valid scenarios."
        )

    inputs_summary = {
        "fcf_0": fcf_0,
        "stage1_growth": stage1_growth,
        "stage1_years": stage1_years,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
        "shares": shares,
        "net_debt": net_debt,
        "fcf_basis": fcf_basis,
        "price": price,
        "n_requested": n,
        "growth_sd": growth_sd,
        "discount_sd": discount_sd,
        "terminal_sd": terminal_sd,
        "fcf_sd": fcf_sd,
    }

    return MonteCarloResult(
        median=float(p50),
        mean=float(np.mean(arr)),
        p10=float(p10),
        p90=float(p90),
        p25=float(p25),
        p75=float(p75),
        prob_undervalued=prob_undervalued,
        n_sims=len(fair_values),
        seed=seed,
        inputs_summary=inputs_summary,
        caveats=caveats,
        engine_version=VALUATION_VERSION,
    )


def _fcf_growth_sd(derived: dict) -> float | None:
    """Stdev of year-over-year FCF growth from ``derived['free_cash_flow']``.

    Only consecutive periods with a strictly positive base are used (growth off
    a non-positive FCF is meaningless). Returns None when fewer than two such
    growth observations exist; the caller then falls back to a default sd.
    """
    fcf = derived.get("free_cash_flow")
    if fcf is None or len(fcf.points) < 3:
        return None
    growths: list[float] = []
    prev = None
    for _, v in fcf.points:
        if prev is not None and prev > 0:
            growths.append(v / prev - 1.0)
        prev = v
    if len(growths) < 2:
        return None
    return float(np.std(growths, ddof=1))


def run_monte_carlo_from_dcf(
    dcf_result,
    derived: dict,
    *,
    price: float | None = None,
    n: int = 5000,
    seed: int = 42,
) -> MonteCarloResult | None:
    """Run a Monte Carlo DCF anchored on an existing :class:`DcfResult`.

    Reuses the DcfResult's base inputs (FCF base, growth, discount/terminal
    rates, shares, net debt, basis) and derives ``growth_sd`` from the
    historical FCF-growth volatility in ``derived['free_cash_flow']`` (sample
    stdev of YoY growth, floored/capped to [0.02, 0.10] so a suspiciously calm
    or explosive history can't produce an absurdly narrow/wide fan). Returns
    None if the base DcfResult lacks the inputs needed to simulate.
    """
    fcf_0 = dcf_result.base_fcf
    shares = dcf_result.shares
    if (
        fcf_0 is None
        or shares is None
        or dcf_result.stage1_growth is None
        or dcf_result.discount_rate is None
        or dcf_result.terminal_growth is None
        or dcf_result.stage1_years is None
    ):
        return None

    hist_sd = _fcf_growth_sd(derived)
    if hist_sd is None:
        growth_sd = _GROWTH_SD_FLOOR
    else:
        growth_sd = max(_GROWTH_SD_FLOOR, min(_GROWTH_SD_CAP, hist_sd))

    result = run_monte_carlo_dcf(
        fcf_0=fcf_0,
        stage1_growth=dcf_result.stage1_growth,
        stage1_years=dcf_result.stage1_years,
        discount_rate=dcf_result.discount_rate,
        terminal_growth=dcf_result.terminal_growth,
        shares=shares,
        net_debt=dcf_result.net_debt,
        price=price,
        n=n,
        seed=seed,
        growth_sd=growth_sd,
        fcf_basis=dcf_result.fcf_basis,
    )
    if result is not None:
        note = (
            f"growth_sd={growth_sd:.4f} derived from historical FCF-growth "
            "volatility"
            + (
                f" (raw {hist_sd:.4f} clamped to "
                f"[{_GROWTH_SD_FLOOR}, {_GROWTH_SD_CAP}])"
                if hist_sd is not None
                and (hist_sd < _GROWTH_SD_FLOOR or hist_sd > _GROWTH_SD_CAP)
                else ""
            )
            if hist_sd is not None
            else "growth_sd fell back to floor (no clean FCF-growth history)"
        )
        result.caveats.append(note)
        result.inputs_summary["growth_sd_source"] = (
            "historical" if hist_sd is not None else "floor_fallback"
        )
    return result
