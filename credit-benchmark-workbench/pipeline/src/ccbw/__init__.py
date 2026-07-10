"""ccbw - Commercial Credit Benchmark Workbench pipeline.

Pulls SEC EDGAR XBRL company facts, normalizes them into a clean annual
financial panel with per-datapoint provenance, builds per-segment /
per-size-bucket benchmark distributions, applies a tunable size-distortion
and survivorship adjustment layer, overlays private borrowers, and validates
departure flags against public deterioration proxies.
"""

__version__ = "0.1.0"
