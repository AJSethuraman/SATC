"""SATC tool implementations — the read/write operations exposed over MCP.

These are plain functions (no ``mcp`` dependency) so they're unit-testable on
their own; :mod:`satc.api.mcp_server` wraps each as an MCP tool. Everything goes
through :class:`~satc.app.state.AppState`, which shares the local SQLite store
with the desktop app — so what Cowork writes here shows up in the app, and vice
versa.

Reads stay de-identified: ``get_client`` returns the *public* projection (masked
TIN, last-4), never the vault's full legal name / SSN.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal


def _to_json(obj):
    """Recursively convert dataclasses / Decimals / dates to JSON-safe values."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_json(x) for x in obj]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _to_json(dataclasses.asdict(obj))
    return obj


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------

def list_clients(state) -> list[dict]:
    """Every client in the practice (de-identified: id + display name)."""
    return [{"client_id": cid, "name": name} for cid, name in state.client_choices()]


def get_client(state, client_id: str) -> dict:
    """A client's public record, returns, line items (with provenance), and documents."""
    pc = state.public_client(client_id)
    if pc is None:
        return {"error": f"client {client_id!r} not found"}
    rets = [r for r in state.returns() if r.client_id == client_id]
    rk_set = {r.return_key for r in rets}
    lines = [li for li in state.mart.line_items if li.return_key in rk_set]
    docs = [d for d in state.documents() if d.client_id == client_id]
    return {
        "client_id": client_id,
        "name": state.name(client_id),
        "public_client": _to_json(pc),
        "returns": _to_json(rets),
        "line_items": _to_json(lines),
        "documents": _to_json(docs),
    }


def estimate_withholding(payload: dict) -> dict:
    """Full-year federal withholding estimate from an EstimatorInput dict."""
    from satc.withholding import EstimatorInput, estimate
    try:
        result = estimate(EstimatorInput.from_dict(payload))
    except Exception as exc:  # noqa: BLE001 - surface bad input as data, not a crash
        return {"error": str(exc)}
    return _to_json(result)


def read_paystub(text: str) -> dict:
    """Parse pasted paystub text into labeled figures (heuristic, no file needed)."""
    from satc.ingest.readers.paystub import PaystubReader
    read = PaystubReader().read_text(text or "")
    return {"labeled_fields": read.labeled_fields, "uncertain": sorted(read.uncertain_labels)}


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------

def create_person_client(state, *, first_name: str, last_name: str, ssn: str = "",
                         email: str = "", phone: str = "", address: dict | None = None) -> dict:
    """Create an individual client (identity -> vault, de-identified projection -> mart)."""
    cid = state.create_person_client(first_name=first_name, last_name=last_name, ssn=ssn,
                                     email=email, phone=phone, address=address)
    return {"client_id": cid, "name": state.name(cid)}


def create_business_client(state, *, legal_name: str, entity_type: str = "SCORP", ein: str = "",
                           email: str = "", phone: str = "", address: dict | None = None) -> dict:
    """Create a business client (S-corp / partnership / etc.)."""
    cid = state.create_business_client(legal_name=legal_name, entity_type=entity_type, ein=ein,
                                       email=email, phone=phone, address=address)
    return {"client_id": cid, "name": state.name(cid)}


def run_intake(state, *, folder: str, client_id: str, tax_year: int = 2024) -> dict:
    """Classify + stage every document in a LOCAL folder for a client; returns a summary."""
    return _to_json(state.run_intake(folder, client_id=client_id, tax_year=tax_year))


def post_confirmed_intake(state, *, client_id: str, tax_year: int = 2024) -> dict:
    """Post the gate's CONFIRMED staged values onto the client's return as line items."""
    return _to_json(state.post_confirmed(client_id=client_id, tax_year=tax_year))


def set_document_status(state, *, document_id: str, status: str) -> dict:
    """Set a document's status (Requested / Received / Sent / Signed / N/A)."""
    state.set_document_status(document_id, status)
    return {"ok": True, "document_id": document_id, "status": status}
