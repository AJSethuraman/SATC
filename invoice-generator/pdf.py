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
"""
import base64
import mimetypes
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


def _logo_data_uri(logo_path):
    """Return a base64 data URI for the logo (used by xhtml2pdf)."""
    if not logo_path or not Path(logo_path).exists():
        return None
    mime = mimetypes.guess_type(str(logo_path))[0] or "image/png"
    # xhtml2pdf (ReportLab) can't rasterize SVG; skip it gracefully.
    if mime == "image/svg+xml":
        return None
    data = base64.b64encode(Path(logo_path).read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _render_with_weasyprint(invoice, output_path, logo_path):
    from weasyprint import HTML

    logo_url = None
    if logo_path and Path(logo_path).exists():
        logo_url = Path(logo_path).resolve().as_uri()
    html_string = render_template(
        "invoice_pdf.html", invoice=invoice, logo_url=logo_url
    )
    HTML(string=html_string, base_url=str(Path(output_path).parent)).write_pdf(
        str(output_path)
    )


def _render_with_xhtml2pdf(invoice, output_path, logo_path):
    from xhtml2pdf import pisa

    html_string = render_template(
        "invoice_pdf_xhtml2pdf.html",
        invoice=invoice,
        logo_data_uri=_logo_data_uri(logo_path),
    )
    with open(output_path, "wb") as fh:
        result = pisa.CreatePDF(html_string, dest=fh, encoding="utf-8")
    if result.err:
        raise RuntimeError("xhtml2pdf failed to render the invoice PDF.")


def render_invoice_pdf(invoice, output_path, logo_path=None):
    """Render ``invoice`` to a PDF at ``output_path`` using the active engine.

    Raises ``RuntimeError`` (not a bare import/OS error) if the selected
    engine can't run, so callers can surface a clean message.
    """
    engine = _select_engine()
    try:
        if engine == "xhtml2pdf":
            _render_with_xhtml2pdf(invoice, output_path, logo_path)
        else:
            _render_with_weasyprint(invoice, output_path, logo_path)
    except RuntimeError:
        raise
    except ImportError as exc:
        raise RuntimeError(
            f"PDF engine '{engine}' is not installed. Run the setup script "
            f"(run.ps1) or `pip install -r requirements.txt`. ({exc})"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint could not load its native libraries. On Windows use "
            "run.ps1 (it falls back to the pure-Python engine automatically); "
            f"on Linux install libpango/cairo. ({exc})"
        ) from exc
    return output_path
