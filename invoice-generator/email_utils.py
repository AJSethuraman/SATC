"""Email delivery over SMTP (invoice PDFs, verification, password reset).

Credentials come exclusively from configuration / environment variables.
"""
import smtplib
from email.message import EmailMessage
from pathlib import Path


def is_configured(config):
    """True if SMTP is set up enough to send mail."""
    return bool(config.get("SMTP_HOST") and config.get("FROM_EMAIL"))


def _deliver(config, msg):
    """Send a prepared EmailMessage via the configured SMTP server."""
    host = config.get("SMTP_HOST")
    from_email = config.get("FROM_EMAIL")
    if not host or not from_email:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST and FROM_EMAIL."
        )
    msg["From"] = from_email
    port = int(config.get("SMTP_PORT", 587))
    username = config.get("SMTP_USERNAME")
    password = config.get("SMTP_PASSWORD")
    use_tls = config.get("SMTP_USE_TLS", True)

    if port == 465:
        with smtplib.SMTP_SSL(host, port) as server:
            if username:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(msg)


def send_email(config, to_email, subject, body):
    """Send a plain-text email."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to_email
    msg.set_content(body)
    _deliver(config, msg)


def send_invoice_email(
    config, to_email, invoice, pdf_path, payment_url=None, html_body=None
):
    """Send the invoice PDF as an attachment to ``to_email``.

    Always includes a plain-text body (for clients that can't render HTML);
    when ``html_body`` is supplied it's added as the richer alternative.
    """
    msg = EmailMessage()
    msg["Subject"] = f"Invoice {invoice.invoice_number}"
    msg["To"] = to_email

    body_lines = [
        "Hello,",
        "",
        f"Please find attached invoice {invoice.invoice_number}.",
    ]
    if payment_url:
        body_lines += ["", f"Pay online here: {payment_url}"]
    body_lines += ["", "Thank you for your business."]
    msg.set_content("\n".join(body_lines))
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    pdf_path = Path(pdf_path)
    if pdf_path.exists():
        # add_attachment on a multipart/alternative message correctly promotes
        # it to multipart/mixed, keeping the text+html alternatives grouped.
        msg.add_attachment(
            pdf_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )
    _deliver(config, msg)
