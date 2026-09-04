# Written Information Security Program — DRAFT

**Sethuraman Accounting, Tax & Consulting LLP (SATC)**

---

> ## ⚠️ THIS IS A DRAFT. IT IS NOT IN FORCE.
>
> **Prepared by software on 4 September 2026**, by reading this repository and
> measuring this machine. **Revised the same day** to record three decisions the
> owner has since made — retention (A9), compensating controls in place of MFA
> (A4a), and the cloud vision fallback (A5, control A5-C). It is **not legal
> advice**, it has **not** been reviewed by a lawyer, and **nobody has signed
> it**.
>
> **The three answers did not make this document shorter.** One gap closed (B7),
> one narrowed to a missing signature (B3), one got *more* serious rather than
> less (B4 — the seven-year destruction turns out to be a promise already made to
> every client, which nothing keeps), and two new gaps surfaced while evidencing
> the rest (B11, B12).
>
> It becomes SATC's WISP only when the owner has read every line, answered the
> questions in **Part C**, corrected anything wrong, and signed it — ideally
> after counsel has looked at it. Until then it is a description of what the
> software does, not a commitment about how the firm operates.
>
> **Part B is a list of things that are required and are not in place.** Read it
> before Part A. A WISP that overstates its controls is worse than no WISP: it
> is a written record of a claim the firm cannot support.

---

## Part 0 · Why this document exists, and what is and is not excused

The **FTC Safeguards Rule (16 CFR Part 314)** treats a tax return preparer as a
"financial institution." It applies to a solo practice.

**§314.6 exempts a firm holding information on fewer than 5,000 consumers from
exactly four requirements**, and no others:

| Waived by §314.6 | |
|---|---|
| 1 | The **written** risk assessment (§314.4(b)(1)) |
| 2 | Continuous monitoring / annual penetration testing + semi-annual vulnerability assessment (§314.4(d)(2)) |
| 3 | The **written** incident response plan (§314.4(h)) |
| 4 | The annual written report to the board or senior officer (§314.4(i)) |

**Everything else still applies in full**, including:

- **The WISP itself** (§314.3(a)) — the exemption does not waive it
- Designating a **Qualified Individual** (§314.4(a))
- **Encryption** of customer information at rest and in transit (§314.4(c)(3))
- **Multi-factor authentication** for anyone accessing an information system, or
  a Qualified-Individual-approved written equivalent (§314.4(c)(5))
- **Access controls** (§314.4(c)(1)) and a **data inventory** (§314.4(c)(2))
- **Secure disposal** of customer information, generally within two years
  (§314.4(c)(6))
- **Change management** (§314.4(c)(7)) and **activity logging** (§314.4(c)(8))
- **Service provider** selection, contracting, and periodic reassessment (§314.4(f))
- **Security awareness training** for personnel (§314.4(e))

Note the asymmetry the exemption creates: the **risk assessment and incident
response plan need not be written**, but the underlying obligation to do those
things does not disappear. This document is shaped after **IRS Publication
5708**, the IRS's small-firm WISP template.

**This draft covers the SATC practice-operations software and the single machine
it runs on.** It does not cover Drake (the system of record for filed returns),
the firm's e-mail, its phone, its paper files, or its physical office. Those are
in scope for the real WISP and are out of scope for what software could
establish. See Part C.

---

# PART A · What the software actually does

**Every control in this part was verified by opening the file, and cites
`path:line`.** Where a claim comes from a dated document rather than from code
or a measurement, it says so. Where something could not be verified, it says
that too.

## A1 · Data inventory and classification (§314.4(c)(2))

Customer information is deliberately **split across two databases**, and the
split is the load-bearing design decision:

| Store | Holds | Encrypted at rest |
|---|---|---|
| `satc_vault.db` — **identity vault** | Legal names, full SSNs/EINs, home addresses, contacts | **Yes** — AES-256-GCM, per field |
| `satc_mart.db` — **de-identified working mart** | Opaque `client_id`, masked last-4, returns, line items, carryforwards, basis, payments, engagements, documents | **No** — it is de-identified by construction |

Declared and implemented at
`satc_system/src/satc/persistence/store.py:1-17` (the two-file split),
`store.py:76-84` (vault schema: `identities`, `vault_addresses`,
`vault_contacts`), `store.py:276` (the vault tables keyed by client).

Everything outside the vault carries **masked identifiers only** —
`satc_system/src/satc/masking.py:48-66` (`mask_value`) is the single function
that produces them, and its contract is that the full identifier never leaves
it. An unrecognised field name still masks rather than passing the value
through (`masking.py:65-66`).

**A third store exists and is not covered by the above.** The engagement
pipeline keeps each engagement as a **directory of plaintext JSON files** on
disk — `client-documents/engagements.py:9-11, 28`. Real names and engagement
details are in cleartext there. It is excluded from git
(`client-documents/.gitignore:13`, verified with `git check-ignore`), and the
lead intake workbook likewise (`.gitignore:20`), but neither is encrypted by
the application. See **Gap B2**.

## A2 · Encryption of customer information at rest (§314.4(c)(3))

- **Algorithm:** AES-256-GCM, applied per field, stored as
  `enc:v1:<base64(nonce|ciphertext+tag)>` —
  `satc_system/src/satc/persistence/crypto.py:30-59`. A fresh 12-byte nonce per
  encryption (`crypto.py:50`). Encryption is idempotent so a value is never
  double-encrypted (`crypto.py:48-49`).
- **Applied on write** to every vault PII column —
  `satc_system/src/satc/persistence/store.py:639-653` (`upsert_identity`), and
  decrypted transparently on read (`store.py:655-668`).
- **Legacy plaintext is migrated and the file VACUUMed** on open —
  `store.py:578-607` (`_encrypt_vault_at_rest`), so a database written by a
  pre-encryption build does not silently keep plaintext in freed pages.
- **File permissions:** best-effort `0700` on the data directory and `0600` on
  each database — `store.py:32-45`. On Windows these are no-ops and NTFS ACLs
  apply instead; the code says so at `store.py:33`.

**Encryption in transit is not applicable to the local apps** — nothing crosses
a network (see A4). It *is* applicable to the OneDrive backup, which is TLS by
Microsoft's client, not by anything in this repository. Not verified here.

## A3 · Key management (§314.2 requires safeguards for key material)

- **The key is a 256-bit data key generated once**, on first run, into the data
  directory as `vault.key` — `crypto.py:95-103`.
- **On Windows it is sealed with DPAPI** (`CryptProtectData`), so only the same
  Windows user account can unseal it — `crypto.py:66-75`. Copying the vault and
  the key to another machine or user does not decrypt it. On any other platform
  it is stored raw in a `0600` file, which the module documents as an explicitly
  weaker fallback (`crypto.py:13-15`).
- **The key is never backed up, and the backup refuses to run if one is found at
  the destination.** `satc_system/scripts/backup_client_data.py:58` declares
  `FORBIDDEN = ("vault.key",)`; `backup_client_data.py:258-271` searches the
  whole destination tree (`rglob`) and, if a key is present, prints `REFUSED`
  and increments the failure count so the run exits non-zero
  (`backup_client_data.py:288-291`). The rationale is written into the module
  docstring at `backup_client_data.py:14-25`: a vault and its key in one cloud
  folder is not an encrypted vault.
- **`--check-key` exists to say, out loud, what losing the key costs** —
  `backup_client_data.py:198-216`.

**The key currently sits in the same directory as the vault it decrypts** and
**has no second copy anywhere.** Recorded in `docs/satc-forge.md:156-158` and
`docs/satc-forge.md:382-386, 436-438`. This is Gap **B1** and it is the single
most consequential item in this document.

## A4 · Access controls and network exposure (§314.4(c)(1))

**Access control is enforced at two layers: the application binds, and the
Windows Firewall. They are not the same thing, and the firewall is the one that
decides reachability.**

**Measured on this machine, 4 September 2026** (`Get-NetTCPConnection -State Listen`):

| Port | Bind | What |
|---|---|---|
| 5050 | `127.0.0.1` | SATC practice-ops GUI |
| 5051 | `127.0.0.1` | client-documents web front door |
| 11434 | `127.0.0.1` | Ollama (local model) |
| 8080 | `0.0.0.0` | Open WebUI |
| 19999 | `::` | Netdata |

The two loopback app binds are hard-coded, not configured:
`satc_system/src/satc/app/server.py:347` — `app.run(host="127.0.0.1", ...,
debug=False, ...)`, and the free-port probe also binds only `127.0.0.1`
(`server.py:317-328`).

**The two `0.0.0.0`/`::` binds are not LAN-reachable.** Verified on this machine
4 September 2026:

- The two auto-created `python.exe` inbound allow rules — the actual LAN path —
  are both **Enabled: False**.
- Two inbound allow rules exist and are enabled: `Forge - Open WebUI (Tailnet
  only)` (local port 8080) and `Forge - Netdata (Tailnet only)` (local port
  19999). **Their address scoping was re-queried directly on 4 September 2026**
  with `Get-NetFirewallAddressFilter`, and both carry exactly
  `RemoteAddress = 100.64.0.0/255.192.0.0` (i.e. `100.64.0.0/10`, the Tailscale
  CGNAT range) and `fd7a:115c:a1e0::/48`. *(The first draft could only cite
  `CLAUDE.md` for these ranges. They are now measured from the firewall itself,
  and they match.)*

**A bind of `0.0.0.0` is therefore not evidence of exposure on this box, and a
bind of `127.0.0.1` is not the thing doing the work.** Whoever maintains this
must check the firewall, not the bind.

**Two request-level guards** protect the local GUI from a browser the preparer
is using — `satc_system/src/satc/app/server.py:73-86`:

- a `Host`-header check that rejects anything not `127.0.0.1`/`localhost`/`::1`
  with **400**, which blocks DNS rebinding (`server.py:73-78`);
- an `Origin`/`Referer` check that rejects cross-origin state-changing requests
  with **403** (`server.py:79-85`).

Session cookies are `HttpOnly` + `SameSite=Lax` (`server.py:62`) and the Flask
secret is a per-install random 32 bytes persisted at `0600`, replacing a
formerly hardcoded key (`server.py:38-56`).

**There is no login. There is no user account, no password, and no MFA on either
local app.** Anything running as this Windows user, or anyone at the keyboard,
has full use of the vault through the app. This is Gap **B3** and it is the
§314.4(c)(5) MFA question. **The firm's answer to it is A4a, immediately below.**

## A4a · Compensating controls in place of MFA (§314.4(c)(5)) — AWAITING WRITTEN APPROVAL

**§314.4(c)(5) allows one of two things.** Either multi-factor authentication for
anyone accessing an information system holding customer information, *or* the use
of "reasonably equivalent or more secure access controls" — but only where those
controls are **approved in writing by the Qualified Individual**. The written
approval is the mechanism; without it the exception does not apply and the firm
is simply non-compliant.

**Owner's decision, 4 September 2026: do not build a login. Rely on the controls
below, and document them.** His reasoning, in his own words: *"this is all local
to here and you'd have to be literally on my lan."*

### What actually protects access to customer information today

Each row was verified — by opening the file, or by measuring this machine on
4 September 2026. Nothing here is asserted from a policy document.

| # | Control | Evidence | Verified |
|---|---|---|---|
| 1 | **A Windows account with a password is required to reach the desktop at all.** The account that owns the data, `ajish`, has `PasswordRequired = True`, password last set 29 July 2026. | `Get-LocalUser` | measured 4 Sep 2026 |
| 2 | **Both applications bind loopback only**, so nothing off the machine can reach them at any address. | `satc_system/src/satc/app/server.py:347` (`host="127.0.0.1"`); free-port probe also loopback-only, `server.py:317-328`; `client-documents/web.py:3089` (no `host=`, so Flask's `127.0.0.1` default) | file + `Get-NetTCPConnection`, 4 Sep 2026 |
| 3 | **The two non-loopback binds are firewalled to the Tailscale ranges only**, and the LAN path is disabled. `Forge - Open WebUI (Tailnet only)` and `Forge - Netdata (Tailnet only)` are Enabled, Inbound, Allow, `RemoteAddress = 100.64.0.0/255.192.0.0` and `fd7a:115c:a1e0::/48`. The two auto-created `python.exe` inbound rules — the actual LAN path — are **Enabled: False**. | `Get-NetFirewallRule` + `Get-NetFirewallAddressFilter` | **measured 4 Sep 2026** — the CIDR scoping is now read from the firewall itself, not from a document |
| 4 | **Identity PII is encrypted at rest with AES-256-GCM**, per field, so possession of `satc_vault.db` alone yields nothing readable. | `satc_system/src/satc/persistence/crypto.py:30-59`; A2 above | file |
| 5 | **The vault key is sealed with Windows DPAPI**, so it unseals only under this Windows user account. Copying the vault *and* the key to another machine or another user still does not decrypt it. **Caveat, stated because it matters:** the seal is best-effort — if `win32crypt` is unavailable the code catches the exception and falls back to storing the key **raw**, with only the file prefix (`DPAPI\0` vs `RAW\0`) to tell the two apart. Nothing warns. | `crypto.py:66-75` (`CryptProtectData`); fallback at `crypto.py:73-75`; `crypto.py:95-103` (`load_or_create_key`) | file |
| 6 | **Request-level guards** reject a foreign `Host` with 400 and a cross-origin state-changing request with 403, so a browser the preparer is using cannot be turned into a path into the app. | `server.py:73-86`; tests at `satc_system/tests/test_app_security.py` | file + 20 tests passing |
| 7 | **The MCP surface never registers a write tool** unless explicitly enabled; a caller cannot name one. | `satc_system/src/satc/api/mcp_server.py:44, 95, 137-147`; A6 above | file |
| 8 | **Single machine, single operator.** One person uses this box; there is no shared workstation, no remote desktop path (the `Remote Desktop Users` group is **empty**, measured), and no second person with an account that reaches the data. | `Get-LocalGroupMember` | measured 4 Sep 2026 |
| 9 | **The debug console is off.** The Werkzeug interactive debugger no longer runs by default — see closed Gap **B7**. | `client-documents/web.py:3076-3090` | file |

### What these controls do NOT cover — read this before signing

The controls above are a perimeter. **They are not authentication, and this
document will not describe them as if they were.**

1. **Anyone with the unlocked Windows session has everything.** There is no
   second gate. Once that desktop is unlocked, the apps are open, the DPAPI seal
   opens automatically because it is keyed to exactly that logged-in user, and
   the vault decrypts transparently. The Windows password is the *only* factor,
   and it protects the session, not the data.
2. **There is no second factor anywhere in this chain.** Not on the Windows
   account, not on the apps. What §314.4(c)(5) asks for by default is precisely
   the thing that is absent.
3. **No per-user identity means no attribution.** Nothing in the apps records
   *who* did something, because there is only ever one "who." That interacts
   directly with the §314.4(c)(8) logging requirement — see Gap **B6**.
4. **⚠️ The screen does not demonstrably lock.** Measured 4 September 2026:
   `ScreenSaveActive = 1`, but **no screensaver is configured**
   (`SCRNSAVE.EXE` unset), `ScreenSaverIsSecure` is unset, and there is no
   `ScreenSaveTimeOut` and no `InactivityTimeoutSecs` machine policy. An
   unattended, unlocked session is therefore the realistic failure mode, and
   control 1 above assumes a lock that could not be shown to exist. **This is the
   weakest link in the whole list.** *(Windows may still lock on sleep/wake via a
   power setting that could not be read without elevation — so this is
   **unverified**, not proven absent. It should be checked and set.)* → new
   Gap **B11**.
5. **⚠️ A second enabled local account exists, and it has no password.**
   `forge-readonly` (Enabled, `PasswordRequired = False`, description "Runs the
   read-only MCP bridge", **never logged on** — `LastLogon` empty). It is **not**
   in `Administrators`, **not** in `Users`, and **not** in `Remote Desktop
   Users`, and the machine sets `LimitBlankPasswordUse = 1`, which confines
   blank-password logons to the physical console — so this is materially
   contained, not open. But it does mean claim 8 ("single operator") is true of
   *practice*, not of *configuration*. → new Gap **B12**.
6. **The perimeter is inherited, not owned.** Control 3 depends on the Tailscale
   tailnet and the Google account behind it; control 1 depends on the Windows
   account. Neither is administered by this software, and MFA on the account
   behind Tailscale is recorded elsewhere as not yet done.
7. **This says nothing about the OneDrive copy.** The backup leaves the machine
   (A7). The compensating controls above are about *this box*; the Microsoft
   tenant account is a separate perimeter with its own MFA question — C3.

### The approval itself — NOT GIVEN

**Everything above is drafted reasoning. It is not the approval.** §314.4(c)(5)
requires the **Qualified Individual** to approve compensating controls **in
writing**. Software describing why controls might be adequate is not that
approval, and cannot become it by being well argued. The rule wants a named
person to accept the residual risk in items 1–7 above and sign for it.

- `[CONFIRM: the name and title of the Qualified Individual approving these compensating controls in place of MFA — see C1]`
- `[CONFIRM: the QI's written approval, in his own words, that controls 1–9 are "reasonably equivalent or more secure access controls" under §314.4(c)(5), having read the seven limitations above]`
- `[CONFIRM: the date of that approval, and where the signed approval is filed]`
- `[CONFIRM: when this approval is re-examined — it is only valid while the facts hold, and items 4 and 5 above are currently open defects]`

**Until those four are filled in and signed, Gap B3 remains open.** The controls
are real and are described accurately; what is missing is a person's signature,
and no amount of documentation substitutes for it.

## A5 · Where client data goes to be read — local inference (§314.4(f))

**By default, no client document leaves the machine.** The default document
reader ladder is entirely local: fillable form fields → text layer → local OCR
(Tesseract) → local Ollama vision, at
`satc_system/src/satc/app/state.py:448-506`.

- Ollama is reached at `http://localhost:11434` —
  `satc_system/src/satc/settings.py:73-74` — and Ollama on this machine is bound
  to `127.0.0.1:11434` (measured today, table in A4).
- The whole posture is stated at `satc_system/src/satc/settings.py:1-13`.

**But there is a cloud fallback, and this document will not pretend otherwise.**
`satc_system/src/satc/ingest/readers/vision.py` sends a **base64 document image**
(`vision.py:159`) to Anthropic's API (`vision.py:74-75`, `vision.py:109-121`).
That is a real disclosure of a client's tax document to a third party.

### The two switches, and their measured state

**Decided by the owner, 4 September 2026: the capability stays in the code, it
stays off, and turning it on requires this WISP to be updated first.** It was not
removed, because the ladder is designed around it as a last rung; it is governed
instead.

Enabling it takes **two independent environment variables**, and neither one
alone is enough — `satc_system/src/satc/settings.py:40-47`:

| # | Switch | Where it is read | Measured state, 4 Sep 2026 |
|---|---|---|---|
| 1 | `SATC_ALLOW_CLOUD` set to `1`/`true`/`yes`/`on` | `cloud_allowed()`, `settings.py:40-42` | **unset** — Process, User and Machine scope |
| 2 | `ANTHROPIC_API_KEY` present | `cloud_vision_enabled()`, `settings.py:45-47` | **unset** — Process, User and Machine scope |

Both were read on this machine on 4 September 2026 via
`[Environment]::GetEnvironmentVariables()` at User and Machine scope and the
process environment. **Both are absent at all three scopes, so cloud vision is
off.** A key on its own does nothing: the module docstring states that opting in
must be "a deliberate act, never an accident of having a key in the environment"
(`settings.py:5-8`), and `cloud_vision_enabled()` requires the conjunction.

Every call site routes through that one gate — `state.py:347-348`,
`state.py:521`, `ingest/classify.py:338-339`, `ingest/scoreboard.py:222, 229` —
so there is one place to check, not five.

### Control A5-C · Enabling cloud vision requires a WISP update first

> **Neither switch may be set on any machine holding real client data until this
> WISP has been updated to cover it.** Setting either one makes **Anthropic a
> service provider holding customer information under §314.4(f)**, which the
> §314.6 small-firm exemption does **not** waive. Before it is turned on once,
> the following must exist in writing: a provider selection/assessment, a
> contract containing safeguards terms, a reassessment cadence, and a separate
> **IRS §301.7216** disclosure-consent analysis (client consent for disclosure of
> return information to a third party is a different question from §314.4(f),
> and carries criminal exposure under §7216).

This control is now stated **in the code as well as here**, as a comment sitting
directly above the two switch functions — `satc_system/src/satc/settings.py:22-37`
— so that whoever reaches for the switch sees the obligation without having to
know this document exists.

**Be clear about what that comment is.** It is a sign, not a lock. Nothing in the
software refuses to run with the variables set; the last line of the comment says
so (`settings.py:36`). The control is procedural and depends on a person honouring
it. Building an actual gate was considered and deliberately not done — the switch
is already off, doubly, and machinery to defend a switch nobody has touched is
cost without benefit.

**Known weakness in the "local" claim:** `ollama_host()` reads
`SATC_OLLAMA_HOST` from the environment and **does not refuse a non-loopback
value** — `settings.py:73-74`. The firm's own research document lists "refuses
non-loopback. No configurable inference base URL" as a non-negotiable invariant
(`docs/research/tax-practice/03-ai-boundary.md:316`). It is not implemented.
Gap **B5**. *(Measured 4 September 2026: `SATC_OLLAMA_HOST` is unset at Process,
User and Machine scope, so the default loopback URL is in force today.)*

## A6 · The MCP surface is read-only by default (§314.4(c)(1))

`satc_system/src/satc/api/mcp_server.py:44` builds the server with
`allow_writes: bool = False`. Only four read/compute tools are registered
(`mcp_server.py:56-89`), and the function **returns at line 95** before the
write-tool decorators at `mcp_server.py:100-133` are ever executed. So a write
tool is not merely refused — it is **never registered with the framework**, and
a caller cannot name it. Writes require `SATC_MCP_ALLOW_WRITES=1`
(`mcp_server.py:137-147`).

The read tools are de-identified by contract: `list_clients` and `get_client`
return the public projection, never the vault legal name or full SSN
(`mcp_server.py:56-70`).

`cowork-plugin/mcp/satc_mcp.py` is a thin proxy to the local withholding API and
defines **no** write tools at all.

## A7 · Backup — and Microsoft as a service provider (§314.4(f))

**The backup runs, off this machine, and verifies itself by restoring.**

`satc_system/scripts/backup_client_data.py`:

- Copies **only** `satc_mart.db` and `satc_vault.db` (`:55`).
- Uses SQLite's **online backup API**, not a file copy, so a live database
  cannot be captured mid-transaction (`:82-93`, rationale at `:33-40`).
- **Reopens and `PRAGMA integrity_check`s every copy** before calling the run a
  success (`:96-114`).
- **`--verify-restore` copies the backup back out, opens it, and compares every
  table's row count to the live database**, then deletes the scratch copy
  unconditionally (`:128-163`).
- Refuses the run if `vault.key` is anywhere in the destination (`:258-271`).
- Keeps the newest 14 dated copies (`:166-173`).
- Targets the **SATC work tenant only** — it reads `OneDriveCommercial` and
  deliberately does not accept `OneDriveConsumer`, so client data cannot land in
  a personal drive (`:64-79`).

Scheduled twice daily-equivalent — 12:30 and at logon, because this machine
starts things at logon rather than boot —
`satc_system/scripts/install_backup_task.ps1:125-128`, rationale at `:21-23`.
The task runs as the signed-in user, `Interactive`/`Limited`, with no stored
password (`install_backup_task.ps1:143-146`), and appends both streams to
`~\.satc\backup.log` (`:121`).

**Measured on this machine, 4 September 2026:** the task
`SATC - Back up client data to OneDrive` is registered, **State: Ready**,
**LastTaskResult: 0**, LastRunTime `2026-09-04 05:47:55`, NextRunTime
`2026-09-04 12:30`.

**This makes Microsoft a service provider holding customer information, and
§314.4(f) is not waived by §314.6.** `docs/satc-forge.md:440-444` records that
sending the vault to Microsoft was a deliberate deviation from local-first,
decided 3 September 2026 with the alternative — one disk, no backup — in view.
Two consequences the firm has to own:

1. **`satc_vault.db` goes up encrypted. `satc_mart.db` goes up as-is.** The mart
   is de-identified, but it is not encrypted by SATC; in the cloud it is
   protected by the tenant account alone (`docs/satc-forge.md:406`).
2. **The tenant account is the perimeter for that copy.** Whatever protects that
   Microsoft account protects the backup. See Part C on MFA.

## A8 · The safeguards that fail the build (§314.4(c)(7))

These are the tests that stop a PII leak from shipping, rather than a policy
saying it must not.

| What it enforces | Where |
|---|---|
| Legal names and full TINs never reach the workbook; no unmasked SSN pattern anywhere in it | `satc_system/tests/test_validation.py:31-44` |
| Clients are referenced in outputs only by opaque `client_id` | `satc_system/tests/test_validation.py:47-51` |
| PII is in the vault file and **not** in the mart file — and is **not plaintext in the vault file either**, while still round-tripping through the API | `satc_system/tests/test_persistence.py:29-46` |
| Names, TINs, addresses and e-mails are ciphertext on disk; legacy plaintext is migrated away | `satc_system/tests/test_vault_crypto.py:20-44` |
| The public projection of an identity exposes neither legal name nor full TIN | `satc_system/tests/test_foundation.py:45-58` |
| No agent/MCP tool result carries an unmasked TIN | `satc_system/tests/test_agent.py:141-148` |
| A foreign `Host` gets 400; a cross-origin POST gets 403 | `satc_system/tests/test_app_security.py` |
| No document a client receives may carry an SSN/ITIN/EIN shape — checked on the **rendered** page, and the refusal never repeats the value it objected to | `client-documents/presend.py:897-925`, guard at `client-documents/tins.py:40-59` |
| The TIN boundary holds at the five free-text inlets where a number actually arrives | `client-documents/tests/test_tins.py` |

**Measured, not asserted.** Run on this machine 4 September 2026:

```
satc_system:      test_vault_crypto.py test_validation.py test_persistence.py
                  test_app_security.py    ->  20 passed
client-documents: tests/test_tins.py                      ->  17 passed
```

**37 of 37 passed.** *(Re-run 4 September 2026 after merging PRs #186, #188 and
#189 into this branch — still 20 + 17 = 37 of 37. A count in a compliance
document is only true of the tree it was measured on, so it was re-measured
rather than carried forward.)* These suites run in CI on every pull request and on every
push to `main` — `.github/workflows/test.yml:17-20` (triggers),
`:28-38` (the `satc_system` and `client-documents` jobs), `:65-66` (`pytest -q`).

Two honest qualifications. The `client-documents` TIN guard is documented at
`client-documents/tins.py:23-27` as **deliberately not** matching nine
undelimited digits, because that shape is indistinguishable from an account or
case number and a guard that cries wolf gets muted. And the shape guard was
measured against 302 files with zero false positives before it was allowed to
block anything (`tins.py:17-21`) — but a guard on a *shape* is not a guarantee
of *no PII*.

## A9 · Retention and secure disposal (§314.4(c)(6))

### A9.1 · The retention period is seven years, and it is a promise to clients

**This was recorded as an open question in the first draft. It is not open.** The
firm has already set its retention period, and has already told every client what
it is, in the engagement letter each of them signs.

All four engagement letter templates carry the same sentence, **verbatim**:

> "We return your original records at the end of the engagement; store them, and
> everything supporting them, somewhere secure. **We keep copies of your records
> and our work papers for seven years, after which they are destroyed.** Our work
> papers are ours, not part of your records."

| Template | Line |
|---|---|
| `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html` | `:100` |
| `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Bookkeeping.html` | `:100` |
| `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Business Return.html` | `:120` |
| `satc-handoff/04-TEMPLATES/SATC Engagement Letter - C Corporation.html` | `:107` |

*(Verified 4 September 2026 by reading all four files; the sentence is identical
in each.)*

It is corroborated by the delivery-letter field notes, which record the division
of labour between the two documents —
`satc-handoff/04-TEMPLATES/FIELDS - Tax Return Delivery Letter.md:153`: **"The
engagement letter owns the firm's seven years."**

**Three things follow, and they matter more than the number itself.**

1. **The period is seven years** for copies of client records and for SATC work
   papers. This satisfies the §314.4(c)(6) requirement to have a defined period,
   and the "legitimate business need" carve-out that lets it exceed two years —
   tax records are exactly the case the carve-out contemplates.
2. **It is a published commitment, not an internal preference.** It is in a
   signed contract with each client. The firm cannot quietly lengthen, shorten,
   or ignore it; changing it means changing the engagement letters.
3. **Work papers are SATC's property, not the client's records** — the same
   sentence says so. That distinction governs what must be returned on
   disengagement versus what SATC keeps and then destroys.

### A9.2 · Nothing destroys anything at seven years

**The promise says records "are destroyed." No mechanism in this software
destroys them.** This was searched for specifically and exhaustively on
4 September 2026, and the finding is a negative one:

> There is **no** code anywhere in this repository that deletes, destroys,
> expires, purges, or archives a client record — a return, a work paper, an
> engagement, a document, a vault identity, or a mart row — **on a schedule or
> automatically, based on age.**

What the search covered, so that the negative can be trusted: every tracked file
for `retention`/`retain`/`dispose`/`destroy`/`expire`/`purge`/`prune`/`TTL`/
`older_than`/`cutoff`; every deletion primitive (`DELETE FROM`, `unlink`,
`rmtree`, `os.remove`); and every scheduling mechanism (cron, APScheduler,
`schedule`, `sched`, Celery, systemd, Windows Task Scheduler, `.ps1` installers,
background threads and timers, `atexit`, and GitHub Actions `schedule:` triggers).

What exists instead is three things, and **none of them is a seven-year clock**:

1. **A 90-day purge of abandoned prospect intake drafts** —
   `client-documents/web.py:135-158` (`purge_drafts`), TTL at `web.py:112-116`,
   set by the firm on 3 September 2026. A draft that was **decided** (refused or
   declined) is kept deliberately (`web.py:119-132`), and a draft whose date will
   not parse is kept rather than destroyed (`web.py:152-153`). It runs
   opportunistically on the index page because no scheduler exists — the code
   says exactly that at `web.py:249-253`. **This is pre-engagement prospect data,
   not client records, and 90 days is not seven years.**
2. **Manual deletion of one client, everywhere** —
   `satc_system/src/satc/persistence/store.py:1216-1237` (`delete_client`),
   which clears every registered mart table and then the vault tables. Exposed
   as `POST /clients/<client_id>/discard`
   (`satc_system/src/satc/app/server.py:308-312`). Its docstring says what it is
   for — discarding a mistakenly-added client and clearing sample data
   (`store.py:1217-1220`). **It takes no date argument, has no age check, and no
   caller runs it on a timer.**
3. **Account deletion in the invoicer** — `invoice-generator/app.py:945-962`,
   password-gated, user-initiated. *(The firm retired the invoicer on
   4 September 2026 in favour of Square. The decision explicitly kept the branch
   and deleted nothing, so the code — and any data it holds — is still on this
   disk. Retired is not removed, and for a disposal question that difference is
   the whole point.)*

**Two near-misses, named so nobody mistakes them for the schedule.**

- **The only scheduled job on this machine creates data; it does not destroy
  client records.** `satc_system/scripts/install_backup_task.ps1:123-152`
  registers the daily 12:30 backup. Its `prune()` step
  (`satc_system/scripts/backup_client_data.py:166-173`, `--keep` default 14 at
  `:189-190`, called at `:283-285`) is **count-based, not age-based** — it keeps
  the newest 14 *copies* however old they are — and it operates only on the
  OneDrive destination tree (`:222-232`), never on the live databases, which it
  opens read-only (`:84`, `:99`, `:118`). It is backup rotation.
- **The per-artifact retention design was specified and never built.** A
  `configs/retention.yaml`, a `retention_until()` function, a `retention_basis`
  on every artifact and a disposal queue, citing §314.4(c)(6) by name:
  `docs/research/tax-practice/02-gap-analysis-and-roadmap.md:241-245`. The same
  document's status table marks "Retention clocks per artifact class" as
  **"none"** at `:68`, noting a single tax-year purge would be the wrong design
  because each artifact class has a different basis. **Confirmed absent:** no
  file matching `*retention*` exists in the repository, and
  `satc_system/configs/firm_policy.yaml` contains no retention key.

The firm's own defect register already carries this as open defect **W5** —
`docs/DEFECT-REGISTER.md:57`.

**So the gap is not "no retention schedule." The period is set and published.
The gap is that a written promise made to every client is not kept by anything.**
Gap **B4**, restated.

## A10 · Activity logging (§314.4(c)(8))

Not established here. Event-log machinery exists in `client-documents`
(`closeout.py`, `payments.py`, `procedures.py`, `requote.py`, `web.py` reference
an append-only event log) but **this draft did not verify that it constitutes a
§314.4(c)(8) audit log of authorised-user activity and unauthorised access
attempts** across the vault. `docs/research/tax-practice/02-gap-analysis-and-roadmap.md:89`
records the requirement as **"none"** — not built — and notes it must log mart
ID plus last-4 and never legal names or full TINs. Gap **B6**, and it is marked
as *unverified* rather than *absent*: somebody should look properly.

---

# PART B · Gaps — required, and not in place

Nothing in this list is an aspiration described as a control. Each is a
requirement of the Safeguards Rule (or a stated invariant of this firm's own
design) that the evidence does not support today.

| # | Gap | Why it matters | Evidence |
|---|---|---|---|
| **B1** | **`vault.key` has no second copy, and lives beside the vault it decrypts.** | Two failures in one. (a) Anyone who can read the data directory has both halves — AES-256 is protecting against a stolen *file*, not a stolen *folder*. (b) If this disk dies, the backup restores a file **nobody can read**. The backup is working exactly as designed and is useless in the disaster it exists for. | `docs/satc-forge.md:156-158, 382-386, 436-438`; `crypto.py:95-103` |
| **B2** | **The engagement store and the leads workbook are plaintext.** Real names, addresses and engagement details sit as JSON files and a spreadsheet, encrypted by nothing in the application. | Only the `satc_system` vault is encrypted. §314.4(c)(3) covers customer information at rest, not just the part that happens to be in SQLite. | `client-documents/engagements.py:9-11, 28`; `.gitignore:13, 20` |
| **B3** | **No authentication on either local app, and no MFA — and the §314.4(c)(5) written approval is unsigned.** *(Narrowed 4 Sep 2026.)* The owner has decided **not** to build a login and to rely on compensating controls instead, which are now enumerated and evidenced in **A4a**. That is a legitimate route under the rule. **What is still missing is the one thing the rule actually names: the Qualified Individual's written approval.** | §314.4(c)(5) permits "reasonably equivalent or more secure access controls" **only** where the QI approves them in writing. Software drafting the reasoning is not the approval. The firm's own research names this: *"A localhost Flask app with no authentication is a live gap... the written artifact must actually exist."* | A4a; `satc_system/src/satc/app/server.py:59-86` (no auth); `docs/research/tax-practice/03-ai-boundary.md:318` |
| **B4** | **A published seven-year destruction promise that nothing implements.** *(Sharpened 4 Sep 2026 — this replaces "no retention schedule," which was the wrong finding.)* The **period is not an open question**: all four engagement letters tell the client "we keep copies of your records and our work papers for seven years, **after which they are destroyed**." **No code destroys anything on a schedule.** The only age-based purge is 90 days on pre-engagement prospect drafts; the only client-record deletion is manual and takes no date. | This is worse than a missing schedule and better documented: it is a **contractual commitment to every client** that the firm has no mechanism to keep. §314.4(c)(6) aside, an unkept written promise in a signed engagement letter is its own exposure. The remedy is either to build the clock or to stop promising it. | A9 above; four engagement letters (A9.1); `client-documents/web.py:135-158`; `store.py:1216-1237`; `02-gap-analysis-and-roadmap.md:68, 241-245`; `docs/DEFECT-REGISTER.md:57` (W5) |
| **B5** | **`ollama_host()` accepts a non-loopback URL from the environment.** | The firm's own stated invariant is that it must refuse one. As written, a single environment variable redirects every "local" inference call — including document images — to an arbitrary host. | `satc_system/src/satc/settings.py:55-56` vs `03-ai-boundary.md:316` |
| **B6** | **§314.4(c)(8) audit logging not established.** | Not proven absent — **not proven present**, which for a compliance claim is the same answer. | A10 above |
| ~~**B7**~~ | ✅ **CLOSED 4 Sep 2026 — `client-documents/web.py` no longer runs with `debug=True`.** The reported gap was real; it has been fixed. Debug is now **off unless `SATC_WEB_DEBUG=1`** is set for that run, and the commented rationale sits at the call site. Measured the same day: `SATC_WEB_DEBUG` is **unset** at Process, User and Machine scope, so the debugger is off on this machine. | *(Was: the Werkzeug interactive debugger is remote code execution to anyone who reaches the port — loopback-only, so never exploitable in practice, but one `host=` argument from being the worst hole in this repository.)* Now opt-in per run. | **Fix:** `client-documents/web.py:3089-3090` — `create_app().run(port=5051, debug=os.environ.get("SATC_WEB_DEBUG") == "1")`; rationale at `web.py:3077-3087`. Landed in **PR #186** (commit `cfcf152`). |
| **B8** | **No disk-encryption status could be established.** BitLocker state could not be read — `Get-BitLockerVolume` and `manage-bde -status C:` both returned **access denied** without elevation. | The DPAPI seal and the `0600` fallback both assume the disk underneath is protected. `README.md:34` and `satc_system/docs/QUICKSTART_WINDOWS.md:84-86` *tell* the operator to keep BitLocker on; nothing checks. **This is unverified, not failed** — it may well be on. | measured 4 Sep 2026 |
| **B9** | **A stray copy of real client data was recorded outside the store** and may still be there. | `docs/satc-forge.md:159-162` records a 160,585-byte workbook left behind by a one-off repair job on 30 July 2026. This draft **did not look**, deliberately. Somebody should. | `docs/satc-forge.md:159-162` |
| **B10** | **Everything administrative.** No Qualified Individual is designated in writing, no incident response steps exist, no service provider has been assessed, no training has been recorded, and this document has no review cadence. | These are Part C, not defects in the software. They are listed here because a WISP without them is not a WISP. | Part C |
| **B11** | **The workstation cannot be shown to lock when unattended — ACCEPTED AS A KNOWN RISK BY THE OWNER, 4 September 2026.** *(New 4 Sep 2026.)* `ScreenSaveActive = 1`, but no screensaver is configured (`SCRNSAVE.EXE` unset), `ScreenSaverIsSecure` is unset, there is no `ScreenSaveTimeOut`, and no `InactivityTimeoutSecs` machine policy. | **The owner was shown this finding and its consequence and chose to leave it, asking that it be written down as a risk rather than fixed** — *"leave it and outline it in the WISP so we know it's a risk"*. Recorded rather than closed, because it is the load-bearing assumption under A4a: the case for not building MFA is that the Windows session is the gate, and a session that never locks is a gate propped open. What remains true is that reaching it needs physical presence at this machine. What is no longer claimable is that an unattended session is protected by anything. **Revisit the moment a second person has physical access to this room, or the machine leaves it.** **Unverified rather than proven absent:** a lock-on-wake power setting could not be read without elevation. | measured 4 Sep 2026; accepted by the owner 4 Sep 2026; A4a limitation 4 |
| **B12** | **A second enabled local account with no password required.** *(New 4 Sep 2026.)* `forge-readonly` — Enabled, `PasswordRequired = False`, described as "Runs the read-only MCP bridge", `LastLogon` empty (never used). | It weakens the "single operator" claim in A4a control 8. **Materially contained, and said so honestly:** it is in none of `Administrators`, `Users` or `Remote Desktop Users`, and `LimitBlankPasswordUse = 1` restricts blank-password logon to the physical console. It should still either be given a password or disabled, since it has never been logged into. | measured 4 Sep 2026 (`Get-LocalUser`, `Get-LocalGroupMember`, `HKLM:\SYSTEM\CurrentControlSet\Control\Lsa`); A4a limitation 5 **DECIDED 4 September 2026: disable it.** The owner chose to disable rather than keep it; the account's own Full Name is "Forge read-only agent", so it was created deliberately for an agent and then never used. Disabling is reversible and destroys nothing — the account and its SID survive. Pending only because it needs elevation: `.satc\DISABLE forge-readonly.bat`. |

**One structural note.** The §314.6 exemption waives the *written* risk
assessment and the *written* incident response plan. It does not waive doing
either. Nothing in this repository shows that either has been done in any form.

**Scoreboard, 4 September 2026.** Of the ten gaps in the first draft: **one is
closed** (B7, fixed in PR #186), **one is narrowed to a single missing signature**
(B3 — the controls now exist and are evidenced in A4a; the QI's written approval
does not), **one is sharpened into a more specific and more serious finding**
(B4 — the retention *period* turned out to be already decided and published, so
the defect is an unkept promise rather than an absent policy), and **two new ones
were found** while evidencing the compensating controls (B11, B12). The rest are
unchanged. A gap list that only ever shrinks is not being looked at properly.

---

# PART C · Questions only the owner can answer

**These are deliberately unfilled.** Following this repository's convention, each
is a `[CONFIRM: ...]`. A `[CONFIRM:` that survives into a finished document means
the document **refuses** rather than shipping a plausible-looking placeholder —
see `docs/HOW-WE-WORK.md:174` and `docs/pipeline-map.md:240`.

**Do not let anything below be answered by software, and do not delete one
without answering it.**

## C1 · The Qualified Individual (§314.4(a))

- `[CONFIRM: who is designated as SATC's Qualified Individual — full name and title]`
- `[CONFIRM: the date of that designation]`
- `[CONFIRM: who covers the role if that person is unavailable for an extended period]`
- `[CONFIRM: the Qualified Individual's written approval of the compensating controls in §A4a, in place of MFA, as §314.4(c)(5) requires — and where that signed approval is filed. The controls have been enumerated and evidenced (A4a) and the owner has decided against building a login; **the signature is the only remaining piece**, and it must be his, not this document's. See Gap B3.]`

## C2 · Incident response (§314.4(h) — the *written plan* is waived; responding is not)

- `[CONFIRM: what counts as a security event that triggers this — the definition the firm will actually use]`
- `[CONFIRM: the first three things the owner does on discovering one, in order]`
- `[CONFIRM: who gets called, with names and numbers — IT/security help, the insurer, counsel]`
- `[CONFIRM: the IRS Stakeholder Liaison contact for reporting a data theft, and the state notification contact(s)]`
- `[CONFIRM: which states' breach-notification laws apply — i.e. which states SATC's clients live in — and the deadline each imposes]`
- `[CONFIRM: how clients are told, in what timeframe, and who writes that message]`
- `[CONFIRM: whether the firm carries cyber liability insurance, with the carrier and policy number]`

## C3 · Service providers (§314.4(f) — **not waived**)

Known recipients of customer information, from Part A:

| Provider | What it receives | Evidence |
|---|---|---|
| **Microsoft (OneDrive / M365)** | `satc_vault.db` (encrypted) and `satc_mart.db` (not encrypted by SATC), daily | A7 |
| **Drake** | The filed returns — the system of record | `CLAUDE.md` |
| **Anthropic** | Client document images — **only if** the two-switch opt-in is turned on. **Measured off, 4 Sep 2026**, and governed by control **A5-C**: turning it on requires this WISP to be updated first. **No assessment is needed while it stays off.** | A5 |
| **Stripe**, **the SMTP sender** | Invoice, customer and payment data, via the invoicer | `invoice-generator/stripe_utils.py`, `email_utils.py` |

- `[CONFIRM: the complete list of service providers that touch client data, including any this repository cannot see — e-mail, phone, e-signature, portal, cloud storage, shredding]`
- `[CONFIRM: how a provider is vetted before it is used, and what evidence is kept of that]`
- `[CONFIRM: which contracts contain a safeguards clause, and where those contracts are filed]`
- `[CONFIRM: how often each provider is reassessed, and who does it]`
- `[CONFIRM: whether MFA is enabled on the Microsoft account that holds the backup. That account is the entire perimeter for the off-machine copy of the vault.]`
**Answered, 4 September 2026 — the cloud vision fallback.** The owner's decision:
**keep the capability, keep it off, and make turning it on require a WISP update
first.** Both switches were measured unset at Process, User and Machine scope
(A5), and the obligation is now stated in the code beside the switch itself
(`satc_system/src/satc/settings.py:22-37`). No §314.4(f) assessment of Anthropic
is required while it remains off, because no customer information is disclosed.
See control **A5-C** for what must happen before it is ever enabled.

- `[CONFIRM: that the owner accepts control A5-C as written — that neither SATC_ALLOW_CLOUD nor ANTHROPIC_API_KEY is set on a machine holding real client data until this WISP is updated to cover Anthropic as a §314.4(f) service provider and a §301.7216 consent analysis is done. This is a procedural commitment: the code comment is a sign, not a lock, and nothing prevents the variables being set.]`

## C4 · Training (§314.4(e) — **not waived**)

- `[CONFIRM: who counts as "personnel" — the owner alone, or are there seasonal preparers, a bookkeeper, an admin, a contractor?]`
- `[CONFIRM: what security awareness training each of them receives, and how often]`
- `[CONFIRM: where completion is recorded]`
- `[CONFIRM: the written §§7216/6713 notice given to any contractor who works against real client data — 26 CFR §301.7216-2(d)(2) requires it. Referenced as needed at docs/research/tax-practice/03-ai-boundary.md:320; no template was found in this repository.]`

## C5 · Retention and disposal (§314.4(c)(6) — **not waived**)

**Answered, 4 September 2026 — the headline period is settled.** SATC keeps
copies of client records and its own work papers for **seven years**, after which
they are destroyed. This is not a preference to be chosen here: it is already
promised in writing in all four engagement letters (A9.1), so it binds. The
remaining questions are about *classes*, *mechanism* and *proof*, not about the
number.

- `[CONFIRM: whether any class of record needs a period DIFFERENT from the blanket seven years — Form 8879 (§1.6695-2 sets 3 years from the later of due or received date), the §1.6695-2 due-diligence bundle, engagement letters themselves, e-mail, the leads workbook. The engagement letter promises seven years for "copies of your records and our work papers"; it does not speak to the rest, and a period that is longer than required is a choice with its own cost.]`
- `[CONFIRM: **from what date the seven years runs** — the letter says "for seven years" without naming the trigger. End of engagement? Filing date? Tax year end? A promise with no clock start cannot be implemented or audited.]`
- `[CONFIRM: how the destruction at seven years will actually happen, given that nothing does it today (Gap B4) -- build the retention clock at docs/research/tax-practice/02-gap-analysis-and-roadmap.md:241-245, or run it as a dated manual procedure with a written record of each disposal. Doing neither leaves a contractual promise unkept.]`
- `[CONFIRM: what happens at the end of each period — deleted, or archived where?]`
- `[CONFIRM: how the seven years applies to the OneDrive backup copies (A7), which are rotated by COUNT (newest 14), not by age. A restored backup could reintroduce a record the firm has already promised to have destroyed.]`
- `[CONFIRM: how paper is destroyed, and by whom]`
- `[CONFIRM: how a disk or machine is sanitised before it leaves the firm's control]`
- `[CONFIRM: whether the firm wants the retention-clock design at docs/research/tax-practice/02-gap-analysis-and-roadmap.md:241-245 built, or whether this stays a manual, written schedule. **Note this is no longer optional in the way it looks:** the seven-year destruction is already promised to clients, so one of the two has to happen.]`

## C6 · Physical and administrative controls this document cannot see

- `[CONFIRM: where the machine physically lives, and who can reach the keyboard]`
- **Partly measured, 4 September 2026.** The `ajish` account **does** require a password (`PasswordRequired = True`, last set 29 July 2026). **The screen lock could not be shown to work** — see Gap **B11**. Also found: a second enabled account, `forge-readonly`, requires **no** password — Gap **B12**.
- `[CONFIRM: whether the session locks when unattended, and after how long — and if it does not, set it. A4a's whole argument for not building MFA assumes it does. See B11.]`
- `[CONFIRM: whether the passwordless forge-readonly account is still needed. It has never been logged into. If it is not, disable it; if it is, give it a password. See B12.]`
- `[CONFIRM: whether BitLocker is enabled on C: — see Gap B8; it could not be read without elevation]`
- `[CONFIRM: where the second copy of vault.key will live — see Gap B1; this is the most urgent single item in this document]`
- `[CONFIRM: how paper documents a client brings in are stored and secured]`

## C7 · Governance of this document

- `[CONFIRM: the effective date once signed]`
- `[CONFIRM: how often this WISP is reviewed — Pub 5708's expectation is at least annually, and after any material change or incident]`
- `[CONFIRM: who performs that review and where the signed copies are kept]`
- `[CONFIRM: what triggers an off-cycle review — new software, a new service provider, a new person, an incident]`
- `[CONFIRM: whether the firm's consumer count is still under 5,000, since the §314.6 exemption in Part 0 depends on it]`

---

## Signature block — unsigned

This document is **not in effect**.

| | |
|---|---|
| Qualified Individual | `[CONFIRM: name]` |
| Signature | *(unsigned)* |
| Date adopted | `[CONFIRM: date]` |
| Next review due | `[CONFIRM: date]` |
| Reviewed by counsel | `[CONFIRM: yes/no, and by whom]` |

---

## Appendix · What this draft did and did not do

**Method.** Every technical claim in Part A was established by opening the file
and citing `path:line`. Machine-state claims marked "measured 4 September 2026"
were established by running a read-only query on this machine that day: the
listening sockets, the firewall rules with their enabled state **and their
address filters**, the backup scheduled task's registration and last result, the
local accounts and their group memberships, the blank-password and screen-lock
registry policies, the four relevant environment variables at Process/User/
Machine scope, and the 37 guard tests.

**Deliberately not done.** This draft **did not open, list, or glob the live
engagement store or the leads workbook**, and contains **no real client name,
e-mail, phone number, TIN, or engagement reference**. Nor does any commit that
touches it.

**How the retention negative was established (A9.2).** A negative finding is only
worth as much as the search behind it, so: every git-tracked file was searched for
`retention`/`retain`/`dispose`/`destroy`/`expire`/`purge`/`prune`/`TTL`/
`older_than`/`cutoff`; for the deletion primitives `DELETE FROM`, `unlink`,
`rmtree`, `os.remove`; and for every scheduling mechanism (cron, APScheduler,
`schedule`, `sched`, Celery, systemd, Windows Task Scheduler, `.ps1` installers,
background threads and timers, `atexit`, GitHub Actions `schedule:` triggers).
Each hit was opened and classified. **One scheduler exists on this machine — the
backup — and it creates and count-rotates copies rather than destroying records.
One age-based purge exists — 90 days, on pre-engagement prospect drafts.** No
file matching `*retention*` exists in the repository.

**Could not be verified.**

- BitLocker status on C: — access denied without elevation, **retried
  4 September 2026 and still denied** (`Get-BitLockerVolume` and
  `manage-bde -status C:` both return access denied). Gap B8 stands unverified.
- Whether Windows locks the session on sleep/wake. The screensaver settings were
  read and show no configured lock (Gap B11), but the `CONSOLELOCK` power setting
  could not be read without elevation, so "does not lock" is **not proven** —
  only "cannot be shown to lock."
- Whether the §314.4(c)(8) audit log exists in a form that satisfies the rule
  (Gap B6).
- Whether the stray client-data copy recorded at `docs/satc-forge.md:159-162` is
  still on disk — deliberately not looked for (Gap B9).
- Everything in Part C. None of it is knowable from a repository.

**Standing caveat.** This describes the software as it is on this branch on
4 September 2026. Code changes; a control that a test proves today is a control
until somebody deletes the test. The tests in A8 run on every pull request, which
is the mechanism that keeps this section from going quietly stale — but only for
the claims a test covers.
