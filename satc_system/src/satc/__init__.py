"""SATC tax line-sheet system + client data mart.

A Drake-adjacent layer for Sethuraman Accounting, Tax & Consulting (SATC). This
package is NOT a tax engine and does not replace Drake's calculation/e-file. It
provides:

  * client intake + a document-extraction engine with a staging/confirmation gate
  * config-driven per-return workpapers ("line sheets") with cross-checks
  * a dated/versioned tax-law reference layer ("crosswalk")
  * a normalized, year-over-year client data mart with roll-forward / proforma
  * a Drake preparer-set parser + client communication generator
  * a document & communication repository and practice dashboards

Hard architectural rule: sensitive PII (full SSN/EIN, raw source documents) never
lives in the workbook. Identity lives in an external, access-controlled vault; the
working data mart stores only de-identified or masked values keyed by stable ids.
The whole data model is designed to port to SQL with no restructuring.
"""

__all__ = ["__version__"]

__version__ = "0.7.1"
