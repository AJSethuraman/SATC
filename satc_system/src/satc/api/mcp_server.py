"""MCP server exposing SATC to a Claude agent (Cowork) — safe by default.

Run it over stdio::

    satc-mcp

Safe by default: the agent gets only READ + COMPUTE tools (list/get clients,
estimate withholding, read paystubs) — it cannot create clients, post to a
return, run intake, or change a document's status. Those WRITE tools are opt-in:
set ``SATC_MCP_ALLOW_WRITES=1`` to expose them. So the thing you launch can't
touch the book of record unless you deliberately turn writes on.

It shares the local SQLite store with the desktop app (``~/.satc/data``, or
``SATC_DATA_DIR``). Reads are de-identified (the public projection's display
label + masked TIN, never the vault's legal name or full SSN) and reload the
store first, so the agent always sees the app's latest committed data.

State sharing: this server is its own process. Durable writes (clients, posted
returns, document status) go to the shared store and appear in the app on its
next reload. The in-memory *staging gate* (``run_intake`` -> confirm ->
``post_confirmed_intake``), however, is private to THIS process and is NOT shared
with the app's ``/staging`` screen — run intake and post it within one agent
session rather than staging here and confirming in the app (or vice-versa).

Requires the optional ``mcp`` dependency::

    pip install -e ".[mcp]"

Connect it to Claude Code / Cowork (stdio) — safe (read-only) by default::

    claude mcp add satc -- satc-mcp

or in an ``.mcp.json`` (the bundled desktop exe serves the same server via
``SATC.exe --mcp``)::

    { "mcpServers": { "satc": { "command": "satc-mcp" } } }
"""

from __future__ import annotations

from satc.api import tools


def _build_server(allow_writes: bool = False):
    # Imported lazily so importing this module (and the rest of SATC) never hard-
    # depends on the optional `mcp` package.
    from mcp.server.fastmcp import FastMCP

    from satc.app.state import AppState

    state = AppState()
    mcp = FastMCP("satc")

    # ---- read ----

    @mcp.tool()
    def list_clients() -> list[dict]:
        """List every client in the practice (de-identified: id + display label,
        never the vault legal name)."""
        state.reload()  # pick up anything the desktop app committed since the last call
        return tools.list_clients(state)

    @mcp.tool()
    def get_client(client_id: str) -> dict:
        """A client's public record, returns, line items (with provenance), and documents.

        De-identified — the legal name / full SSN stays in the vault, never returned here.
        """
        state.reload()  # see the app's latest committed data
        return tools.get_client(state, client_id)

    @mcp.tool()
    def estimate_withholding(payload: dict) -> dict:
        """Full-year federal withholding estimate + per-paycheck W-4 (line 4c) recommendation.

        ``payload`` is an EstimatorInput dict, e.g.::

            {"filing_status": "married_jointly", "tax_year": 2025,
             "jobs": [{"pay_frequency": "biweekly", "gross_pay_per_period": "2500",
                       "federal_tax_withheld_per_period": "300",
                       "ytd_taxable_wages": "30000", "ytd_federal_tax_withheld": "3600"}],
             "other_income": {...}, "deductions": {...}, "prior_year_tax": "..."}
        """
        return tools.estimate_withholding(payload)

    @mcp.tool()
    def read_paystub(text: str) -> dict:
        """Parse pasted paystub text into labeled figures (gross, federal withheld, YTD, frequency)."""
        return tools.read_paystub(text)

    if not allow_writes:
        # Safe by default: read + compute only — the agent cannot change the book
        # of record. Writes are opt-in via SATC_MCP_ALLOW_WRITES=1 (or
        # _build_server(allow_writes=True)).
        return mcp

    # ---- write (opt-in; shares the store with the desktop app) ----

    @mcp.tool()
    def create_person_client(first_name: str, last_name: str, ssn: str = "",
                             email: str = "", phone: str = "", address: dict | None = None) -> dict:
        """Create an individual client. Identity (name/SSN) -> vault; de-identified projection -> mart."""
        return tools.create_person_client(state, first_name=first_name, last_name=last_name,
                                          ssn=ssn, email=email, phone=phone, address=address)

    @mcp.tool()
    def create_business_client(legal_name: str, entity_type: str = "SCORP", ein: str = "",
                               email: str = "", phone: str = "", address: dict | None = None) -> dict:
        """Create a business client (S-corp / partnership / C-corp / etc.)."""
        return tools.create_business_client(state, legal_name=legal_name, entity_type=entity_type,
                                            ein=ein, email=email, phone=phone, address=address)

    @mcp.tool()
    def run_intake(folder: str, client_id: str, tax_year: int = 2024) -> dict:
        """Classify + stage every document in a LOCAL folder for a client. Returns a summary.

        Values are *staged*, not trusted. Staging lives in THIS server's in-memory gate
        (a separate process from the desktop app), so confirm and post them within this
        same agent session — they will NOT appear on the app's /staging screen.
        """
        return tools.run_intake(state, folder=folder, client_id=client_id, tax_year=tax_year)

    @mcp.tool()
    def post_confirmed_intake(client_id: str, tax_year: int = 2024) -> dict:
        """Post THIS session's CONFIRMED staged values onto the client's return as line
        items. Durable once posted (shows up in the app on its next reload)."""
        return tools.post_confirmed_intake(state, client_id=client_id, tax_year=tax_year)

    @mcp.tool()
    def set_document_status(document_id: str, status: str) -> dict:
        """Set a document's status (Requested / Received / Sent / Signed / N/A)."""
        return tools.set_document_status(state, document_id=document_id, status=status)

    return mcp


def main() -> None:
    """Console-script entry point (``satc-mcp``): run the server over stdio.

    Safe by default (read + compute). Set ``SATC_MCP_ALLOW_WRITES=1`` to also
    expose the write tools (create clients, run intake, post returns, set
    document status) — only if you want the agent to change client data.
    """
    import os

    allow = os.environ.get("SATC_MCP_ALLOW_WRITES", "").strip().lower() in {"1", "true", "yes"}
    _build_server(allow_writes=allow).run()


if __name__ == "__main__":
    main()
