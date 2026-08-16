"""The plain-English backtest verdict keys off IC significance, never Sharpe."""

from dataclasses import dataclass

from stock_helper.backtest.verdict import backtest_verdict


@dataclass
class FakeResult:
    mean_ic: float | None = None
    ic_t_stat: float | None = None
    quantile_spread_mean: float | None = None
    n_dates: int = 10
    # A deliberately gaudy Sharpe to prove the verdict ignores it.
    sharpe_annualized: float | None = 3.0


def test_no_edge_when_ic_insignificant():
    # High Sharpe but IC ~0 and t-stat tiny -> must NOT be called an edge.
    v = backtest_verdict(FakeResult(mean_ic=0.012, ic_t_stat=0.24,
                                    quantile_spread_mean=-0.023))
    assert v.label == "NO EDGE"
    assert v.tone == "neutral"


def test_worth_a_look_when_ic_significant_and_positive():
    v = backtest_verdict(FakeResult(mean_ic=0.06, ic_t_stat=3.1,
                                    quantile_spread_mean=0.015))
    assert v.label == "WORTH A LOOK"
    assert v.tone == "good"


def test_backwards_when_signal_predicts_negatively():
    v = backtest_verdict(FakeResult(mean_ic=-0.05, ic_t_stat=-2.6,
                                    quantile_spread_mean=-0.02))
    assert v.label == "BACKWARDS"
    assert v.tone == "bad"


def test_couldnt_test_with_too_few_dates():
    v = backtest_verdict(FakeResult(mean_ic=None, ic_t_stat=None, n_dates=1))
    assert v.label == "COULDN'T TEST"


def test_significant_but_trivial_ic_is_still_no_edge():
    # t clears the bar but the effect is microscopic -> not worth chasing.
    v = backtest_verdict(FakeResult(mean_ic=0.01, ic_t_stat=2.5,
                                    quantile_spread_mean=0.001))
    assert v.label == "NO EDGE"
