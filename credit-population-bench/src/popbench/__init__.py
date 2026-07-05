"""Consumer credit population analysis bench.

A deterministic pandas engine that a bank credit reviewer drives from an
``.xlsm`` surface: load a loan-level consumer-loan flat file, map its (often
inconsistent) headers to a canonical-field contract, validate/clean the
population with a documented audit trail, stratify it (mapped group-bys **and**
user-defined derived cohorts), compute balance- and count-weighted portfolio
metrics, and support documentable judgmental sampling for linesheet review.

Design invariants (see ``docs/prd-credit-population-bench.md``):

- The math lives here in pandas, behind one button; Excel is the load surface
  and the output (values) surface, not a formula engine.
- Every rate ships on **both** a dollar basis and a count basis, always labeled.
- URCCP thresholds are **imported** from the shared credit-core, never forked.
- Nothing is computed on a dirty population: hard errors refuse; only safe,
  declared normalizations run automatically, each recorded.
"""

from __future__ import annotations

__version__ = "0.1.0"
