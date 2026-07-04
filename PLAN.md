# SATC — Plan & To-Do Log

> Living log of where the project stands, what's in flight, and what's decided.
> Keep the date current when editing. Newest decisions at the top of the log.
>
> **Last updated: 2026-07-04**

## Where things stand

- **Branch:** `claude/happy-heisenberg-5rt6y1` (draft PR #21 → `main`). Suite: **242 passing**.
- **The app:** local Flask GUI (`satc-app`, default port 5050) over a shared SQLite store
  (`~/.satc/data`). Identity vault (names/SSN/EIN) is split from the de-identified working
  mart. Drake remains the system of record.
- **Built this cycle:** withholding estimator (multi-job, paystub reader, click-to-teach
  layouts, audit tape) · client intake & engagement workflows · localhost JSON API
  (`/api/withholding/estimate`, `/read-paystub`, `/meta`) · Cowork plugin (`cowork-plugin/`,
  thin HTTP-proxy MCP server + skill) · safe-by-default full MCP server (`satc-mcp`) ·
  one-exe packaging (`SATC.exe` = GUI; `SATC.exe --mcp` = agent server).
- **Agent authority model (decided):** *read + prepare, human commits.* The MCP server
  registers only read/compute tools unless `SATC_MCP_ALLOW_WRITES=1` is explicitly set —
  enforced by wiring (unregistered tools don't exist to call), pinned by tests.

## In flight

- **Full review + industry-norms research (5 parallel agents, launched 2026-07-03):**
  1. Security audit of the repo (vault-at-rest, Flask CSRF/auth, MCP surface)
  2. Handoff/usability audit ("stranger gets this today — where do they get stuck?")
  3. Compliance norms research (FTC Safeguards Rule/WISP, IRS Pub 4557/5708, §7216 & AI)
  4. Industry feature norms (TaxDome/Canopy/Drake portals — table stakes vs differentiators)
  5. Distribution norms (code signing/SmartScreen, installers, `.mcpb` for Claude Desktop)
  → Next: synthesize into a prioritized roadmap; big changes go to the owner before build.

## Review findings

### Security audit (done 2026-07-03) — verified against code
- **CRITICAL C1 — vault is plaintext.** `persistence/store.py` stores full legal
  names + SSN/EIN in an **unencrypted** SQLite file (`satc_vault.db`); a real SSN was
  pulled straight out with `strings`. No encryption, no restrictive file ACLs. This is
  the top fix and the crux of the compliance gap.
- **HIGH H2 — DNS-rebinding.** Flask sets no Host-header/trusted-host check; a malicious
  page the preparer visits could rebind to `127.0.0.1:5050` and read `/clients`, `/export`,
  `/source` (raw W-2/1099 PDFs). Fix: `before_request` Host allow-list (+ optional token).
- **HIGH H3 — no CSRF.** No tokens on any POST route; a drive-by page can blind-POST
  `/clients/<id>/discard`, `/sample/clear`, `/staging/post`, etc. Fix: Flask-WTF CSRF +
  `SameSite=Strict`.
- **MEDIUM:** M4 data dir/files at default perms (want 0700/0600 + NTFS ACLs) · M5 local
  API unauthenticated (low data impact) · M6 organizer PDFs write cleartext names to the
  unprotected data dir · M7 hardcoded default `secret_key`.
- **LOW:** L8 `run_intake` takes an arbitrary folder (writes-only) · L9 shared SQLite
  connection across threads (corruption risk).
- **Verified GOOD (don't churn):** MCP safe-by-default gating holds; MCP reads are truly
  de-identified everywhere (incl. provenance/documents); loopback bind + debug off; no
  eval/pickle/shell=True; Jinja autoescape on; `/source` path-traversal-resistant; cloud
  egress off by default; mart export is de-identified; uploads use secure_filename+tmp.

### Handoff / usability audit (done 2026-07-03) — verified against files + GitHub
- **Three-products drift (top blocker).** Default branch `main` has only a stub +
  `drake-entry-assistant/` — none of the real app. All 57 commits live on
  `claude/happy-heisenberg-5rt6y1` (unmerged). Latest Release is **v0.7.0**, whose exe
  **predates** the withholding API, MCP server, Cowork plugin, and `--mcp`. So the code on
  `main`, the exe on Releases, and the newest docs describe three different products.
- **No way to *get* the software from the docs.** No root README; `satc_system/README.md`
  starts at "double-click install.bat" but never says how to obtain the folder, and the
  code isn't on the default branch (Download ZIP gets the wrong thing).
- **OCR broken on a clean Windows box even when followed correctly.** `ingest/ocr.py`
  shells out to poppler's `pdftoppm` — not bundled, not a pip dep, not checked by doctor,
  not documented. `pymupdf` (already a dep) could do it. Also Tesseract detection is
  PATH-only with no override, so doctor says "not installed" when it is.
- **Agent story can't be set up by a non-technical person + doc contradicts code.**
  `docs/MCP.md` documents write tools unconditionally (they're now gated by
  `SATC_MCP_ALLOW_WRITES`, which appears in zero .md files); `claude mcp add satc -- satc-mcp`
  fails because `[local]` doesn't install the `mcp` extra. `cowork-plugin/mcpb/manifest.json`
  entry_point is `server/satc_mcp.py` but the file is at `mcp/satc_mcp.py` — **bundle path broken**.
- **Data location / backup / SSN story undocumented + a silent data-split trap.** Source
  install stores in `satc_system/build/data/`; the exe uses `~/.satc/data` — switch modes and
  your clients "vanish." No backup command/doc; `satc reset` deletes both DBs with no confirm.
  The plaintext-SSN fact is admitted only in one line of `docs/MCP.md`.
- **USER_GUIDE is for the wrong OS/product** (`apt-get install libreoffice-calc`, Linux dev steps).
- **Verified GOOD:** first-run sample-data UX (seeds once, banner on every page, one-click clear);
  `satc doctor` + Setup screen speak to preparers; `install.bat`/`SATC.bat` two-double-click flow;
  robust port pick; privacy posture real in code; `ARCHITECTURE.md` strong; CI attaches exe on tags.

### Compliance — FTC Safeguards Rule / WISP (done 2026-07-04) — primary-source (eCFR/FTC/IRS)
- **The Rule applies to a solo tax preparer** (preparers are "financial institutions"; no headcount
  exemption from *coverage*). (16 CFR 314; FTC guidance.)
- **The <5,000-consumer exemption (§314.6) waives ONLY four things:** the *written* risk assessment,
  annual pen-test/vuln-scan, *written* incident-response plan, and annual board report. **Everything
  else still applies.**
- **NON-waived, still required for a solo preparer:** **encryption at rest AND in transit** (§314.4(c)(3)),
  **MFA** (c)(5), **access controls** (c)(1), a Qualified Individual, the WISP itself, service-provider
  oversight, training, secure disposal. → **The plaintext-SSN vault (C1) is a real, non-waivable
  violation.** BitLocker alone = defensible checkbox but leaves SSNs readable on a running machine;
  **app-level vault encryption (SQLCipher/AES-256, key via Windows DPAPI/keystore) is the defensible
  fix** and also earns the breach-rule "encrypted" carve-out.
- **Breach rule (eff. May 13 2024):** notify FTC ≤30 days if *unencrypted* customer info of ≥500
  consumers is acquired — intact encryption (uncompromised key) keeps an incident out of the trigger.
- **IRS side** operationalizes the same duty: Pub 4557 (references the FTC WISP requirement), Pub 5708
  (small-firm WISP template), the "Security Six" (incl. drive encryption + MFA), PTIN-renewal
  data-security attestation. No separate standard — points back to the Safeguards Rule.
- **Implication:** SATC should ship vault encryption + a WISP template (Pub 5708) as product features;
  these are the difference between "hobby tool" and "giveable to a real practice."

### Compliance — §7216 / AI use (done 2026-07-03) — search-sourced, spot-check before quoting
- **New (June 24 2026): IRS OPR Alert 2026-19**, first formal guidance on practitioner AI use —
  Circular 230-framed; says handle client data "using only secure, enterprise-approved AI systems,"
  don't use "unsecured or public" tools, verify AI output. **Introductory — does NOT resolve** whether
  cloud-AI input is a §7216 "disclosure" needing consent.
- **Settled consensus:** entering identifiable client return data into public/free LLMs is effectively
  prohibited (AICPA 1.700.001 confidentiality + likely §7216 disclosure; §7216 criminal, §6713 civil);
  "disclosure" happens the moment data hits a third-party server; **no IRS §7216 AI-specific guidance
  exists** (7216 Info Center unchanged since Rev. Proc. 2013-14).
- **Unsettled:** whether the auxiliary-services exception covers proprietary/hosted AI (AICPA Tax
  Adviser leans yes; Gorczynski leans no); enterprise zero-retention deployments; whether
  **de-identification alone** avoids consent (reg text §301.7216-1(b)(3) says redaction does NOT
  exit the definition — cuts against intuition).
- **Direct implication for SATC:** our local-first, on-device posture is the *right* architecture for
  this — the exposure is entirely in the optional cloud-vision path (already gated by
  `SATC_ALLOW_CLOUD=1` + key). Keeping the default fully local is a compliance feature, not just a
  preference. Any cloud-AI feature needs a §7216 consent workflow before it touches identifiable data.

### Research NOT finished (hit account session limit, resets 3:20am UTC 2026-07-04)
- FTC Safeguards Rule / WISP full requirement + <5,000-consumer exemption detail (partial only)
- Industry feature norms (TaxDome/Canopy/Drake pricing, table stakes) — vendor sites bot-blocked
- Form 8879 e-sign + KBA facts/costs
- Distribution norms (code signing/SmartScreen, Azure Trusted Signing, `.mcpb` packaging)
- **To resume:** re-run these four after the limit resets; vendor pages need Wayback/search fallback.

## To-do

### Security fixes (from audit — triage with owner before big changes)
- [ ] **C1**: encrypt vault at rest (SQLCipher or app-level AES w/ DPAPI/OS-keychain key) + lock file ACLs
- [ ] **H2**: Host-header allow-list on the Flask app
- [ ] **H3**: CSRF tokens on all POST routes + SameSite cookies
- [ ] **M4/M6/M7**: restrictive dir/file perms; protect organizer PDFs; per-install random secret_key
- [ ] Decide local-API auth token (M5) and thread-safe store access (L9)

### Handoff quick-wins (each < 1 hr, low-risk — safe to do without a big-change sign-off)
- [ ] Add a root `README.md` (what SATC is; how to get the exe; which branch is live)
- [ ] Fix `cowork-plugin/mcpb/manifest.json` entry_point (`server/` → `mcp/`)
- [ ] Swap `pdftoppm` → pymupdf in `ingest/ocr.py` (kills undocumented poppler dep); add Tesseract
      `C:\Program Files\Tesseract-OCR` probe + `SATC_TESSERACT` override to `doctor.py`
- [ ] Update `docs/MCP.md` (document `SATC_MCP_ALLOW_WRITES` read-only default, `SATC.exe --mcp`,
      full `.venv\Scripts\satc-mcp` path, `[local]` lacks `mcp`, dev-vs-exe data dir)
- [ ] `install.bat` fail-loud on pip error; `satc reset` type-YES confirm
- [ ] "Your data" section in README (both data-dir locations, vault unencrypted, backup = copy folder,
      uninstall leaves it behind, never email the .db)
- [ ] Retitle `docs/USER_GUIDE.md` → `DEVELOPING.md`; write a real Windows quickstart in its place

### Recommended sequence (proposed — awaiting owner sign-off on the big items)
1. **Gate on safety before any real-SSN handoff:** C1 vault encryption + M4 file perms, then H2 Host
   guard + H3 CSRF. These are the "we're doing something wrong" items; a plaintext SSN store you hand
   to a colleague is the single biggest liability.
2. **Make it truly giveable:** merge to `main` + cut a real release (v0.8.0) so code/exe/docs agree;
   handoff quick-wins above; the "hand to a colleague" doc package.
3. **Then build toward industry norms** (pending the features/distribution research after reset):
   likely secure client portal for doc collection, 8879 KBA e-sign, engagement letters.

### Blocked on a human (CI permissions block the automation path)
- [ ] **Build v0.7.1 `SATC.exe`** — GitHub → Actions → *Build Windows app* → Run workflow on
      branch `claude/happy-heisenberg-5rt6y1` (or push tag `v0.7.1` from a local clone).
      The current v0.7.0 exe predates the withholding API and the `--mcp` agent mode.

### Next (pending synthesis of the five reports)
- [ ] Triage security-audit findings; fix criticals (expect: vault encryption at rest,
      CSRF on form routes, local API auth)
- [ ] Triage handoff-audit blockers; write the "give this to a colleague" package
- [ ] Compliance gap list (WISP template, §7216/AI stance) → decide what SATC must do vs document
- [ ] Roadmap: what to build next, informed by industry table-stakes research

### Decided, not yet done
- [ ] Windows quickstart doc for Claude Desktop setup (exact config-file steps, both
      from-source `satc-mcp` and future `SATC.exe --mcp` paths)

### Explicitly deferred (decided against for now)
- HTTP refactor of the full read+write MCP server — investigated 2026-07-03, net-negative
  today (0 of 7 heavy tools have JSON endpoints; shared store already gives write
  visibility; folder-intake provenance doesn't survive an HTTP boundary). Revisit only if
  the agent must be decoupled from the host machine.
- Shared staging gate (agent stages intake → human confirms in app) — deferred with the
  decision to keep intake entirely in the app.

## Decisions log

- **2026-07-03 — Review & research pass ordered.** Owner directive: review everything,
  fix what's wrong, research industry norms, design for handoff ("time to look higher").
  Big changes require owner sign-off.
- **2026-07-03 — One exe, both modes.** Bundle the agent server into `SATC.exe` behind
  `--mcp` rather than shipping two artifacts. `mcp` package added to the frozen build.
- **2026-07-03 — Safe by default.** Agent gets read/compute only; writes are opt-in via
  `SATC_MCP_ALLOW_WRITES=1`. Chosen over per-write confirmation prompts and full autonomy.
- **2026-07-03 — Intake stays in the app.** Agent does not stage intake; the staging gate
  is per-process and won't be shared across processes for now.
- **2026-07-03 — Two audit-found bugs fixed** (`a639931`): read tools leaked the vault
  legal name (now return the de-identified display label); staging-gate desync documented
  and read tools now `reload()` first.
- **2026-07-03 — Withholding-only over HTTP.** The Cowork plugin proxies just the
  stateless, no-PII withholding API; the heavy tools stay in-process.
- **2026-06 — Cowork plugin built** to the four-layer blueprint (app API → thin MCP proxy
  → plugin skills → agent), scoped to withholding.
