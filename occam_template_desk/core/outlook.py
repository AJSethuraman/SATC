from __future__ import annotations

import json
import platform
from pathlib import Path

class OutlookDraftService:
    def is_available(self) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import win32com.client  # noqa: F401
            return True
        except Exception:
            return False

    def create_draft(self, to: str, subject: str, body: str, html_body: bool = False, attachments: list[str] | None = None, output_dir: str | Path | None = None) -> dict:
        attachments = attachments or []
        if not self.is_available():
            return self.fallback_status(output_dir, "Outlook or pywin32 is unavailable.")
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.Subject = subject
        if html_body:
            mail.HTMLBody = body
        else:
            mail.Body = body
        for attachment in attachments:
            mail.Attachments.Add(str(Path(attachment).resolve()))
        mail.Save()
        mail.Display(False)
        return {"attempted": True, "created": True, "mode": "local_outlook", "message": "Outlook draft created and opened. Nothing was sent."}

    def fallback_status(self, output_dir: str | Path | None, reason: str) -> dict:
        status = {"attempted": True, "created": False, "mode": "fallback_files", "message": reason, "safe_note": "No email was sent."}
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            (Path(output_dir) / "outlook_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status
