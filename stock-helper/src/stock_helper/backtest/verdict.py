"""Turn backtest statistics into a plain-English verdict.

The whole point of the backtester is to answer one question in words a
non-quant can act on: *did ranking stocks by this signal actually sort future
winners from losers, or were we just riding the market?* This module maps the
honest, market-neutral statistics (the information coefficient and its
significance) onto a blunt label + explanation.

Why IC and not Sharpe: the IC ("did cheap beat expensive in the RANKING")
ignores whether the market as a whole went up, so it isolates the signal's own
skill. A high Sharpe with a near-zero IC just means the market rose — not that
the signal worked. The verdict therefore keys off IC, never Sharpe.
"""

from dataclasses import dataclass

# A |t-stat| this large is our bar for "probably not luck" (~2 sigma).
_SIGNIFICANT_T = 2.0
# Below this |IC| the ranking is, for practical purposes, a coin flip.
_TRIVIAL_IC = 0.02


@dataclass
class Verdict:
    label: str  # short banner: "NO EDGE", "WORTH A LOOK", ...
    tone: str  # "good" | "bad" | "neutral" -> caller colors it
    headline: str  # one plain sentence
    plain_points: list[str]  # bullet explanations in plain English


def _skill_score(mean_ic: float | None) -> int:
    """IC (~-1..+1) rescaled to an intuitive -100..+100 'skill score'."""
    if mean_ic is None:
        return 0
    return round(mean_ic * 100)


def backtest_verdict(result) -> Verdict:
    """Map a BacktestResult onto a plain-English verdict.

    Decision rule (keyed on IC, the market-neutral skill measure):
    - not enough data                      -> COULDN'T TEST
    - |t| < 2 or |IC| tiny                  -> NO EDGE (indistinguishable from luck)
    - t >= 2 and IC > 0 and cheap>expensive -> WORTH A LOOK
    - t <= -2 (signal predicts backwards)   -> BACKWARDS
    """
    ic = result.mean_ic
    t = result.ic_t_stat
    spread = result.quantile_spread_mean  # top-minus-bottom future return
    score = _skill_score(ic)

    if ic is None or t is None or result.n_dates < 3:
        return Verdict(
            label="COULDN'T TEST",
            tone="neutral",
            headline="Not enough point-in-time history to judge this signal.",
            plain_points=[
                "The test needs several rebalance dates with prices on both "
                "ends; widen the date range or check that prices downloaded.",
            ],
        )

    # Was the "cheap" group actually ahead of the "expensive" group?
    if spread is None:
        beat = "couldn't be measured"
    elif spread > 0:
        beat = f"the cheap group beat the expensive group by {spread:+.1%} per period"
    else:
        beat = (
            f"the cheap group actually LOST to the expensive group by "
            f"{spread:+.1%} per period"
        )

    sureness = (
        "we can be fairly confident this isn't luck"
        if abs(t) >= _SIGNIFICANT_T
        else "this is well within what random luck produces, so treat it as noise"
    )

    # Signal predicts the WRONG way, and significantly so.
    if t <= -_SIGNIFICANT_T:
        return Verdict(
            label="BACKWARDS",
            tone="bad",
            headline="This signal sorted stocks the WRONG way over this period.",
            plain_points=[
                f"Skill score {score} out of 100 (0 = pure luck): a clearly "
                "negative score means the 'cheap' picks tended to LOSE to the "
                "'expensive' ones.",
                f"Over this window {beat}.",
                "Don't trade this as a buy signal here — if anything it did the "
                "opposite of what you'd want.",
            ],
        )

    # Real, statistically-meaningful positive skill.
    if t >= _SIGNIFICANT_T and ic > _TRIVIAL_IC and (spread or 0) > 0:
        return Verdict(
            label="WORTH A LOOK",
            tone="good",
            headline="Ranking stocks by this signal DID sort future winners from losers.",
            plain_points=[
                f"Skill score {score} out of 100 (0 = pure luck): the higher-"
                "ranked (cheaper) stocks tended to do better afterward.",
                f"Over this window {beat}, and {sureness}.",
                "This is a lead worth digging into — but it's still free, "
                "survivorship-biased data over a short window, so confirm it on "
                "a longer period before risking money.",
            ],
        )

    # Everything else: no measurable edge.
    return Verdict(
        label="NO EDGE",
        tone="neutral",
        headline="This signal added nothing over just owning the market here.",
        plain_points=[
            f"Skill score {score} out of 100 (0 = pure luck): essentially zero, "
            "so the ranking couldn't tell future winners from losers.",
            f"Over this window {beat}, and {sureness}.",
            "Any profit you'd have made came from the market rising, not from "
            "this rule — so don't trade it as-is.",
        ],
    )
