"""Email delivery of invoice PDFs over SMTP.

Credentials come exclusively from configuration / environment variables.
"""
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_invoice_email(config, to_email, invoice, pdf_path, payment_url=None):
    """Send the invoice PDF as an attachment to ``to_email``.

    ``config`` is the Flask app config (or any mapping) providing the SMTP_*
    and FROM_EMAIL settings. Raises ``RuntimeError`` if SMTP is unconfigured.
    """
    host = config.get("SMTP_HOST")
    from_email = config.get("FROM_EMAIL")
    if not host or not from_email:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST and FROM_EMAIL in .env."
        )

    msg = EmailMessage()
    msg["Subject"] = f"Invoice {invoice.invoice_number}"
    msg["From"] = from_email
    msg["To"] = to_email

    body_lines = [
        f"Hello,",
        "",
        f"Please find attached invoice {invoice.invoice_number}.",
    ]
    if payment_url:
        body_lines += ["", f"Pay online here: {payment_url}"]
    body_lines += ["", "Thank you for your business."]
    msg.set_content("\n".join(body_lines))

    pdf_path = Path(pdf_path)
    if pdf_path.exists():
        msg.add_attachment(
            pdf_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )

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
