"""Consumer Credit Red-Flag Monitor (External Signals v1).

A deterministic, config-driven tool that pulls external macro / rate /
consumer-credit signals from FRED, compares each to its prior valid reading
against a configured threshold, auto-flags breaches, and writes an Excel
workbook the consumer team uses to disposition whether a flagged move matters.

No AI/ML anywhere in the compute path: every flag is pure threshold logic and
every judgment is human. The tool reports and flags; people decide.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
