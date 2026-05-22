from __future__ import annotations

import getpass
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_audit(template_path: str, template_type: str, client: dict, validation: dict, generated_files: list[str], outlook_status: dict | None = None) -> dict:
    path = Path(template_path)
    return {
        "run_id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "template_file_path": str(path),
        "template_name": path.name,
        "template_type": template_type,
        "client_name": client.get("Client Name", ""),
        "client_id": client.get("Client ID", ""),
        "validation_status": validation.get("status", ""),
        "blockers": validation.get("blockers", []),
        "warnings": validation.get("warnings", []),
        "generated_files": generated_files,
        "outlook_draft_status": outlook_status or {"attempted": False, "created": False},
        "environment": {"user": getpass.getuser(), "platform": platform.platform(), "python": platform.python_version()},
    }

def write_json(path: str | Path, data: dict) -> str:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return str(path)
