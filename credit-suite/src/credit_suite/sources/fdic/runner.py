#!/usr/bin/env python3
"""Bank Peer Monitor -- the FDIC runner, on the shared credit-suite engine.

    python runner.py --workbook Bank_Peer_Monitor.xlsm [--demo] [--asof YYYY-MM-DD]
    python runner.py --lookup "KeyBank"            resolve a name to a CERT
    python runner.py -w BOOK.xlsm --tieout 628 [20260331]

Exit codes (TEMPLATE_CONTRACT section 4): 0 OK, 1 run error, 2 gate error,
3 missing secret. JSON status on stdout, human summary on stderr.

Everything generic lives in ``credit_suite.engine``. What is here is FDIC's:
the status wording, the three digest annotations (merger survivorship, the
uninsured-deposit null, the roster ACTIVE flag), the tie-out rendering against
the Call Report facsimile, and the CERT lookup.

The status dict keeps FDIC's published key names (``banks``, ``cert``,
``texas``, ``set_max_repdte``) rather than the engine's generic ones. That is a
deliberate compatibility surface: the monitoring email and the acceptance
harness read those keys, and renaming them would be an output change in a change
whose whole purpose is that outputs do not change.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from typing import Dict, List, Optional

from credit_suite.engine import runtime
from credit_suite.engine.config import Config
from credit_suite.engine.digest import EntityContext
from credit_suite.engine.gates import EntityCapacityError, WatchlistRefused
from credit_suite.engine.metrics import MetricError
from credit_suite.engine.provider import MissingSecret, resolve_secret
from credit_suite.engine.workbook import OpenpyxlBackend, RawLayoutMismatch
from credit_suite.sources.fdic import adapter, fields
from credit_suite.sources.fdic.engine_api import (DASH_TABS, STATUS_COL,
                                                  STATUS_COL_BY_TAB)
from credit_suite.sources.fdic.spec import FDIC

CDR_FACSIMILE_URL = ("https://cdr.ffiec.gov/public/ManageFacsimiles.aspx"
                     "?cert={cert}&dt={mmddyyyy}")
BANKFIND_URL = "https://banks.data.fdic.gov/bankfind-suite/bankfind?name={cert}"


# --------------------------------------------------------------------------
# FDIC's digest annotations -- what makes a blank or an odd figure auditable
# --------------------------------------------------------------------------

def annotate_merger_survivorship(ctx: EntityContext) -> List[str]:
    """Trap F6: a >25% single-quarter asset jump usually means an acquisition,
    which makes every ratio and growth screen for that quarter unreliable."""
    if len(ctx.periods) < 2:
        return []
    newest = ctx.periods[0][1].get("ASSET")
    prior = ctx.periods[1][1].get("ASSET")
    if newest is None or prior in (None, 0):
        return []
    jump = (newest / prior - 1.0) * 100.0
    if jump <= 25.0:
        return []
    return ["ASSET +%.0f%% in one quarter -- possible merger survivorship "
            "distortion (trap F6); ratios and CRE growth screens unreliable "
            "this quarter." % jump]


def annotate_uninsured_deposit_null(ctx: EntityContext) -> List[str]:
    """Trap F3, made auditable: DEPUNINS is genuinely null below the $1B
    reporting threshold, so the blank is explained rather than shown as 0."""
    if not ctx.latest_fields:
        return []
    if ctx.latest_fields.get("DEPUNINS") is not None:
        return []
    if not any(v is not None for v in ctx.latest_fields.values()):
        return []
    return ["DEPUNINS is null this quarter -- uninsured-deposit share left "
            "BLANK, never 0 (RC-O Mem 2 is filed by $1B+ reporters; smaller "
            "banks carry FDIC estimates or nulls)."]


def annotate_roster_inactive(ctx: EntityContext) -> List[str]:
    """The institutions roster is the independent check on a bank still being
    a bank -- a merged one keeps answering the financials endpoint."""
    roster = ctx.roster_row
    if not roster:
        return []
    active = str(roster.get("ACTIVE", "1")).strip()
    if active in ("1", "True", "true"):
        return []
    return ["roster reports ACTIVE=%s (ENDEFYMD=%s) -- possible "
            "merger/closure; check /institutions and /history."
            % (roster.get("ACTIVE"), roster.get("ENDEFYMD"))]


ANNOTATORS = (annotate_merger_survivorship, annotate_uninsured_deposit_null,
              annotate_roster_inactive)


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def _to_published_status(status: dict) -> dict:
    """The engine's generic keys -> FDIC's published ones.

    Not cosmetic: the monitoring email and the acceptance harness read these
    names, and a rename would be an output change inside a change whose whole
    purpose is that outputs do not change.
    """
    digest = status.pop("digest")
    banks = []
    for entity in digest["entities"]:
        bank = dict(entity)
        bank["cert"] = bank.pop("key")
        bank["texas"] = bank.pop("headline")
        banks.append(bank)

    out = dict(status)
    out["peer_slots"] = out.pop("entity_slots")
    out["banks_active"] = out.pop("entities_active")
    out["banks_landed"] = out.pop("entities_landed")
    out["banks_excluded"] = out.pop("entities_excluded")
    out["alert_banks"] = out.pop("alert_entities")
    out["watch_banks"] = out.pop("watch_entities")
    out["stale_banks"] = out.pop("stale_entities")
    out["digest"] = {"banks": banks, "medians": digest["medians"],
                     "set_max_repdte": digest["set_max_period"]}
    return out


def status_lines(status: dict) -> List[str]:
    """The three status-panel lines, in FDIC's vocabulary."""
    line2 = ("Banks %s/%s - %s ALERT / %s WATCH / %s STALE"
             % (status.get("banks_landed", 0), status.get("banks_active", 0),
                status.get("alert_banks", 0), status.get("watch_banks", 0),
                status.get("stale_banks", 0)))
    refused = len(status.get("watchlist_refusals") or [])
    if refused:
        line2 += " - %d REFUSED (see digest)" % refused
    errors = len(status.get("errors") or [])
    if errors:
        line2 += " - %d FETCH ERRORS (slots blanked)" % errors
    return [
        "Last run  %s (%s)" % (status.get("timestamp", ""), status.get("mode", "")),
        line2,
        "FDIC data vintage: %s" % (status.get("vintage") or "n/a"),
    ]


def run(workbook_path: str, demo: bool = False, asof: Optional[date] = None,
        provider=None) -> dict:
    """One refresh against the CLOSED workbook.

    ``provider`` is injectable so a test can drive a frozen or failing source
    without the runner knowing how one is built.
    """
    asof = asof or date.today()
    backend = OpenpyxlBackend(workbook_path, FDIC, fields.RAW_FIELDS)
    cfg = backend.read_config()

    if provider is None:
        provider = adapter.make_provider(cfg, demo, asof)
    mode = "demo" if isinstance(provider, adapter.FdicDemoProvider) else "live"

    status = runtime.run_refresh(
        backend=backend, cfg=cfg, provider=provider,
        registry=fields.REGISTRY, fields=fields.RAW_FIELDS,
        field_units=fields.FIELD_UNITS, asof=asof, mode=mode,
        annotators=ANNOTATORS, headline_metric="TEXAS",
        secret=resolve_secret(cfg))

    published = _to_published_status(status)
    backend.write_status_lines(status_lines(published), DASH_TABS,
                               STATUS_COL_BY_TAB, STATUS_COL)
    backend.finalize()
    return published


# --------------------------------------------------------------------------
# tie-out (contract section 12) and lookup (section 13)
# --------------------------------------------------------------------------

def facsimile_url(cert: str, iso: str) -> str:
    parts = str(iso)[:10].split("-")
    return CDR_FACSIMILE_URL.format(cert=cert,
                                    mmddyyyy="%s%s%s" % (parts[1], parts[2],
                                                         parts[0]))


def bankfind_url(cert: str) -> str:
    return BANKFIND_URL.format(cert=cert)


def read_provenance_rows(wb) -> Dict[str, dict]:
    """Parse the `_provenance` tab into ``{field: {...}}``. Empty when absent."""
    if "_provenance" not in wb.sheetnames:
        return {}
    ws = wb["_provenance"]
    rows: Dict[str, dict] = {}
    started = False
    for row in ws.iter_rows(values_only=True):
        first = "" if not row or row[0] is None else str(row[0]).strip()
        if not started:
            started = first.lower() == "field"
            continue
        if not first:
            continue
        cells = list(row) + [None] * 6
        rows[first] = {
            "field": first, "schedule": cells[1] or "", "caption": cells[2] or "",
            "mdrm": cells[3] or "", "flag": cells[4] or "", "notes": cells[5] or "",
        }
    return rows


def _cmd_lookup(name: str, demo: bool) -> int:
    if demo:
        print("--lookup needs the live FDIC API (it resolves a real CERT); "
              "it is not available in --demo.", file=sys.stderr)
        return runtime.EXIT_GATE_ERROR
    try:
        matches = adapter.FdicProvider().lookup(name)
    except Exception as exc:                       # noqa: BLE001
        print("lookup failed: %s" % exc, file=sys.stderr)
        return runtime.EXIT_RUN_ERROR
    if not matches:
        print("no institution matched %r." % name, file=sys.stderr)
        return runtime.EXIT_OK
    print("%-8s %-7s %-14s %-4s %s" % ("CERT", "ACTIVE", "ASSET($000)", "ST",
                                       "NAME"))
    for row in matches:
        print("%-8s %-7s %-14s %-4s %s"
              % (row.get("CERT", ""), row.get("ACTIVE", ""),
                 row.get("ASSET", ""), row.get("STALP", ""), row.get("NAME", "")))
    print("\nPaste the CERT into the [PEERS] table in _config, then re-run.",
          file=sys.stderr)
    return runtime.EXIT_OK


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Bank Peer Monitor refresh")
    ap.add_argument("-w", "--workbook", default=None,
                    help="path to the .xlsm (required unless --lookup)")
    ap.add_argument("--demo", action="store_true",
                    help="deterministic offline provider; no key, no network")
    ap.add_argument("--asof", default=None, help="YYYY-MM-DD (testing)")
    ap.add_argument("--lookup", metavar="NAME", default=None,
                    help="resolve an institution name to its CERT (live only)")
    ap.add_argument("--tieout", nargs="+", metavar="ARG", default=None,
                    help="CERT [REPDTE] -- print each value with its source")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.lookup:
        return _cmd_lookup(args.lookup, args.demo)
    if not args.workbook:
        print("--workbook is required (or use --lookup).", file=sys.stderr)
        return runtime.EXIT_GATE_ERROR
    if args.tieout is not None and len(args.tieout) > 2:
        print("--tieout takes CERT [REPDTE].", file=sys.stderr)
        return runtime.EXIT_GATE_ERROR

    asof = (datetime.strptime(args.asof, "%Y-%m-%d").date()
            if args.asof else None)
    try:
        status = run(args.workbook, demo=args.demo, asof=asof)
    except (WatchlistRefused, MetricError, EntityCapacityError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        print("GATE ERROR: %s" % exc, file=sys.stderr)
        return runtime.EXIT_GATE_ERROR
    except MissingSecret as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        print("MISSING SECRET: %s" % exc, file=sys.stderr)
        return runtime.EXIT_MISSING_SECRET
    except (RawLayoutMismatch, Exception) as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}))
        print("RUN ERROR: %s" % exc, file=sys.stderr)
        return runtime.EXIT_RUN_ERROR

    ok = runtime.run_succeeded({
        "entities_active": status["banks_active"],
        "entities_landed": status["banks_landed"]})
    payload = {"ok": ok, **{k: v for k, v in status.items() if k != "digest"}}
    print(json.dumps(payload))

    print("%s: %s/%s banks landed, %s ALERT / %s WATCH / %s STALE banks "
          "(%s ALERT flags), refused=%s, vintage=%s"
          % ("OK (demo)" if status["mode"] == "demo" else "OK",
             status["banks_landed"], status["banks_active"],
             status["alert_banks"], status["watch_banks"],
             status["stale_banks"], status["alert_flags"],
             len(status["watchlist_refusals"]), status["vintage"]),
          file=sys.stderr)
    return runtime.EXIT_OK if ok else runtime.EXIT_NOTHING_PULLED


if __name__ == "__main__":
    raise SystemExit(main())
