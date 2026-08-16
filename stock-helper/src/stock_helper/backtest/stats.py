"""Statistics for signal evaluation (pure; None/degenerate-safe).

The information coefficient (IC) is the rank correlation between a signal and the
return that follows it: does a higher signal today actually sort tomorrow's
returns? Rank correlation (Spearman) rather than Pearson because raw returns are
heavy-tailed and we only trust the *ordering* the signal produces, not its
linear scale.

The significance tools are deliberately conservative. A per-date bootstrap CI
asks whether the mean IC survives resampling the dates themselves (the real unit
of independent evidence), and the deflated Sharpe ratio discounts an observed
Sharpe by how many strategies were tried to find it — the multiple-testing
correction that separates a genuine edge from the best of many coin flips.
"""

import math
from statistics import NormalDist

import numpy as np

_NORM = NormalDist()


def _clean_pairs(
    a: list[float | None], b: list[float | None]
) -> tuple[list[float], list[float]]:
    """Zip two series and keep only positions where BOTH are real numbers."""
    xs: list[float] = []
    ys: list[float] = []
    for x, y in zip(a, b, strict=False):
        if x is None or y is None:
            continue
        fx, fy = float(x), float(y)
        if math.isnan(fx) or math.isnan(fy):
            continue
        xs.append(fx)
        ys.append(fy)
    return xs, ys


def _clean(xs: list[float | None]) -> list[float]:
    return [float(x) for x in xs if x is not None and not math.isnan(float(x))]


def _rank_avg(xs: list[float]) -> list[float]:
    """Rank values ascending, assigning tied values their average rank (1-based).

    Average ties keep the rank vector's mean/variance well-defined so Spearman
    reduces to Pearson-on-ranks even with duplicate values.
    """
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # positions i..j share this average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:  # zero variance in either -> correlation undefined
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    return sxy / math.sqrt(sxx * syy)


def spearman_ic(
    signal_values: list[float | None], forward_returns: list[float | None]
) -> float | None:
    """Spearman rank correlation between a signal and its forward returns.

    Returns None if fewer than 3 paired non-None points, or if either side is
    constant (zero rank variance) — a rank correlation is meaningless there.
    """
    xs, ys = _clean_pairs(signal_values, forward_returns)
    if len(xs) < 3:
        return None
    return _pearson(_rank_avg(xs), _rank_avg(ys))


def ic_summary(ics: list[float | None]) -> dict:
    """Summarize a series of per-date ICs.

    Returns mean_ic, ic_std (sample, ddof=1), n, ic_t_stat = mean / (std/sqrt n),
    and hit_rate (share of ICs > 0). None-safe: None ICs are dropped first, and
    dispersion-dependent fields are None when n < 2.
    """
    vals = _clean(ics)
    n = len(vals)
    if n == 0:
        return {"mean_ic": None, "ic_std": None, "n": 0, "ic_t_stat": None, "hit_rate": None}
    mean_ic = sum(vals) / n
    hit_rate = sum(1 for v in vals if v > 0) / n
    if n < 2:
        return {"mean_ic": mean_ic, "ic_std": None, "n": n, "ic_t_stat": None, "hit_rate": hit_rate}
    ic_std = float(np.std(vals, ddof=1))
    t_stat = None if ic_std == 0 else mean_ic / (ic_std / math.sqrt(n))
    return {"mean_ic": mean_ic, "ic_std": ic_std, "n": n, "ic_t_stat": t_stat, "hit_rate": hit_rate}


def quantile_spread(
    signal_values: list[float | None],
    forward_returns: list[float | None],
    q: int = 5,
) -> float | None:
    """Mean forward return of the top signal-quantile minus the bottom quantile.

    Names are sorted by signal and split into q roughly equal buckets; the result
    is (mean return of highest-signal bucket) - (mean return of lowest-signal
    bucket). Higher signal is assumed to map to higher return — the caller orients
    the signal beforehand. Returns None with fewer than q*2 paired points (too few
    to populate distinct extreme buckets).
    """
    xs, ys = _clean_pairs(signal_values, forward_returns)
    if q < 2 or len(xs) < q * 2:
        return None
    order = np.argsort(np.asarray(xs), kind="stable")
    rets = np.asarray(ys)[order]
    buckets = np.array_split(rets, q)
    return float(buckets[-1].mean() - buckets[0].mean())


def bootstrap_mean_ci(
    values: list[float | None],
    *,
    n_boot: int = 2000,
    seed: int = 7,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, float | None]:
    """Percentile bootstrap CI for the mean of a per-date series.

    Resamples the values with replacement (the dates are the independent unit of
    evidence) and returns (lo, hi, mean) at the (alpha/2, 1-alpha/2) percentiles.
    Seeded for determinism. (None, None, None) if there are no real values.
    """
    vals = _clean(values)
    n = len(vals)
    if n == 0:
        return (None, None, None)
    mean = float(np.mean(vals))
    arr = np.asarray(vals)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = arr[idx].mean(axis=1)
    lo = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    hi = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return (lo, hi, mean)


def deflated_sharpe_ratio(
    sharpe: float,
    *,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

    DSR is the probability that the observed (per-period) Sharpe would NOT be
    exceeded by the best of ``n_trials`` random strategies with no real edge. It
    is the probabilistic Sharpe ratio evaluated against a deflated benchmark
    SR0 = the expected maximum Sharpe under the null across n_trials:

        DSR = Phi( ((SR - SR0) * sqrt(n_obs - 1))
                   / sqrt(1 - skew*SR + (kurtosis - 1)/4 * SR^2) )

    The benchmark uses the expected-maximum-of-N-Gaussians approximation

        SR0 = sqrt(V) * [ (1 - g) * Z^-1(1 - 1/T) + g * Z^-1(1 - 1/(T*e)) ]

    with g = Euler-Mascheroni (~0.5772), T = n_trials, and V = 1/(n_obs - 1) the
    sampling variance of a Sharpe estimate under the null (SR = 0). With a single
    trial there is no selection to correct for, so SR0 = 0 and DSR reduces to the
    plain probabilistic Sharpe ratio. Returns a probability in [0, 1].
    """
    if n_obs < 2 or math.isnan(sharpe):
        return 0.0
    var_sr = 1.0 / (n_obs - 1)
    if n_trials <= 1:
        sr0 = 0.0
    else:
        gamma = 0.5772156649015329  # Euler-Mascheroni constant
        z1 = _NORM.inv_cdf(1.0 - 1.0 / n_trials)
        z2 = _NORM.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
        sr0 = math.sqrt(var_sr) * ((1.0 - gamma) * z1 + gamma * z2)
    denom = 1.0 - skew * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2
    if denom <= 0:  # pathological higher-moment combination -> undefined
        return 0.0
    stat = (sharpe - sr0) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return float(_NORM.cdf(stat))
