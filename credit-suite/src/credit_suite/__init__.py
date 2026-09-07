"""credit-suite - the one shared engine behind the Credit-Risk Template Suite.

Each monitor in the suite (FRED, FDIC, bureau, macro, CFPB, EDGAR) is a
*provider adapter* plus a *config seed*; everything else -- config parsing,
transforms, thresholds, the watchlist gate, the workbook builder, house style,
the VBA emitter, provenance and the ASCII bundler -- lives here, once.

See ``docs/prd-credit-suite-consolidation.md`` for scope and the repo-root
``TEMPLATE_CONTRACT.md`` for the contract every monitor must satisfy.
"""

__version__ = "0.1.0"
