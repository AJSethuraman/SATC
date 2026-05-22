from __future__ import annotations

from pathlib import Path
from typing import Any

from .outlook import OutlookDraftService
from .renderer import detect_unresolved_placeholders


def _validation_status(validation: Any) -> str:
    if isinstance(validation, dict):
        return str(validation.get("status", ""))
    return str(getattr(validation, "status", ""))


def _validation_blockers(validation: Any) -> list:
    if isinstance(validation, dict):
        return validation.get("blockers", []) or []
    return getattr(validation, "blockers", []) or []


def _unresolved_from_validation(validation: Any) -> list[str]:
    if isinstance(validation, dict):
        return validation.get("unresolved_placeholders", []) or []
    return []


def create_outlook_draft_if_allowed(validation, mode: str, email_rendered: dict, values: dict, attachments: list[str] | None = None, service: OutlookDraftService | None = None, output_dir: str | Path | None = None) -> dict:
    """Create a draft only when explicitly allowed; never sends email."""
    status = _validation_status(validation)
    if _validation_blockers(validation) or "blocked" in status.lower() or "do not send" in status.lower():
        return {"attempted": False, "created": False, "mode": mode, "message": "Blocked or Do Not Send validation prevents Outlook draft creation.", "safe_note": "No email was sent."}
    unresolved = sorted(set(_unresolved_from_validation(validation) + detect_unresolved_placeholders(email_rendered.get("subject", "")) + detect_unresolved_placeholders(email_rendered.get("body", ""))))
    if unresolved:
        return {"attempted": False, "created": False, "mode": mode, "message": "Unresolved placeholders prevent Outlook draft creation.", "unresolved_placeholders": unresolved, "safe_note": "No email was sent."}
    if mode != "local_outlook":
        return {"attempted": False, "created": False, "mode": mode, "message": "Outlook draft mode is not local_outlook.", "safe_note": "No email was sent."}
    service = service or OutlookDraftService()
    body = email_rendered.get("body", "")
    body_path = str(email_rendered.get("body_path", ""))
    html_body = Path(body_path).suffix.lower() == ".html"
    attachments = attachments or []
    if not service.is_available():
        status = service.fallback_status(output_dir, "Outlook or pywin32 is unavailable; copy-ready files were generated.")
        status["attachments"] = attachments
        return status
    status = service.create_draft(
        to=values.get("Client Email", ""),
        subject=email_rendered.get("subject", ""),
        body=body,
        html_body=html_body,
        attachments=attachments,
        output_dir=output_dir,
    )
    status["attachments"] = attachments
    return status
