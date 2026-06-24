# SATC over MCP — letting a Claude agent (Cowork) drive SATC

`satc-mcp` is an [MCP](https://modelcontextprotocol.io) server that exposes SATC's
read **and** write operations as structured tools, so a Claude agent can create
clients, ingest documents, post intake, and run withholding estimates
programmatically — no clicking the web UI.

It shares the **same local SQLite store** as the desktop app (`~/.satc/data`, or
`SATC_DATA_DIR`). Anything the agent writes shows up in the app, and vice-versa.

## Install & run

```bash
cd satc_system
pip install -e ".[local,mcp]"     # adds the `mcp` SDK
satc-mcp                          # runs the server over stdio
```

## Connect it to Claude Code / Cowork

```bash
claude mcp add satc -- satc-mcp
```

…or add it to an `.mcp.json`:

```json
{ "mcpServers": { "satc": { "command": "satc-mcp" } } }
```

Point `SATC_DATA_DIR` at the same folder the desktop app uses if you've customized it.

## Tools

**Read**
- `list_clients()` — every client (de-identified: id + display name).
- `get_client(client_id)` — public record, returns, line items (with provenance), documents.
- `estimate_withholding(payload)` — full-year federal projection + W-4 (4c) recommendation. `payload` is an `EstimatorInput` dict (`filing_status`, `jobs:[…]`, `tax_year`, `other_income`, `deductions`, `prior_year_tax`, …).
- `read_paystub(text)` — parse pasted paystub text into labeled figures.

**Write** (shares the store with the app)
- `create_person_client(first_name, last_name, ssn=…, email=…, phone=…, address=…)`
- `create_business_client(legal_name, entity_type=…, ein=…, …)`
- `run_intake(folder, client_id, tax_year)` — classify + **stage** a local folder of documents (values are staged, not trusted, until confirmed).
- `post_confirmed_intake(client_id, tax_year)` — post **confirmed** staged values onto the return as line items.
- `set_document_status(document_id, status)`

## Trust & privacy boundary

- **Reads stay de-identified.** `get_client` returns the *public projection* (masked TIN / last-4), never the vault's full legal name or SSN.
- **Writes do touch the vault** (e.g., `create_person_client` stores the SSN in the identity vault). The vault is local and, today, **unencrypted** — same as the desktop app.
- **No auth.** `satc-mcp` runs locally over stdio; whoever can launch it has full read+write to the local data. That's the same trust boundary as double-clicking the app. Don't expose it beyond the machine without adding authentication.

## How it's built

`satc/api/tools.py` holds the plain (mcp-free, unit-tested) tool functions;
`satc/api/mcp_server.py` is a thin FastMCP wrapper that registers each one against
a shared `AppState`. To add a tool: write it in `tools.py`, then register it in
`_build_server()`.
