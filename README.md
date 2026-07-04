# SATC — a practice-operations tool for a tax office

**SATC** helps a solo tax preparer *run the practice* — collect and retain client
information, track engagements and document requests, and provide small services
like a household withholding estimate. It works **around Drake Tax**, which stays
the system of record for the actual returns. SATC is **not** a tax engine and does
not replace Drake's calculations or e-file.

Everything runs locally on one Windows PC. No cloud account; nothing leaves the
machine by default.

## Get it

**Option A — the app (no Python).** Download **`SATC.exe`** from the
[Releases](../../releases) page and double-click it; it opens SATC in your browser.
Because the app is unsigned, Windows SmartScreen may say *"Windows protected your
PC"* — click **More info → Run anyway** (this is expected for an unsigned app).

**Option B — from source.** Click **Code → Download ZIP**, unzip, open the
`satc_system` folder, and double-click **`install.bat`** once, then **`SATC.bat`**
to start.

New here? Read the **[Windows Quickstart](satc_system/docs/QUICKSTART_WINDOWS.md)** —
install, first run, add a client, collect documents, and the data-safety basics.

## Your client data (read before entering real SSNs)

- Client identity (names, SSNs/EINs) lives in an **encrypted** vault
  (`satc_vault.db`, AES-256; on Windows the key is sealed to your user account).
- It lives in your data folder: `%USERPROFILE%\.satc\data` for the app, or
  `satc_system\build\data\` if you run from source — **the two are separate**, so
  data entered in one mode won't appear in the other.
- **Back up** by copying that folder. **Uninstalling does not delete it.** Keep the
  machine's disk encryption (BitLocker) on, keep the folder out of shared/synced
  drives unless you intend it, and never email the `.db` files.
- See **[Your Data & Security](satc_system/docs/QUICKSTART_WINDOWS.md#your-data--security)**
  for the full picture and your WISP obligations.

## Drive it with an AI assistant (optional)

SATC can be driven from Claude Desktop / Cowork in plain language. By default the
agent is **read-only** — it can look things up and run withholding, but cannot
change client records. See **[Using SATC with an agent](satc_system/docs/MCP.md)**.

## Documentation

| Doc | For |
|-----|-----|
| [Windows Quickstart](satc_system/docs/QUICKSTART_WINDOWS.md) | New users — install → first return, + data safety & troubleshooting |
| [Using SATC with an agent](satc_system/docs/MCP.md) | Connecting Claude Desktop / Cowork |
| [Architecture](satc_system/ARCHITECTURE.md) | Maintainers — where each piece lives |
| [Developing](satc_system/docs/DEVELOPING.md) | Running from source, tests, workbook build |
| [Data Model](satc_system/docs/DATA_MODEL.md) · [Methodology](satc_system/docs/METHODOLOGY.md) | Design detail |

> **Repo status:** active development happens on a feature branch; `main` holds the
> last released state. Check the [Releases](../../releases) page for the current build.
