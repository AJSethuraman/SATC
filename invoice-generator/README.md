# Invoicer — Python Invoice Generator

A clean, self-hosted invoice generator built with Flask. Sign up for an
account, create professional invoices through a web GUI, generate polished
PDFs, collect payments via Stripe Checkout, email invoices to clients, and
drive everything programmatically through a per-user JSON API. Runs locally on
Windows in one command, or deploys as a hosted website (Docker / Render) with
PostgreSQL.

This is an independent implementation. It does **not** use or depend on
Invoice-Generator.com's API, code, branding, or design.

> **Accounts:** the first thing you'll do is **sign up** at `/signup`. Each
> user only sees their own invoices, and each user gets a personal API key
> (shown on the Account page).

## Quick start (Windows — one PowerShell command)

From this folder, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

`run.ps1` does everything for you and is safe to re-run:

1. Finds Python 3 (installs it via `winget` if it's missing).
2. Creates a local virtual environment in `.venv`.
3. Installs the Python dependencies — **pure pip, no native libraries, no
   admin, no downloads.**
4. Creates `.env` from the template if you don't have one.
5. Starts the app and opens **http://localhost:5000** in your browser.

Stop the app with `Ctrl+C`.

> **PDF engine on Windows:** PDFs are rendered by `xhtml2pdf`, a pure-Python
> engine, so there's nothing extra to install. (On Linux/Docker the app
> automatically uses WeasyPrint for slightly higher-fidelity output — see
> `PDF_ENGINE` below. You can force either engine anywhere by setting
> `PDF_ENGINE=weasyprint` or `PDF_ENGINE=xhtml2pdf`.)

## Quick start (Docker — one command)

The fastest way to run it. Docker bundles every dependency, including the
native libraries WeasyPrint needs for PDF rendering, so there's nothing else
to install.

```bash
cd invoice-generator
cp .env.example .env        # optional: add Stripe / SMTP values
docker compose up           # add --build the first time or after changes
```

Open **http://localhost:5000** and sign up. The SQLite database (including
uploaded logos, which are stored in the DB) persists in a Docker named volume
across restarts.

To stop: `Ctrl-C`, then `docker compose down` (add `-v` to also wipe the
stored data).

## Deploy as a hosted website (Render)

This turns it into a real, public website with HTTPS, PostgreSQL, and a
permanent Stripe webhook — your end users just visit a URL and never run
anything. A `render.yaml` blueprint lives at the repo root.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ajsethuraman/satc)

**One-click path:**

1. Click the button above (sign in / create a free Render account first).
2. Render reads `render.yaml`, builds the app from the `invoice-generator`
   folder, creates a PostgreSQL database, wires `DATABASE_URL`, and generates
   `FLASK_SECRET_KEY`. Click **Apply** — you don't have to fill anything in to
   get it running.
3. When the deploy finishes, open the URL and **sign up**. You can already
   create invoices and download PDFs.

**Then, to take payments** (whenever you're ready):

4. In the **Stripe dashboard → Developers → API keys**, copy your secret and
   publishable keys into the service's Environment in Render
   (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`).
5. In **Stripe → Developers → Webhooks → Add endpoint**, enter
   `https://YOUR-APP.onrender.com/webhook/stripe`, choose the
   `checkout.session.completed` event, then copy its signing secret
   (`whsec_...`) into `STRIPE_WEBHOOK_SECRET`. Save — Render redeploys
   automatically. No Stripe CLI needed in production.

Notes:
- `APP_BASE_URL` is detected automatically from Render's `RENDER_EXTERNAL_URL`,
  so there's nothing to set for redirects to work.
- The image includes WeasyPrint's native libraries, so hosted PDFs use the
  high-fidelity engine (`PDF_ENGINE=weasyprint`, set in the blueprint).
- The blueprint uses Render's **free** web + Postgres tiers so you can try it at
  $0. The free web instance sleeps after inactivity (slow first request) and
  the free database has storage/expiry limits — change the `plan:` values to
  `starter` in `render.yaml` for an always-on production setup.
- Any host that runs a Dockerfile works (Railway, Fly.io, a VPS); just provide
  a Postgres `DATABASE_URL` and the same environment variables.

## Quick start (without Docker)

Requires Python 3.10+. WeasyPrint needs a few native libraries
(Pango, Cairo, GDK-PixBuf). On Debian/Ubuntu:

```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev
```

(See the [WeasyPrint install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)
for macOS/Windows instructions.) Then:

```bash
cd invoice-generator
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env
flask --app app run              # http://localhost:5000
```

The database and tables are created automatically on first run; open
http://localhost:5000 and sign up. For auto-reload during development use
`flask --app app run --debug`.

## Features

- **Accounts** — email/password sign-up and login (hashed passwords); each
  user sees only their own invoices and gets a personal API key.
- **Web GUI** — invoice form with from/business, bill-to, optional ship-to,
  invoice number, date, payment terms, due date, PO number, currency, line
  items (description/qty/rate/amount), tax, discount, shipping, amount paid,
  notes, terms, and optional logo upload.
- **Dynamic line items** — add/remove rows with live in-browser total updates.
- **Accurate math** — subtotal, flat or percentage discount, flat or
  percentage tax (applied after discount), shipping, total, and balance due.
- **Professional PDF** via Jinja2 + WeasyPrint (or pure-Python xhtml2pdf).
- **Persistence** through SQLAlchemy — SQLite locally, PostgreSQL in production.
  Logos are stored in the database; PDFs are regenerated on demand.
- **Invoice history** — view, download PDF, edit, delete, and export the list
  to CSV.
- **Stripe Checkout** — create a hosted payment session for the balance due
  (no raw card handling), store the payment URL on the invoice, surface a
  "Pay online" link on the PDF/email, and mark invoices **Paid** via webhook.
- **Email delivery** — send the invoice PDF over SMTP, including the payment
  link when available.
- **JSON REST API** — create/list/fetch/delete invoices, generate PDFs, and
  create Stripe payment links programmatically (see below).

## Tech stack

Flask · Flask-Login · Jinja2 · WeasyPrint or xhtml2pdf (PDF) · SQLAlchemy ·
SQLite / PostgreSQL · Stripe Python SDK · Gunicorn · Docker · custom
navy/gray/white CSS · vanilla JS for dynamic rows.

## Project layout

```
invoice-generator/
├── app.py                  # Flask app factory, auth + web routes
├── api.py                  # JSON REST API blueprint (per-user keys)
├── config.py               # Environment-driven configuration
├── models.py               # User / Invoice / LineItem + total calculations
├── helpers.py              # Currency formatting & form parsing
├── pdf.py                  # PDF rendering (WeasyPrint / xhtml2pdf dispatch)
├── stripe_utils.py         # Stripe Checkout + webhook helpers
├── email_utils.py          # SMTP email sending
├── templates/              # Jinja2 templates (UI, auth, PDF)
├── static/                 # CSS, JS
├── tests/                  # Calculation unit tests
├── run.ps1                 # Windows one-shot setup & run (PowerShell)
├── Dockerfile              # Single-image build with native deps baked in
├── docker-compose.yml      # One-command local run
├── requirements.txt        # Core dependencies
└── requirements-deploy.txt # + PostgreSQL driver (used by the Docker image)
```

## Environment variables

Copy `.env.example` to `.env` and fill in what you need. The app runs fine with
none of these set — Stripe, email, and the API stay disabled until configured.

| Variable                 | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `FLASK_SECRET_KEY`       | Flask session signing key (use a strong random value)|
| `APP_BASE_URL`           | Public base URL (Stripe redirects, API PDF links)    |
| `APP_ENV`                | `production` enables secure cookies (set when hosted) |
| `DATABASE_URL`           | DB connection; defaults to local SQLite, set Postgres in prod |
| `PDF_ENGINE`             | `auto` (default), `weasyprint`, or `xhtml2pdf`       |
| `STRIPE_SECRET_KEY`      | Stripe secret key (`sk_test_...` in test mode)       |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (optional)                    |
| `STRIPE_WEBHOOK_SECRET`  | Webhook signing secret (`whsec_...`)                 |
| `SMTP_HOST`              | SMTP server hostname                                 |
| `SMTP_PORT`              | SMTP port (587 STARTTLS, 465 SSL)                    |
| `SMTP_USERNAME`          | SMTP username                                         |
| `SMTP_PASSWORD`          | SMTP password / app password                          |
| `SMTP_USE_TLS`           | `true` to use STARTTLS (ignored for port 465)        |
| `FROM_EMAIL`             | From address for outgoing invoice emails             |

## JSON REST API

The API uses **per-user keys**. Sign up, open the **Account** page, and copy
your API key. Send it as the `X-API-Key` header on every `/api/*` call (except
`/api/health`); a wrong/missing key returns **401**. Every request is scoped to
the invoices owned by that key's user.

| Method & path                          | Description                          |
|----------------------------------------|--------------------------------------|
| `GET /api/health`                      | Liveness probe (no auth)             |
| `POST /api/invoices`                   | Create an invoice                    |
| `GET /api/invoices`                    | List your invoices                   |
| `GET /api/invoices/{id}`               | Fetch one of your invoices           |
| `DELETE /api/invoices/{id}`            | Delete one of your invoices          |
| `GET /api/invoices/{id}/pdf`           | Download the invoice PDF             |
| `POST /api/invoices/{id}/payment-link` | Create a Stripe Checkout link        |

### Create an invoice

```bash
curl -X POST http://localhost:5000/api/invoices \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "from_info": "Acme LLC\n1 Road\nTown",
        "bill_to": "Client Co\n2 Street",
        "currency": "USD",
        "items": [
          {"description": "Design work", "quantity": 10, "rate": 100},
          {"description": "Hosting", "quantity": 1, "rate": 50}
        ],
        "tax": {"value": 8.25, "percent": true},
        "discount": {"value": 25, "percent": false},
        "shipping": 15,
        "amount_paid": 100,
        "notes": "Thank you",
        "create_payment_link": true
      }'
```

Notes on the request body:

- Required: `from_info`, `bill_to`, and at least one `items` entry.
- `invoice_number` is optional — omit it to auto-number (`INV-0001`, ...).
- `tax` and `discount` accept either `{"value": N, "percent": true|false}` or a
  bare number (treated as a flat amount). Tax defaults to percentage, discount
  to flat.
- `create_payment_link: true` also creates a Stripe Checkout link (requires
  `STRIPE_SECRET_KEY`). If Stripe isn't configured the invoice is still created
  and a `warnings` array explains why the link was skipped.

### Response (`201 Created`)

```json
{
  "id": 1,
  "invoice_number": "INV-0001",
  "status": "Sent",
  "currency": "USD",
  "subtotal": 1050.0,
  "discount": 25.0,
  "tax": 84.56,
  "shipping": 15.0,
  "total": 1124.56,
  "amount_paid": 100.0,
  "balance_due": 1024.56,
  "stripe_payment_url": "https://checkout.stripe.com/c/pay/...",
  "pdf_url": "http://localhost:5000/api/invoices/1/pdf"
}
```

Validation failures return **422** with a `details` array.

## Stripe Checkout (test mode)

1. Put your test secret key in `.env` as `STRIPE_SECRET_KEY=sk_test_...`.
2. Open an invoice and click **Create Stripe Payment Link** (or pass
   `create_payment_link: true` to the API). This creates a Checkout Session for
   the balance due and stores the hosted payment URL on the invoice.
3. Pay with a [test card](https://stripe.com/docs/testing) such as
   `4242 4242 4242 4242`, any future expiry, any CVC.

### Testing the webhook locally

The webhook route is `POST /webhook/stripe`. It marks an invoice **Paid** when
it receives a verified `checkout.session.completed` event.

1. Install the [Stripe CLI](https://stripe.com/docs/stripe-cli) and log in:
   ```bash
   stripe login
   ```
2. Forward events to your local app:
   ```bash
   stripe listen --forward-to localhost:5000/webhook/stripe
   ```
3. The CLI prints a signing secret (`whsec_...`). Put it in `.env` as
   `STRIPE_WEBHOOK_SECRET=whsec_...` and restart the app.
4. Complete a test payment from an invoice's payment link while `stripe listen`
   is running. The matching invoice flips to **Paid** and its amount paid is set
   to the total.

> A manually `stripe trigger`-ed event won't carry your invoice's metadata, so
> it won't match a real invoice. To test the full path, pay a real Checkout link
> created from an invoice.

## Email

With the `SMTP_*` and `FROM_EMAIL` variables set, open an invoice and use the
**Send by Email** panel. The generated PDF is attached and, if a Stripe payment
link exists, it's included in the message body. For Gmail, use an
[App Password](https://support.google.com/accounts/answer/185833).

## Tests

```bash
python -m pytest
```

The included tests cover the invoice math (subtotal, flat/percentage discount
and tax, shipping, total, and balance due).

## Notes

- Required fields (from, bill-to, invoice number, at least one line item) are
  validated client-side, server-side in the web form, and in the API.
- Each user only sees their own invoices; the API is scoped by the per-user key.
- Uploaded logos are validated (Pillow) and stored in the database, then
  embedded into the PDF as a data URI — nothing is written to a public folder.
- Session cookies are HTTP-only and `SameSite=Lax`, and become Secure when
  `APP_ENV=production`. For a high-traffic public deployment, consider adding
  CSRF tokens (e.g. Flask-WTF) as a further hardening step.
- If you deploy publicly: serve over HTTPS, set a strong `FLASK_SECRET_KEY`,
  use PostgreSQL via `DATABASE_URL`, and review data-protection obligations.

### Upgrading a local database

The schema changed to add accounts and move logos into the DB. If you have an
old local `invoices.db` from a previous version, delete it (it's dev data) and
restart — the new tables are created automatically. Hosted Postgres deployments
start fresh, so this only affects local SQLite files.
