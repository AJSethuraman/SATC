"""A rendered comms draft as an HTML email.

Only drafts with a payment QR code go out as HTML -- the code is a picture, and
plain text cannot carry one. Everything else stays plain text, as before.
"""

from __future__ import annotations

import html as _html
import io
import re

from satc.comms.render import QR_MARKER

#: The id the QR image is attached under; the HTML refers to ``cid:payqr``.
QR_CID = "payqr"

_BULLET = re.compile(r"^\s*[•\-\*]\s+")
_NUMBER = re.compile(r"^\s*(\d+)\.\s+")
_LINK = re.compile(r"https?://[^\s<>\"]+[^\s<>\".,;:)]")
# The signature starts at the sign-off and keeps its line breaks.
_SIGNOFF = re.compile(r"^(Thank you,|Sincerely,|Best,|Regards,)\s*$", re.M)


def qr_png(url: str) -> bytes:
    """The payment link as a PNG QR code (error correction M: a smudge still scans)."""
    import segno

    buf = io.BytesIO()
    segno.make(url, error="m", micro=False).save(
        buf, kind="png", scale=8, border=2, dark="#132437")
    return buf.getvalue()


def _inline(text: str) -> str:
    """Escape ``text`` and make its links clickable."""
    return _LINK.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>',
                     _html.escape(text, quote=False))


def _block(block: str) -> str:
    """One blank-line-separated block: a bulleted list, a numbered list, or a paragraph."""
    lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
    if all(_BULLET.match(ln) for ln in lines):
        return "<ul>" + "".join(f"<li>{_inline(_BULLET.sub('', ln))}</li>" for ln in lines) + "</ul>"
    if _NUMBER.match(lines[0]):
        items: list[str] = []
        for ln in lines:
            if _NUMBER.match(ln):
                items.append(_NUMBER.sub("", ln).strip())
            else:                                  # a wrapped continuation line
                items[-1] += " " + ln.strip()
        return "<ol>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ol>"
    # The template is hard-wrapped for reading on disk; the email reflows.
    return "<p>" + _inline(" ".join(ln.strip() for ln in lines)) + "</p>"


def to_html(body: str, *, qr_url: str = "") -> str:
    """``body`` (plain text, hard-wrapped) as an HTML email.

    Arial 12pt with real lists, and the signature block in the smaller
    signature font, as the firm set the invoice email in Outlook on
    13 October 2026.
    """
    m = _SIGNOFF.search(body)
    main, sig = (body[:m.start()], body[m.start():]) if m else (body, "")
    parts: list[str] = []
    for block in re.split(r"\n\s*\n", main.strip()):
        if not block.strip():
            continue
        if block.strip() == QR_MARKER:
            if qr_url:
                parts.append(f'<p><a href="{_html.escape(qr_url)}"><img src="cid:{QR_CID}" '
                             f'width="160" height="160" alt="Scan to pay"></a></p>')
            continue
        parts.append(_block(block))
    sig_html = ""
    if sig.strip():
        sig_lines = [ln.strip() for ln in sig.strip().split("\n")
                     if ln.strip() and "DRAFT for preparer review" not in ln]
        sig_html = ('<p style="font-family:Calibri,sans-serif;font-size:11pt">'
                    + "<br>".join(_html.escape(ln, quote=False) for ln in sig_lines) + "</p>")
    return ('<html><body><div style="font-family:Arial,sans-serif;font-size:12pt">'
            + "\n".join(parts) + "</div>" + sig_html + "</body></html>")
