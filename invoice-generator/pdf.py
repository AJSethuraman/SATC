"""PDF generation from Jinja2 HTML templates.

Two rendering engines are supported so the app works on any platform with no
manual native-library setup:

* **WeasyPrint** - highest-fidelity output; used on Linux/Docker where its
  native libraries (GTK/Pango/Cairo) are available. Renders ``invoice_pdf.html``.
* **xhtml2pdf** - pure-Python (pip only, no native libraries, no downloads);
  the reliable fallback on Windows. Renders the table-based
  ``invoice_pdf_xhtml2pdf.html``.

The engine is chosen by the ``PDF_ENGINE`` config setting:

* ``auto`` (default) - WeasyPrint if its libraries import, otherwise xhtml2pdf.
* ``weasyprint`` / ``xhtml2pdf`` - force a specific engine.

The logo is read from the invoice (stored in the DB) and embedded as a base64
data URI, so PDF rendering needs no filesystem access to uploads.
"""
import base64
from pathlib import Path

from flask import current_app, render_template

_WEASY_AVAILABLE = None


def _weasyprint_available():
    """Return True if WeasyPrint and its native libraries import. Cached."""
    global _WEASY_AVAILABLE
    if _WEASY_AVAILABLE is None:
        try:
            import weasyprint  # noqa: F401

            _WEASY_AVAILABLE = True
        except Exception:
            _WEASY_AVAILABLE = False
    return _WEASY_AVAILABLE


def _select_engine():
    engine = (current_app.config.get("PDF_ENGINE") or "auto").lower()
    if engine == "auto":
        return "weasyprint" if _weasyprint_available() else "xhtml2pdf"
    return engine


def _logo_data_uri(invoice, allow_svg):
    """Return a base64 data URI for the invoice logo, or None."""
    data = getattr(invoice, "logo_data", None)
    if not data:
        return None
    mime = invoice.logo_mimetype or "image/png"
    # ReportLab (xhtml2pdf) can't rasterize SVG; skip it for that engine.
    if mime == "image/svg+xml" and not allow_svg:
        return None
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _render_with_weasyprint(invoice, output_path):
    try:
        from weasyprint import HTML
    except (OSError, ImportError) as exc:
        raise RuntimeError(
            "WeasyPrint could not load its native libraries. On Windows use "
            "run.ps1 (it falls back to the pure-Python engine automatically); "
            f"on Linux install libpango/cairo. ({exc})"
        ) from exc

    html_string = render_template(
        "invoice_pdf.html",
        invoice=invoice,
        logo_data_uri=_logo_data_uri(invoice, allow_svg=True),
    )
    HTML(string=html_string, base_url=str(Path(output_path).parent)).write_pdf(
        str(output_path)
    )


def _render_with_xhtml2pdf(invoice, output_path):
    from xhtml2pdf import pisa

    html_string = render_template(
        "invoice_pdf_xhtml2pdf.html",
        invoice=invoice,
        logo_data_uri=_logo_data_uri(invoice, allow_svg=False),
    )
    with open(output_path, "wb") as fh:
        result = pisa.CreatePDF(html_string, dest=fh, encoding="utf-8")
    if result.err:
        raise RuntimeError("xhtml2pdf failed to render the invoice PDF.")


def render_invoice_pdf(invoice, output_path):
    """Render ``invoice`` to a PDF at ``output_path`` using the active engine.

    Raises ``RuntimeError`` (not a bare import/OS error) if the selected
    engine can't run, so callers can surface a clean message.
    """
    engine = _select_engine()
    try:
        if engine == "xhtml2pdf":
            _render_with_xhtml2pdf(invoice, output_path)
        else:
            _render_with_weasyprint(invoice, output_path)
    except RuntimeError:
        raise
    except ImportError as exc:
        raise RuntimeError(
            f"PDF engine '{engine}' is not installed. Run the setup script "
            f"(run.ps1) or `pip install -r requirements.txt`. ({exc})"
        ) from exc
    except Exception as exc:
        # Any other rendering failure (e.g. a bad image) becomes a clean,
        # surfaced error rather than a 500.
        raise RuntimeError(f"PDF rendering failed: {exc}") from exc
    return output_path
