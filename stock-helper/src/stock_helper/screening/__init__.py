"""Cross-sectional OUTLIER SCREENER (candidate screens, not buy lists).

Ranks a local universe on already-computed valuation/quality/forensic figures
using robust (median/MAD) cross-sectional standardization — within industry
bucket when the bucket is large enough, else against the whole universe. Every
number here is *reused* from ``valuation.compute_valuation`` (this package never
re-derives a ratio) so the audit trail is unbroken.

Screens surface CANDIDATES for further reading — they are unscored and NOT
backtested. Distress/manipulation flags are SCREENS, never verdicts.
"""

SCREEN_ENGINE_VERSION = "screen-0.1"
