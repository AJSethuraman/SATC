"""What each monitor needs inlined -- the bundle recipes, as data.

One entry per monitor. Adding a source means adding an entry here, not editing
the inliner.
"""

from __future__ import annotations

from pathlib import Path

from credit_suite.engine.inline import BundleSpec

_SOURCES = Path(__file__).resolve().parent / "sources"

FDIC = BundleSpec(
    name="fdic_monitor",
    workbook="Bank_Peer_Monitor",
    roots=("credit_suite.sources.fdic.layout",
           "credit_suite.sources.fdic.runner",
           "credit_suite.engine.package"),
    layout_module="credit_suite.sources.fdic.layout",
    runner_module="credit_suite.sources.fdic.runner",
    macro_module="PeerMonitor",
    macro_path=_SOURCES / "fdic" / "macro.bas",
    asof="2026-03-31",
    extra_notes=(
        'python runner.py --workbook ".\\\\Bank_Peer_Monitor.xlsm"'
        "           # LIVE -- the FDIC API is KEYLESS",
        'python runner.py --lookup "KeyBank"'
        "                            # find a CERT",
        'python runner.py --workbook ".\\\\Bank_Peer_Monitor.xlsm" --tieout 628'
        "  # verify a value",
        "Peers live in the _config [PEERS] table: edit a row and re-run, no rebuild.",
    ),
)

FRED = BundleSpec(
    name="dashboard",
    workbook="FRED_Credit_Risk_Dashboard",
    roots=("credit_suite.sources.fred.layout",
           "credit_suite.sources.fred.runner",
           "credit_suite.engine.package"),
    layout_module="credit_suite.sources.fred.layout",
    runner_module="credit_suite.sources.fred.runner",
    macro_module="FREDDashboard",
    macro_path=_SOURCES / "fred" / "macro.bas",
    requirements="pandas>=1.5\nopenpyxl>=3.0\nfredapi>=0.5\n",
    asof="2026-03-01",
    extra_notes=(
        'python runner.py --workbook ".\\\\FRED_Credit_Risk_Dashboard.xlsm"'
        "   # LIVE -- needs FRED_API_KEY",
        "Live FRED pulls need a free API key in the FRED_API_KEY environment",
        "variable (or the fred_api_key cell in _config).",
    ),
)

SPECS = {"fdic": FDIC, "fred": FRED}
