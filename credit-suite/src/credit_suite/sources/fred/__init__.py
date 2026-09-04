"""The FRED credit-risk dashboard: national time-series from FRED/ALFRED.

The grandfathered monitor. It predates TEMPLATE_CONTRACT and diverges from it in
ways output parity pins: a `Watchlist_Geo` tab rather than `Watchlist`, a
`--backend` flag no other runner accepts, `[THRESHOLDS]` as two global bands
reached through workbook DEFINED NAMES rather than a per-metric table, and raw
blocks anchored by a series' position in `_config` rather than by a slot.

None of that is tidied here. De-grandfathering is a deliberate, separately
tested change with an updated golden -- never a silent side effect of moving the
code onto the shared engine.
"""
