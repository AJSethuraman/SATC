"""PDF generation using a Jinja2 HTML template rendered by WeasyPrint."""
from pathlib import Path

from flask import render_template
from weasyprint import HTML


def render_invoice_pdf(invoice, output_path, logo_path=None):
    """Render ``invoice`` to a PDF file at ``output_path``.

    ``logo_path`` is an optional absolute filesystem path to the uploaded
    logo, embedded into the document via a ``file://`` URL.
    """
    logo_url = None
    if logo_path and Path(logo_path).exists():
        logo_url = Path(logo_path).resolve().as_uri()

    html_string = render_template(
        "invoice_pdf.html", invoice=invoice, logo_url=logo_url
    )
    # base_url lets WeasyPrint resolve any relative static asset references.
    HTML(string=html_string, base_url=str(Path(output_path).parent)).write_pdf(
        str(output_path)
    )
    return output_path
