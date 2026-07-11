"""Walk-forward signal evaluation (IC, quantile spread, cost model, DSR).

Educational only. Everything here runs over NON-CANONICAL, SURVIVORSHIP-BIASED
free prices (Stooq): delisted names are absent, which inflates results and hides
distress. Nothing in this package is a performance claim. The honest-significance
tools (bootstrap CI across dates, deflated Sharpe with a multiple-testing
penalty) exist precisely so a signal that merely got lucky is not mistaken for
one that works.
"""

BACKTEST_VERSION = "backtest-0.1"
