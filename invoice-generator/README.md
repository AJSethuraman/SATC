# Invoicer — Python Invoice Generator

A clean, self-hosted invoice generator built with Flask. Create professional
invoices, generate polished PDFs, track them in a local database, collect
payments via Stripe Checkout, and email invoices to clients.

This is an independent implementation. It does **not** use or depend on
Invoice-Generator.com's API, code, branding, or design.

## Features

- **Invoice form** with from/business, bill-to, optional ship-to, invoice
  number, date, payment terms, due date, PO number, currency, line items,
  tax, discount, shipping, amount paid, notes, terms, and optional logo upload.
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

## Tech stack

Flask · Jinja2 · WeasyPrint · SQLite · SQLAlchemy · Stripe Python SDK ·
custom navy/gray/white CSS · vanilla JS for dynamic rows.

## Project layout

```
invoice-generator/
├── app.py              # Flask app factory + routes
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
└── requirements.txt
```

## Setup

Requires Python 3.10+. WeasyPrint needs a few native libraries
(Pango, Cairo, GDK-PixBuf). On Debian/Ubuntu:

```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
```

(See the [WeasyPrint install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)
for macOS/Windows instructions.)

Then:

```bash
cd invoice-generator
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env with your values
```

## Run

```bash
flask --app app run
```

Visit http://localhost:5000. The SQLite database (`invoices.db`) and tables
are created automatically on first run.

To run with auto-reload during development:

```bash
flask --app app run --debug
```

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable                 | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `FLASK_SECRET_KEY`       | Flask session signing key                            |
| `APP_BASE_URL`           | Public base URL (used for Stripe redirects/webhook)  |
| `STRIPE_SECRET_KEY`      | Stripe secret key (`sk_test_...` in test mode)       |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (optional)                    |
| `STRIPE_WEBHOOK_SECRET`  | Webhook signing secret (`whsec_...`)                 |
| `SMTP_HOST`              | SMTP server hostname                                 |
| `SMTP_PORT`              | SMTP port (587 STARTTLS, 465 SSL)                    |
| `SMTP_USERNAME`          | SMTP username                                         |
| `SMTP_PASSWORD`          | SMTP password / app password                          |
| `SMTP_USE_TLS`           | `true` to use STARTTLS (ignored for port 465)        |
| `FROM_EMAIL`             | From address for outgoing invoice emails             |

Stripe and email features stay hidden/disabled in the UI until the relevant
variables are set, so the app runs fine with no configuration for local use.

## Stripe Checkout (test mode)

1. Put your test secret key in `.env` as `STRIPE_SECRET_KEY=sk_test_...`.
2. Open an invoice and click **Create Stripe Payment Link**. This creates a
   Checkout Session for the balance due and stores the hosted payment URL on
   the invoice. You're redirected to Stripe's hosted page.
3. Use a [test card](https://stripe.com/docs/testing) such as
   `4242 4242 4242 4242`, any future expiry, and any CVC.

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
4. Complete a test payment (or trigger one manually):
   ```bash
   stripe trigger checkout.session.completed
   ```
   The matching invoice's status flips to **Paid** and its amount paid is set
   to the total.

> Note: a manually triggered event won't carry your invoice's metadata, so it
> won't match a real invoice. To test the full path, create a payment link from
> an invoice and pay it with a test card while `stripe listen` is running.

## Email

With the `SMTP_*` and `FROM_EMAIL` variables set, open an invoice and use the
**Send by Email** panel. The generated PDF is attached and, if a Stripe payment
link exists, it's included in the message body. For Gmail, use an
[App Password](https://support.google.com/accounts/answer/185833) rather than
your account password.

## Tests

```bash
python -m pytest
```

The included tests cover the invoice math (subtotal, flat/percentage discount
and tax, shipping, total, and balance due).

## Notes

- Required fields (from, bill-to, invoice number, at least one line item) are
  validated both client-side before submission and server-side before saving
  or generating a PDF.
- Uploaded logos are stored under `static/uploads/` and embedded into the PDF.
- This project is for general invoicing; if you deploy it publicly, serve over
  HTTPS, set a strong `FLASK_SECRET_KEY`, and review data-protection obligations.
```
