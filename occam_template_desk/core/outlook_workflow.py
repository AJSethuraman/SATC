from __future__ import annotations

from pathlib import Path

from .outlook import OutlookDraftService


def create_outlook_draft_if_allowed(validation, mode: str, email_rendered: dict, values: dict, attachments: list[str] | None = None, service: OutlookDraftService | None = None, output_dir: str | Path | None = None) -> dict:
    """Create a draft only when explicitly allowed; never sends email."""
    if getattr(validation, "blockers", None):
        return {"attempted": False, "created": False, "mode": mode, "message": "Blocked validation prevents Outlook draft creation.", "safe_note": "No email was sent."}
    if mode != "local_outlook":
        return {"attempted": False, "created": False, "mode": mode, "message": "Outlook draft mode is not local_outlook.", "safe_note": "No email was sent."}
    service = service or OutlookDraftService()
    body = email_rendered.get("body", "")
    body_path = str(email_rendered.get("body_path", ""))
    html_body = Path(body_path).suffix.lower() == ".html"
    if not service.is_available():
        return service.fallback_status(output_dir, "Outlook or pywin32 is unavailable; copy-ready files were generated.")
    return service.create_draft(
        to=values.get("Client Email", ""),
        subject=email_rendered.get("subject", ""),
        body=body,
        html_body=html_body,
        attachments=attachments or [],
        output_dir=output_dir,
    )
