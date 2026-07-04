"""Market, peer, and calibration context: Phase 4/5 slices."""

from datetime import date

import pandas as pd
import pytest

from conftest import mk_series
from stock_helper.features.context import (
    compute_market_context,
    percentile_rank,
)
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.signals.engine import evaluate_signals

D = date


def synthetic_prices(n=300, start_price=100.0, daily_gain=0.1):
    days = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {"Date": days, "Close": [start_price + i * daily_gain for i in range(n)]}
    )


def fundamentals():
    return {
        "diluted_shares": mk_series("diluted_shares", [(D(2024, 12, 31), 1_000_000.0)], unit="shares"),
        "net_income": mk_series("net_income", [(D(2024, 12, 31), 5_000_000.0)]),
        "revenue": mk_series("revenue", [(D(2024, 12, 31), 50_000_000.0)]),
    }


def test_market_context_valuation_and_momentum():
    market = compute_market_context(synthetic_prices(), fundamentals())
    assert market is not None
    assert market.momentum_12_1 is not None and market.momentum_12_1 > 0
    assert market.volatility_60d is not None
    assert market.market_cap == pytest.approx(market.price * 1_000_000.0)
    assert market.pe == pytest.approx(market.market_cap / 5_000_000.0)
    assert market.ps == pytest.approx(market.market_cap / 50_000_000.0)


def test_market_context_short_history_omits_momentum():
    market = compute_market_context(synthetic_prices(n=100), fundamentals())
    assert market.momentum_12_1 is None  # < 252 sessions → no 12-1 claim
    assert market.pe is not None


def test_negative_earnings_gives_no_pe():
    series = fundamentals()
    series["net_income"] = mk_series("net_income", [(D(2024, 12, 31), -1_000_000.0)])
    market = compute_market_context(synthetic_prices(), series)
    assert market.pe is None
    assert market.ps is not None


def test_percentile_rank():
    assert percentile_rank(5.0, [1.0, 2.0, 3.0, 4.0]) == 100.0
    assert percentile_rank(0.0, [1.0, 2.0, 3.0, 4.0]) == 0.0
    assert percentile_rank(2.5, [1.0, 2.0, 3.0, 4.0]) == 50.0


def test_context_signals_gate_on_extras():
    """Without extras (price data off / history replay), context signals are
    UNAVAILABLE with a helpful hint — never silently skipped or faked."""
    derived = compute_derived_metrics(fundamentals())
    outcomes = {s.definition.key: s.outcome for s in evaluate_signals("technology", derived)}
    for key in ("valuation_context", "momentum_12_1"):
        assert outcomes[key].status == "UNAVAILABLE"
        assert "ENABLE_PRICE_DATA" in outcomes[key].interpretation
    assert outcomes["disclosure_risk_language"].status == "UNAVAILABLE"
    assert "--with-documents" in outcomes["disclosure_risk_language"].interpretation
    assert outcomes["industry_relative_context"].status == "UNAVAILABLE"


def test_context_signals_with_extras():
    from stock_helper.parsing.text_metrics import compute_risk_language

    class FakeChunk:
        def __init__(self, chunk_id, text):
            self.chunk_id = chunk_id
            self.text = text

    derived = compute_derived_metrics(fundamentals())
    market = compute_market_context(synthetic_prices(), fundamentals())
    risk = compute_risk_language(
        [FakeChunk("acc1:risk_factors:0",
                   "Litigation and impairment risks may adversely harm results. " * 30)],
        [FakeChunk("acc0:risk_factors:0",
                   "Different prior year risks involving penalties and defaults entirely. " * 30)],
    )
    outcomes = {
        s.definition.key: s.outcome
        for s in evaluate_signals(
            "technology", derived, extras={"market": market, "risk_language": risk, "peers": None}
        )
    }
    valuation = outcomes["valuation_context"]
    assert valuation.status == "OK"
    assert valuation.score == 0  # unscored by design
    assert "P/E" in valuation.value_text
    assert "non-canonical" in valuation.caveat.lower()

    momentum = outcomes["momentum_12_1"]
    assert momentum.status == "OK"
    assert momentum.direction == "improving"

    disclosure = outcomes["disclosure_risk_language"]
    assert disclosure.status == "OK"
    assert disclosure.numeric_value is not None  # novelty computed
    assert disclosure.evidence and "risk_factors" in disclosure.evidence[0].reference

    assert outcomes["industry_relative_context"].status == "UNAVAILABLE"  # peers None


def test_calibration_summary_counts():
    from stock_helper.signals.base import SignalOutcome
    from stock_helper.signals.definitions import REGISTRY
    from stock_helper.signals.engine import EvaluatedSignal
    from stock_helper.signals.history import HistoryPoint, OutcomeLabel, calibration_summary

    definition = next(d for d in REGISTRY if d.key == "revenue_growth_yoy")
    improving = EvaluatedSignal(definition, SignalOutcome(direction="improving"))
    label_up = OutcomeLabel(20, D(2024, 11, 4), D(2024, 12, 2), 0.05)
    label_down = OutcomeLabel(20, D(2025, 5, 5), D(2025, 6, 2), -0.03)
    points = [
        HistoryPoint(as_of=D(2024, 11, 1), signals=[improving], outcomes={20: label_up}),
        HistoryPoint(as_of=D(2025, 5, 2), signals=[improving], outcomes={20: label_down}),
    ]
    cells = calibration_summary(points)
    assert len(cells) == 1
    cell = cells[0]
    assert cell.signal_key == "revenue_growth_yoy"
    assert cell.improving_total == 2
    assert cell.improving_up == 1
    assert cell.deteriorating_total == 0
