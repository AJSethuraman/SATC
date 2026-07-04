# SATC — Plan & To-Do Log

> Living log of where the project stands, what's in flight, and what's decided.
> Keep the date current when editing. Newest decisions at the top of the log.
>
> **Last updated: 2026-07-04**

## What SATC is (positioning — read the norms through this lens)

SATC is **process-flow / practice-operations software for the owner**, not a tax-prep engine and
not a TaxDome/Canopy competitor. **Drake stays the system of record for returns.** SATC's job:
run the business, **collect and retain client info**, provide **small services** (e.g. the
withholding estimator), and make the owner's life easier. Therefore the industry research is a
**reference map, not a feature target** — adopt norms that serve the owner's workflow; skip
client-product features (payments/invoicing, KBA e-sign, a full public portal) unless the owner
specifically wants them (Drake Portals already covers e-sign/portal if ever needed). The one thing
the "product vs internal tool" distinction does **not** change: holding client SSNs triggers the
same legal duties either way — Phase 0 below stands regardless.

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

### Industry feature norms (done 2026-07-04) — TaxDome/Canopy/Drake/SafeSend/Liscio
- **Table stakes** (every serious tool has these): secure client document portal · digital
  organizers/questionnaires · **mobile photo-scan upload** · doc-request lists tied to checklists
  with auto-reminders · **8879 e-sign with KBA** · engagement letters · workflow/job tracking
  (statuses + due dates) · secure two-way messaging (incl. SMS) · payments/invoicing · prior-year
  rollover.
- **Differentiators worth targeting:** **deep Drake integration is a real market gap** (incumbents
  pair alongside or replace Drake) → SATC's Drake-native shaping is a genuine edge · passwordless
  magic-link + mobile-first client access (the #1 adoption lever) · "last-mile" assembled-return
  delivery (review → 8879 e-sign → vouchers → K-1s; SafeSend's moat) · client-facing withholding tool
  (uncommon — SATC already has it) · flat pricing + zero setup.
- **8879 KBA facts:** KBA required for *remote* e-sign (3-of-4 identity questions), every time unless
  in-person or a multi-year business relationship. Cost ≈ **$1/sig (TaxDome)** up to **$13–17/return
  (SafeSend)**; $2.99–$5 common. (Drake's per-event KBA $ unconfirmed — credit/bulk model.)
- **Pricing SATC competes against:** Drake Portals (SecureFilePro) **$230/yr** (portal only) →
  TaxDome **~$800/user/yr** (full platform); Canopy modular ~$540–800/yr and climbs.
- **Top practitioner pain points (our opening):** brutal setup (TaxDome 6–12 wks) · slow/no-human
  support · cost & billing friction · **client-adoption friction is #1** — portals flatline, clients
  revert to email; **69% of accountants say they spend too much time gathering docs**; mobile is a
  dealbreaker for 60%+. SATC's wedge = low-friction adoption + zero setup (pre-shaped around Drake).
- **AI trend (real, shipped):** industry converged on three jobs — (1) **auto-classify/rename/route
  uploaded docs to the right checklist item**, (2) extract key fields (name/year/form type),
  (3) **auto-generate doc-request lists from prior-year data**. Canopy pushing an "agent that does the
  work." → SATC already does (1); (1)+(3) are the highest-leverage AI targets and attack the #1 pain.

### Distribution / signing / .mcpb (done 2026-07-04)
- **Unsigned PyInstaller exe** → SmartScreen "unrecognized app / Unknown publisher" + **AV
  false-positive quarantine is common with PyInstaller** (esp. `--onefile`).
- **Build change: switch `--onefile` → `--onedir`.** Faster cold start + materially less
  AV-quarantine risk. (Concrete spec change to `packaging/satc_app.spec`.)
- **Signing:** cheapest credible = **Azure Artifact Signing (formerly Trusted Signing) ~$9.99/mo**,
  now open to **individuals in US/Canada** (identity via Entra Verified ID; no 3-yr business history).
  ⚠️ **Signing no longer auto-clears SmartScreen in 2026** (EV instant-reputation is gone) — reputation
  still accrues over downloads. Signing buys a real publisher name + AV cert-whitelisting, not silence.
- **.mcpb (renamed from .dxt) is the non-technical MCP install path** — a zip + `manifest.json`,
  installed via **Claude Desktop → Settings → Extensions → Install Extension… (one click, NO JSON
  editing)**; `user_config` prompts at install. Official directory exists with review + "Verified" badge.
- **Big one: a `.mcpb` can launch `SATC.exe` directly** — `server.type:"binary"`,
  `command:"${__dirname}/server/SATC.exe"`, `args:["--mcp"]`. So we can ship ONE `.mcpb` bundling the
  exe; the colleague one-click-installs it in Claude Desktop. This **replaces the earlier
  hand-edit-claude_desktop_config.json instructions** as the real distribution path.
- **Tesseract bundling:** ship `tesseract.exe` + `tessdata/` + Apache-2.0 LICENSE/NOTICE; wire
  `tesseract_cmd`/`--tessdata-dir` (ties to the handoff OCR fix).

## Recommended roadmap (synthesized 2026-07-04 — awaiting owner sign-off on the big items)

**Phase 0 — Safe-for-real-data (gating; must precede any real-SSN handoff):**
1. **Vault encryption at rest** (SQLCipher or AES-256, key via Windows DPAPI so a non-technical user
   needs no passphrase). *Legally non-waivable* per FTC Safeguards §314.4(c)(3) even under <5,000
   clients; also earns the breach-rule "encrypted" carve-out. **Owner decision needed on approach.**
2. **CSRF tokens + Host-header allow-list** on the Flask app (H3/H2); restrictive dir/file perms (M4).
3. Ship a **WISP template** (IRS Pub 5708) as a product artifact — turns compliance into a feature.

**Phase 1 — Actually giveable:**
4. Merge to `main` + cut a **matching release** (code/exe/docs agree); root README; handoff quick-wins
   (fix `.mcpb` entry_point, OCR poppler→pymupdf, doctor Tesseract probe, doc fixes, data-dir doc).
5. Build **`--onedir`**, **sign with Azure Artifact Signing (~$10/mo)**, ship a **`.mcpb`** that
   launches `SATC.exe --mcp` (one-click Claude Desktop install). Write the "hand to a colleague" pack.

**Phase 2 — Sharpen the process flow (serve the owner, NOT compete with TaxDome):**
6. **Info collection & retention core** (the heart of what SATC is): tighten the existing
   intake → engagement-checklist → doc-request → retention loop; prior-year rollover; a single
   "what's outstanding, for whom" glance. This is "collect and retain info," not a product portal.
7. **Small services that save the owner time:** extend the withholding-estimator pattern with other
   quick client calcs; **AI doc classification/routing + auto doc-request-list generation** (SATC
   already classifies docs — highest-leverage "make my life easier" win; attacks the doc-gathering
   time sink without building a whole platform).
8. **Only if the owner wants it:** a *lightweight* secure way for clients to send docs (mobile photo →
   SATC) purely to stop the owner chasing paper — scoped as the owner's convenience, not a portal
   product. Client-facing e-sign/KBA/payments are explicitly OUT unless a concrete need appears
   (Drake Portals already does e-sign). Industry norms informed this list; they don't dictate it.

## To-do

### Security fixes (Phase 0 — in progress)
- [x] **C1 vault encryption** — AES-256-GCM on all vault PII (`persistence/crypto.py`); key sealed by
      DPAPI on Windows / 0600 key file elsewhere; transparent migration of legacy plaintext + VACUUM;
      tests prove the SSN is ciphertext on disk. `cryptography` added as a base dependency.
- [x] **M4 file perms** — data dir 0700, DB + key files 0600 (POSIX; NTFS ACLs on Windows).
- [ ] **H2**: Host-header allow-list on the Flask app
- [ ] **H3**: CSRF (origin/referer check + SameSite cookies) on POST routes
- [ ] **M7**: per-install random secret_key (replace hardcoded default)
- [ ] **M6**: protect organizer PDFs (perms / purge after send)
- [ ] **M5** local-API guard (largely covered by H2) · **L8** intake-folder guard · **L9** thread-safe store
- [ ] **Bugs:** mcpb entry_point path · OCR pdftoppm→pymupdf · doctor Tesseract probe · install.bat
      fail-loud · `satc reset` confirm

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

### Recommended sequence
See **"Recommended roadmap"** above (Phase 0 safety → Phase 1 giveable → Phase 2 features).

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
