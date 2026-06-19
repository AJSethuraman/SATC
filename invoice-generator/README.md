# Invoicer — Python Invoice Generator

A clean, self-hosted invoice generator built with Flask. Create professional
invoices through a web GUI, generate polished PDFs, track them in a local
database, collect payments via Stripe Checkout, email invoices to clients, and
drive everything programmatically through a token-protected JSON API.

This is an independent implementation. It does **not** use or depend on
Invoice-Generator.com's API, code, branding, or design.

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
cp .env.example .env        # optional: add Stripe / SMTP / API_KEY values
docker compose up           # add --build the first time or after changes
```

Open **http://localhost:5000**. The SQLite database, generated PDFs, and
uploaded logos persist in Docker named volumes across restarts.

To stop: `Ctrl-C`, then `docker compose down` (add `-v` to also wipe the
stored data).

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

The database and tables are created automatically on first run. For
auto-reload during development use `flask --app app run --debug`.

## Features

- **Web GUI** — invoice form with from/business, bill-to, optional ship-to,
  invoice number, date, payment terms, due date, PO number, currency, line
  items (description/qty/rate/amount), tax, discount, shipping, amount paid,
  notes, terms, and optional logo upload.
- **Dynamic line items** — add/remove rows with live in-browser total updates.
- **Accurate math** — subtotal, flat or percentage discount, flat or
  percentage tax (applied after discount), shipping, total, and balance due.
- **Professional PDF** rendered from an HTML/CSS template via Jinja2 + WeasyPrint.
- **SQLite persistence** through SQLAlchemy. Generated PDFs are saved to
  `invoices/`.
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

Flask · Jinja2 · WeasyPrint or xhtml2pdf (PDF) · SQLite · SQLAlchemy ·
Stripe Python SDK · Gunicorn · Docker · custom navy/gray/white CSS · vanilla
JS for dynamic rows.

## Project layout

```
invoice-generator/
├── app.py              # Flask app factory + web routes
├── api.py              # JSON REST API blueprint
├── config.py           # Environment-driven configuration
├── models.py           # SQLAlchemy models + total calculations
├── helpers.py          # Currency formatting & form parsing
├── pdf.py              # WeasyPrint PDF rendering
├── stripe_utils.py     # Stripe Checkout + webhook helpers
├── email_utils.py      # SMTP email sending
├── templates/          # Jinja2 templates (UI + PDF)
├── static/             # CSS, JS, uploaded logos
├── invoices/           # Generated PDFs (gitignored)
├── tests/              # Calculation unit tests
├── run.ps1             # Windows one-shot setup & run (PowerShell)
├── Dockerfile          # Single-image build with native deps baked in
├── docker-compose.yml  # One-command run + persistent volumes
└── requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and fill in what you need. The app runs fine with
none of these set — Stripe, email, and the API stay disabled until configured.

| Variable                 | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `FLASK_SECRET_KEY`       | Flask session signing key                            |
| `APP_BASE_URL`           | Public base URL (Stripe redirects, API PDF links)    |
| `API_KEY`                | Token for the JSON API; blank = API disabled (503)   |
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

Set `API_KEY` in `.env` to enable it. Every `/api/*` call (except
`/api/health`) requires an `X-API-Key` header matching that value; without a
configured key the API returns **503**, and with a wrong key **401**.

| Method & path                          | Description                          |
|----------------------------------------|--------------------------------------|
| `GET /api/health`                      | Liveness probe (no auth)             |
| `POST /api/invoices`                   | Create an invoice                    |
| `GET /api/invoices`                    | List all invoices                    |
| `GET /api/invoices/{id}`               | Fetch one invoice                    |
| `DELETE /api/invoices/{id}`            | Delete an invoice                    |
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
- Uploaded logos are stored under `static/uploads/` and embedded into the PDF.
- The JSON API is disabled unless `API_KEY` is set, so it's never accidentally
  public.
- If you deploy this publicly, serve over HTTPS, set a strong `FLASK_SECRET_KEY`
  and `API_KEY`, and review data-protection obligations.
```
