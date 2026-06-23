"""Email delivery over SMTP (invoice PDFs, verification, password reset).

Mail goes out via the app's shared SMTP / SendGrid sender by default, with the
workspace's address set as Reply-To so client replies reach them. A workspace
can instead configure its own SMTP server (bring-your-own), in which case that
server and From address are used. The send call is logged on both success and
failure (including the SMTP status/response); secrets are never logged.

Credentials come from configuration / per-workspace settings.
"""
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

logger = logging.getLogger("invoicer.email")


def mask_email(addr):
    """Mask the local part of an email so logs don't leak full addresses."""
    addr = (addr or "").strip()
    if "@" not in addr:
        return "***" if addr else ""
    local, _, domain = addr.partition("@")
    return f"{(local[:1] or '')}***@{domain}"


def is_configured(config):
    """True if the shared/app SMTP sender is set up enough to send mail."""
    return bool(config.get("SMTP_HOST") and config.get("FROM_EMAIL"))


def can_send(config, user=None):
    """True if mail can actually be sent for this workspace — via the shared app
    SMTP, or the workspace's own custom SMTP (which requires a workspace-owned
    From address, not just credentials)."""
    return bool(
        is_configured(config) or (user is not None and user.custom_smtp_ready)
    )


def resolve_sender(config, user=None):
    """Resolve the effective From / Reply-To / SMTP server for a workspace.

    - Custom SMTP set on the workspace -> use their server and From address.
    - Otherwise -> the app's shared/authenticated sender, with Reply-To set to
      the workspace's address (sending From an unauthenticated customer domain
      over the shared account would land in spam, so we only change Reply-To).
    """
    from_name = ""
    reply_to = ""
    if user is not None:
        from_name = (user.email_from_name or user.business_name or "").strip()
        reply_to = (
            user.email_reply_to
            or user.email_from_email
            or user.business_email
            or ""
        ).strip()

    # Only send via the workspace's own SMTP when it has a workspace-owned From
    # address — never relay the app's shared FROM_EMAIL through a customer's
    # server (providers reject it and clients see the wrong sender). If custom
    # SMTP is set without a From, fall through to the shared sender below.
    if user is not None and user.custom_smtp_ready:
        return {
            "host": user.smtp_host,
            "port": int(user.smtp_port or 587),
            "username": user.smtp_username,
            "password": user.smtp_password,
            "use_tls": True,
            "from_email": (user.email_from_email or user.business_email).strip(),
            "from_name": from_name or "Invoicer",
            "reply_to": reply_to,
            "via": "custom-smtp",
        }
    return {
        "host": config.get("SMTP_HOST"),
        "port": int(config.get("SMTP_PORT", 587)),
        "username": config.get("SMTP_USERNAME"),
        "password": config.get("SMTP_PASSWORD"),
        "use_tls": config.get("SMTP_USE_TLS", True),
        "from_email": config.get("FROM_EMAIL"),
        "from_name": from_name or "Invoicer",
        "reply_to": reply_to,
        "via": "shared",
    }


def _deliver(sender, msg, to_email):
    """Send a prepared message via the resolved sender.

    Logs the attempt, success (with any refused recipients), and failure (with
    the SMTP status code/response), and re-raises on failure so callers never
    silently swallow it. Usernames/passwords are never logged.
    """
    host = sender.get("host")
    from_email = sender.get("from_email")
    if not host or not from_email:
        raise RuntimeError("Email is not configured (no SMTP host / from address).")

    msg["From"] = formataddr((sender.get("from_name") or "", from_email))
    if sender.get("reply_to"):
        msg["Reply-To"] = sender["reply_to"]

    port = int(sender.get("port", 587))
    username = sender.get("username")
    password = sender.get("password")
    use_tls = sender.get("use_tls", True)
    via = sender.get("via", "?")

    logger.info(
        "email send attempt via=%s host=%s:%s from=%s to=%s subject=%r",
        via, host, port, mask_email(from_email), mask_email(to_email),
        msg.get("Subject"),
    )
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                if username:
                    server.login(username, password)
                refused = server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                if username:
                    server.login(username, password)
                refused = server.send_message(msg)
    except smtplib.SMTPException as exc:
        code = getattr(exc, "smtp_code", None)
        resp = getattr(exc, "smtp_error", None)
        if isinstance(resp, bytes):
            resp = resp.decode("utf-8", "replace")
        logger.error(
            "email send FAILED via=%s to=%s smtp_code=%s response=%s error=%s",
            via, mask_email(to_email), code, resp, exc.__class__.__name__,
        )
        raise
    except Exception as exc:
        logger.error(
            "email send FAILED via=%s to=%s error=%s: %s",
            via, mask_email(to_email), exc.__class__.__name__, exc,
        )
        raise

    if refused:
        logger.error(
            "email send refused recipients via=%s refused=%s",
            via, {mask_email(k): v for k, v in refused.items()},
        )
    else:
        logger.info("email send OK via=%s to=%s", via, mask_email(to_email))
    return refused


def send_email(config, to_email, subject, body, user=None):
    """Send a plain-text email (system mail uses the app default sender)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to_email
    msg.set_content(body)
    _deliver(resolve_sender(config, user), msg, to_email)


def send_invoice_email(
    config, to_email, invoice, pdf_path, payment_url=None, html_body=None,
    user=None,
):
    """Send the invoice PDF as an attachment to ``to_email``.

    Always includes a plain-text body (for clients that can't render HTML);
    when ``html_body`` is supplied it's added as the richer alternative. The
    sender identity is resolved from the invoice's workspace.
    """
    if user is None:
        user = getattr(invoice, "owner", None)

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
    _deliver(resolve_sender(config, user), msg, to_email)
