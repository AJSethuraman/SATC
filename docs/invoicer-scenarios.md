# Invoicer — the scenario harness

**Date:** 2026-08-27
**Artifact:** `invoice-generator/exercise.py`
**Run it:** `cd invoice-generator && python exercise.py` (exit 0 = no surprises)
**Companion:** `docs/invoicer-review.md` (the 2026-08-26 code review; not repeated here)
**Governing document:** `docs/SOFTWARE-TENETS.md`

This is the third thing that looks at Invoicer, and it is deliberately not
like the other two.

| | Runs on | Asserts | Produces |
|---|---|---|---|
| `tests/` (57 tests) | fixtures | properties that must never regress | nothing |
| `docs/invoicer-review.md` | a running instance, by hand, once | nothing; it is prose | a list of findings |
| `exercise.py` (281 checks) | a live app, every time | that each step happened, on the artifact | 48 invoices, 53 PDFs, real email |

`pytest` is the gate. This is the demonstration — the thing you run when
somebody asks "show me it works," and the thing that opens what came out
rather than counting it. The distinction is **S22**: CI holds what must never
regress; a harness produces what must be looked at; they are not substitutes.

---

## What one run does

Two owners sign up through the signup form, log in through the login form,
fill in a business profile, and then run a small practice between them: 48
invoices raised, edited, discounted, taxed, part-paid, overpaid, chased when
overdue, emailed, exported and — where they should not have been raised —
deleted. Payments arrive as Stripe webhooks signed with a throwaway secret and
verified by Stripe's own verifier. Everything goes over real HTTP through the
Flask test client with **CSRF protection and the rate limiter left on**, plus
a live Werkzeug server for the browser check.

Last run: **281 checks · 600 things compared · 53 PDFs opened · 0 surprises ·
16 known and documented · 1 not checked.**

Everything it writes goes to `invoice-generator/out/`, which this pass added to
`.gitignore` (**S22.4** — the first version of the sister harness wrote a
hundred rendered client letters into a tracked directory).

### The chapters

| Chapter | What it drives | Denominator |
|---|---|---|
| `accounts` | signup (3 refusals + 2 successes + a duplicate), a form post with no CSRF token, login, wrong password, unknown account, logout, `?next=` off-site (4 shapes), the login rate limit, anonymous access to every owner page | 8 owner routes, 14 login attempts |
| `profile` | the profile gate on `/new` **and** on the raw `POST /invoices` behind it | 3 |
| `clients` | the client on an invoice: created, read, corrected, searched for, and deleted with its line items; numbering after a deletion | 13 |
| `money` | 23 invoice shapes — 14 raised, 9 refused | 14 invoices re-added in exact decimal |
| `currency` | 7 currencies formatted on the page and in the PDF; changing the account default | 7 |
| `payments` | partial, duplicate, overpayment, overdue, overdue-outranks-partial, mark-paid, mark-unpaid, edit-after-payment | 18 |
| `isolation` | account B against 4 read routes, 5 write routes and 4 API endpoints of account A's invoice; History; CSV; public tokens | 13 routes + 2 exports |
| `api` | key auth, create, read back, list, delete, auto-numbering, PDF, key rotation, 12 malformed bodies, 3 non-finite literals | 12 refusals |
| `stripe` | 6 bad signatures, 1 good one, 4 duplicate deliveries, foreign account, wrong currency, unsettled ACH then settlement, unknown invoice, unhandled type, cross-account forgery | 6 signatures, 4 retries |
| `email` | the real MIME message: subject, text part, HTML part, PDF attachment, template tokens, a failed send | 2 bodies |
| `csv` | header, one row per invoice, every total reconciled against the database, every row re-added, formula injection | 30+ invoices |
| `artifacts` | **every PDF this run produced, opened**; the public page in Chromium | 53 PDFs |
| `errors` | 6 dead URLs, a stack-trace check, 405, password reset, a corrupt logo upload | 6 |
| `posture` | the structural findings a request-level harness cannot see | 5 |

---

## How it proves things, and why that shape

### PDFs are opened, not counted

Every PDF produced in the run — the owner's download, the API's, the client's
public download, and the one actually attached to the email — is put through
`verify_pdf`, which:

1. extracts the text with `pypdf` and requires the **invoice number**, the
   **client's name** and the **total** to be on the page;
2. requires the number *labelled* "Total" to equal the total in the database,
   and the same for "Balance due" (present-somewhere is not the same claim);
3. fails on any `{{`, `}}`, `{%`, `None` or `Undefined` left in the text;
4. **rasterises page 1 with PyMuPDF and counts the ink.** Text extraction
   proves the text objects exist in the content stream. It proves nothing
   about visibility: white-on-white, a zero-height box, a clipped region and a
   failed font all extract perfectly and print blank. A page under 1% coverage
   is not an invoice.

This exists because of **S1**. The sister harness in `client-documents/` once
reported "190 documents produced, 0 surprises" having read every one of them
as a string; every one opened as unstyled plain text.

### The page the client opens is opened in a real browser

`browser_check` starts a live Werkzeug server and loads `/i/<token>` in
Chromium via Playwright, then reads back what the **browser computed** — the
rendered text, the character count, the page height, the resolved font, the
buttons — and requires the invoice number, the client name and a figure to be
visible. A page that serves a perfectly good 200 and renders to nothing fails
here and nowhere else.

### Money is checked against arithmetic the app does not do

Two independent checks on every invoice raised:

* the invariant `sum(line totals) − discount + tax + shipping == total`, on
  **all 14**, not on one (**S18/S19**);
* the whole invoice recomputed in `decimal.Decimal` with `ROUND_HALF_UP`, from
  the values that were typed into the form.

The second matters. Recomputing with the app's own method would only prove the
app agrees with itself, which is the shape of every bug in
`SOFTWARE-TENETS.md` part 0. The previous review checked the first kind and
concluded "I could not produce an arithmetic error"; the second kind produces
three on the first run, and they are in the "still wrong" list below.

### Three verdicts, and one of them is a tripwire

`ok` / `FAIL` / `KNOWN`. A `KNOWN` is a real defect, reproduced deliberately,
written up below with a reason it was not fixed — it does **not** fail the
run, because a documented problem is not a surprise. But each one is wired
backwards: if the behaviour ever changes, even to something better, the check
goes `FAIL` and names this document. A list of known problems that quietly
stops being true is worse than no list, because people stop reading it
(**S4**, **S25**).

Both halves were proved red before this was written (**S15**):

* changing the PDF template's Total to print the *subtotal* → 6 named PDFs
  reported, "the PDF says Total $1,494.00 but the database says $1,509.00",
  exit 1.
* removing the ownership test from `owned_or_404` → 5 failures naming the
  route and the status, exit 1.
* running `--only artifacts` with no invoices in the book → the totals check
  passed on an empty set and **the denominator floor caught it** ("more than a
  handful of PDFs were actually opened": 0). That is **S2** doing its job.

---

## What it found, and what was fixed

Three fixes, each minimal, each with a regression test in
`invoice-generator/tests/test_scenarios.py` that was **proved red against the
unfixed code** before being kept. Test count 49 → 57.

### 1. A number that is not a number was billed rather than refused — HIGH

`helpers.parse_float` caught the `ValueError` from `float("$500.00")` and
returned its default. So a rate pasted with its currency symbol on it — which
is how an amount arrives from a quote, an email, or another system — created a
**line item worth nothing**. The invoice saved, displayed, exported, rendered
to PDF and could be emailed to the client for $0.00, with no warning at any
point. `"1.234,56"` is worse: comma-stripping turns it into `1.23456`, a
plausible-looking $1.23.

Worse still, `"1e400"` is a *valid* float literal that evaluates to `inf`, and
`1e308 × 10` overflows to `inf` on multiply. `inf × 0% tax` is `nan`, and
`nan < 0` is `False`, so the negative-total guard waved it through. The row
was stored, and the History page then read **`$nan` for outstanding, overdue
AND paid** — every KPI in the account, not just that invoice's row. The
owner's dashboard stopped reporting any figure at all. Reproduced.

The JSON API had the same holes through a different function (`_to_float`),
and Python's JSON decoder accepts the bare literals `NaN` and `Infinity`.

**Fix.** One shared `helpers.parse_money(value) -> (number, ok)` used by
**both** front doors, so a value one refuses cannot be quietly accepted by the
other (**S3** — they had separate coercion with separate holes). Absence stays
forgiving: `None` and `""` still mean "leave it at the default", which is what
a blank tax or shipping box means. A value that is present and is not a finite
number stops the save with a message naming the field. Both validators also
refuse an invoice whose total is not finite, which catches the overflow route
where every individual input parsed fine.

Caught by `test_unparseable_money_is_refused_not_silently_billed_as_zero`,
`test_an_overflowing_rate_cannot_produce_a_nan_invoice`,
`test_a_literal_exponent_overflow_is_refused_too`, `test_api_rejects_a_nan_rate`,
`test_both_front_doors_refuse_the_same_unparseable_value`.

### 2. Mismatched line-item arrays silently dropped a line — HIGH

`docs/invoicer-review.md` finding 15, left alone there. `zip` truncates to the
shortest of the three parallel form arrays, so three descriptions, three rates
and two quantities produced a **two-line invoice**: $200.00 instead of
$300.00, created, sendable, payable, with no error anywhere. One disabled
input, one JS change or one row the browser dropped is enough.

**Fix.** Refuse the submission when the three arrays disagree in length, and
say so. Filling the missing cell with a blank quantity — the other obvious
repair — would bill that line at zero, which is the same failure wearing a
hat. This is the approach the review itself proposed; it is taken now because
the harness proved the silent path, and because the same pass also proved a
refusal on the *edit* route leaves the stored invoice untouched (the edit path
clears `invoice.items` on the live ORM instance before validation runs).

Caught by `test_mismatched_line_item_arrays_are_refused_not_silently_truncated`
and `test_a_refused_edit_leaves_the_stored_invoice_untouched`.

### 3. The JSON API accepted a negative `amount_paid` — MEDIUM

`{"amount_paid": -500}` on a $100 invoice made `balance_due` **$600**, adding
$500 of money nobody will ever pay to the account's outstanding KPI. A
negative payment is not a refund; nothing downstream expects one.

**Fix.** Refuse it in `api._validate`. Overpayment (`amount_paid > total`)
stays legal — that happens for real, and the harness checks it is recorded in
full rather than clipped.

Caught by `test_api_rejects_a_negative_amount_paid`.

### What the harness confirmed was already right

Stated plainly rather than padded (**S27**). Each of these was probed and held:

* **Authorization**, on 13 per-invoice routes and both exports. Account B
  cannot read, edit, delete, settle, reopen, email, download or API-fetch
  account A's invoice, and A's invoice was byte-identical after all fourteen
  attempts.
* **Webhook signatures.** Six bad ones — absent, empty, wrong secret, forged,
  a valid signature over a *different* body, and one two days stale — all
  refused, and none of them credited a cent.
* **Idempotency.** One event delivered four times credits once. So does an ACH
  settlement retried after it lands.
* **Tax order.** Charged on the discounted base: 50% off $1,000 then 10% tax
  is $550.00, not $600.00.
* **The totals invariant**, on all 14 invoices raised, including a credit
  line, a zero-quantity line, $117,585,000.00 and $0.03.
* **PDF rendering**, in seven currencies including `CHF 1,000.00` and
  `¥1,000.00` — every symbol renders and extracts, every page has ink on it,
  every Total matches the database.
* **Email.** Real subject, real text and HTML alternatives, real PDF
  attachment, no unresolved template tokens in either body, and a failed send
  leaves the invoice on `Draft` rather than claiming it went out.
* **The open-redirect and CSRF guards**, the login rate limit, the profile
  gate, and the 404 path for six dead URLs.

---

## What is still wrong, worst first

Each of these is reproduced by a `KNOWN` tripwire in `exercise.py`. None was
fixed, and each says why.

### 1. ~~A public invoice link outlives the invoice and points at the next one~~ — **FIXED 27 Aug 2026**

`/i/<token>` signs the invoice's **integer primary key**. SQLite hands the
next insert the highest free rowid, so deleting an invoice releases its id and
the next invoice raised on the instance takes it. Every link already sitting
in a client's inbox then resolves to somebody else's invoice.

The harness reproduces it **across accounts**: owner A raises a confidential
$5,000.00 invoice, sends the link, deletes the invoice; owner B — a different
workspace — raises the next invoice, which inherits the id; A's client opens
the link A sent them and reads B's `$7,777.00` invoice, client name and all.
Nothing in Invoicer's authorization is wrong here — the public page is meant
to be readable by whoever holds the link — the identifier underneath it is.

**Who is exposed.** Postgres allocates from a sequence and never reuses, so
the Render deployment in `render.yaml` is **not** affected. `docker-compose.yml`
— the documented one-command self-host — sets
`DATABASE_URL=sqlite:////app/data/invoices.db`, and so does the local
`run.ps1` path and the bare `flask run` default. Every one of those is
affected.

**How it was fixed, without invalidating a single link.** The reasoning above
was that every honest fix changes the token payload — and it is right about
tokens. It does not have to be a token. `Invoice.__table_args__` now carries
`sqlite_autoincrement`, so SQLite keeps a monotonic counter in
`sqlite_sequence` and never hands a deleted invoice's id to the next one. Every
link already in a client's hands keeps working and keeps pointing where it was
minted to point; a deleted invoice's link 404s, as it did before, and goes on
404ing forever instead of coming back to life as somebody else's invoice.

**One thing an existing instance must know.** A SQLite file created before this
does not gain the flag — the table would have to be rebuilt. New installs are
safe. An instance that has already been deleting invoices should not be trusted
with a public link until its `invoices` table is rebuilt.

The harness's tripwire on this fired the moment the behaviour changed, which is
what a tripwire is for. It is now two standing assertions

### 2. No payments ledger: three ways real money is destroyed — HIGH

`docs/invoicer-review.md` finding 4, unchanged, and all three halves are
reproduced here:

* **mark-unpaid erases a Stripe-confirmed payment.** $400.00 confirmed by
  Stripe becomes $0.00 on one click, and replaying the original webhook will
  **not** restore it — the session id is still in `paid_session_ids`, so the
  handler treats it as already credited. The money cannot be recovered by any
  action in the app.
* **mark-paid over a partial payment loses the provenance.** $400.00 by card
  and $700.00 by cheque become one indistinguishable `1100.00`. If the card
  payment is later disputed there is no record of what it was.
* **deleting a paid invoice destroys the payment record.** $900.00 that Stripe
  still holds a charge for now has no counterpart in this system to reconcile
  against.

**Why left alone.** Unchanged from the review: this needs a `Payment` table
(invoice_id, amount, currency, source `stripe|manual`, stripe_session_id,
created_at, reversed_at), `Invoice.amount_paid` becoming a derived sum, both
`mark-*` routes writing rows instead of assigning a float, a soft delete when
any payment exists, and the idempotency key moving from a comma-separated
string to a unique index. That is a schema change plus a backfill plus a
rework of the webhook credit path, on a production-autodeploying app.

### 3. Invoices lose a cent to binary float rounding — MEDIUM, and it is a charging change — NEW

Three of the fourteen invoices raised in an ordinary run disagree with exact
decimal arithmetic by exactly one cent:

| Invoice | Exact | Invoicer says |
|---|---|---|
| 12.75 hours at $187.50, 6.5% tax | $2,546.02 | **$2,546.01** |
| 0.25 hours at $250.50 | $62.63 | **$62.62** |
| 8.25% tax on a $1,394.00 base (JSON API) | $115.01 | **$115.00** |

None of these is exotic. Quarter-hour billing at a rate ending in `.50`, and a
tax that lands on half a cent, are what an ordinary week produces. The cause is
two compounding effects: Python's `round` is round-half-to-**even**, not
half-up, and the values are binary floats that cannot hold `0.125` or `2.675`
exactly. The direction of the error depends on the digits, so it favours the
client sometimes and the firm sometimes.

This is the *active* form of `invoicer-review` finding 13, which recorded the
float columns as a structural risk and said "I could not produce an arithmetic
error." It could not, because it checked that the total equals the sum of the
**displayed** parts — which is true, and is a different claim from the total
being right.

**Why left alone.** Fixing it changes what a client is charged, by a cent, on
invoices that may already have been issued and paid. That is the owner's call,
not a drive-by fix. **Proposed approach:** move the monetary columns to
`Numeric(12, 2)` and the derived properties to `decimal.Decimal` with
`ROUND_HALF_UP`, under Alembic, as its own change — and decide first whether
historical invoices are restated or left as issued.

### 4. History KPIs add different currencies together — MEDIUM

`invoicer-review` finding 7, unchanged — but the harness shows it is reachable
with **no API involved**: the owner only has to change their default currency
once, after which the KPI cards sum every invoice's balance regardless of
currency and label the result with the new symbol. Seven invoices in seven
currencies here become one confident figure.

**Why left alone.** The honest fix changes what the dashboard displays — group
the cards by currency, or restrict them to the default and count the rest
separately. That is a product decision about the History page.

### 5. Two invoices can carry the same number — MEDIUM

`invoice_number` has no unique constraint. The harness creates two invoices in
one account both called `DUP-0007`, to different clients, for $100.00 and
$9,000.00. `next_invoice_number` was fixed in the previous pass so the
*suggestion* no longer repeats, which reduces collisions; nothing prevents
them. Nothing can reconcile that against a client's accounts payable, and it is
usually noticed when somebody pays the wrong one.

**Why left alone.** A unique index on `(user_id, invoice_number)` is a schema
change and needs a decision about existing duplicate rows.

### 6. Workspace SMTP passwords are stored in plaintext — MEDIUM

`invoicer-review` finding 12, unchanged and re-verified: a password set through
`/account/email` comes back out of the `users` table byte for byte. Any
database read yields working outbound mail credentials for every workspace
that configured one, and those are frequently a real mailbox password rather
than an app token. It sits badly against `CLAUDE.md`'s own PII posture, which
requires an AES-256 vault in `satc_system`.

**Why left alone.** Needs a key-management decision (where the key lives on
Render, how it rotates) plus a migration. **Proposed approach:** a Fernet
`TypeDecorator` keyed on a second `generateValue` secret; write encrypted,
tolerate plaintext on read for one release, then backfill.

### 7. An unconfigured webhook secret answers Stripe with a 500 — MEDIUM

`app.py` returns `("Webhook secret not configured", 500)`. A 5xx makes Stripe
retry with backoff and eventually **disable the endpoint**, at which point
*other* invoices' payments stop being credited too — a configuration mistake
on one deploy becomes lost payments across the account. The misconfiguration
deserves a loud alarm; the answer to Stripe should be a 4xx (or the endpoint
should refuse to exist until the secret is set).

**Why left alone.** Changing a webhook response code is a production behaviour
change on the money path and deserves its own deliberate pass with the Stripe
dashboard in view.

### 8. Rate limits are per-worker — LOW-MEDIUM

`invoicer-review` finding 14, unchanged and now checked mechanically:
`RATELIMIT_STORAGE_URI` is `memory://` while the `Dockerfile` runs
`gunicorn --workers 2`, so "10 per minute" on login is really 10 per worker
per minute and resets on every deploy — which, with autodeploy on, is every
push. **Proposed approach:** add Redis to the blueprint, or set
`--workers 1 --threads 8` so the configured numbers are honest.

### 9. A due date before the issue date is accepted — LOW

An invoice issued today with a custom due date of five days ago is created and
is **overdue the moment it exists** — it lands straight in the Overdue KPI and
the chase list. A transposed date entry is enough.

**Why left alone.** Trivially fixable, but it is a new refusal on the invoice
form and I would rather the owner decided whether back-dating a due date is
ever legitimate for them (it can be, on a re-issued invoice) than have me
forbid it.

### 10. A blank row with a quantity becomes an empty line item — LOW

The invoice form's rows default to quantity 1, and the "skip the empty row"
test is `not desc and qty == 0 and rate == 0`. So a row with nothing typed in
it but the default quantity still becomes a line item with an empty
description and $0.00, which then prints as a blank row on the client's PDF.

**Why left alone.** The right repair is in `invoice_form.html`'s JavaScript
(don't submit untouched rows) as much as in the server, and it wants the form
in view. Cosmetic, but it is on a document a client reads.

### 11. Pillow is used but not declared — LOW

`invoicer-review` finding 16, unchanged. `app.py` imports `PIL` to validate
raster logos and it appears in neither requirements file — it is present only
transitively via the PDF engines. Drop one of those and **every raster logo
upload is silently rejected**, because the `ImportError` is caught by the same
handler that catches a corrupt image.

### 12. The plain-text email body carries no amount — LOW, and it is wording

The invoice email's `text/plain` alternative reads, in full: *"Hello, / Please
find attached invoice EML-0001. / Pay online here: … / Thank you for your
business."* No amount, no due date, no balance. The HTML alternative has all
three, so most clients are fine; anyone reading in plain text, or behind a
gateway that strips HTML, gets an invoice email with no figure in it.

**Why left alone.** This is client-facing wording. Per the repo's own rule,
wording changes are flagged, not made. **Proposed approach:** add the amount
due and the due date to the text body, matching the HTML — the firm should
write the sentence.

---

## What this run deliberately does not check

Stated so the next person inherits the blind spot as a known one (**S27**,
day-one rule 10).

* **Postgres.** Everything here runs on SQLite, as does `pytest`. Production
  is Postgres. That difference is not cosmetic — finding 1 above exists on one
  engine and not the other — and it means the class of failure most likely to
  break a deploy is exactly the class neither suite can see. Adding a
  `services: postgres` block to the CI job remains the review's second
  recommendation and is still worth doing.
* **Stripe itself.** Checkout Session creation is a local fake. The signature
  verifier is real and the payloads are real shapes, but no request leaves the
  machine, and nothing here proves an actual Connect account behaves as
  assumed.
* **Real SMTP.** The transport is faked at `smtplib`, so the message is built
  for real and delivered nowhere. Nothing here proves deliverability, SPF/DKIM
  alignment, or how a specific mail client renders the HTML.
* **There is no client record to CRUD.** Invoicer has no client table: the
  client is free text in `bill_to`, copied onto each invoice. So "client CRUD"
  is exercised as invoice CRUD, and the harness records a `skip` saying so.
  The consequence is worth naming on its own: **there is no way to correct a
  client's address across the invoices already raised**, and no client list.
* **Concurrency.** One request at a time. Two simultaneous webhooks for the
  same invoice, or two workers booting `_ensure_schema` at once, are not
  exercised.
* **The browser check is one page, two invoices.** The public invoice page,
  payable and settled. The owner-facing pages are checked as HTML strings, not
  opened.
* **Logo rendering.** A corrupt upload is refused and the PDF still renders; a
  *valid* logo is never uploaded, so nothing here proves a logo appears
  correctly in the PDF or the email.

---

## The pre-flight check, run

Against `SOFTWARE-TENETS.md`'s own list, for this pass:

1. **Claim named.** "Two owners can run a small practice through Invoicer end
   to end, and every artifact it produces says the right number."
2. **Suite run, count read.** 49 → 57. The number moved because eight new
   guards landed.
3. **New guards proved red.** All eight failed against the unfixed code; the
   output is in this pass's notes.
4. **Real front doors driven.** Both — the web forms with CSRF on, and the
   JSON API with a real key. Where they share a decision they now share a
   function.
5. **Denominator printed.** 600 comparisons, and the empty-set case was proved
   to fail.
6. **Artifacts opened.** 53 PDFs parsed and rasterised; the client's page
   loaded in Chromium against a live server.
7. **More than one shape.** 14 invoice shapes, 7 currencies, 2 accounts, both
   sides of the paid/unpaid, overdue/current and settled/partial boundaries.
8. **Controls run on real work.** The harness *is* the control; `pytest` is
   the gate.
9. **Retirement finished.** `helpers.parse_float` and `api._to_float` are both
   gone, their six callers moved to the shared `parse_money`, and a grep for
   either name across the project returns only this document and one test
   docstring naming the bug.
10. **Output location checked.** `invoice-generator/out/` added to
    `.gitignore`; `git status` shows nothing invoice-shaped.
11. **Not-checked stated.** The section above.
