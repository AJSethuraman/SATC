from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
SETTINGS_PATH = REPO_ROOT / "occam_settings.json"

@dataclass
class OccamSettings:
    data_workbook_path: str
    template_folder_path: str
    output_folder_path: str
    client_sheet_name: str = "Clients"
    client_match_field: str = "Client ID"
    default_firm_name: str = "Occam Advisors"
    default_tax_year: str = "2025"
    outlook_draft_mode: str = "fallback_files"

    @classmethod
    def defaults(cls) -> "OccamSettings":
        return cls(
            data_workbook_path=str(PACKAGE_ROOT / "sample_data" / "Occam_Data.xlsx"),
            template_folder_path=str(PACKAGE_ROOT / "sample_templates"),
            output_folder_path=str(PACKAGE_ROOT / "output"),
        )

def ensure_default_settings(path: str | Path = SETTINGS_PATH) -> OccamSettings:
    path = Path(path)
    if not path.exists():
        settings = OccamSettings.defaults()
        save_settings(settings, path)
        return settings
    return load_settings(path)

def load_settings(path: str | Path = SETTINGS_PATH) -> OccamSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(data, dict):
            data = {}
    except (OSError, json.JSONDecodeError):
        data = {}
    defaults = asdict(OccamSettings.defaults())
    defaults.update(data)
    allowed = set(defaults)
    return OccamSettings(**{key: value for key, value in defaults.items() if key in allowed})

def save_settings(settings: OccamSettings, path: str | Path = SETTINGS_PATH) -> None:
    path = Path(path)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    Path(settings.output_folder_path).mkdir(parents=True, exist_ok=True)
