# Keeping leads in a spreadsheet

Formspree's free plan keeps only **30 days** of submission history, so without
this the durable record of a lead is "whatever is still in the inbox". This
flow turns each intake email into a spreadsheet row automatically.

Everything here uses **standard** Power Automate connectors. Nothing needs a
premium licence — that is why the intake sends a machine-readable line instead
of expecting an HTTP webhook, which *is* premium.

---

## What the email actually contains

Each notification ends with a `_json` field holding every answer in one line:

```
_json
{"services":["individual_tax","tax_resolution"],"individual_complexity":["w2","k1"],
 "business_structure":["sole_prop","s_corp"],"tax_status":"unsure","urgency":"no",
 "notes":"…","contact":{"name":"…","email":"…","phone":"…","preferred":"Email",
 "location":"Cleveland, OH","consent":true}}
```

The prose above it is for a human reading the email. The `_json` line is for
this flow. Parsing the prose would break the first time a question is reworded;
the keys never change.

---

## Step 1 · The workbook

In **OneDrive** (business), create `SATC leads.xlsx` and put these headers in
row 1:

```
Received | Name | Email | Phone | Location | Preferred | Services |
Individual complexity | Business structure | Tax status | Bookkeeping status |
Urgency | Deadline | Notes | Raw JSON
```

Then: select row 1 → **Insert → Table** → tick **My table has headers** → OK.
With it selected, open **Table Design** and rename `Table1` to **`Leads`**.

> **It must be a real Excel Table.** Power Automate's "Add a row" action cannot
> write to a plain sheet, and every workbook is called `Table1`, so naming it
> is what stops the flow writing into the wrong place later.

Keeping **Raw JSON** as the last column costs nothing and means a question
added later is still captured, even before the spreadsheet has a column for it.

---

## Step 2 · The flow

**make.powerautomate.com** → **Create** → **Automated cloud flow** → trigger
**When a new email arrives (V3)** (Office 365 Outlook).

### Trigger settings

| Field | Value |
|---|---|
| Folder | `Inbox` |
| From | the Formspree sender address, copied from a real notification |
| Include Attachments | No |

> Filter on **From**, not on subject. Formspree titles its emails its own way,
> and a subject filter breaks silently the day they change the template.
>
> The trigger only sees the **Inbox** — mail sitting in Junk never fires it.
> That is why the Exchange mail-flow rule bypassing spam filtering for
> `formspree.io` matters here too, not just for your own reading.

### Action 1 — Html to text

Add **Html to text** (Content Conversion). Set **Content** to the trigger's
**Body**. Formspree sends HTML; this turns it into plain lines.

### Action 2 — Compose, named `AfterJson`

```
last(split(body('Html_to_text'), '_json'))
```

Everything after the `_json` label, which includes the JSON and any footer.

### Action 3 — Compose, named `JsonOnly`

```
substring(outputs('AfterJson'), indexOf(outputs('AfterJson'), '{'), add(sub(lastIndexOf(outputs('AfterJson'), '}'), indexOf(outputs('AfterJson'), '{')), 1))
```

Takes from the first `{` to the last `}`. Slicing on braces rather than on line
breaks means a Formspree footer, a signature, or wrapped lines cannot break it.

### Action 4 — Parse JSON

**Content:** `outputs('JsonOnly')`

**Schema:**

```json
{
  "type": "object",
  "properties": {
    "services":              { "type": "array", "items": { "type": "string" } },
    "individual_complexity": { "type": "array", "items": { "type": "string" } },
    "business_structure":    { "type": "array", "items": { "type": "string" } },
    "business_complexity":   { "type": "array", "items": { "type": "string" } },
    "revenue_band":       { "type": "string" },
    "tax_status":         { "type": "string" },
    "bookkeeping_status": { "type": "string" },
    "urgency":            { "type": "string" },
    "deadline":           { "type": "string" },
    "notes":              { "type": "string" },
    "contact": {
      "type": "object",
      "properties": {
        "name":      { "type": "string" },
        "email":     { "type": "string" },
        "phone":     { "type": "string" },
        "preferred": { "type": "string" },
        "location":  { "type": "string" },
        "consent":   { "type": "boolean" }
      }
    }
  }
}
```

> **Mark nothing as required.** Most questions are conditional — a personal-tax
> lead has no `business_structure` at all — and a required property that is
> absent fails the whole run.

### Action 5 — Add a row into a table

**Excel Online (Business)** → **Add a row into a table**. Location: OneDrive
for Business; Document: `SATC leads.xlsx`; Table: `Leads`.

| Column | Expression |
|---|---|
| Received | `utcNow()` |
| Name | `coalesce(body('Parse_JSON')?['contact']?['name'], '')` |
| Email | `coalesce(body('Parse_JSON')?['contact']?['email'], '')` |
| Phone | `coalesce(body('Parse_JSON')?['contact']?['phone'], '')` |
| Location | `coalesce(body('Parse_JSON')?['contact']?['location'], '')` |
| Preferred | `coalesce(body('Parse_JSON')?['contact']?['preferred'], '')` |
| Services | `join(coalesce(body('Parse_JSON')?['services'], createArray()), ', ')` |
| Individual complexity | `join(coalesce(body('Parse_JSON')?['individual_complexity'], createArray()), ', ')` |
| Business structure | `join(coalesce(body('Parse_JSON')?['business_structure'], createArray()), ', ')` |
| Tax status | `coalesce(body('Parse_JSON')?['tax_status'], '')` |
| Bookkeeping status | `coalesce(body('Parse_JSON')?['bookkeeping_status'], '')` |
| Urgency | `coalesce(body('Parse_JSON')?['urgency'], '')` |
| Deadline | `coalesce(body('Parse_JSON')?['deadline'], '')` |
| Notes | `coalesce(body('Parse_JSON')?['notes'], '')` |
| Raw JSON | `outputs('JsonOnly')` |

> `coalesce(…, '')` is doing real work: a skipped question is **absent**, not
> empty, and referencing an absent property without it fails the run. Same for
> `createArray()` on the list fields — `join` on null throws.

---

## Step 3 · Test it

Fill in the live form and send one. Within a minute or two a row should appear.

If the run fails, open it in the flow history — Power Automate shows each
action's input and output, so you can see exactly where it stopped. The usual
culprits, in order:

1. Table not named `Leads`, or not a real Table
2. Column header spelled differently from the mapping above
3. The email landed in Junk, so the trigger never fired

---

## Step 4 · Know when it breaks

Add a failure alert **inside the flow** — it does better than announcing a
problem, it hands back the lead that would otherwise be lost.

1. **+** below *Add a row into a table* → **Send an email (V2)**
2. **To:** your own address
3. **Subject:** `Intake flow FAILED — lead not filed`
4. **Body:** `outputs('JsonOnly')` — the whole submission
5. Click the **⋯** on that email action → **Configure run after**
6. **Uncheck** *is successful*; **check** *has failed*, *has timed out*, *is skipped*

That inverts the action: it fires only when the row write did not happen. The
JSON travels with it, so the lead can be filed by hand rather than
reconstructed.

### The free cross-check

Every submission produces two things: an email from Formspree and a row in the
sheet. **The email is the source of truth; the sheet is derived from it.** If an
email arrives with no matching row, the flow is broken — and no lead has been
lost, only its filing.

### Three ways it stops quietly

- **Junk.** The trigger watches the **Inbox** only. If Formspree mail starts
  being filtered, the flow never fires — no error, no alert, nothing in the run
  history. This is the one failure mode that no alert catches, and the reason
  the Exchange mail-flow rule for `formspree.io` is a dependency rather than a
  convenience.
- **90 days idle.** Power Automate suspends flows that have not run. It emails
  first; one click re-enables.
- **A broken connection.** A password change or revoked MFA can invalidate the
  stored Office 365 connection. Runs then fail with an authentication error
  until it is reconnected — the failure alert above will catch this one.

### Where it runs

On Microsoft's servers, continuously. Not on any laptop. Nothing needs to be
open — not Outlook, not Excel, not the OneDrive sync client. A submission at
2am on a Sunday is filed at 2am on a Sunday.

---

## What the values look like

The spreadsheet stores the **stored values**, not the on-screen labels —
`individual_tax` rather than "Individual tax preparation". That is deliberate:
they are stable and filterable, and the prose in the email covers readability.
The labels live in `website/intake-config.js` if a lookup is ever wanted.
