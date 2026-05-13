from __future__ import annotations

from pathlib import Path
from .simple_xlsx import read_xlsx
from .template_scanner import normalize_field_name

class OccamWorkbook:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.sheets = read_xlsx(self.path)

    def rows(self, sheet: str) -> list[dict]:
        return self.sheets.get(sheet, [])

    def settings_dict(self) -> dict:
        return {r.get("Setting", ""): r.get("Value", "") for r in self.rows("Settings")}

    def clients(self, sheet: str = "Clients") -> list[dict]:
        return self.rows(sheet)

    def get_client_by_id(self, client_id: str, sheet: str = "Clients") -> dict:
        for row in self.clients(sheet):
            if str(row.get("Client ID", "")) == str(client_id):
                return row
        return {}

    def get_client_by_name(self, name: str, sheet: str = "Clients") -> dict:
        for row in self.clients(sheet):
            if row.get("Client Name") == name:
                return row
        return {}

    def invoices_for_client(self, client_id: str) -> list[dict]:
        return [r for r in self.rows("Invoices") if str(r.get("Client ID", "")) == str(client_id)]

    def missing_items_for_client(self, client_id: str) -> list[dict]:
        return [r for r in self.rows("Missing Items") if str(r.get("Client ID", "")) == str(client_id)]

    def field_pool_for_client(self, client: dict) -> dict[str, tuple[str, str]]:
        pool: dict[str, tuple[str, str]] = {}
        def add_map(row: dict, source: str):
            for k, v in row.items():
                if v not in (None, ""):
                    pool[normalize_field_name(k)] = (str(v), source)
        add_map(self.settings_dict(), "Settings sheet")
        add_map(client, "Clients table")
        client_id = client.get("Client ID", "")
        invoices = self.invoices_for_client(client_id)
        if invoices:
            add_map(invoices[0], "Invoices table")
        missing = self.missing_items_for_client(client_id)
        if missing:
            items = [m.get("Missing Item", "") for m in missing if str(m.get("Status", "")).lower() != "received"]
            pool[normalize_field_name("Missing Items")] = ("; ".join(items), "Missing Items table")
        return pool
