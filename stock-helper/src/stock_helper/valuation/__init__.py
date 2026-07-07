"""Fundamental valuation engine (DCF, multiples, quality factors).

Research aid — NOT investment advice. Every value here is a scenario estimate
that falls out of explicit, editable assumptions, not a price target. See
DISCLAIMER.md. Non-financial companies get FCF-DCF; banks/insurers are routed
to dividend-discount / justified-P/B (FCF-DCF is invalid for them).
"""

VALUATION_VERSION = "valuation-0.1"

# Shared result statuses (mirrors signals.base philosophy).
OK = "OK"
NOT_APPLICABLE = "NOT_APPLICABLE"  # method invalid for this industry bucket
NEGATIVE_FCF = "NEGATIVE_FCF"  # can't DCF a negative cash-flow base
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # not enough periods
UNAVAILABLE = "UNAVAILABLE"  # required metric/price not mapped
