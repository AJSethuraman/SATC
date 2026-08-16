"""Cross-sectional outlier screener: pure-engine tests over tiny fixed universes.

These exercise standardize / compute_composites / flag_outliers / run_screen
directly on synthetic UniverseRows (no DB, no valuation) so the ranking and flag
logic is deterministic and fast."""

from stock_helper.screening.engine import (
    compute_composites,
    flag_outliers,
    standardize,
)
from stock_helper.screening.metrics import STANDARDIZABLE, UniverseRow
from stock_helper.screening.screens import SAVED_SCREENS, run_screen


def row(ticker: str, *, bucket: str = "industrial", flags=None, **metrics) -> UniverseRow:
    """Build a UniverseRow with every standardizable metric defaulting to None,
    overridden by keyword."""
    base: dict[str, float | None] = {k: None for k in STANDARDIZABLE}
    base.update(metrics)
    return UniverseRow(
        ticker=ticker,
        company_id=None,
        name=ticker,
        bucket=bucket,
        sic="3711",
        market_cap=None,
        metrics=base,
        flags=list(flags or []),
    )


def _full(ticker, fvg, ey, fcf, ev_ebit, p_b, pio, gp, roic, roe, **kw):
    return row(
        ticker,
        fair_value_gap=fvg, earnings_yield=ey, fcf_yield=fcf,
        ev_ebit=ev_ebit, p_b=p_b,
        piotroski_f=pio, gross_profitability=gp, roic=roic, roe=roe,
        **kw,
    )


# A fixed 5-name industrial universe. VAL is an extreme value outlier (cheap on
# every value metric); the other four form a tight, monotonically-ordered
# cluster A > B > C > D on value.
MAIN_UNIVERSE = [
    _full("A", 0.05, 0.05, 0.05, 25, 5.5, 6, 0.30, 0.15, 0.18),
    _full("B", 0.04, 0.045, 0.045, 26, 5.6, 5, 0.25, 0.12, 0.15),
    _full("C", 0.03, 0.04, 0.04, 27, 5.7, 4, 0.20, 0.10, 0.12),
    _full("D", 0.02, 0.035, 0.035, 28, 5.8, 3, 0.15, 0.08, 0.10),
    _full("VAL", 0.20, 0.30, 0.25, 10, 4.0, 5, 0.28, 0.13, 0.16),
]


def _cross_section(rows, **kw):
    cs = standardize(rows, **kw)
    compute_composites(cs)
    flag_outliers(cs)
    return cs


def test_deep_value_ranking_and_flag():
    cs = _cross_section(MAIN_UNIVERSE)

    # Every name has full value+quality coverage -> composites all defined.
    for t in ("A", "B", "C", "D", "VAL"):
        assert cs.value_score[t] is not None
        assert cs.quality_score[t] is not None
        assert cs.combined_score[t] is not None

    ranked = run_screen(cs, SAVED_SCREENS["deep_value"])
    assert [e.ticker for e in ranked] == ["VAL", "A", "B", "C", "D"]
    assert [e.rank for e in ranked] == [1, 2, 3, 4, 5]

    # VAL is a >2σ value outlier -> deep_value; its quality is mid-pack, so it is
    # NOT tagged a quality compounder.
    assert "deep_value" in cs.flags["VAL"]
    assert "quality_compounder" not in cs.flags["VAL"]


def test_lower_is_better_sign_flip():
    # Only ev_ebit varies; the lowest (cheapest) must earn the highest z.
    rows = [
        row("LOW", ev_ebit=8),
        row("R2", ev_ebit=10),
        row("R3", ev_ebit=12),
        row("R4", ev_ebit=14),
        row("HIGH", ev_ebit=30),
    ]
    cs = standardize(rows)
    z_low = cs.z["ev_ebit"]["LOW"]
    z_high = cs.z["ev_ebit"]["HIGH"]
    assert z_low is not None and z_high is not None
    assert z_low > 0 > z_high  # cheap = positive (better), expensive = negative
    assert z_low > z_high
    # Percentile is oriented the same way (cheap = best).
    assert cs.percentile["ev_ebit"]["LOW"] > cs.percentile["ev_ebit"]["HIGH"]


def test_sector_fallback_to_whole_universe():
    # Two buckets of two names each: neither reaches min_sector_n=5, so by_sector
    # standardization must fall back to the whole universe and match by_sector=False.
    rows = [
        row("A", bucket="tech", fair_value_gap=0.05),
        row("B", bucket="tech", fair_value_gap=0.10),
        row("C", bucket="industrial", fair_value_gap=0.02),
        row("D", bucket="industrial", fair_value_gap=0.08),
    ]
    by_sector = standardize(rows, by_sector=True, min_sector_n=5)
    whole = standardize(rows, by_sector=False)
    assert by_sector.z["fair_value_gap"] == whole.z["fair_value_gap"]


def test_missing_metric_row_excluded_not_zeroed():
    rows = list(MAIN_UNIVERSE) + [row("EMPTY")]  # EMPTY has all-None metrics
    cs = _cross_section(rows)

    # Excluded from composites entirely — None, never a fabricated 0.
    assert cs.value_score["EMPTY"] is None
    assert cs.quality_score["EMPTY"] is None
    assert cs.combined_score["EMPTY"] is None

    ranked = run_screen(cs, SAVED_SCREENS["deep_value"])
    assert "EMPTY" not in [e.ticker for e in ranked]


def test_value_trap_flag():
    # TRAP is cheap on every value metric but weak on every quality metric.
    rows = [
        _full("A", 0.00, 0.040, 0.030, 20, 3.0, 7, 0.30, 0.15, 0.18),
        _full("B", 0.01, 0.045, 0.035, 19, 3.1, 6, 0.32, 0.16, 0.17),
        _full("C", 0.02, 0.050, 0.040, 18, 3.2, 7, 0.31, 0.14, 0.19),
        _full("D", 0.03, 0.055, 0.045, 17, 3.3, 6, 0.33, 0.15, 0.18),
        _full("TRAP", 0.50, 0.300, 0.250, 5, 0.5, 1, 0.02, 0.01, 0.01),
    ]
    cs = _cross_section(rows)
    assert cs.value_score["TRAP"] > 2.0
    assert cs.quality_score["TRAP"] < -1.0
    assert "deep_value" in cs.flags["TRAP"]
    assert "value_trap" in cs.flags["TRAP"]


def test_distress_and_manipulation_flags():
    rows = [
        row("HEALTHY", altman_z=5.0),
        row("LOWZ", altman_z=1.0),  # below 1.81 distress floor
        row("AGREE", altman_z=3.0, flags=["distress_models_agree"]),
        row("MANIP", altman_z=4.0, beneish_m=-1.0, flags=["beneish_manipulation_flag"]),
    ]
    cs = _cross_section(rows)
    assert "distress" not in cs.flags["HEALTHY"]
    assert "distress" in cs.flags["LOWZ"]
    assert "distress" in cs.flags["AGREE"]  # via model agreement, not raw Z
    assert "manipulation_risk" in cs.flags["MANIP"]

    watch = run_screen(cs, SAVED_SCREENS["distress_watch"])
    tickers = [e.ticker for e in watch]
    assert set(tickers) == {"LOWZ", "AGREE"}
    # Ascending by Altman Z: most distressed (lowest Z) first.
    assert tickers[0] == "LOWZ"

    manip = run_screen(cs, SAVED_SCREENS["manipulation_watch"])
    assert [e.ticker for e in manip] == ["MANIP"]
