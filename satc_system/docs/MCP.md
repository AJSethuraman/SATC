# Using SATC with an AI assistant (Claude Desktop / Cowork)

`satc-mcp` is an [MCP](https://modelcontextprotocol.io) server that exposes SATC to
a Claude agent as structured tools, so you can drive SATC in plain English —
look up clients and run withholding checkups, and (only if you turn it on) create
clients and post intake.

**Safe by default.** The agent gets only **read + compute** tools. It **cannot**
create clients, post to a return, run intake, or change a document's status unless
you explicitly enable writes with `SATC_MCP_ALLOW_WRITES=1`. An agent can't call a
tool that was never registered, so this is enforced by the wiring, not by trust.

It shares the **same local store** as the desktop app (`~/.satc/data`, or
`SATC_DATA_DIR`), so the agent reads the app's data, and anything you commit in the
app is what the agent sees. Reads are **de-identified** — the agent gets the display
label + masked TIN, never the legal name or full SSN. (The vault is encrypted at
rest; see the Quickstart's *Your Data & Security*.)

## Set it up (the easy way — bundled exe, no Python)

The `SATC.exe` build runs as the agent server when launched with `--mcp`, so you can
point Claude Desktop straight at it. In **Claude Desktop → Settings → Extensions →
Install Extension…**, choose the SATC `.mcpb` bundle (or add the server manually):

```json
{
  "mcpServers": {
    "satc": { "command": "C:\\path\\to\\SATC.exe", "args": ["--mcp"] }
  }
}
```

No JSON editing is needed if you install the `.mcpb`; the extension UI handles it.

## Set it up (from source)

```bash
cd satc_system
pip install -e ".[local,mcp]"       # install.bat already installs this
```

Then point your agent at the `satc-mcp` command. In **Claude Code**:

```bash
claude mcp add satc -- satc-mcp
```

…or in a config file (Claude Desktop's `claude_desktop_config.json`, or an
`.mcp.json`). On Windows the command is the full path to the installed shim, e.g.
`C:\path\to\satc_system\.venv\Scripts\satc-mcp.exe` (a plain `satc-mcp` only works
if that folder is on `PATH`).

## Tools

**Read + compute (always available):**
- `list_clients()` — every client, de-identified (id + display label).
- `get_client(client_id)` — public record, returns, line items (with provenance), documents.
- `estimate_withholding(payload)` — full-year federal projection + W-4 (4c) recommendation.
  `payload` is an `EstimatorInput` dict (`filing_status`, `jobs:[…]`, `tax_year`, …).
- `read_paystub(text)` — parse pasted paystub text into labeled figures.

**Write (only when `SATC_MCP_ALLOW_WRITES=1`):**
- `create_person_client(...)` / `create_business_client(...)` — write identity to the vault.
- `run_intake(folder, client_id, tax_year)` — classify + **stage** a local folder (staged, not trusted).
- `post_confirmed_intake(client_id, tax_year)` — post **confirmed** staged values onto the return.
- `set_document_status(document_id, status)`

## Trust & privacy boundary

- **Read-only by default** — the recommended posture. The agent can't change client
  data unless you set `SATC_MCP_ALLOW_WRITES=1` when launching the server.
- **Reads are de-identified** — `list_clients`/`get_client` return the display label
  and masked TIN, never the legal name or full SSN.
- **Local, over stdio, no network auth** — whoever can launch the server has whatever
  access it was started with. Don't expose it beyond the machine.
- **The staging gate is per-process:** if you enable writes and run intake through the
  agent, confirm and post it *in the same agent session* — those staged figures don't
  appear on the app's `/staging` screen (a separate process).

## How it's built

`satc/api/tools.py` holds the plain (mcp-free, unit-tested) tool functions;
`satc/api/mcp_server.py` is a thin FastMCP wrapper. `_build_server(allow_writes)`
registers the read tools always and the write tools only when writes are enabled;
`main()` reads `SATC_MCP_ALLOW_WRITES` from the environment. To add a tool, write it
in `tools.py` and register it in `_build_server()`.
