# The project register

One card per project canon knows about. **A card says what a project IS, never
what its code currently does** — no file inventory, no counts, no status, no
"currently". Those are true the day they are written and quietly false a week
later, and a card that has been wrong once is still consulted, which is what
makes it worse than no card.

`adopt.Card` refuses to hold any of them, and `tests/test_adopt.py` has one test
per shape. Bassy reads the repository itself when it needs to know the state;
this exists so it knows what it is reading.

Cards are written by a person after an adoption run, never generated from one.
The guard caught its first real card on the first try: both entries below
originally named the documents that govern them, and both read better without.

---

## credit-review-os

**What it is:** A loan-review workpaper system that produces one committee-grade Excel workbook per engagement — a linesheet for each loan, a portfolio roll-up, a de-identified data mart, and a findings register.

**What it is for:** The consulting line, not the tax practice. A single reviewer runs a bank's loan review and emails the workbook; the regulatory crosswalk inside it is what proves the method meets the interagency standard.

**Stack:** Python, openpyxl, YAML program configs

**Where it lives:** Its own folder in the SATC monorepo. Governed by the analytics-line contract, not the practice plan.

**Convictions that apply:** none recorded

---

## stock-helper

**What it is:** A local-first research helper that digests SEC filings and XBRL company facts into signal reports, where every signal traces back to a source document, an accession number, or a calculation over disclosed facts.

**What it is for:** Grounded equity research for one operator. Explicitly not a buy/sell bot: the point is that a claim can be followed back to a filing.

**Stack:** Python, SQLite, uv

**Where it lives:** Its own folder in the SATC monorepo. Part of the consulting line, not the practice.

**Convictions that apply:** none recorded

---

## occam

**What it is:** A double-entry bookkeeping engine whose source of record is one Excel workbook per client, driven through an HTTP API, with an AI staff accountant that proposes work the engine verifies or refuses.

**What it is for:** The bookkeeping the practice does for its clients. A local model onboards a client, categorises a period, reconciles against statements and posts approved work; a human reviewer owns the ledger decisions and the client relationship, and the engine — not a prompt — is what holds that line.

**Stack:** Python, FastAPI, openpyxl, Ollama via MCP; a Vite/TypeScript client

**Where it lives:** Its own repository, separate from the SATC monorepo. Runs on the Forge, bound to loopback, and published across the private tailnet by Tailscale Serve rather than by binding a public interface.

**Convictions that apply:** none recorded
