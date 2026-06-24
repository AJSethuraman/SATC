# SATC Withholding — a Cowork plugin

Drive SATC's **withholding estimator** in plain language. An agent (Claude Code /
Cowork) asks the running SATC desktop app to project a household's full-year
federal withholding and recommend a **W-4 line-4c** adjustment — through the
app's local JSON API.

It follows the four-layer pattern from `BUILDING_A_COWORK_PLUGIN.md`:

```
agent (Cowork)  ->  this plugin (skill + MCP config)  ->  MCP server (HTTP proxy)  ->  SATC app's /api/withholding/*
```

The MCP server is a **thin adapter**: each tool is one HTTP call to the app. It
imports no SATC internals and keeps no state — the app stays the source of
truth. **Scope: withholding compute only.** It is stateless, writes nothing, and
touches no client PII (no vault, no data mart), so there is no destructive action
to confirm.

## What's here

```
cowork-plugin/
├── .claude-plugin/plugin.json     # plugin manifest
├── mcp/
│   ├── satc_mcp.py                # the MCP server (FastMCP, HTTP proxy)
│   └── requirements.txt           # mcp>=1.2.0, httpx>=0.27.0
├── mcp.json.template              # MCP config -> rename to .mcp.json
├── mcpb/manifest.json             # optional .mcpb (Desktop Extension) bundle
└── skills/satc-withholding/SKILL.md
```

## Tools (all read/compute — none destructive)

| Tool | Calls | Does |
|------|-------|------|
| `satc_withholding_meta` | `GET /api/withholding/meta` | Accepted filing statuses, pay frequencies, default year, field guide. **Call first.** |
| `satc_read_paystub` | `POST /api/withholding/read-paystub` | Parse pasted paystub text into labeled figures (on-device). |
| `satc_estimate_withholding` | `POST /api/withholding/estimate` | Full-year projection + W-4 line-4c recommendation. |

## Setup

1. **Run the SATC app** on the same machine, with a pinned port:
   ```bash
   SATC_PORT=5050 satc-app        # Windows: set SATC_PORT=5050 && satc-app
   ```
   It prints `http://127.0.0.1:5050`. Leave the window open.

2. **Install the MCP server's deps:**
   ```bash
   pip install -r cowork-plugin/mcp/requirements.txt
   ```

3. **Activate the MCP config:** review `mcp.json.template` and rename it to
   `.mcp.json` at the plugin root (adjust `SATC_BASE_URL` if your app's port
   differs).

4. **Smoke-test the server standalone** (app running):
   ```bash
   python cowork-plugin/mcp/satc_mcp.py
   ```

Then load the plugin in Cowork and say *"do a paycheck withholding checkup"* —
the `satc-withholding` skill orchestrates the three tools.

## Notes

- **Pin the port.** The app auto-picks a free port if 5050 is taken; setting
  `SATC_PORT=5050` keeps `SATC_BASE_URL` stable.
- **No PII.** This plugin only does stateless withholding math. The fuller
  in-process `satc-mcp` server (create clients, run intake, post a return) lives
  in the main package and is the path for read+write client work later — but it
  imports SATC internals and shares the local store, so it is intentionally *not*
  part of this withholding plugin.
