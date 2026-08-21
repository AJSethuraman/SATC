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

## 1 · Firm settings — 9 open

These block **every real render**. The merge engine treats a surviving
`[CONFIRM:` exactly like an unfilled field and refuses to produce the document,
so a placeholder can never reach a client. `--draft` renders past them, stamped.

Four are a date. Two are a sentence. Two block nothing today.

| # | Setting | Blocks | Shape of the answer |
|---|---|---|---|
| 1 | `materials_deadlines.2026.individual_1040` | Tax letter · organizer · onboarding | One date |
| 2 | `materials_deadlines.2026.s_corp_1120s` | Business return letter | One date |
| 3 | `materials_deadlines.2026.partnership_1065` | Business return letter | One date |
| 4 | `materials_deadlines.2026.c_corp_1120` | Business return letter | One date |
| 5 | `delivery.ack_window` | Onboarding letter | A duration that drops into a sentence — "three business days" |
| 6 | `delivery.payment_instruction` | Every invoice | One sentence naming how a client pays. **Names the processor**, so it changes when that does |
| 7 | `billing.contact_email` | Every invoice | Does `billing@satcllp.com` exist, or use the main address? |
| 8 | `legal_name` | Nothing yet — footers hardcode it | The exact name on the Ohio LLP filing. **Three variants are in use and only one is on the filing** |
| 9 | `hard_no[1]` | Nothing — it gates declining work | The rest of the "we don't take this" list |

## 2 · One contradiction that needs a ruling

**`<<TaxYear>>` is alive in six places** while §4 of the authoring contract
says *"Never add `TaxYear` back."* Three uses in the tax engagement letter,
three in the organizer, plus both field docs and the registry. Either
`PeriodLabel` replaces it everywhere, or the rule is relaxed. Renaming touches
two templates, two field docs, the registry and the tests in one commit.

## 3 · The fee schedule — structure built, numbers open

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
