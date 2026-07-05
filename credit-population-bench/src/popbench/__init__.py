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


def _ensure_shared_core_on_path() -> None:
    """Make the shared ``satc_credit_core`` importable at runtime from a dev
    checkout (the emailable ASCII bundle vendors it, so this is a no-op there).

    Guarded: only acts if the package isn't already importable, so it never
    shadows an installed/vendored copy."""
    try:
        import satc_credit_core  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    import sys
    from pathlib import Path

    # src/popbench/__init__.py -> parents[3] is the repo root; the shared
    # package's project dir sits beside this project there.
    candidate = Path(__file__).resolve().parents[3] / "satc_credit_core"
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


_ensure_shared_core_on_path()
