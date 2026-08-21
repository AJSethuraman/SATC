# Invoicer — Design Package

Self-hosted invoicing for freelancers and small firms. Complete, implementable
design system + screens. **Vanilla CSS, no build step, Jinja-friendly, WCAG AA.**

Open **`index.html`** for the visual hub linking every artifact + the design rationale.

## File map

```
invoicer/
├── index.html                     ← start here: hub + rationale
├── Invoicer Design System.html    ← living style guide (color, type, spacing, components)
├── static/
│   └── css/
│       └── style.css              ← THE stylesheet for the whole web UI
└── templates/                     ← one file per Flask route, sample data inline
    ├── landing.html               ← marketing landing page
    ├── login.html                 ← split-screen auth
    ├── signup.html                ← account creation
    ├── invoices.html              ← invoice history (dashboard: KPIs, filters, table)
    ├── invoice_form.html          ← create/edit, dynamic line items + live totals (vanilla JS)
    ├── invoice_detail.html        ← read view: paper preview, status, activity timeline
    ├── account.html               ← Connect Stripe status, API key, business profile
    ├── invoice_pdf.html           ← INVOICE PDF — table-based, A4, both engines, logo + no-logo
    └── email_invoice.html         ← transactional invoice email (table-based HTML email)
```

## Wiring it into Flask/Jinja

- Web pages link the stylesheet at `static/css/style.css`. In Jinja use
  `{{ url_for('static', filename='css/style.css') }}`.
- Each template uses literal sample data so it previews on its own — replace the
  literals with `{{ variables }}` and `{% for %}` loops.
- Fonts: Hanken Grotesk (UI) + JetBrains Mono (figures/IDs), loaded from Google
  Fonts in each `<head>`. Self-host them if you'd rather not hit a CDN.

### The invoice PDF (most important constraint)

`templates/invoice_pdf.html` is **self-contained** (its own `<style>`, no external
CSS) and uses **table-based layout, inline-safe CSS, no flexbox/grid/absolute
positioning** so it renders identically in:

- **WeasyPrint** (primary)
- **xhtml2pdf** (fallback)

It's A4, embeds the logo as a base64 data URI (`{{ business.logo_uri }}`), and
falls back to a typographic wordmark when no logo is set. Screen-only chrome
(grey backdrop, shadow, captions) is hidden via `@media print` and `.screen-only`.

```python
from weasyprint import HTML
html = render_template("invoice_pdf.html", invoice=inv, business=biz)
pdf  = HTML(string=html).write_pdf()        # primary
# fallback: xhtml2pdf.pisa.CreatePDF(html, dest=buffer)
```

The file ships **two variants** stacked (with-logo / no-logo) for preview — in
production you render one, driven by `{% if business.logo_uri %}`.

## Accessibility

- Primary action blue `#2563eb` passes AA (5.1:1) with white text.
- Lighter `#3b82f6` is used only for hovers/tints/focus rings (non-load-bearing).
- Visible focus rings via `:focus-visible`. Responsive down to mobile.

## Tokens (quick reference)

| Role            | Value                                   |
|-----------------|-----------------------------------------|
| Navy (brand)    | `#1f2a44`                               |
| Action blue     | `#2563eb` (hover `#1d4ed8`)             |
| Ink (text)      | `#0f1729`                               |
| Paid / Overdue  | `#16a34a` / `#dc2626`                    |
| Neutrals        | slate ramp `#f8fafc → #0f172a`          |
| UI / Mono font  | Hanken Grotesk / JetBrains Mono         |
| Spacing base    | 4px scale                               |
| Radius          | 6 / 10 / 16 / full                       |
