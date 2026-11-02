# Workpaper Studio — decision and requirements register

*Updated 1 November 2026. Source of truth for scope. The argument for each item is in `DESIGN-REVIEW.md`. Nothing here is decided until its status says so.*

**Status key:** CONFIRMED = your words · PROPOSED = my choice, awaiting you · OPEN = needs an answer · DEFAULT = I proceed on this unless told otherwise.

## A · Decisions needed from you

| ID | Decision | Options | Recommendation | Status | Unblocks |
|---|---|---|---|---|---|
| D1 | Who configures tools | A: the firm, for itself and its clients · B: each customer alone · C: hosted multi-tenant | **A, designed so B is possible.** The owner has since said they may want to sell this, which makes B (a buyer adapting an installed pack) real; the journey demonstrates it without multi-tenancy | OPEN | Setup depth, install model |
| D2 | Relationship to `credit-review-os` | Extend · sibling · replace | **Sibling folder; import its programs as templates; revisit after slice 4** | OPEN | Where code lives |
| D3 | Finished form | Workbook · local app · hosted | **Local app; workbook, PDF, feed as outputs; portable tool packs** | OPEN | Architecture |
| D4 | Source of calculations | Library only · library + org arithmetic · free formulas | **Library methods (tier 1) + org-written rules (tier 3); org arithmetic deferred** | OPEN | Method model |
| D5 | First use case | Credit review · accounting | **Credit review; bank reconciliation only for reuse** | OPEN | Slice order |
| D6 | Maker-checker enforced from slice 1 | Yes · later | **Yes** | DEFAULT | Roles |
| D7 | Output feed format | Needs the receiving system's owner | None until supplied. Mock is `workpaper-feed/0.1-draft`, **unverified** | OPEN, external | Slice 3 feed |
| D8 | Evidence | References only · store files | **References only** | DEFAULT | Storage |
| D9 | Storage and backup | Local single file · server database | **Local single file; backup owner named at install** | DEFAULT | Slice 0 |
| D10 | Name; where work is logged | The owner, 2 Nov 2026: *"workpaper studio is a good name for this - at least some sort of studio sounds good"* | **"Workpaper Studio" is accepted.** "Studio" is settled; the first word may still change. Project log in `docs/`; one-line pointer in `CLAUDE.md` | CONFIRMED | Naming |
| D11 | Does evidence staleness block or warn | Block · warn | **Warn** (prototype). Organization could choose per document kind | OPEN | Release check |
| D12 | Workbook export: live formulas or values | Formulas · values · both | **Values plus a formulas sheet**; needs your view on auditor expectations | OPEN | Slice 3 |
| D13 | Review routing by rule (C8/C12) | One review always · route by exception | **Route by exception**, built later | OPEN | Stages |
| D14 | May a calculated value ever be overridden | Never · with controls | **Never.** Exceptions sit beside it | PROPOSED | Overrides |
| D15 | Who owns the know-how in the owner's workbook | — | **Answered by the owner, 1 Nov 2026:** *"this does not matter at all, i can recreate this with or without the examples. we are doing unique work"*. Closed. The prototype keeps its own example wording regardless | DECIDED | — |
| D16 | Business model | Packs · runtime · packs-as-a-service (see `MARKET-AND-PACKS.md`) | **Start with packs-as-a-service, learn what buyers change, then sell packs** | OPEN | Packaging, support |
| D17 | Which niche first | — | **Reframed by the owner, 1 Nov 2026:** *"literally people who can use it like auditors and such for sure but there has to be ways to adapt this"*. A niche is a starting pack and a set of patterns, not a constraint on the product. Auditors are a confirmed audience; the product must adapt to others without new code | DECIDED (direction) | Listing, first packs |
| D18 | Ranking block types | — | **Withdrawn.** I asked which table shape mattered most. The owner: *"they serve distinct purposes and they may even be different from client to client. asking a question like this is straight up counter to the spirit of this."* Resolved by P16: there is one table primitive, and shapes are configuration | DECIDED | — |

## B · Confirmed requirements (traceable to your brief)

| ID | Requirement |
|---|---|
| R1 | Tools operate deterministically. No chatbot, no AI-generated conclusions, no prompt-based setup. AI is not a runtime requirement. |
| R2 | Setup has three levels: organization defaults, tool configuration, individual case. Offered as a proposal to evaluate. |
| R3 | Distinguish people who configure from people who complete and review. |
| R4 | Reusable building blocks; no feature forced into every tool; starting templates with sensible defaults; setup needs no software knowledge. |
| R5 | Separate calculation logic from policy, applicability and presentation. |
| R6 | A selected component brings its inputs, validation and explanations; removing it does not remove information another needs. |
| R7 | Required, optional and conditional sections. |
| R8 | Distinguish missing, zero, not applicable and deliberately excluded. An incomplete required calculation never becomes zero or a pass. |
| R9 | Methods are defined and approved; overrides controlled; a saved workpaper retains template and calculation versions; results traceable. |
| R10 | Limited library of tested specialist calculations; do not pretend to cover every rule; no invented authoritative policy; fictional demonstration rules, labelled. |
| R11 | Design is a core workstream: navigation, hierarchy, type, spacing, restrained colour, dense tables, keyboard, accessibility, validation, comments, print/export. Two or three directions, one recommended. Real screens. |
| R12 | Realistic empty, incomplete, error and completed states; preserve user work; make entered, calculated, missing, reviewed and changed obvious. |
| R13 | Credit-review demonstration: calculation, repeating table, conditional section, evidence reference, reviewer feedback, output. A second light accounting example for reuse. |
| R14 | Synthetic data; mocked integrations and unverified behaviour labelled. No deploy, no real systems, no client data, no purchases, no production changes. |
| R15 | Address ownership, storage, permissions, audit, portability. Do not assume a stack, cloud or multi-tenant model. |
| R16 | Stop at a design-review checkpoint; document scope and decisions for the next session. |
| R17 | **Access is defined by the organization.** The owner, 2 Nov 2026: *"i like the idea of having users but it should be definable by the organization for what each level of access can actually do"*. |
| R18 | **Work starts from a list the master database supplies, and the finished record goes back the same way.** The owner, 2 Nov 2026: *"in my work version employees choose a linesheet from a list created by the master database loading into that excel sheet"*, and *"this would also be the method for feeding any associated "datamart" with it"*. The proposal is in `DATA-RECORD.md`. |

## C · Proposed choices (mine)

P1 five roles (preparer, reviewer, tool designer, method approver, org admin) · P2 a method library as its own level between organization and tool · P3 five value states plus *Calculated* · P4 tests return Pass, Fail or Not tested, never a silent pass · P5 exceptions sit beside a calculated value · P6 reviewers are read-only and raise points (C7) · P7 tool packs as portable data · P8 release check as a blocking gate (modelled on the pre-send gate) · P9 direction A with B's inspector and density · P10 sections that stop applying keep their entries hidden · P11 case statuses: drafting, in review, returned, approved, released · P12 two kinds of "error log": inline issues for users, a diagnostic log for admins · P13 a **pack** is one portable file carrying the author's know-how; recommended limits must be confirmed by the buyer; structure can be locked so updates apply cleanly · P14 a **test questions** block (a table of numbered questions with test steps, a rating list and comments) is a first-class building block · P15 the feed can be a flat row generated from the configuration, with missing values counted beside it · **P16 one table primitive, never a catalogue of special blocks.** Rows and columns are each a fixed list, entries the preparer adds, or an organization list; cells take their type from whichever side is fixed; worked-out lines come from a short list of operations; totals and answer counts are settings. A repeating table, a question framework, line items by person or by period, a checklist, a sample and a valuation by class are all this one block. Organizations save their own shapes as **patterns**, which travel inside packs. *A request for a new kind of block is a request for a new pattern, or a missing axis option, and is answered by configuration, not code.*

**P17 · Organization-defined access** (answers R17). **Built 2 Nov 2026** (`access.py`, the Access screen, `tests/test_access.py`). The organization names its own levels, for example "Tester", "QC reviewer" or "Credit admin". It ticks what each level may do from a fixed list of actions: enter, mark not applicable or excluded, submit, raise points, answer points, clear points, return, record exceptions, acknowledge exceptions, approve, release, propose a tool, approve a tool, set limits, manage people and levels, and see all cases or only assigned ones. People hold one or more levels. Two rules are **not** configurable, because they are what makes the record worth trusting:
- nobody approves work they entered, or a tool or limit they proposed;
- every action stays in the log.

An organization can add second-person rules, for example on limits (walk defect 10), but cannot remove these two. A change to levels is itself a logged, versioned event.

**P18 · The data record** (answers R18). See `DATA-RECORD.md`. **Built 2 Nov 2026**: the work list read from the master database, the data mart, and the Results screen. The data mart's design is a recommendation the owner invited (*"it should work better if possible"*) and has not yet confirmed.

**P19 · Tester and reviewer lists come from the organization's people.** Found while loading the master list: the tool carried a fixed list of tester names that did not match who actually has access, so lines were refused for naming real people. A pack now names `@preparers` or `@reviewers`, and the installation fills those lists from whoever's access includes entering or approving.

## D · Unresolved questions

1. ~~Your workbook's real fields, formulas and layout (not seen).~~ Seen 1 Nov 2026 (35 photographs): see `REFERENCE-WORKBOOK.md`. Still unseen: the content of the Change Log, Master_Table, Questions, policy-guidance, feed-audit, feed-schema and contract tabs. 2. The receiving system's format and who owns it. 3. Retention periods. 4. The first real organization and its approver structure. 5. Whether any organization needs tier-2 arithmetic soon. 6. Whether reviewers need a second-reviewer path. 7. Whether the "personal data" classes are enough (names, TINs, account numbers) or need per-organization definitions.

## E · Scope

**In v1:** the blocks; one credit tool; one accounting tool; three library methods (DTI, LTV, reconciliation) plus a draft DSCR for the lifecycle; review and audit; paper, workbook and feed outputs; setup for organization, tools and methods.
**Out of v1:** multi-tenant service; document storage; live integrations; tier-2 methods; mobile entry; any AI; any real policy or threshold.
