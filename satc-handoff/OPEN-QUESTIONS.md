# Open questions — the running list

Everything waiting on Arjun, in one place, so it accumulates here rather than
scrolling past in a chat window. Agents append; nobody answers on his behalf.

**How to use it:** work down at a break point. Each item says what it blocks, so
the ones blocking nothing can wait indefinitely and the ones blocking a client
document cannot.

Two kinds of item, and they are answered in different places:

- **Firm settings** — a `[CONFIRM: …]` in `client-documents/registry/firm-settings.yaml`.
  Answering means replacing that placeholder on one line. `cd client-documents
  && make doctor` lists these live, so that command is always the truth and this
  file is a convenience copy.
- **Everything else** — a decision with no home yet. Answer it here, in the
  thread, or wherever it lands, and whoever picks it up wires it in.

---

## 1 · Firm settings — all closed

**Re-measured 28 August 2026: `cd client-documents && make doctor` reports
"No open decisions. Real renders will produce documents."** Every row below is
settled and wired in — the four deadlines carry real dates, `legal_name`,
`ack_window`, `billing.contact_email` and the hard-no list are answered, and
`payment_instruction` now carries a sentence.

The table is kept because it is the record of what was decided and when, not
because anything is outstanding. **The one thing that is still open is not a
setting** — it is the processor question in row 6, which a sentence cannot fix.
See below.

These blocked **every real render** while they were open. The merge engine
treats a surviving `[CONFIRM:` exactly like an unfilled field and refuses to
produce the document, so a placeholder can never reach a client. `--draft`
renders past them, stamped.

| # | Setting | Blocks | Shape of the answer |
|---|---|---|---|
| 1 | `materials_deadlines.2026.individual_1040` | Tax letter · organizer · onboarding | One date |
| 2 | `materials_deadlines.2026.s_corp_1120s` | Business return letter | One date |
| 3 | `materials_deadlines.2026.partnership_1065` | Business return letter | One date |
| 4 | `materials_deadlines.2026.c_corp_1120` | Business return letter | One date |
| ~~5~~ | ~~`delivery.ack_window`~~ | Onboarding letter | **Settled 25 Aug 2026: "three business days"** — with a caveat that belongs on the confirmation screen, not in the string: it is three business days *unless the client books their own time on Calendly*, in which case the next step is theirs |
| ~~6~~ | ~~`delivery.payment_instruction`~~ | Every invoice | **Sentence settled**; the processor is not. See "Square or Stripe" below — the sentence now names a Square link the invoice cannot produce |
| ~~7~~ | ~~`billing.contact_email`~~ | Every invoice | **Settled 25 Aug 2026: `arjun_sethuraman@satcllp.com`.** No separate billing box. The website footer still prints `billing@satcllp.com` in one place and is now wrong |
| ~~8~~ | ~~`legal_name`~~ | **Every template** | **Settled 25 Aug 2026: `Sethuraman Accounting, Tax, and Consulting LLP`** — the Oxford-comma form, which is already what all ten footers print. See below |
| ~~9~~ | ~~`hard_no[1]`~~ | Nothing — it gates declining work | **Settled 26 Aug 2026**, in the firm's own words: hard nos exist to say the firm cannot provide assurance, being uncredentialed to give an opinion — not to make a list of refusals |

### Square or Stripe — the one that is still open

Row 6 is settled as a *sentence* and unsettled as a *system*, and the gap is
visible to a client. `firm-settings.yaml` now says:

> Payment is by card or bank transfer through the secure Square link on your
> invoice. If you would rather pay another way, tell us and we will arrange it.

**The invoice carries no link.** It has 41 merge fields and not one of them is a
URL, and there is no Square code anywhere in the repository — `invoice-generator`
is Stripe from end to end. So the sentence promises a client something the
software cannot put on the page.

**The firm's leaning, 28 August 2026: "square is fine for now I think maybe
price dependent."** That reads as: stay on Square unless the pricing argues
otherwise. It is recorded as a leaning rather than a decision because the cost
comparison has not been done — and because "Square stays" is the expensive
answer for the software, not the cheap one: Invoicer's Stripe checkout, webhook
and four templates would be the side that moves.

Nothing should be built against either processor until this is a decision.


### `legal_name` — settled, and it landed on the form already in use

It was recorded above as blocking "nothing yet — footers hardcode it". The
hardcoding is precisely *why* it blocks, and `firm-settings.yaml` says so
plainly: **"Until this is settled, no template should ship to a client."**

The reasoning is mechanical. Every other open decision is a `[CONFIRM:` inside a
merge field, and the merge engine refuses to render while one survives — the
guard catches it. The legal name is **not a merge field**. It is typed into the
footer of all ten templates, so nothing checks it, and a wrong one ships
silently past every gate the pipeline has.

Grepping the templates finds the three variants:

| In the templates | Count |
|---|---|
| `Sethuraman Accounting, Tax & Consulting LLP` (footer form) | 23 |
| `Sethuraman Accounting Tax and Consulting` | 1 |
| `Sethuraman Accounting Tax & Consulting LLP` | 1 |

A **fourth** spelling turned up later, outside the repo: the firm's own fee
workbook heads its client-facing quote sheet *"Sethuraman Accounting Tax and
Consulting LLP"* — no commas at all.

**Settled 25 August 2026 as `Sethuraman Accounting, Tax, and Consulting LLP`.**

The lucky part: that is the form every template footer already prints, so no
template changes. The other two spellings in this repo survive only inside notes
*about* this problem — this file and the two engagement-letter warnings — never
in a footer. Nothing shipping was wrong.

What is still wrong is outside the repo: the workbook's quote sheet, which goes
to clients. And the structural point stands unchanged — the name is typed into
ten footers rather than merged, so the next time it is mistyped, nothing will
catch it either.

## 2 · One contradiction that needs a ruling

**`<<TaxYear>>` is alive in six places** while §4 of the authoring contract
says *"Never add `TaxYear` back."* Three uses in the tax engagement letter,
three in the organizer, plus both field docs and the registry. Either
`PeriodLabel` replaces it everywhere, or the rule is relaxed. Renaming touches
two templates, two field docs, the registry and the tests in one commit.

## 3 · The fee schedule — structure built, numbers open

> **Closed 26 August 2026, and this section is now history rather than a
> question.** `fee-schedule.yaml` carries the firm's own figures — an hourly
> rate, package amounts, per-unit prices and allowances — derived with `cli.py
> hours` from hours × rate rather than typed, and `cli.py doctor` reports *"No
> open decisions."* Two `[CONFIRM:` strings survive in the file and both are
> inside the comment below, describing the state it was in. Two amounts have
> moved since: the entity base now carries a **two-K-1 allowance**, which flows
> through an amendment. Everything from here down is kept because it is the
> record of how the numbers were arrived at.

`client-documents/registry/fee-schedule.yaml` exists and is wired: the
interview's counts become the estimate's line items and total. **Every amount in
it is a `[CONFIRM:`** — §9 says fee figures are yours to set.

An unpriced item does not become zero. The placeholder is carried to the line
and then to the total, and the estimate refuses to render rather than quoting
$0 for a service. Fill these in and the fee estimate renders for real.

**One structural decision first**, because it changes every number under it:

| | |
|---|---|
| `base_covers` | Does the base fee cover the **first state and locality**, or the **federal return only**? Two firms can quote the same $785 from different structures, and only one can explain it to a client who asks. |

**Then the amounts — 14 of them** (an earlier draft of this file said 18; its
own table said 14, and `python cli.py doctor` agrees with the table):

| Group | What is needed |
|---|---|
| Base, by return | 1040 · 1120-S · 1065 · 1120 — four figures |
| Per unit | state return · local return · rental property · K-1 received · Schedule C business — five figures |
| Brokerage band | light · medium · heavy — three figures (`none` is a real zero) |
| Cleanup band | light · heavy — two figures (`none` is a real zero) |

**If you do not have these numbers**, that is the expected case and there is a
way in. Nobody knows their own prices in the abstract; they know their own work.
So `python cli.py price` asks the same fourteen questions in hours —

> *how long does a plain 1040 take you, start to filed?*

— and multiplies by an hourly rate. **Both numbers are yours**; the tool
supplies neither and invents nothing. Answering nine of fourteen leaves the
other five as `[CONFIRM:`, which is a correct outcome, not a failed run.

Rounding is off unless you ask. `$437.50` is what 2.5 hours at $175 costs;
`$450.00` is a pricing policy, and `--round-to 25` is how you say you have one.

`samples/fee-schedule-example.yaml` shows the shape filled in with **fictional**
numbers, and `python cli.py interview --fee-schedule samples/fee-schedule-example.yaml`
renders a complete estimate from them. Use it to sanity-check the structure
before committing to your own figures.

## 4 · Things with no home yet

Found while building; nowhere to put the answer until someone decides.

- **`MaterialsDeadline` needs a wider key than it has.** Settings key it by
  season and return type. The business letter needs the **entity** deadline
  (earlier than the individual one) and the extension notice needs the
  **extension-season** deadline. Same field name, three settings behind it.
- **Does one RITA filing count as one locality or several?** Already a
  `[CONFIRM]` inside `interview.yaml` itself, on the `localities` question. It
  is a pricing input.
- **`FirstDeliverableTarget` — resolved, but check the call.** It was registered
  `source: engagement` while nothing derived it, so the onboarding letter could
  never render. It is now asked on the call, as a judgement made against the
  materials deadline and the workload. If it should instead be a firm rule
  ("three weeks after the file is complete"), say so and it moves to settings.

## 5 · Getting a signature — the shape is decided, four details are not

**Decided 28 August 2026: Option A.** Encyro carries the signature and a human
sends by hand through it; the software does the tracking and the chasing. Not an
API vendor — Encyro has no customer API, and scripting its web interface would
degrade an MFA control the FTC Safeguards Rule requires, break silently on a
client-facing send, and is commonly forbidden by portal terms. Two corrections
from the firm are wired in and both stand: *"No encyro is cheaper and has kba"*
and *"Drake can print our 8879."* The second removes the reason to buy Drake
E-Sign — Drake produces the PDF, Encyro carries the signature, one vendor and
one subscription.

Everything below is what is still open, ordered by what it blocks.

| | What it blocks |
|---|---|
| **The covering-note wording** | **Every automated send.** `registry/signing.yaml` carries the subject and body behind a `[CONFIRM: ]` and `outgoing.py` **refuses to compose** until it is accepted or rewritten. To accept: delete the `[CONFIRM: ` and its closing `]`, leaving the words. The pack still builds either way. The draft is assembled from sentences already published in the onboarding letter, not invented |
| **The one email to Encyro** | The rest of `docs/research-e-signature.md`, entirely. Four questions, drafted there in §5 and §5b — see below |
| **Does Pub 1345's KBA regime reach the entity forms?** | Nothing today, and any sentence anybody writes about 8879-CORP or 8879-PE. **Genuinely unresolved** |
| **Does the `[Secure]` keyword survive to the client?** | Nothing today. `secure_keyword` in `registry/signing.yaml` ships **empty** until somebody sends one to themselves and looks |

### The one email — four questions, one reply

Written out in full in `docs/research-e-signature.md` §5 and §5b. In short:

1. **Does the 8879 e-signature use knowledge-based authentication generated
   from credit-file or public-record data meeting NIST SP 800-63 IAL2, or an SMS
   access code?** An answer naming the KBA data provider closes it permanently.
   **Keep the reply** — it is the evidence, and there is currently none on file.
2. Is there a documented HTTP API on `api.encyro.com` — even partner-only or
   under NDA — and how does a one-person firm apply for a key?
3. Does the `[Secure]` subject keyword work anywhere but the installed Outlook
   add-in — an SMTP relay, an address to email or BCC?
4. What is the exact subject and body format of the notification email sent when
   a signer completes a request, and does it carry a stable request ID we can
   parse?

### The caveat that outranks everything in the research document

**None of the regulatory wording was read from a primary source.** This
environment's egress proxy denies `irs.gov`, `govinfo.gov`, `uscode.house.gov`,
`codes.ohio.gov`, `ecfr.gov` and `ftc.gov` — 403 on CONNECT, confirmed against
the proxy's own status endpoint — and every vendor domain with them. The URLs
cited are the real primary sources; the substance came from search indexes **of**
those documents. **Somebody must open `p1345.pdf`** before a line of it is built
against or a word of it reaches a client. Each claim in the document is marked
✓ *cited, unread* or ✗ *could not verify at all*.

That is also why question 3 above stays open rather than being settled by
reading: Pub 4163 governs business MeF returns and could not be checked, so
`registry/signing.yaml` names the entity forms and asserts nothing about
identity proofing. **The software must not assert it either way.**

## 6 · A second copy of the data

Carried over from `docs/REPO-INVENTORY.md` §4 because it belongs on the list a
human works down, not only in a snapshot. Engagements are plain files on one
disk and `satc_system`'s vault is two local SQLite files. There is no sync and
no backup anywhere in the code. It blocks nothing today and everything the day
it matters, and no agent can decide where the second copy lives.

---

## Answered

**No accreditation is being sought, and none is claimed.** *(was §2, the
regulator question — the largest open item in the run)* The firm is not
pursuing registration with the Accountancy Board of Ohio and is not asking
whether it needs to. The only credential claimed is personal: Arjun Sethuraman
holds a CPA licence in Ohio.

Withdrawn rather than answered — the question stops mattering once the claim it
was gating is this narrow. Wired in: the website's item 1 placeholder is gone,
the footer states the entity fact and the personal credential as two sentences,
and the comment above them records that the credential is worded about a person
on purpose, so a later edit does not promote it to "CPA firm".

**"Coming soon" is off the website.** *(was §4)* `index.html:826` read "Anyone
who needs assurance work — coming soon" under *Probably not a fit*. The
negation was fine; the forward promise was not, and with no assurance work
being pursued it contradicted the same page's attest disclaimer. Two words
deleted.

**A credit prints in parentheses.** *(was §3a — the only open item that changed
a document clients already read)* `FIELDS - Invoice.md` was the wrong document
and is corrected, along with the `.ref` block inside `SATC Invoice.html` and
the example payload, which still carried `−$150`. No shipped output changed:
both money formatters already implemented parentheses.
