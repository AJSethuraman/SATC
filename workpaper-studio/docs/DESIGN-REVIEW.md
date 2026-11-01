# Workpaper Studio — design review checkpoint

*Working title. 1 November 2026. Status: **design checkpoint. No product code exists.** The only code is a clickable prototype in `prototype/`, built on synthetic data with fictional rules.*

**Shortest version: open `prototype/configurable.html`.** A tool is configuration, so you edit it on the left and the workpaper on the right is generated from it. Four unrelated tools run on the same engine. Everything below is the argument for that.

**Read this first, then `DECISIONS.md`.** This file is the argument; `DECISIONS.md` is the register of what is confirmed, proposed and open; `HANDOFF.md` is how the next session continues.

---

## 0 · What I need from you

Five decisions change what gets built. The rest have defaults I will proceed on unless you say otherwise. Full text, options and reasons are in §3.

| # | Decision | My recommendation |
|---|---|---|
| D1 | Who configures a tool: the firm, for itself and its clients, or each customer organization on its own? | **The firm, with setup that a customer admin could later use.** No multi-tenant service. |
| D2 | Extend `credit-review-os`, or start a sibling? | **Sibling folder.** `credit-review-os` stays the generated-workbook path; its programs become starting templates. |
| D3 | What is the finished thing: a workbook, an application, or both? | **A configured local application. Workbook, PDF and data feed are outputs, never the interface.** |
| D4 | Where do calculations come from? | **A small tested library. Organizations choose and tune methods; they do not write arithmetic.** Simple rules for applicability and limits are organization-written. |
| D5 | First use case | **Small-business credit review** (your workbook), with month-end bank reconciliation only as the proof of reuse. |

Also needed, but not blocking design: **the real output feed format** from whoever owns the receiving system (D7), and your own workbook or photographs, which I have not seen (§1).

---

## 1 · What I inspected, and what I did not have

**Inspected.** The whole repo's top level, `CLAUDE.md`, `docs/DESIGN-PRINCIPLES.md`, `docs/REPO-INVENTORY.md`, `canon/CONVICTIONS.md` and `TENETS.md`, `credit-review-os/` (README, a program YAML, the linesheet builder), and `satc_system/configs/line_sheets/`.

**Not available.**
- **No photographs, and no copy of your Excel linesheet.** Nothing in the repo or the session. I worked from your description. Where I mapped one of its features to a design, that is my reading, and a photograph could correct it (table in §7).
- **The AI KIT tabs.** Not seen. Treated as development templates, as you said.
- **Any verified integration contract** for the system your workbook feeds. The feed in the prototype is a labelled mock.

**What already exists, and why it matters.** The repo is not greenfield for this idea:

| Existing | What it does | Relevance |
|---|---|---|
| `credit-review-os/` | YAML program per line of business → a generated, encrypted Excel workpaper per engagement. Token grammar (`{row_id}`, `[POL key]`), exception model, evidence staleness, regulatory crosswalk. 106 tests. | The closest ancestor. Its **interface is Excel** and its PRD makes the workbook the source of truth. This product inverts that. |
| `satc_system/configs/line_sheets/*.yaml` | Tax line-sheet configs with row kinds (`input`, `computed`, `crosscheck`, `cflink`). | Same pattern, tax side. Confirms the config-as-data approach works here. |
| `client-documents/` pre-send gate | A blocking check before anything leaves. | The model for this product's **release check**. |
| `canon/` | The firm's recorded convictions. | Several bind this design (§10). |

Neither existing project has: an interactive case interface, versioned methods with an approval path, repeating tables, the missing/zero/N/A/excluded distinction as data, reviewer feedback as a first-class object, or a case that pins the versions it was done under. Those are the new ground.

---

## 2 · My understanding of the product

**One sentence.** A way for an organization to define a structured review once, from tested building blocks, and then have its people complete, review and release that review as a record in which every number can be traced to an entry and a rule.

**What it is.**
- **Deterministic.** Same entries, same versions, same results. Nothing generated, nothing estimated. People exercise and document judgment; the software never substitutes for it.
- **Configured, not coded.** Setup is choosing and arranging, in the customer's words. Nobody needs to understand software architecture.
- **A record, not a form.** A saved case keeps what was entered, what was calculated, under which template and method versions, who reviewed it, and what changed.

**What it is not.** Not a tax engine (Drake stays the system of record for filed returns). Not a general spreadsheet. Not a workflow suite with chat or AI. Not a dashboard. Not an assertion of any lending, tax or accounting rule: every method and threshold in the prototype is fictional and labelled so.

**Three levels** (your proposal; I think it holds, with one adjustment).

1. **Organization defaults**: terminology, roles, reference lists, evidence expectations, data connections.
2. **Tool configuration**: sections, fields, repeating tables, guidance, calculation components, limits, review stages, outputs.
3. **Case**: facts entered; organization-defined conditions decide which parts apply.

*Adjustment.* Between levels 1 and 2 sits a thing the prompt implies but does not name: the **method library** (approved calculations). A method is not organization policy and not a tool layout. It is reusable arithmetic with declared inputs, owned and approved separately. Treating it as its own level-1½ object is what lets you "select a component and have its inputs, validation and explanations come along", and later remove it without losing information another component needs (§6).

**Who is who.** Configuring and doing are different people, and the design enforces it:

| Role | Does | Never does |
|---|---|---|
| **Preparer** | Completes the case; answers review points | Sees setup screens; approves own work |
| **Reviewer** | Reads; raises review points; acknowledges exceptions; approves | Edits the preparer's entries |
| **Tool designer** | Builds and changes tools and drafts methods | Approves own method or tool change |
| **Method approver** | Approves a method or tool change someone else wrote | Authors the change they approve |
| **Organization admin** | Terminology, lists, expectations, roles, connections | Completes cases |

One person may hold several roles. No one may hold author and approver of the same change.

---

## 3 · The decisions that matter

### D1 · Who configures: the firm, or each customer?
Your prompt says "customers" and "an organization can configure a tool for its own work". The repo's own docs describe `credit-review-os` as a single-operator consulting tool. The answer changes support model, data ownership, installation and whether multi-tenancy is ever needed.
- **A. The firm configures, for itself and its clients.** Setup built so a customer admin could do it. One organization per installation.
- **B. Customers self-serve.** Needs onboarding, support tooling, and a safer sandbox for bad configuration.
- **C. Hosted multi-tenant service.**

**Recommend A.** You said not to assume SaaS prematurely, and C9/C11 point the same way: do the thorough thing the design already implies (versioning, role separation, portable packs) and not the speculative one (tenants, billing). The test of "could a customer admin do it" is built into the prototype: Setup is the only place configuration lives, and the case screen never shows it.
**Cost of being wrong.** If you are in fact selling this to customers who set it up alone, the setup flows need more guard rails and a gentler first run. Direction C's walkthrough is reserved for exactly that.

### D2 · Extend `credit-review-os`, or a sibling?
- **Extend.** Least duplication. But its design principle, "the workbook is the source of truth," conflicts with an application that is.
- **Sibling, reusing ideas.** Two projects for a while.
- **Replace.** Loses a working, tested, deployable path that banks behind a DLP boundary can use.

**Recommend sibling.** `credit-review-os` keeps doing what it does. Its programs (`c_and_i.yaml` and the others) are the first starting templates: an importer should read them, which is also a good test that the new model is not narrower than the old. Revisit convergence after slice 4. *Bassy's C9 applies: this adds a mechanism beside an existing one. I am doing it because the interface differs in kind, not to avoid a refactor, and I have named the convergence point so it does not drift.*

### D3 · What is the finished thing?
| Form | Good | Bad |
|---|---|---|
| **Generated workbook/package** | Familiar; works behind strict boundaries; nothing to install | Weak at repeating tables, conditional sections, validation, comments, versioned records. These are the pain points you described |
| **Configured application** | Real validation, states, review, save and retrieve, audit | Something to run; needs a store |
| **Hosted service** | Easy rollout | Data leaves the organization; the repo's own principle 11a warns against it |

**Recommend a configured local application with workbook, PDF and JSON as outputs.** "Local" means it runs on a machine or server the organization controls. The configuration travels as a **tool pack**: one versioned, portable folder of data files (tool, methods, reference lists, test vectors, checksums). A pack can be reviewed, diffed, emailed and archived. **A workbook export remains a first-class output**, so an organization that must stay in Excel still can.

### D4 · Where do calculations come from?
Three tiers, in descending trust:
1. **Library methods.** Written, tested and shipped by us. Declared inputs, declared treatment of each value state, test vectors. An organization selects and tunes them within declared options (for example which income types count) and cannot change their arithmetic.
2. **Organization methods from primitives.** *Deferred.* Sums, ratios, annualizing, with required test vectors and approval. Only built once a real need appears.
3. **Rules.** Applicability conditions, validations and limits written by the organization in a plain-sentence builder over named facts. No arithmetic.

**Recommend this, starting with tier 1 and tier 3.** It meets "limited library of tested specialist calculations", and it keeps a customer from writing a wrong formula and trusting it. *Open*: which language runs the engine (§8). One implementation only.

### D5 · First use case
**Small-business credit review.** It is your actual workbook, it exercises every building block, and `credit-review-os` gives a comparison target. Month-end bank reconciliation is a second, lightweight tool to prove reuse (§5). Not two products.

### Further decisions with defaults (see `DECISIONS.md`)
D6 maker-checker enforced from slice 1. D7 feed format owned by the receiving system. D8 evidence stored as references, not files. D9 storage and backup. D10 name and where work is logged.

---

## 4 · Primary users, first use case, workflow, scope

**Confirmed (from your words):** deterministic, no AI in the product; three-level setup as a proposal; configurators distinct from completers and reviewers; reusable blocks without forcing every feature into every tool; separate calculation logic from policy, applicability and presentation; distinguish missing, zero, N/A and excluded; incomplete never silently zero or passes; controlled overrides; saved workpaper retains template and calculation versions; traceable results; a limited tested library; fictional rules for demonstration; design as a core workstream with two or three directions; stop at a checkpoint.

**Proposed (mine, for you to accept or change):** the five roles above; the five-stage workflow below; the method lifecycle; direction A; the tool-pack idea; the release check; case statuses.

**Unresolved:** D1–D5 above; the feed format; whether the workbook export carries live formulas or values (affects trust and size of build); whether staleness of evidence blocks or warns (prototype warns); data retention periods; who the first real organization is.

**Workflow** (`prototype`: each step is clickable)

1. **Organization setup** (admin): words, lists, evidence expectations, roles, connections.
2. **Tool design** (designer): choose a template, add sections and components, set modes (required, optional, conditional), set limits, test and publish.
3. **Approval** (method approver): approves a method or tool change someone else wrote.
4. **Case**: preparer creates a case; sections appear as the rules say; entries are saved as they go.
5. **Review**: reviewer raises points anchored to sections; preparer replies; reviewer clears.
6. **Release**: a blocking check, then workpaper, workbook and feed.
7. **Retrieve**: the case reopens exactly as saved, under the versions it was made with.

**Scope.** v1 is: the building blocks, one credit tool, one accounting tool, the library of three methods, review and audit, outputs. Out: multi-tenant service, document storage, any live integration, tier-2 methods, mobile entry.

---

## 5 · The three levels, with a worked example

**Credit review**

| Level | What is defined | Example in the prototype |
|---|---|---|
| 1 Organization | Words, lists, expectations, roles | The case is a "Case"; the person is a "Preparer". Pay stubs may be 120 days old, a tax return 400 (fictional). Exception reasons are a list. |
| ½ Method library | DTI-DEMO 1.0, LTV-DEMO 1.0 | DTI takes income rows, debt rows and a proposed payment. A missing amount blocks the result. A zero counts as zero and is disclosed. N/A is rejected. An excluded row is left out and disclosed. |
| 2 Tool | Five sections; Collateral is conditional; two tests | "Collateral applies when Security is Secured." DTI at most 40% and LTV at most 80%, fictional. |
| 3 Case | The facts | Harbor Millwork LLC (synthetic) is secured; the router is pledged; the rental income is missing. |

**What happens in the case, end to end.** The rental amount is blank, so DTI shows "Not calculated," names the missing input and links to it, and the policy test reads "Not tested. This is not a pass." The preparer enters 1,450. DTI computes 51.3% and fails the fictional limit; the calculated value is not changed, and an **exception** is recorded beside it with a reason code and a note. The reviewer asks what supports counting the rent, and the preparer answers. The reviewer acknowledges the exception and approves. The release check passes. Output is a workpaper, a data feed with every value carrying its state, and (planned) a workbook.

**Second example: month-end bank reconciliation.** Built from the same blocks. See the *Compare tools* view in Setup.

| Reused unchanged | Configured differently | New |
|---|---|---|
| Sections and modes, fields, repeating tables, evidence references, value states, release check, review points, exceptions, audit log, output formats | Evidence expectations, policy limit ($0.00 difference, fictional), stages (two, not three), reason list, terminology | One method with three test vectors (REC-DEMO), nothing else |

That ratio is the claim to test in slice 5: **a second tool should need one new method and no engine change.**

---

## 6 · Calculations, rules and values

### 6.1 Four things kept apart

| Concern | Lives in | Changes how often | Who |
|---|---|---|---|
| **Calculation**: arithmetic and what each input state does | Method library | Rarely | Designer, approver |
| **Policy**: limits and thresholds | Policy set (versioned) | By decision | Organization |
| **Applicability**: which parts apply | Tool rules | Per tool | Designer |
| **Presentation**: layout, wording, guidance | Tool | Often | Designer |

A DTI method needs a defined income, debt, period and proposed-payment treatment. Two approved methods may share arithmetic and still not be interchangeable, because their treatments differ; they are separate library entries with separate IDs. The 40% in the prototype is **not** in the method. It is in the policy set, which a different organization would replace.

### 6.2 Five states for every value

| State | Meaning | Looks like | In a calculation |
|---|---|---|---|
| **Entered** | Someone supplied a value, including `0` | White field | Used |
| **Missing** | Required and not supplied | Dashed amber, named | Blocks the result |
| **Zero** | An entered `0` | As entered | Counts as zero, and the trace says so |
| **Not applicable** | Marked, with a reason | N/A chip and reason | Per method: rejected for required inputs |
| **Excluded** | Left out on purpose, with a reason | Struck through | Omitted, and the result discloses it |
| **Calculated** | Produced by a method | Tinted, read-only | Never typed over |

An incomplete required calculation returns **Not calculated**, never zero and never a pass. A test on it reads **Not tested**, which is a third answer and not a pass. (`DESIGN-PRINCIPLES` §1 and §5; `TENETS` S5.) **Each method declares, per input, what each state does.** The prototype shows that table for DTI and enforces it.

### 6.3 Method lifecycle and approval
Draft → Tested → Approved → Published in a tool. A method cannot be approved without test vectors, cannot be approved by its author, and a draft method cannot be added to a published tool. Approval, who approved and when, and the version are on the method's page.

### 6.4 Overrides are recorded beside, never typed over
A failed policy test can carry an **exception**: reason code from an organization list, a written explanation, who recorded it, who acknowledged it. The calculated value is untouched and the original result remains visible. Exceptions show in the workpaper and the feed. Who may record or acknowledge is a role permission. *Open:* whether a calculated value itself may ever be overridden. The prototype says no.

### 6.5 Versions and replay
A saved case pins `{template, method versions, policy set, terminology snapshot}` and the as-of date. Reopening it recomputes under those versions and must reproduce the saved results. Moving to a newer template is an explicit action that shows the difference first. Tool, method and policy versions are immutable once published.

### 6.6 Trace
Every result opens to a trace: each input with its value, a link to the entry, the method, template and policy versions, and what was disclosed (zero counted, rows excluded). Nothing is unexplained.

### 6.7 Removing a component without losing information another needs
Facts belong to the **tool**, not to a component. Each component *declares* what it needs. Remove one and the builder says what is kept ("Existing debts stays: Debt service coverage still needs it") and what goes. The prototype's Setup → Tools shows this. In a case, entries in a section that stops applying are **kept and hidden**, not deleted.

---

## 7 · Your workbook's features, and where each lands

(*My reading of your description; a photograph could correct it.*)

| Workbook capability | Where it lands in the design |
|---|---|
| Structured inputs | Fields and repeating tables with value states |
| Questions and guidance | Per-field guidance, versioned with the tool, shown in the side panel |
| DTI and cash-flow calculations | Library methods with declared inputs and tested vectors |
| Collateral analysis | A conditional section with its own method and test |
| Reference lists | Organization reference lists; retire, never delete |
| Saving and retrieving | Autosave; a worklist; retrieval reproduces pinned versions |
| Reviewer information | Stages with who and when; review points; sign-offs |
| Error logging | Two things: user-facing **issues** (inline, in blockers) and an admin **diagnostic log** (never shown to preparers) |
| Output feed to another system | A versioned data feed where every value carries its state; **format unverified** |

---

## 8 · Architecture and delivery

### 8.1 Stack-neutral invariants
Whatever is built, these hold (each becomes a test, §9):
1. **One calculation implementation.** The engine that computes in the case screen is the engine that computes in tests, export and replay (`TENETS` S3). Test vectors are data, so a second implementation could be checked against them.
2. **Config is data.** Tool packs are files, validated against a schema; a pack that fails validation refuses to load and says what to fix.
3. **A fact is `{state, value, reason, source}`.** Never a bare value.
4. **Immutable versions; append-only history.** Published versions never change. Events (entries, reviews, approvals) are only added to.
5. **No network, no model.** The runtime has no outbound network dependency and imports no model client (an ast-based test, as the repo does for SMTP).
6. **Personal data is classified per field** and masked by default in every export.

### 8.2 Data model (outline)
Organization defaults (versioned) → Method (versioned) → Policy set (versioned) → Tool pack (versioned, references methods and policy) → Case (facts, states, pinned versions) → Event log (append-only) → Outputs (generated, fingerprinted).

### 8.3 Ownership, storage, permissions, audit, portability
- **Ownership.** The organization owns its data and its packs. Nothing is sent to us, and there is no phone-home.
- **Storage.** One local store per organization (single-file database), plus pack files on disk. *Open (D9):* where it lives and who backs it up.
- **Permissions.** Roles are derived from the signed-in session, never accepted as an argument (`DESIGN-PRINCIPLES` §6). Maker-checker is enforced in the engine, not the screen.
- **Audit.** Append-only events with actor, time, what changed (old and new). Entries, state changes, review actions, approvals, releases. A hash chain is optional and proposed only if an auditor asks.
- **Portability.** Packs are open text. Cases export as the data feed and as a workbook. A full export (packs plus cases plus log) is a first-class command, tested by importing it into a clean install.

### 8.4 Delivery options

| Option | What it is | For | Against |
|---|---|---|---|
| **1. Local web app** (recommended) | Runs on an organization machine or server; browser UI; local store | Real validation, review, audit; no data leaves; matches this repo's other apps | Something to run |
| **2. Single-file offline app** | One HTML file, no server; data in the browser or a file | Zero install, DLP-friendly, **what the prototype is** | Weak for several users, audit and backup |
| **3. Desktop-packaged** | Option 1 in an installer | Familiar to staff | Packaging effort (repo already has a release path for `SATC.exe`) |
| **4. Hosted multi-tenant** | A service | Easy rollout | Data leaves; contradicts the repo's principle 11a; not recommended now |

**Recommend option 1, with option 3 later**, after a short spike comparing a Python engine behind a local API against a JavaScript engine shared with the screen. The criteria are one implementation, testability, and fit with the repo's stack; I lean Python because the repo's tests, vault pattern and `credit-review-os` importer all live there. **I have not chosen a stack; the invariants above are what is decided.**

### 8.5 Mocked and unverified
Feed contract and the "loan system" and "ledger package" connections are mocks. The workbook export is not built. Printing and PDF are not exercised in the prototype (the frame it publishes in cannot open a print dialog); a print stylesheet exists and is unverified.

---

## 9 · Design

**Principles.** The screen is the page. Complexity lives in Setup and never reaches the case. State is encoded in form and in words, never colour alone. Missing is named and linked. Nothing a person typed is lost: autosave, a kept-but-hidden rule for sections that stop applying, undo on row removal.

**Recommended direction: A, the workpaper**, borrowing B's inspector and B's density for setup. Rationale and trade-offs: `prototype/directions.html`.

**Screens.** Cases (a worklist, not a dashboard) · Workpaper (rail, document, inspector) · Output (paper, feed, workbook, release check) · Setup (Organization, Tools with a compare view, Methods).

**States designed and visible in the prototype:** empty (calm until touched), in progress with gaps, errors with a failed save, in review with reviewer feedback, approved and ready to release, a worklist with nothing for a role, a section that does not apply, one that cannot be told yet.

**Accessibility, as built and as checked.** Real tables with headers; every control labelled; visible focus; skip link; `aria-live` for calculation changes; disabled-looking actions stay reachable so they can explain themselves; keyboard: Enter moves down a table and adds a row, `[` and `]` change section, Esc closes. **Checked:** no console errors; no horizontal scroll at 400px; light and dark. **Not checked:** a screen-reader pass, an automated audit, contrast measurement beyond sight. These are acceptance items for slice 1.

---

## 10 · Where this touches what the firm has recorded

- **C7, the reviewer carries the preparer's work and asks, not corrects.** Reviewers are read-only and raise points; preparers decide. A preparer can send up what is above their level (an exception).
- **C9 and C11, simplest is the thorough thing done once.** Versioning, role separation and portable packs are in v1 because they are known. Multi-tenancy, tier-2 methods and document storage are not.
- **C8 and C12, gate on the difficulty of the call.** *Proposed, not built:* review routing by rule, so a clean case takes one review and a case with an exception takes a second. Needs your view.
- **`DESIGN-PRINCIPLES`:** §1 never invent a value; §2 facts carry how we know (evidence); §5 refuse rather than default; §6 engine disposes; §10 errors name the next step; §11 only masked values leave.
- **`CLAUDE.md` hard constraints.** Client PII is load-bearing. The feed is de-identified by default. Methods and thresholds are never invented; the prototype's are labelled fictional. *No AI anywhere in the product.*

---

## 11 · Implementation plan with acceptance criteria

Slices are vertical. Each ends with something runnable and a statement that can fail.

**Slice 0: Foundations (no UI).** Fact-state model; engine contract; schema for packs, methods, policy; the three library methods with vectors; the importer's shape.
- Each method returns the same result for the same facts across 1,000 generated cases, and a mutation of its treatment of any value state turns a test red.
- No method returns a number when a required input is missing, invalid or N/A.
- A pack with an unknown field, a cycle or a dangling reference refuses to load and names the file and line.

**Slice 1: Credit review, entries and calculation.** Case screen with fields, repeating tables, conditional section, evidence references, save and retrieve.
- All five value states are reachable from the keyboard alone and distinguishable without colour.
- Changing Security to Unsecured hides Collateral, keeps its entries, and restoring returns them unchanged.
- Reload after a forced network or disk failure loses no entry.
- A screen-reader pass and an automated accessibility check both complete with no serious issues.

**Slice 2: Review and audit.** Stages; review points; exceptions; append-only log; version pinning and replay.
- A reviewer cannot change an entry through the UI or the API.
- Reopening a saved case after a method changes reproduces every saved result byte for byte.
- The event log can be replayed to reconstruct the case.

**Slice 3: Output.** Paper layout, workbook, data feed, release check.
- A case with a missing required input cannot be released by any route, UI or API.
- The feed never carries a missing value as zero; a de-identified feed contains no field marked personal (scan test).
- Every output is opened by the thing that consumes it (browser for paper, a spreadsheet engine for the workbook, a schema validator for the feed) (`TENETS` S1).

**Slice 4: Tool configuration.** Builder; method lifecycle; maker-checker; publish; upgrade.
- A person cannot approve a method or tool change they wrote; the refusal names who can.
- A draft method cannot be published into a tool.
- Removing a component keeps every fact another selected component needs.
- Existing cases keep their pinned versions after a publish; upgrading shows a difference first.

**Slice 5: Second tool proves reuse.** Bank reconciliation.
- Building it requires one new method with vectors and no change to the engine, the screens or the output code.

**Slice 6: Organization setup and hardening.** Terminology, lists (retire, never delete), expectations, roles; import of `credit-review-os` programs; full export and clean-install import.
- Retiring a list value never alters an existing case.
- Importing the shipped `c_and_i` program yields a tool that passes the same exception tests as the workbook.
- A full export imported into an empty install reproduces every case and the whole log.

**Cross-cutting, every slice.** No network call and no model-client import in the runtime (ast test). Personal data masked by default (scan test). Every client-facing sentence in a shipped template follows the firm's copy rules (`CLAUDE.md`). Every invariant above has a test that was seen to fail.

---

## 12 · What the prototype does and does not demonstrate

**Does, and checked in a browser.** 13 method test vectors run live and pass. 25 scripted interactions pass (live recalculation; clearing an input returns to *Not calculated*; zero is a value; the conditional section hides, keeps and restores; N/A refused for a calculation input; N/A with a reason; exclusion; Enter adds a row; reload preserves edits; reviewer raises a point; return and changed-since-submission marking; reviewer read-only; bank reconciliation reaches $0.00; terminology flows through). No console errors. No horizontal scroll at 400px. Light and dark.

**Does not.** Persistence beyond this browser. A server, accounts or real roles (the role switch is a prototype device). The workbook export. Printing. Any real integration. Several of the Setup controls are display-only where marked.

**Bugs found by actually using it, fixed:** the conditional section did not re-render when its controlling field changed; "Go to it" focused the help button, not the field; the top bar scrolled sideways at phone width. A fourth was caught by looking at the screen: a new case opened as a wall of amber.
