"""SATC withholding — an MCP server for Cowork (a thin HTTP proxy).

Architecture (see ../README.md and the BUILDING_A_COWORK_PLUGIN blueprint):

    agent  ->  this MCP server  ->  the running SATC app's local JSON API

Each tool is ONE HTTP call to the SATC desktop app. This server imports no SATC
internals and owns no state — the app is the source of truth. Withholding is
stateless compute: these tools read figures and calculate; they never write a
ledger and never touch a stored client record, so none of them is destructive.

Configure the target with an env var (defaults to the app's default port):

    SATC_BASE_URL   http://127.0.0.1:5050
    SATC_TIMEOUT    30   (seconds)

Smoke-test it standalone (with the SATC app running):

    pip install -r requirements.txt
    python satc_mcp.py
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("SATC_BASE_URL", "http://127.0.0.1:5050").rstrip("/")
TIMEOUT = float(os.environ.get("SATC_TIMEOUT", "30"))

mcp = FastMCP("satc-withholding")  # tools are namespaced under this server name


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


def _get(path: str, **params: Any) -> Any:
    with _client() as c:
        r = c.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()


def _post(path: str, payload: dict | None = None) -> Any:
    with _client() as c:
        try:
            r = c.post(path, json=payload or {})
        except httpx.ConnectError as exc:  # app not running / wrong port
            raise RuntimeError(
                f"Can't reach the SATC app at {BASE_URL}. Is it running? "
                f"Start it (SATC_PORT=5050 satc-app) or fix SATC_BASE_URL. ({exc})"
            ) from exc
        if r.status_code >= 400:  # surface the API's own guard message, not a stack trace
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise RuntimeError(f"SATC API {r.status_code}: {detail}")
        data = r.json()
        # The compute endpoint reports bad input as {"error": ...} with HTTP 200 —
        # never let that read as a silent success (blueprint §3.6).
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"SATC: {data['error']}")
        return data


@mcp.tool()
def satc_withholding_meta() -> dict:
    """Accepted estimate inputs — filing statuses, pay frequencies, the default
    tax year, and a one-line guide to each field. Read-only. CALL THIS FIRST so
    the figures you assemble match exactly what the estimator validates."""
    return _get("/api/withholding/meta")


@mcp.tool()
def satc_read_paystub(text: str) -> dict:
    """Parse pasted paystub TEXT into labeled figures (gross pay, federal tax
    withheld, year-to-date amounts, pay frequency). Read-only and on-device —
    nothing is stored or sent anywhere. Use it to turn a paystub the user pastes
    into the numbers an estimate needs. Returns ``labeled_fields`` plus
    ``uncertain`` (labels the reader was unsure about) — show the user the
    figures and confirm anything in ``uncertain`` before relying on it."""
    return _post("/api/withholding/read-paystub", {"text": text})


@mcp.tool()
def satc_estimate_withholding(payload: dict) -> dict:
    """Full-year federal withholding projection + per-paycheck W-4 (line 4c)
    recommendation for a household. Stateless compute: it writes nothing and
    touches no client record, so it is safe to call without confirmation.

    ``payload`` is an EstimatorInput dict (call ``satc_withholding_meta`` first
    for the accepted values)::

        {"filing_status": "married_jointly", "tax_year": 2025,
         "jobs": [{"pay_frequency": "biweekly", "gross_pay_per_period": "2500",
                   "federal_tax_withheld_per_period": "300",
                   "ytd_taxable_wages": "30000", "ytd_federal_tax_withheld": "3600",
                   "pay_periods_remaining": 12}],
         "other_income": {...}, "deductions": {...}, "prior_year_tax": "..."}

    Returns ``breakdown`` (total tax liability, projected withholding) and
    ``recommendation`` (projected balance + suggested additional 4c per period),
    plus any ``notes`` (e.g. a tax-year fallback). Bad input is raised as an
    error, not returned as an empty success."""
    return _post("/api/withholding/estimate", payload)


if __name__ == "__main__":
    mcp.run()
