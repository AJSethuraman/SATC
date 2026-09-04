# SATC — Plan & To-Do Log

> Living log of where the project stands, what's in flight, and what's decided.
> Keep the date current when editing. Newest decisions at the top of the log.
>
> **Last updated: 2026-08-27**

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

> **2026-08-27.** This section and "In flight" below had gone thirteen days
> stale, and the review findings further down had gone nearly two months
> stale — several of them describe defects that were fixed weeks ago. The
> stale parts are now marked in place rather than deleted, because what a
> finding said and when it stopped being true are both worth keeping.
>
> **`docs/REPO-INVENTORY.md` is the current map of the whole repo** and is
> the file to read first. This one is the decision log.

- **Test suites, 27 August:** `client-documents` **966** · `satc_system`
  **259** · `invoice-generator` **63**. The 242 below was `satc_system` on
  14 August.
- **In flight now:** PR #155 on
  `claude/satc-handoff-batches-2-4-n2qrl9-b7-fee-estimate` — the controls
  layer around the document pipeline: a blocking pre-send gate, the tenet
  linter in both halves, the lifecycle documents, the close-out
  reconciliation, and generated operating procedures. Draft; nothing near
  `main`.
- **The `satc_system` branch below:** `claude/happy-heisenberg-5rt6y1`
  (draft PR #21 → `main`). Suite: **242 passing** as of 14 August; 259 today.
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

- **Full review + industry-norms research (5 parallel agents, launched 2026-07-03)
  — DELIVERED. The findings are below; several are since fixed, and each is
  marked.**
  1. Security audit of the repo (vault-at-rest, Flask CSRF/auth, MCP surface)
  2. Handoff/usability audit ("stranger gets this today — where do they get stuck?")
  3. Compliance norms research (FTC Safeguards Rule/WISP, IRS Pub 4557/5708, §7216 & AI)
  4. Industry feature norms (TaxDome/Canopy/Drake portals — table stakes vs differentiators)
  5. Distribution norms (code signing/SmartScreen, installers, `.mcpb` for Claude Desktop)
  → Next: synthesize into a prioritized roadmap; big changes go to the owner before build.

## Review findings

### Security audit (done 2026-07-03) — verified against code

> **Re-verified against the code on 2026-08-27: C1, H2, H3, M4 and M6 are
> FIXED.** `persistence/crypto.py` encrypts the vault's PII with AES-256-GCM;
> `app/server.py` rejects a non-loopback `Host` header and a state-changing
> request a browser marks as cross-origin; the data directory and its files
> are created 0700/0600, and the organizer PDF folder with them. The entries
> below are left as written, with their status noted, because the finding and
> the date it stopped being true are both worth keeping. **M5, M7, L8 and L9
> were not re-checked and are not claimed either way.**

- **CRITICAL C1 — vault is plaintext. FIXED (AES-256-GCM, `crypto.py`).** `persistence/store.py` stores full legal
  names + SSN/EIN in an **unencrypted** SQLite file (`satc_vault.db`); a real SSN was
  pulled straight out with `strings`. No encryption, no restrictive file ACLs. This is
  the top fix and the crux of the compliance gap.
- **HIGH H2 — DNS-rebinding. FIXED (`server.py` Host allow-list).** Flask sets no Host-header/trusted-host check; a malicious
  page the preparer visits could rebind to `127.0.0.1:5050` and read `/clients`, `/export`,
  `/source` (raw W-2/1099 PDFs). Fix: `before_request` Host allow-list (+ optional token).
- **HIGH H3 — no CSRF. FIXED (cross-origin state-changing requests refused).** No tokens on any POST route; a drive-by page can blind-POST
  `/clients/<id>/discard`, `/sample/clear`, `/staging/post`, etc. Fix: Flask-WTF CSRF +
  `SameSite=Strict`.
- **MEDIUM:** ~~M4 data dir/files at default perms~~ **FIXED (0700/0600)** · M5 local
  API unauthenticated (low data impact) · ~~M6 organizer PDFs write cleartext names to the
  unprotected data dir~~ **FIXED (folder restricted to 0700)** · M7 hardcoded default `secret_key`.
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
  oversight, training, secure disposal. → **The plaintext-SSN vault (C1) was a real, non-waivable
  violation. It is encrypted as of the C1 fix** — AES-256-GCM at the field
  level, which is the "app-level vault encryption" this paragraph names as
  the defensible answer. BitLocker alone = defensible checkbox but leaves SSNs readable on a running machine;
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

- **The agent factory — a skill that builds an expert.** The firm's own thought, raised
  4 September 2026 while specifying expert desks: *"it might make sense for us to make a
  dedicated skill or some session or whatever that helps create an agent and perform the
  required research and validate its findings and run it up against bassy's judgment with
  canon."* It runs the research, validates the findings against primary sources, and puts
  the result up against the record before anything ships. Sibling to
  `docs/prd-expert-desks.md`, not part of it — the desks work has to prove the shape
  first, or the factory is built against an imagined product.
- **The second expert desk, and its metric.** v2 of the desks work, and it is the proof
  that the mechanism generalised: the number to report is **how many changes the second
  desk forces on the shared layer.** Zero means general; four means it was accounting
  wearing a framework's clothes. The domain should be deliberately far from accounting —
  law, prompting, or market research were all named.

**Phase 0 — Safe-for-real-data (gating; must precede any real-SSN handoff):**
1. **Vault encryption at rest** (SQLCipher or AES-256, key via Windows DPAPI so a non-technical user
   needs no passphrase). *Legally non-waivable* per FTC Safeguards §314.4(c)(3) even under <5,000
   clients; also earns the breach-rule "encrypted" carve-out. **Owner decision needed on approach.**
2. **CSRF tokens + Host-header allow-list** on the Flask app (H3/H2); restrictive dir/file perms (M4).
3. Ship a **WISP template** (IRS Pub 5708) as a product artifact — turns compliance into a feature.

**Fee automation (added 2026-08-25, after the pricing sign-off):**
- **Phase A — the 1040 fee estimate renders for real.** Specified in
  `client-documents/docs/prd-1040-fee-estimate.md`. Reshape `fee-schedule.yaml` to hold
  the four-package ladder, the $50 per-form rule and the allowances, fill in the signed
  prices, and prove a real estimate out of both front doors.
- **Phase B — the invoice bridge.** Estimate line items → an invoice **carrying a Square
  payment link**. Its first question — which processor the client sees — was answered
  2026-09-04 (Square; Invoicer retired). What is left is the wiring: `payments.py` builds
  the link and nothing calls it, while the delivery letter already promises it.
- **Phase C — entity returns.** The `1120S/1065/1120` bases and the five business-return
  gates (balance sheet $350, payroll $150, inventory $125, assets bought this year $95,
  first year $250), on the pattern Phase A establishes.

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

### The end-of-cycle reconciliation control

- [ ] **Check our data against what was actually filed, and update it.** The
      firm, 26 August 2026: *"our interview and such is system of record until
      proven wrong. we should update the data to match what we file if
      required. this should be a control we build at the end of the cycle."*
      Filing is the moment our answers are proven right or wrong, and today
      nothing looks. Until this exists, "authoritative until proven wrong" has
      no mechanism behind the second half. Depends on nothing else; blocked
      only on where the filed figures are read from.

### Owed to the firm when the documents are done

- [ ] **Walk the whole fee schedule with the firm, line by line.** Asked for on
      26 August 2026: *"when we are said and done i will have you give me the
      fee schedule and we will ensure it's right."* Not a diff and not a
      summary — the schedule itself, in a form the firm can read straight
      through and correct. Every price, every assumption, every publish
      decision, and what each one prints on a client's estimate. This is the
      point at which the money is signed off as a whole rather than a round at
      a time, so it comes after the documents settle, not before.

### Raised in the sign-off room, 26 August 2026 — build work, not wording

These came out of the firm reading the rendered documents. The wording notes
were applied the same day; these three are the ones that need something built.

- [ ] **A licence expiry check.** The firm: *"let's make a note to incorporate
      a license expiry check we can email clients about as well."* We ask for
      photo ID at onboarding and an ID has a date on it, so the software could
      watch it and write to the client before it lapses. Nothing captures the
      date today — the request list asks for the ID, not for what is on it.
      Needs deciding: whether the expiry is a field on the record at all, given
      an ID is identity data and `CLAUDE.md` keeps that out of this store.
- [ ] **A business attachment for Schedule C clients.** The firm, on the
      onboarding letter's one-line request for business income and expenses:
      *"there is likely more to this - maybe we should just have a separate
      attachment for business stuff depending on your situation."* Right, and
      it is a document rather than a longer line — what a Schedule C needs
      depends on payroll, inventory, a vehicle, a home office. The line is left
      as it stands until that attachment exists.
- [ ] **Preliminary and final numbers on the delivery letter.** The firm: *"we
      can have a process that inputs the preliminary numbers (these) into the
      workbook which then fills the template (or whatever we are using as a
      database) and then we can record final numbers as well."* The delivery
      letter's `ReturnsDelivered` list is hand-built today. It should come from
      the same place the return's figures do, and the final numbers should be
      recorded when they are known.


### Security fixes (Phase 0 — in progress)
- [x] **C1 vault encryption** — AES-256-GCM on all vault PII (`persistence/crypto.py`); key sealed by
      DPAPI on Windows / 0600 key file elsewhere; transparent migration of legacy plaintext + VACUUM;
      tests prove the SSN is ciphertext on disk. `cryptography` added as a base dependency.
- [x] **M4 file perms** — data dir 0700, DB + key files 0600 (POSIX; NTFS ACLs on Windows).
- [x] **H2 Host-header allow-list** — `before_request` rejects non-loopback Host (blocks DNS-rebinding).
- [x] **H3 CSRF** — `before_request` blocks state-changing requests with a foreign Origin/Referer;
      no-Origin local tools + the JSON API still work; SameSite=Lax + HttpOnly session cookie.
- [x] **M7 secret_key** — per-install random key (persisted 0600), overridable via env; old hardcoded
      default gone. (M5 local-API is now covered by the H2 Host guard.)
- [x] **M6** organizer PDFs written 0600 in a 0700 dir (cleartext names protected).
- [x] **L8** intake-folder guard (opt-in `SATC_INTAKE_ROOT`) · **L9** app runs single-threaded
      (shared SQLite conns aren't concurrency-safe).
- [x] **Bugs:** `.mcpb` entry_point path fixed · OCR now rasterizes with pymupdf (no poppler) ·
      Tesseract auto-detected (+`SATC_TESSERACT`) · `install.bat` fails loudly + installs `[local,mcp]` ·
      `satc reset` requires typed confirmation (`--yes` to skip).

**✅ PHASE 0 COMPLETE (2026-07-04)** — all audit findings (C1/H2/H3/M4-M7/L8/L9) and handoff bugs
patched and tested; suite 259 passing. Safe to hold real client SSNs (on a Windows box with the
DPAPI-sealed vault key). Remaining before a real handoff = Phase 1 (merge to main, matching release,
docs) — not security.

### Phase 1 — documentation (done 2026-07-04)
- [x] Root `README.md` — what SATC is (practice-ops, Drake stays SoR), how to get it, data-safety, docs map.
- [x] `docs/QUICKSTART_WINDOWS.md` — the real end-user guide (install → first return + Your Data & Security
      + troubleshooting table). This is the doc the handoff audit said was missing.
- [x] `docs/MCP.md` rewritten — safe-by-default read-only, `SATC.exe --mcp` + `.mcpb`, full
      `.venv\Scripts\satc-mcp` path, `[local,mcp]`, dev-vs-exe data dir, encrypted-vault note.
- [x] `USER_GUIDE.md` → `DEVELOPING.md` (retitled; end users pointed to the Quickstart).
- [x] "Your data" guidance in root README + `satc_system/README.md` (encrypted vault, two data dirs,
      backup=copy folder, uninstall leaves it, never email .db, WISP obligation).
- [x] Handoff bugs (mcpb path, OCR/poppler, doctor Tesseract, install.bat, reset) — done in Phase 0.

### Recommended sequence
See **"Recommended roadmap"** above (Phase 0 safety → Phase 1 giveable → Phase 2 features).

### Blocked on a human (CI permissions block the automation path)
- [ ] **Build v0.7.1 `SATC.exe`** — GitHub → Actions → *Build Windows app* → Run workflow on
      branch `claude/happy-heisenberg-5rt6y1` (or push tag `v0.7.1` from a local clone).
      The current v0.7.0 exe predates the withholding API and the `--mcp` agent mode.

### Next (pending synthesis of the five reports)

**Three of these four were done and never ticked** — checked against the code and
the files on 4 September 2026, not against this document. Left visible rather
than deleted, because the fourth is real and deleting the list would have taken
it with them.

- [x] ~~Triage security-audit findings; fix criticals~~ — **superseded by Phase 0
      above**, which is marked COMPLETE and names each fix. Verified on the code:
      `persistence/crypto.py` (AES-256-GCM at rest), `app/server.py:79-83`
      (rejects a cross-origin state change), `app/server.py:35,324` (binds
      127.0.0.1, `_LOCAL_HOSTS` gate).
- [x] ~~Triage handoff-audit blockers; write the "give this to a colleague"
      package~~ — `satc_system/docs/QUICKSTART_WINDOWS.md` exists; Phase 1 above
      records it as "the doc the handoff audit said was missing".
- [x] ~~Roadmap~~ — **"Recommended roadmap"** above, synthesized 2026-07-04.
- [ ] **The WISP. This one is real, and it is the only thing in this list that
      is.** See the FTC Safeguards findings above: the <5,000-consumer exemption
      waives the *written risk assessment*, the pen-test, the *written incident
      response plan* and the annual board report — and **the WISP itself is
      listed as NOT waived**, alongside encryption, MFA, access controls, a
      Qualified Individual, service-provider oversight, training and secure
      disposal. IRS Pub 5708 is a small-firm template. Nothing in this
      repository is a WISP; searched 4 September 2026.

      **Two things since 3 September make it more pressing, not less:**
      the Forge now holds real client data rather than a test rig, and the daily
      backup sends the vault to Microsoft — which puts a **service provider** in
      scope, and service-provider oversight is on the non-waived list too.
      Encryption at rest, the other non-waived item this repository owns, is
      done.

### Decided, not yet done
- [ ] Windows quickstart doc for Claude Desktop setup (exact config-file steps, both
      from-source `satc-mcp` and future `SATC.exe --mcp` paths)

### Explicitly deferred (decided against for now)
- ~~**Square vs Stripe — `delivery.payment_instruction`.**~~ **DECIDED 2026-09-04:
  Invoicer is retired.** The firm takes Square, Invoicer is Stripe end to end
  (`invoice-generator/stripe_utils.py`, `stripe==10.5.0`, and no Square anywhere in it),
  and the document pipeline is where invoicing actually lives. PR #139 — the Invoicer
  restyle — was closed with the decision. The branch is kept; nothing was deleted.

  **What the decision did NOT do, and this is the part that matters.** Retiring Invoicer
  removes the *conflict*; it does not build the link. Three facts, each verified in
  source rather than read off a document:

  | | |
  |---|---|
  | `registry/firm-settings.yaml:101` | promises the client *"the secure Square link on your invoice"* |
  | `invoicing.py:35` | says it deliberately **"does not take payment"** — the bridge stops at the document |
  | `payments.py:303` | can build a Square payment link, **and nothing outside that file calls it** |

  So a client reading a delivery letter today is told to pay through a link the invoice
  does not carry. That is now the whole of Phase B, and it was never Invoicer's to close.
  The Stripe-vs-Square question is answered; the wiring is not written.
- **The 2026 materials deadlines** — four firm settings that block the engagement and
  organizer letters, not the estimate. Each needs a lead time chosen against the filing
  date, which is its own conversation (2026-08-25).
- **Bookkeeping pricing** — parked with a reason rather than left blank: *"this just
  needs its own workstream and we will get there when we get there - for now we have
  cleanup in tax prep."* The `assumed.cleanup` hourly line holds the honest tax-prep
  case meanwhile (2026-08-25, thread T-12).
- **Interview and pricing for non-return services** — bookkeeping, advisory, planning,
  entity setup, notice resolution. Each needs its own base-and-adder model; the first
  interview build covers **tax return preparation only**. Roadmap, not a permanent no
  (2026-08-14). See `docs/prd-interview-and-field-registry.md`.
- **RITA locality counting** — whether one Ohio RITA filing counts as a single locality
  or several, for both the `LocalReturns` string and the billable count. Deferred while
  prices are deferred; it changes a fee, not a field (2026-08-14).
- HTTP refactor of the full read+write MCP server — investigated 2026-07-03, net-negative
  today (0 of 7 heavy tools have JSON endpoints; shared store already gives write
  visibility; folder-intake provenance doesn't survive an HTTP boundary). Revisit only if
  the agent must be decoupled from the host machine.
- Shared staging gate (agent stages intake → human confirms in app) — deferred with the
  decision to keep intake entirely in the app.

## Decisions log

- **2026-09-04 — Docket answers (desk build).** Four decisions put to the firm as a
  form and answered there; recorded here because an answer that lives only in a page
  has to be asked again.

  **Merge the desk build.** *"Merge it."* PR #235 — seven of eleven desk slices plus
  the scoreboard harness. Merging is the precondition for issue #230, the hook switch.

  **Issue #227 runs on the Forge, not from a cloud session.** *"Run it on the Forge."*
  A cloud session reaches neither Ollama nor the GPU, and a frontier-only row would
  answer none of what C10 asks — the whole question is what the local lean costs, and
  one row cannot say. Remote Control on that machine is where both rows exist.

  **The nine older draft pull requests get triaged.** *"Triage and report back."*
  Read and report; close nothing without a further yes. The repository was carrying
  ten open pull requests, all drafts, nine of them predating the desk work — a pile
  nobody triages is where the next genuine thing stops being noticed.

  **The Codification licence's AI clause is checked at purchase.** *"Will check the
  clause and report."* §3(b) of the free licence bars use in connection with large
  language models under any circumstances; whether Professional View carries the same
  clause is unread. It decides one field: ASC stays `human_only` or becomes
  `signed_in_browser`. The design is built so that is a data edit, not a rebuild.

  **Later the same day, the firm put it on the backburner:** *"backburner the paid cert,
  we will test the process and see what we learn."* So ASC stays `human_only`, and the
  first desk proves the mechanism on federal authority — public, binding, and free —
  before anyone spends money to widen it. This is the right order and not merely the
  cheap one: a licence bought to feed a process nobody has run yet is a bet on a design
  that has produced no evidence. What the fixed-assets desk scores is the evidence, and
  it decides whether the paid view is worth buying at all.

- **2026-09-04 — An agent reads what the firm pays for, on the machine that is already
  signed in.** Standing rule for any agent of this practice that reaches the web, recorded
  while specifying a browser capability for the desks (issue #231).

  **Where it runs decides what it can reach, and the two cases are not alike.** An
  Anthropic-hosted cloud session sits behind an egress proxy: Chromium is pre-installed
  there, `no_proxy` covers only localhost, the Anthropic API and package registries, and a
  browser's traffic is refused exactly as any other client's is — so inside a cloud
  container a different client is not a different permission, and the fix is the
  environment's allowlist rather than another tool. A **Remote Control session on the
  firm's own machine is not that**: it *"uses your machine's network and files, not a cloud
  environment"*, so there is no proxy and nothing to route around. The first version of
  this entry generalised the container's constraint to every session and was wrong.

  **A fresh browser is not the firm's browser.** Reaching a licensed source is not the same
  as being able to read it: Checkpoint or ASC Professional View answer to a signed-in
  session, so the capability that matters is driving the browser profile that is *already*
  logged in, on the machine that holds it. That is what the firm meant by *"as though it is
  using my work computer"*, and it is why this belongs on the Forge — not because a cloud
  container is blocked, but because a cloud container is nobody.

  **Reachable is not the same as permitted, and reading grants no storage right.** Terms
  and robots.txt still decide whether a source may be accessed automatically, wherever the
  session runs — a question separate from copyright, and unread for FASB as of this date. A
  licensed source stays uncacheable whatever client read it: the citation and tier are
  recorded, the text is not. Credentials never enter a repository in any form.

- **2026-09-04 — Expert desks: the mechanism is the deliverable, one desk is the
  proof.** Grilled this session; spec in `docs/prd-expert-desks.md`. A *desk* is an
  expert a doer agent consults so a question does not reach the firm — it answers only
  from cited authority, states how binding that authority is, and escalates rather than
  guesses. Three rulings worth keeping out of the PRD, because they outlive it:

  **Roles divide by information, not by subject.** The firm's first shape was one agent
  per topic — GAAP, cash basis, fixed assets. C7 says *"the division is not headcount,
  it is information"*, and each of those decomposes into an engine plus an input rather
  than into a brain: basis is a recorded fact about the engagement that selects rules,
  and fixed assets is a depreciation engine plus one judgment call. The split that
  survives is doer → desk → firm.

  **Big 4 guidance is not primary authority.** Proposed as such and corrected in the
  grill. It is one firm's reading of the standard, and a record that flattens the
  distinction hands over a whitepaper's opinion in the same voice as a regulation —
  which is the *"large conjecture"* failure the firm named in the same breath. Three
  tiers; anything resting only on tier 2 or 3 is an escalation, not an answer.

  **What may be stored is a per-source fact, not a policy.** Researched, not assumed —
  `docs/research/accounting-authority-sources.md`. FASB's notice forbids content being
  *"stored in a retrieval system"*, and a git repository is one; 17 U.S.C. § 105 puts
  federal authority in the public domain. Offline storage does not change the analysis;
  a licence the firm holds might. So `may_store` is a field per source, defaulting to
  `license_check`, which stores nothing.

- **2026-09-04 — The Forge is a flag, not a gate, until VRAM allows.** Anything the
  practice builds is scored on the Forge *and* on a frontier model, two denominators
  reported side by side and never summed. The firm: *"it's also acceptable that it would
  not work on our current hardware, that should just be flagged. at some point we will
  have enough vram, for now we are limited."* This is how C10's lean gets honoured
  without becoming a rule that stalls work — the cost of running local is measured
  rather than argued about.

- **2026-08-27 — The pre-send gate blocks, with a logged override.** The firm's
  choice over advisory-only and over blocking-with-no-escape: *a gate with no
  override will one day stop a return going out at eleven at night and there
  will be nothing to do about it; a gate that can be waved through silently is
  not a gate.* `--force` needs `--reason`, and both go to the engagement's own
  append-only log. If the log cannot be written, the pack is not written.
- **2026-08-27 — Exact tenets block; judgement ones advise.** A tenet a machine
  can check exactly becomes a hard failure. One it can only guess at prints as a
  note, and is promoted only after a full cycle with no false positive. Eight
  block today; ten advise behind `package --notes`; thirteen were measured and
  dropped because a machine is the wrong instrument for them.
- **2026-08-27 — Reconciliation is a short close-out interview, not a Drake
  read.** What we said in January, checked against what was filed in April, from
  the preparer's own answers. **No question asks for a figure** — a test enforces
  it — because a figure would make this a second set of books, and Drake stays
  the system of record.
- **2026-08-27 — Operating procedures are generated from the harness.** Not
  written beside the software. Every step is read out of the code that performs
  it, so the document cannot name a command that does not exist or claim a check
  the gate does not run. `procedures --check` fails in the suite when the
  committed copy drifts.
- **2026-08-27 — Order of work: money risk, then gates, then features, then
  procedures.** The firm's ranking. Procedures went last deliberately —
  documenting an ungated pipeline documents a pipeline that can still ship
  unreadable documents.
- **2026-08-27 — Every check reports its denominator.** Forced by finding two
  blocking gates that had passed on every real send while examining nothing. A
  check with nothing to look at prints `NONE`, never `ok`, and the count comes
  from the check's own census rather than from beside it. See
  `docs/SOFTWARE-TENETS.md` S2.

- **2026-08-25 — Build one thing correctly, then use it as the blueprint.** The
  operator's own framing while scoping the fee-estimate work: *"we can do one thing
  at a time correctly and use that as our kind of blueprint for the next step."*
  Applied immediately — the estimate v1 covers Form 1040 only, with entity returns,
  the invoice bridge, the payment processor and the materials deadlines all fenced
  out rather than carried along. It is a working principle, not a one-off scoping
  call: prefer a narrow path proven end to end over a wide one proven nowhere.
- **2026-08-25 — Gates are complexity checks answered from facts, and past the
  assumptions the fixed prices stop applying.** Written as the header comment of
  `client-documents/registry/fee-schedule.yaml` so nobody changes a price without
  reading it. Three claims: a gate never asks a client to rate their own complexity;
  hourly is what happens *instead of* a fixed price, not a surcharge on one; and
  every price assumes the client supplies what we asked for. The corollary, from the
  same week: where **our process** costs more than the return needs, that is a cost
  to fix, not a cost to bill (`docs/workflow-friction-log.md`).
- **2026-08-25 — Pricing goes on a public page, for transparency.** The firm, against
  a recommendation to show the number only at the end of the intake: *"i plan to
  operate transparently and find it personally frustrating it is hard to know what
  you will pay upfront on most tax sites."* The recommendation was about risk; the
  decision is about positioning, which is the firm's call. Three consequences are now
  requirements rather than good practice — nothing goes on the page that is not in
  `fee-schedule.yaml`, the three unset entity bases say "quoted after a conversation"
  rather than leaving a gap a visitor fills in, and the page must be checkable
  against the schedule in under a minute. Instructions for the website agent are in
  `docs/pricing-for-website.md`; the intake estimate is the second half of the same
  idea, not a replacement for it.
- **2026-08-25 — What a package covers prints on the estimate, and `includes:` is
  followed rather than printed.** An estimate that names a package and a price and
  nothing else asks the client to take the number on faith. "Everything in Standard"
  is true on a price page where the reader can see Standard and meaningless on an
  estimate where they see one package, so the ladder is data and the chain is
  expanded. It carries the allowances down with it, so a package cannot claim to
  include everything in the rung below and quietly allow less. Counted lines say
  "after the first" for the same reason.
- **2026-08-25 — Warn, do not derive.** Rentals outnumbering local returns is worth a
  preparer's eye and is not a fact the software may infer: townships levy no income
  tax, an out-of-state rental owes an Ohio city nothing, and deriving the count would
  quietly bill for returns nobody has to file. That needed a third channel — until
  now the interview could say HARD NO or nothing. `Outcome.flags` is preparer-facing,
  changes no price, reaches no client document, and appears on every outcome
  including the refused ones.
- **2026-08-25 — Brokerage comes off the hourly list; an assumption and a price for
  the same overrun is worse than either alone.** $45 a statement past the first, $95
  for one that has to be keyed, and `assumed.brokerage` deleted rather than reworded.
  The direction of travel is worth noticing: an assumption with an hourly consequence
  is what a firm writes when it has not decided the price. What the deletion cost the
  client — the estimate no longer warns that keying costs $95 — is open as T-14.
- **2026-08-25 — The pricing write-up is retired; the sheet carries the reasoning.**
  Deferred twice, which was the signal. Every line on the price sheet now carries its
  own justification and `docs/pricing-and-deadlines-basis.md` holds the derivation, so
  a third prose copy only went stale faster than the other two.

- **2026-08-14 — `EngagementRef` format wins over the lead number.** The templates
  specify `YYYY-NNNN` (`2027-0114`) and require it byte-identical across letter,
  estimate, onboarding letter and every invoice. The `SATC leads.xlsx` Lead Number
  formula generates `2026 - 0001`. The template format is authoritative; the lead number
  changes to match, and a lead's number becomes its `EngagementRef` on conversion — one
  identifier for a client's whole life.
- **2026-08-14 — `PeriodLabel` is derived per document, not stored.** The estimate and
  onboarding letter use it for the engagement period ("2026 tax year"); the invoice uses
  it for the period billed ("March 2027"). Sharing one stored value would print the wrong
  thing on one of them.
- **2026-08-14 — `MaterialsDeadline` is a firm setting, not a per-client answer.** One
  fixed date per return type per season. It prints in three documents and the organizer's
  field doc calls a mismatch "this template's most likely bug".
- **2026-08-14 — The interview record holds no TIN.** Legal name, address, email and
  phone are in scope; SSN, ITIN and EIN are not, and a denylist test enforces it. The
  record lives in OneDrive, which is not an appropriate store for identifiers.
- **2026-08-14 — No fee quoted on the call.** A single estimate follows in writing inside
  the engagement letter, under the standing disclosure paragraph. The live site's
  "discuss timeline and cost" over-promises this and needs a copy fix.
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
