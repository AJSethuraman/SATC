"""Economic conditions outside a bank's control, each read against its own past.

A separate tool from the loss thresholds. It reads public economic series --
unemployment, jobless claims, insurance and house prices, credit spreads,
financial conditions, household debt -- and says where each stands against
its own history, and whether its change is inside its normal movement. It
rates nothing (the firm, 22 Oct 2026). The series and why each is here are in
docs/macro/reports/Macro risk indicators for lending.md ("ready to rate" and
"usable with care").

Public data only, from the publisher or FRED. No key is needed for any series
in the catalog. Every choice that is the firm's is a required setting; the
tool never fills one in.
"""
