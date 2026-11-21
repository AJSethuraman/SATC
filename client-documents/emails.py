"""A merged email template -> the parts of an email, and a draft to open.

WHY THIS EXISTS. Two documents stopped being letters on 24 October 2026. The
firm, on both the onboarding letter and the organizer cover letter: "this is
actually supposed to be sent as an email not an attachment." So their templates
are email bodies now -- a ``<div class="email">`` in Arial 12pt with real
lists, the format the firm set in Outlook on 13 October -- and this turns a
merged one into what a mail client needs: a subject, an HTML body, and a plain
text version of the same words for clients whose mail shows no HTML.

A template names its own subject in ``<div class="subject">``, so the subject
is merged from the record like everything else and lives beside the body it
belongs to. It is taken out of the body here.

THE ENCODING IS NOT A DETAIL. Outlook mis-read an LF file with
quoted-printable text on 13 October 2026: it scattered "=" through a client
email, broke its payment link and dropped its image. Drafts written here are
CRLF and base64, the shape that opened cleanly.
"""

from __future__ import annotations

import html as _html
import re
from email.charset import BASE64, Charset
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

_SUBJECT = re.compile(r'\s*<div class="subject">(.*?)</div>', re.S)
_BODY = re.compile(r'<div class="email"[^>]*>(.*)</div>', re.S)


class EmailError(RuntimeError):
    """A template that cannot become an email."""


def is_email(html: str) -> bool:
    """Whether a rendered document is an email body rather than a page."""
    return '<div class="email"' in html


def _text(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment))


def parts(html: str) -> tuple[str, str]:
    """(subject, body html) of a merged email template."""
    m = _SUBJECT.search(html)
    if not m:
        raise EmailError("the email template has no <div class=\"subject\">")
    subject = " ".join(_text(m.group(1)).split())
    return subject, html[:m.start()] + html[m.end():]


def to_plain(html: str) -> str:
    """The HTML body as plain text: paragraphs, bullets, line breaks."""
    body = _BODY.search(html)
    s = body.group(1) if body else html
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "\n• " + _text(m.group(1)).strip(), s, flags=re.S)
    s = re.sub(r"</?ul[^>]*>", "\n", s)
    s = re.sub(r"<p[^>]*>(.*?)</p>", lambda m: "\n\n" + m.group(1).strip(), s, flags=re.S)
    s = _text(s)
    lines = re.sub(r"\n{2,}", "\n\n", "\n".join(ln.rstrip() for ln in s.split("\n"))).split("\n")
    out: list[str] = []
    for ln in lines:
        bullet = ln.startswith("• ")
        if out and bullet and out[-1] == "" and len(out) > 1 and out[-2].startswith("• "):
            out.pop()                      # bullets in one list sit together
        if out and bullet and out[-1] and not out[-1].startswith("• "):
            out.append("")                 # a blank line before a list starts
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def to_eml(subject: str, html: str, plain: str, *, to: str = "", sender: str = "",
           attachments: "list[Path] | tuple[Path, ...]" = (), headers: dict | None = None,
           today=None) -> bytes:
    """An unsent draft: HTML with a plain-text alternative, plus attachments.

    ``X-Unsent: 1`` makes Outlook open it as a draft to send, not a received
    message. CRLF and base64 throughout -- see the module docstring.
    """
    cs = Charset("utf-8")
    cs.body_encoding = BASE64

    def part(text: str, sub: str) -> MIMEText:
        p = MIMEText("", sub)
        p.set_charset(cs)
        p.set_payload(text, cs)
        return p

    alt = MIMEMultipart("alternative")
    alt.attach(part(plain, "plain"))
    alt.attach(part(html, "html"))
    if attachments:
        msg = MIMEMultipart("mixed")
        msg.attach(alt)
        for path in attachments:
            path = Path(path)
            sub = "pdf" if path.suffix.lower() == ".pdf" else "html"
            a = MIMEApplication(path.read_bytes(), _subtype=sub)
            a.add_header("Content-Disposition", "attachment", filename=path.name)
            msg.attach(a)
    else:
        msg = alt
    if to:
        msg["To"] = to
    if sender:
        msg["From"] = sender
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True) if today is None else today
    msg["X-Unsent"] = "1"
    for key, value in (headers or {}).items():
        msg[key] = value
    return msg.as_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
