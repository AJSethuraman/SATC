"""SATC EDGAR Industry Assumption-Set Tool.

Derives credit-relevant financial benchmark RANGES (not averages) from SEC
EDGAR public-company XBRL data, broken out BY REVENUE TIER, for use as a
*calibrated reference* when analyzing private middle-market borrowers.

The package is intentionally pure-stdlib and fully deterministic: identical
inputs (and cache contents) always produce byte-identical outputs.
"""

__version__ = "0.1.0"
