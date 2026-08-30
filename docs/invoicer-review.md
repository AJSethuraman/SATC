# Invoicer (`invoice-generator/`) — code review

**Date:** 2026-08-26
**Scope:** `invoice-generator/` only. `app.py`, `api.py`, `models.py`, `pdf.py`,
`email_utils.py`, `stripe_utils.py`, `helpers.py`, `config.py`, `templates/`,
`Dockerfile`, `docker-compose.yml`, and the repo-root `render.yaml`.
**Test baseline:** 7 passing before this pass, 43 after
(`tests/test_calculations.py` 7 + new `tests/test_scenarios.py` 36).

This app takes money, sends email, and autodeploys to Render on every push to
`main`. There is no staging gate, so everything below is a statement about
production.

Every finding was reproduced against a running instance before being written
down. Findings marked **FIXED** have a fix in the working tree with a comment
naming the scenario test that catches the regression; findings marked
**LEFT ALONE** have a proposed approach and no code change.

---

## Summary

The app is in better shape than its risk profile suggested. Two areas I
expected to be the worst are actually its strongest:

- **Authorization is correct on every route.** Every per-invoice web route and
  every JSON API route resolves ownership before acting, and I could not get
  user B to read, edit, settle, or delete user A's invoice through any of the
  routes I probed. Anonymous access redirects to login everywhere it should.
- **The totals arithmetic does not drift.** Every intermediate (`item.amount`,
  `subtotal`, `discount_amount`, `tax_amount`, `total`) is rounded to 2dp
  before the next one consumes it, so the displayed total always equals the sum
  of the displayed parts. I ran 20,000 randomised invoices looking for a
  disagreement and found zero.

The real problems are elsewhere: a Stripe event that is credited before the
money has settled, an insecure secret-key default that a self-hosted deploy can
trip over silently, and stored `status` fields that go stale when an invoice is
edited or reversed. The single most consequential structural gap is that there
is **no payments ledger** — `amount_paid` is one mutable float on the invoice
row, which is why three separate findings below all reduce to "real money is
destroyed with no record."

---

## Findings, worst first

### 1. `checkout.session.completed` is credited before the money settles — **HIGH** — FIXED

**Where:** `app.py:1408` (`stripe_webhook`).

Stripe fires `checkout.session.completed` the moment the customer finishes the
Checkout page. For delayed-notification payment methods — ACH direct debit,
SEPA, Bacs, Boleto, OXXO, Konbini — that happens **days before the funds
clear**, and the event carries `payment_status: "unpaid"`. The handler read
`amount_total` and credited it regardless.

**Failure scenario:** A client pays a $500.00 invoice by ACH bank debit. The
session completes; the invoice flips to `Paid`, `amount_paid` becomes 500.00,
`balance_due` becomes 0.00, and it drops out of the outstanding KPI. Four days
later the debit is returned for insufficient funds. Nothing in the app ever
learns this. The invoice reads as settled forever and the $500.00 is never
chased.

Reproduced: posting a signed `checkout.session.completed` with
`payment_status: "unpaid"` set a fresh $500.00 invoice to `Paid` /
`amount_paid=500.0`.

This only bites once the owner enables a delayed payment method in their Stripe
Checkout settings. Card-only accounts always report `paid`. It is a cheap fix
and a large downside, so it was worth taking now rather than waiting for the
setting to change.

**Fix:** credit only when `payment_status` is `paid` or `no_payment_required`,
and handle `checkout.session.async_payment_succeeded` — the event Stripe sends
when a delayed payment actually settles — alongside `completed`.
Caught by `test_delayed_payment_method_is_not_credited_until_it_settles`.

---

### 2. Production boots on the development secret key — **HIGH** — FIXED

**Where:** `config.py:32` — `SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")`.

`SECRET_KEY` signs **both** Flask session cookies **and** the `/i/<token>`
public invoice links. If `FLASK_SECRET_KEY` is unset, the app starts normally
on a value that is published in this repository, with no warning at any log
level.

**Failure scenario:** Someone deploys the Docker image outside the Render
blueprint — `docker compose up` on a VPS, a manual Render service, a second
environment — and does not set `FLASK_SECRET_KEY`. Anyone who knows this app is
open-source can then (a) mint a session cookie for `user_id=1` and take over
the account, and (b) forge `/i/<token>` links for invoice ids `1, 2, 3…` and
read every client name, line item, and amount in the database.

Reproduced: with `APP_ENV=production` and no `FLASK_SECRET_KEY`, the app booted
happily, and a token signed with the literal string `dev-only-change-me`
returned HTTP 200 with the client name, line items, and amount in the body.

The blessed path is safe — `render.yaml` sets `FLASK_SECRET_KEY` via
`generateValue: true` — which is exactly why this had gone unnoticed.

**Fix:** `create_app` now raises at boot when `ENV == "production"` and the
secret is empty or the dev default. This cannot fire on the Render blueprint
(the key is generated there), and on a hand-rolled deploy failing loudly at
startup is strictly better than silently serving forgeable sessions.
Caught by `test_production_refuses_to_boot_on_the_development_secret_key`.

---

### 3. Editing a paid invoice leaves it reading "Paid" while money is owed — **HIGH** — FIXED

**Where:** `app.py:1054` (`update_invoice`). Root cause is that
`Invoice.status` is a stored column while `balance_due` is derived, and the
edit path updated the second without reconsidering the first.

**Failure scenario:** A $1,100.00 invoice is paid in full and marked `Paid`.
The owner then edits it to add $4,000.00 of extra scope. The total becomes
$5,500.00 and `balance_due` becomes $4,400.00 — but `status` is still `Paid`,
so:

- `display_status` returns `Paid` (it short-circuits on `status == "Paid"`), so
  the badge says settled;
- the History KPIs skip it entirely, because `outstanding` only sums invoices
  where `status != "Paid"`.

$4,400.00 is owed and is invisible in both places an owner would look for it.
Reproduced exactly as described.

**Fix:** after a successful edit, reopen the invoice (`Paid` → `Sent`) when
`balance_due > 0`, and settle it when an edit lowers the total to at or below
what was already paid. Caught by
`test_editing_a_paid_invoice_upward_reopens_it` and
`test_editing_a_paid_invoice_downward_settles_it`.

---

### 4. No payments ledger: three ways real money is destroyed — **HIGH** — LEFT ALONE

**Where:** `models.py:145-171` (`amount_paid`, `paid_session_ids` on `Invoice`).

`amount_paid` is a single mutable float on the invoice row, and
`paid_session_ids` is a comma-separated string of Stripe session ids with **no
amounts attached**. Nothing records *when* money arrived, *how much* each
payment was, or *whether it was manual or confirmed by Stripe*. Three distinct
findings all reduce to this:

**4a. `mark-unpaid` erases a Stripe-confirmed payment.** `app.py:1129` sets
`amount_paid = 0.0` outright. It exists to reverse a manual "mark as paid" but
cannot distinguish that from a webhook credit. *Scenario:* a client pays
$400.00 by card; the owner clicks "mark as unpaid" to correct something; the
$400.00 is gone. Because `cs_...` stays in `paid_session_ids`, replaying the
original webhook will **not** restore it — the money cannot be recovered by any
action in the app. Reproduced.

**4b. `mark-paid` overwrites a partial payment.** `app.py:1119` sets
`amount_paid = invoice.total`. *Scenario:* $400.00 of $1,100.00 has been paid
by card; the owner receives the remaining $700.00 as a cheque and clicks "mark
as paid". `amount_paid` jumps to 1,100.00, which is correct by luck — but the
$400.00 card payment and the $700.00 cheque are now indistinguishable, and if
the card payment is later disputed there is no record of what it was.

**4c. Deleting an invoice destroys its payment record.** `app.py:1091` and
`api.py:296`. The cascade removes the invoice and its line items, and
`amount_paid` goes with the row. *Scenario:* a $1,100.00 paid invoice is
deleted; Stripe still holds the charge, and this system has no counterpart to
reconcile it against. Reproduced.

**Why left alone:** every real fix needs a `Payment` table (invoice_id, amount,
currency, source `stripe|manual`, stripe_session_id, created_at, reversed_at),
which is a schema change plus a backfill plus a rework of the webhook credit
path and both mark-* routes. That is more than one safe pass on a
production-autodeploying app.

**Proposed approach:** add `Payment` as an append-only ledger; make
`Invoice.amount_paid` a derived property summing non-reversed payments; make
`mark-paid`/`mark-unpaid` write a `manual` payment row and a reversal row
respectively rather than assigning a float; make invoice deletion a soft delete
(`deleted_at`) when any payment exists. The idempotency key moves from the
`paid_session_ids` string to a unique index on `Payment.stripe_session_id`,
which also makes the duplicate-webhook guarantee a database constraint instead
of a string search.

Two tripwire tests pin the current behaviour and are written to **fail** when
this is fixed, with instructions to rewrite them:
`test_mark_unpaid_erases_a_recorded_stripe_payment` and
`test_deleting_a_paid_invoice_destroys_the_payment_record`.

---

### 5. Open redirect on `/login?next=` — **MEDIUM** — FIXED

**Where:** `app.py:654` (`login`) — previously `if not nxt or not nxt.startswith("/")`.

`//evil.example.com/steal` starts with `/`, so it passed the check — but it is
a *protocol-relative* URL, and the browser resolves it to
`https://evil.example.com/steal`.

**Failure scenario:** A phishing email links to
`https://invoicer.example/login?next=//evil.example.com/account`. The victim
sees the genuine Invoicer domain and a genuine login form, signs in
successfully, and is dropped on the attacker's page — at the precise moment
they have just confirmed to themselves that the site is real. Reproduced:
`Location: //evil.example.com/steal`.

**Fix:** also reject `//` and `/\` prefixes. Caught by
`test_login_next_parameter_cannot_redirect_off_site`.

---

### 6. A discount over 100% produces a negative invoice — **MEDIUM** — FIXED

**Where:** `app.py:415` (`_validate_invoice`) and `api.py:126` (`_validate`).
Neither bounded the discount.

**Failure scenario:** A 150% discount on a $1,000.00 invoice drives
`taxable_base` to -$500.00, which produces a **negative tax** of -$50.00 and a
total of -$550.00. The PDF renders it, the CSV exports it, and — because the
History KPI sums `balance_due` — it **subtracts $550.00 from the outstanding
figure**, understating what is owed across the entire book by that amount.
Reproduced. A typo of `150` for `15` is enough.

**Fix:** both entry points now reject a percentage discount above 100, reject
negative discount and tax values, and reject any invoice whose total is
negative. Exactly 100% remains legal (a fully written-off invoice). Negative
*line items* remain legal — they are how credits and adjustments are entered —
so only a negative bottom line is refused. Caught by
`test_discount_over_one_hundred_percent_is_rejected` and
`test_api_rejects_a_discount_over_one_hundred_percent`.

---

### 7. History KPIs add different currencies together — **MEDIUM** — LEFT ALONE

**Where:** `app.py:1329-1343` (the KPI block in `history`), and the `currency=`
argument passed to the template just below it.

`outstanding`, `overdue`, and `paid_total` sum `balance_due` across **all** of a
user's invoices, then render the result with the user's *default* currency
symbol.

**Failure scenario:** An owner with a $1,000.00, a €1,000.00, and a ¥1,000.00
invoice outstanding sees **"$3,000.00 outstanding."** The true figure is three
separate amounts, one of which (¥1,000) is worth about $7. Reproduced exactly.

Reachable because the JSON API sets `currency` per invoice (`api.py:95`) and
because changing the account default leaves historical invoices on the old
currency. The web form always uses the account default, so a web-only,
never-changed-currency user will not hit it.

**Why left alone:** the honest fix changes what the dashboard displays — either
group the KPI cards by currency, or restrict the KPIs to the default currency
and show a separate count of invoices in other currencies. That is a product
decision about the History page, not a bug fix, and it belongs with the owner.

**Proposed approach:** group `all_inv` by `currency` in the route, pass a list
of per-currency KPI blocks, and render one card row per currency present
(collapsing to today's single row in the overwhelmingly common one-currency
case, so nothing changes visually for most users).

---

### 8. Spreadsheet formula injection in the CSV export — **MEDIUM** — FIXED

**Where:** `app.py:1355` (`export_csv`); the `_csv_safe` helper added at
`app.py:475`.

**Failure scenario:** `bill_to` is free text and — through the JSON API — can be
written by a third-party system rather than by the account owner. A client name
of `=cmd|'/c calc'!A1` is written raw into the export. Excel, LibreOffice and
Google Sheets all execute a cell whose text begins with `=`, `+`, `-`, or `@`,
so the payload runs on the accountant's machine the moment they open the file.
Reproduced: the raw row began `INV-CSV,2026-08-26,=cmd|'/c calc'!A1,...`.

This matters more here than in a generic app: the whole point of the export is
that a bookkeeper opens it in a spreadsheet.

**Fix:** a `_csv_safe` helper prefixes a leading `=`, `+`, `-`, `@`, tab, or CR
with an apostrophe, which renders the cell inert while still displaying the
original text. Applied to `invoice_number` and `bill_to` — the two free-text
columns. Caught by
`test_csv_export_neutralises_spreadsheet_formula_injection`.

---

### 9. Suggested invoice numbers repeat after any deletion — **MEDIUM** — FIXED

**Where:** `app.py:494` (`next_invoice_number`) — previously
`count = Invoice.query.filter_by(...).count()`.

**Failure scenario:** The owner issues INV-0001, INV-0002, INV-0003 and deletes
INV-0002. The count is now 2, so the next invoice is suggested as **INV-0003** —
a number already in use. Nothing enforces uniqueness (`invoice_number` has no
unique constraint), so two different invoices, to two different clients, both
called INV-0003 now exist. This cannot be reconciled against Drake or against
the client's own accounts payable, and is typically noticed only when someone
pays the wrong one. Reproduced.

**Fix:** derive the suggestion from the highest numeric suffix already issued
rather than from the surviving row count. Only the *suggestion* changes; the
field remains free text, so no existing numbering scheme is broken. Caught by
`test_suggested_invoice_number_does_not_repeat_after_a_deletion`.

Note this reduces collisions but does not prevent them — a unique index on
`(user_id, invoice_number)` would, and is a schema change; see "left alone".

---

### 10. Unauthenticated, unthrottled Stripe session creation on the public pay route — **MEDIUM** — FIXED

**Where:** `app.py:1265` (`public_pay`). The route is `@csrf.exempt`
and has no `@login_required` — both correct, since the paying client has no
account — but it had no rate limit either.

**Failure scenario:** Anyone holding a public invoice link (which is designed to
be forwarded around a client's accounts payable department) can POST to it in a
loop. Every hit creates a real Checkout Session on the **owner's** connected
Stripe account. A few thousand requests bury the owner's Stripe dashboard in
abandoned sessions and consume their Stripe API rate budget.

**Fix:** `@limiter.limit("20 per hour")`. Note this is per-IP and, with
`RATELIMIT_STORAGE_URI` defaulting to `memory://`, per-worker — see finding 14.

---

### 11. PDF filename derived from unsanitised user input — **MEDIUM-LOW** — FIXED

**Where:** `app.py:450` (`generate_pdf`) — previously
`f"invoice_{invoice.invoice_number}_{invoice.id}.pdf".replace("/", "-")`.

`invoice_number` is free text and lands in the output path. Only the POSIX
separator was stripped.

**Failure scenario:** An invoice number of `..\..\..\windows\system32\evil`
produced the filename `invoice_..\..\..\windows\system32\evil_8.pdf`. On the
Windows `run.ps1` path — a supported way to run this app — that is a directory
traversal that writes the PDF outside `INVOICES_DIR`. The same unsanitised
string is also handed to the browser as `download_name`. On Linux/Docker the
backslash is an ordinary filename character, so production is not currently
exposed; the local Windows run is.

**Fix:** whitelist `[A-Za-z0-9._-]` in the number before it reaches the
filename, and strip leading/trailing dots and dashes. Caught by
`test_pdf_filename_cannot_escape_the_invoices_directory`.

---

### 12. Workspace SMTP passwords are stored in plaintext — **MEDIUM** — LEFT ALONE

**Where:** `models.py:65` — `smtp_password = db.Column(db.String(255), default="")`.

A workspace that brings its own SMTP server has that password stored as
cleartext in the `users` table, and it is read back verbatim at
`email_utils.py:71`.

**Failure scenario:** Any read access to the database — a Postgres backup, a
support query, a SQL injection anywhere in a future feature, a Render dashboard
session — yields working outbound mail credentials for every workspace that
configured one. Those credentials are frequently a real mailbox password rather
than an app-specific token.

This sits badly against the repo's own PII posture in `CLAUDE.md`, which
requires an AES-256 vault for sensitive values in `satc_system`.

**Why left alone:** doing it properly means a key-management decision (where
does the encryption key live on Render, how is it rotated) plus a migration of
existing rows. That is a design call for the owner, not a drive-by fix.

**Proposed approach:** encrypt at rest with Fernet using a
`SMTP_CREDENTIAL_KEY` env var (a second Render `generateValue` secret), via a
SQLAlchemy `TypeDecorator` so the column change is transparent to
`email_utils`. Write encrypted on save, tolerate plaintext on read for one
release, then backfill and make encrypted-only.

The password is at least already write-only in the UI — a blank submission
keeps the stored value (`app.py:829`) — so it is not echoed back to the browser.

---

### 13. Money is stored as `Float`, and schema changes rely on `create_all` plus hand-written DDL — **MEDIUM** — LEFT ALONE

**Where:** `models.py` — `tax_value`, `discount_value`, `shipping`,
`amount_paid`, `quantity`, `rate` are all `db.Float` (IEEE-754 double on both
SQLite and Postgres). And `app.py:92` (`_ensure_schema`) is a hand-rolled
additive migration run at every boot, alongside `db.create_all()`.

I want to be precise about the float risk, because it is smaller than it looks:
**I could not produce an arithmetic error.** The properties in `models.py` round
to 2dp at every step, so the total always equals the sum of its displayed parts
(20,000 randomised invoices, zero mismatches), and the Stripe minor-unit
conversion `int(round(amount * 100))` is exact at seven figures. The exposure is
structural rather than active: any future code that sums these columns **in
SQL** (`func.sum(Invoice.amount_paid)`) instead of in Python bypasses the
rounding discipline entirely and will drift.

`_ensure_schema` is careful — idempotent, race-safe across gunicorn workers,
tolerant of a failed inspect — but it is a growing hand-written migration
system with no version tracking, no down-migrations, and no test. Its
`column_exists` helper returns `True` on any inspection failure, meaning a
transient database hiccup at boot silently skips DDL and the app runs on with a
missing column.

**Why left alone:** both are schema changes on a live Postgres database with no
staging environment. Not a one-pass change.

**Proposed approach:** adopt Flask-Migrate/Alembic, generate an initial revision
that matches today's schema, and retire `_ensure_schema` once every environment
is stamped. In the same migration, move monetary columns to
`Numeric(12, 2)` and the derived properties to `decimal.Decimal`, keeping the
existing 2dp rounding semantics. Do the Alembic adoption first and alone — it
is the change that makes the second one safe.

---

### 14. Rate limits are per-worker in production — **LOW-MEDIUM** — LEFT ALONE

**Where:** `config.py:67` — `RATELIMIT_STORAGE_URI` defaults to `memory://`, and
`Dockerfile` runs `gunicorn --workers 2`.

**Failure scenario:** The login limit reads `10 per minute`, but with two
worker processes each holding its own in-memory counter, the effective limit is
20 per minute, and it resets on every deploy (which, with autodeploy on, is
every push). Password-guessing is throttled roughly half as much as intended.
The same applies to the signup, password-reset, and new `public_pay` limits.

**Why left alone:** the fix is provisioning a Redis instance and setting
`RATELIMIT_STORAGE_URI` — an infrastructure and cost decision, not a code
change. `render.yaml` would need a Redis service added.

**Proposed approach:** either add Redis to the blueprint, or set
`--workers 1 --threads 8` in the Dockerfile so the in-memory counter is
authoritative. The second is free and would make the configured numbers honest.

---

### 15. Mismatched line-item form arrays silently drop a line — **LOW** — LEFT ALONE

**Where:** `app.py:398` — `for desc, qty, rate in zip(descriptions, quantities, rates)`.

`zip` truncates to the shortest of the three parallel form arrays.

**Failure scenario:** Any client that posts three descriptions, three rates, and
two quantities (a JS bug, a disabled input, a partially-filled row removed by
the browser) has its **third line item silently discarded**. I submitted three
lines and two quantities and got a two-line invoice for $300.00 instead of
$600.00 — with no error shown. The invoice is created, sent, and paid at the
wrong amount.

**Why left alone:** the current UI always posts balanced arrays, so this is not
reachable through the shipped form today; it is a robustness gap that becomes a
real bug the moment `invoice_form.html`'s JavaScript changes. The fix is small
but changes the create/edit contract, so it deserves its own change with the
form JS in view.

**Proposed approach:** use `itertools.zip_longest(..., fillvalue="")` and reject
the submission with a validation error if the array lengths disagree — silently
inventing a blank quantity would be worse than refusing.

---

### 16. `Pillow` is used but not declared as a dependency — **LOW** — LEFT ALONE

**Where:** `app.py:326` — `from PIL import Image` inside `_read_logo`, wrapped
in a bare `except Exception: return None, None`. `Pillow` appears in neither
`requirements.txt` nor `requirements-deploy.txt`; it is currently present only
transitively, via `weasyprint` / `xhtml2pdf` / `reportlab`.

**Failure scenario:** If a future dependency bump drops the transitive Pillow —
for example pinning `PDF_ENGINE=weasyprint` and trimming `xhtml2pdf` — the
`ImportError` is swallowed by the same `except` that handles corrupt images, and
**every raster logo upload is silently rejected**. Owners would see their logo
simply never appear, with nothing in the logs.

**Proposed approach:** add `Pillow` to `requirements.txt` explicitly, and catch
`ImportError` separately from image-validation failures so a missing library
logs a warning instead of being mistaken for a bad file.

---

## Categories where I found nothing

Stated plainly rather than padded:

- **Authorization.** Nothing. Every per-invoice route I probed — 9 web routes,
  4 API routes, and the public-link routes — correctly scopes to the owner or
  to a signed token. `owned_or_404` in `app.py`
  and `_owned_or_404` in `api.py` are applied consistently, and I could not find
  a route that reads or mutates an invoice without going through one of them.
  Anonymous access to owner-facing pages redirects to login without exception.
- **Totals arithmetic.** Nothing. The rounding discipline is correct and
  consistent; see finding 13 for the structural caveat, which is not an active
  bug.
- **Webhook signature verification, idempotency, and ordering.** Nothing beyond
  finding 1. Bad signatures are rejected (400) before the payload is parsed;
  duplicate delivery of the same session id is a genuine no-op; a 30-day-old
  replayed payload is rejected on Stripe's timestamp tolerance; an event whose
  invoice no longer exists returns 200 rather than 500 (correct — a 500 would
  trigger Stripe's retry storm and eventual endpoint disabling, which would
  drop *other* invoices' payments); a currency mismatch is refused; and a
  connected account cannot claim another account's invoice via forged
  `metadata.invoice_id`. This handler has clearly been thought about.
- **Password storage and session handling.** Nothing. Werkzeug's
  `generate_password_hash` (scrypt by default in Werkzeug 3), no custom crypto,
  `HTTPONLY` + `SameSite=Lax` cookies, `SECURE` in production. Reset and
  verification tokens are `itsdangerous` signed with sane max-ages (1 hour for
  reset, 24 hours for verify) and the reset flow correctly marks the email
  verified.
- **CSRF.** Nothing. `CSRFProtect` is global; the three exemptions are the JSON
  API (custom `X-API-Key` header, which browsers cannot set cross-origin without
  a preflight), the Stripe webhook (signature-verified), and `public_pay`
  (unauthenticated by necessity — now rate-limited, finding 10).
- **XSS in templates.** Nothing. No `|safe`, no `autoescape false`, no
  `Markup()` on user data anywhere in `templates/`. The one filter that emits
  markup, `nl2br`, escapes before wrapping — `app.py:72`.
- **Secrets in the repo.** Nothing. `.env` is gitignored and not tracked;
  `.env.example` contains only empty placeholders; no key material is
  hardcoded anywhere. The one insecure *default* is finding 2. Logging is
  careful — `email_utils.mask_email` masks addresses, and SMTP
  usernames/passwords are explicitly never logged.
- **Email failure handling.** Nothing. `_deliver` re-raises on failure rather
  than swallowing, the caller catches and flashes the error, and — importantly —
  the invoice's `status` is only advanced to `Sent` *after* delivery is
  accepted, so a failed send cannot leave the owner believing the client
  received it. Verified by `test_a_failed_send_does_not_mark_the_invoice_sent`.
  Address validation is thin (`"@" in email` at signup) but the SMTP layer
  rejects genuinely malformed recipients and refused recipients are logged.
- **Cascade deletes and orphan rows.** Nothing structurally wrong.
  `User → Invoice` and `Invoice → LineItem` both use
  `cascade="all, delete-orphan"`, and I confirmed line items are removed with
  their invoice. The problem with deletion is what it does to *payment records*
  (finding 4c), not to orphans.
- **PDF generation.** Nothing. It rendered valid PDFs for every edge case I
  threw at it: zero-amount, no line items at all, $108M, negative quantities, a
  150% discount, sub-cent fractions, and the partial/paid/overpaid states. The
  engine auto-fallback (WeasyPrint → xhtml2pdf) works, and render failures are
  converted to a clean `RuntimeError` that callers surface as a flash message
  rather than a 500.
- **Square.** There is no Square integration in this codebase. The brief asked
  me to review Stripe *and Square* webhooks; `grep -ri square` across all
  Python, HTML, YAML, and Markdown returns nothing. Stripe is the only payment
  processor. Worth confirming that this matches the owner's expectation — if
  Square was believed to be integrated, that belief is wrong.

---

## Deploy-specific notes

- `render.yaml` sets `PDF_ENGINE=weasyprint` explicitly and the Dockerfile
  installs its native libraries, so production does not depend on the `auto`
  fallback. Good.
- `healthCheckPath: /api/health` is unauthenticated and returns a constant —
  correct, and it leaks nothing.
- **SQLite-vs-Postgres:** the app runs on SQLite locally and Postgres in
  production, and nothing in the test suite exercises Postgres. The concrete
  divergences I can see are: `_ensure_schema`'s `ALTER TABLE` statements behave
  differently on failure (Postgres aborts the surrounding transaction; the
  `safe_exec` rollback handles this, but it is doing real work that SQLite never
  requires), and `db.Float` is `REAL` on SQLite versus `double precision` on
  Postgres. Neither produced a bug I could demonstrate, but the *absence of any
  Postgres test* means a schema change that works locally can still fail on
  deploy — and with autodeploy, "fail on deploy" means "fail in production".
  Worth adding a Postgres service to the `pytest (invoice-generator)` CI job.
- `plan: free` for both the web service and the database. Render's free
  Postgres expires, and the free web instance cold-starts — a cold start on a
  Stripe webhook delivery risks a timeout and a retry rather than a lost
  payment, so this is a reliability annoyance rather than a correctness bug.

---

## Is this safe to keep autodeploying on every push?

**Not as it stands — but the gap is process, not code quality.**

The code is better than I expected. The webhook handler in particular has been
carefully thought about, authorization is genuinely correct everywhere, and the
totals arithmetic holds. Three of the four highest-severity findings were narrow
bugs with contained fixes, all now made and covered.

What makes the current setup unsafe is the combination of:

1. **No staging gate.** `autoDeploy: true` on `main` with no manual promotion
   step means every merge is a production release of an app that moves money.
2. **The test job does not gate the deploy.** `.github/workflows/test.yml` runs
   `pytest` on pull requests and on pushes to `main`, but Render watches the
   branch independently. A red test suite does not stop a deploy. The suite
   going from 7 to 43 tests only helps if something is actually reading the
   result.
3. **No Postgres in CI.** The suite runs entirely on SQLite while production is
   Postgres, so the class of failure most likely to take the site down at boot —
   a schema or DDL difference in `_ensure_schema` — is exactly the class CI
   cannot see.
4. **`_ensure_schema` runs at every boot** and can, on a bad day, silently skip
   DDL (finding 13).

My recommendation, in order and each cheap:

1. **Gate the deploy on the tests.** Either switch Render to
   `autoDeploy: false` and deploy via a workflow step that runs after `pytest`
   passes, or use a Render deploy hook fired from CI. This is the single
   highest-value change on this list and it is a configuration edit.
2. **Add Postgres to the invoice-generator CI job** (a `services: postgres`
   block and a `DATABASE_URL`), so the suite runs against the engine production
   uses.
3. **Then** take finding 4 (the payments ledger) and finding 13 (Alembic)
   deliberately, as their own changes, with the gate in place.

Until at least (1) is done, I would treat every push to `main` as a change to a
live payment system and review it as one. After (1) and (2), routine autodeploy
becomes a reasonable posture for this app.

---

## What changed in this pass

**Fixed** (all in the working tree, uncommitted; each fix carries a comment
naming the test that catches it):

| File | Change |
|---|---|
| `app.py` | Webhook: require settled `payment_status`; handle `checkout.session.async_payment_succeeded` |
| `app.py` | `create_app`: refuse to boot in production on the dev secret key |
| `app.py` | `update_invoice`: recompute `status` after an edit changes the total |
| `app.py` | `login`: reject `//` and `/\` in `?next=` |
| `app.py` | `_validate_invoice`: bound discount to 0–100%, reject negative tax/discount and negative totals |
| `app.py` | `export_csv`: neutralise formula injection via new `_csv_safe` |
| `app.py` | `next_invoice_number`: derive from highest issued number, not row count |
| `app.py` | `generate_pdf`: whitelist characters in the filename |
| `app.py` | `public_pay`: add a rate limit |
| `api.py` | `_validate`: mirror the web form's discount/total bounds |

**Added:** `tests/conftest.py` (environment isolation — neutralises any local
`.env` so a test run cannot reach real Stripe, SMTP, or database credentials)
and `tests/test_scenarios.py` (36 scenario tests).

**Not changed:** findings 4, 7, 12, 13, 14, 15, 16 — each has a proposed
approach above. No existing test was weakened or removed.
