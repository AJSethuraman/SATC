"""Open a pre-written email as a real draft in the user's mail client.

The app runs as a local server on the preparer's own machine, so the server
process can drive the desktop Outlook sitting next to it. On Windows with the
classic Outlook desktop app this uses COM automation (``win32com``) to pop a
compose window with To / Subject / Body — and any attachments (e.g. a client
organizer PDF) — already filled in, ready for the preparer to review and send.

Everywhere COM is unavailable (non-Windows, "new Outlook"/web, or pywin32 not
installed) :func:`open_outlook_draft` returns ``ok=False`` and the caller falls
back to a ``mailto:`` link plus the plain text, so the feature degrades cleanly
instead of breaking.
"""

from __future__ import annotations

import os
import tempfile
import sys
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(slots=True)
class DraftResult:
    """Outcome of attempting to open an Outlook draft."""

    ok: bool
    method: str           # "outlook" when a draft opened; "unavailable" otherwise
    detail: str = ""      # human-readable reason when ``ok`` is False


#: MAPI property: the Content-ID an inline image is referred to by (``cid:...``).
_PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"


def outlook_available() -> bool:
    """Whether driving Outlook via COM is even possible on this machine."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
    except Exception:  # noqa: BLE001 - pywin32 missing / partial install
        return False
    return True


def open_outlook_draft(
    *, to: str = "", subject: str = "", body: str = "",
    attachments: list[str] | None = None,
    html_body: str = "", inline_images: dict[str, bytes] | None = None,
) -> DraftResult:
    """Pop a pre-filled Outlook compose window (Windows + classic Outlook).

    Returns ``DraftResult(ok=True, method="outlook")`` once the draft is shown.
    Any failure (no Windows, no pywin32, Outlook not reachable) returns
    ``ok=False`` with a reason — never raises — so callers can fall back.
    """
    attachments = attachments or []
    if sys.platform != "win32":
        return DraftResult(False, "unavailable",
                           "Outlook automation is only available on Windows.")
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return DraftResult(False, "unavailable",
                           f"The Outlook integration (pywin32) isn't installed ({exc}).")

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        if to:
            mail.To = to
        mail.Subject = subject
        if html_body:
            # AN HTML DRAFT CARRIES PICTURES -- the invoice email's payment QR
            # code (found by Codex on PR #430: as plain text the client saw the
            # marker, not a code). Each image is attached and given the
            # Content-ID the HTML points at, which is what makes Outlook show
            # it in the body instead of listing it as an attachment.
            for cid, data in (inline_images or {}).items():
                fd, tmp = tempfile.mkstemp(suffix=".png", prefix=f"{cid}-")
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                att = mail.Attachments.Add(tmp, 1, 0)
                att.PropertyAccessor.SetProperty(_PR_ATTACH_CONTENT_ID, cid)
            mail.HTMLBody = html_body
        else:
            mail.Body = body
        for path in attachments:
            if path and os.path.exists(path):
                mail.Attachments.Add(os.path.abspath(path))
        mail.Display(False)  # show the draft, don't block the request
        return DraftResult(True, "outlook")
    except Exception as exc:  # noqa: BLE001 - COM/Outlook not reachable
        return DraftResult(False, "unavailable",
                           f"Couldn't reach the Outlook desktop app ({exc}).")
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:  # noqa: BLE001
            pass


def mailto_url(*, to: str = "", subject: str = "", body: str = "") -> str:
    """A ``mailto:`` link that opens the default mail client with fields filled.

    The universal fallback when Outlook COM isn't available. Note that some mail
    clients cap the body length and none support attachments via ``mailto:``.
    """
    params = []
    if subject:
        params.append("subject=" + quote(subject))
    if body:
        params.append("body=" + quote(body))
    query = ("?" + "&".join(params)) if params else ""
    return f"mailto:{quote(to)}{query}"
