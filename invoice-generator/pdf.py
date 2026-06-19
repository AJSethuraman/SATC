"""PDF generation using a Jinja2 HTML template rendered by WeasyPrint.

WeasyPrint is imported lazily inside :func:`render_invoice_pdf` so the rest of
the app (the web GUI, history, etc.) still starts even if WeasyPrint's native
libraries (GTK/Pango on Windows) aren't installed yet. Only PDF generation
fails in that case, with a clear, actionable message.
"""
from pathlib import Path

from flask import render_template


def render_invoice_pdf(invoice, output_path, logo_path=None):
    """Render ``invoice`` to a PDF file at ``output_path``.

    ``logo_path`` is an optional absolute filesystem path to the uploaded
    logo, embedded into the document via a ``file://`` URL.
    """
    try:
        from weasyprint import HTML
    except OSError as exc:  # native libs (GTK/Pango/Cairo) missing
        raise RuntimeError(
            "PDF engine not ready: WeasyPrint could not load its native "
            "libraries. On Windows, run run.ps1 to install the GTK runtime "
            "(or install GTK3 manually); on Linux install libpango/cairo. "
            f"Original error: {exc}"
        ) from exc

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
