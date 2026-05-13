from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@dataclass
class ValidationResult:
    status: str
    blockers: list[str]
    warnings: list[str]
    next_actions: list[str]

    @property
    def can_generate(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict:
        return {"status": self.status, "blockers": self.blockers, "warnings": self.warnings, "next_actions": self.next_actions}

def _blank(v) -> bool:
    return v is None or str(v).strip() == ""

def _num(v) -> float:
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except Exception:
        return 0.0

def _date(v):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(v), fmt).date()
        except Exception:
            pass
    return None

def validate_run(template_path, template_type: str, values: dict, placeholders: list[str], output_folder, subject: str = "", template_text: str = "", overrides: dict | None = None, outlook_requested: bool = False, outlook_available: bool = True, missing_items: list | None = None) -> ValidationResult:
    blockers, warnings = [], []
    path = Path(template_path)
    if not path.exists():
        blockers.append("Selected template cannot be read.")
    try:
        Path(output_folder).mkdir(parents=True, exist_ok=True)
    except Exception:
        blockers.append("Output folder cannot be created.")
    if _blank(values.get("Client Name") or values.get("client name")):
        blockers.append("Client Name is missing.")
    if template_type == "email":
        email = values.get("Client Email") or values.get("client email")
        if _blank(email):
            blockers.append("Client Email is missing for this email template.")
        elif not EMAIL_RE.match(str(email)):
            blockers.append("Client Email is invalid for this email template.")
        if _blank(subject):
            blockers.append("Email template has no subject line.")
    for field in placeholders:
        if _blank(values.get(field)) and _blank(values.get(field.lower())):
            blockers.append(f"Required placeholder value is blank: {field}.")
    lower_name = path.name.lower()
    if any(word in lower_name for word in ["old", "draft", "copy", "deprecated"]):
        warnings.append("Template file name suggests it may be old, draft, copy, or deprecated.")
    if not placeholders:
        warnings.append("Template has no placeholders.")
    if "engagement" in lower_name and _num(values.get("Fee Amount") or values.get("fee amount")) == 0:
        warnings.append("Fee Amount is zero or blank for this engagement letter.")
    if "invoice" in lower_name:
        if _blank(values.get("Invoice Number") or values.get("invoice number")):
            blockers.append("Invoice Number is missing for this invoice email.")
        if _blank(values.get("Invoice Amount") or values.get("invoice amount")):
            blockers.append("Invoice Amount is missing for this invoice email.")
        if _blank(values.get("Payment Link") or values.get("payment link")):
            warnings.append("Payment Link is missing for this invoice email.")
    if "missing document" in lower_name or "missing" in lower_name:
        manual = values.get("Missing Items") or values.get("missing items")
        if not missing_items and _blank(manual):
            blockers.append("No missing items found and no manual missing items entered.")
    due = _date(values.get("Due Date") or values.get("due date"))
    if due:
        days = (due - date.today()).days
        if days < 0:
            warnings.append("Due Date is in the past.")
        elif days <= 7:
            warnings.append("Due Date is within 7 days.")
    if overrides:
        warnings.append("User manually overrode one or more auto-filled values.")
    if outlook_requested and not outlook_available:
        warnings.append("Outlook draft creation is requested but Outlook integration is unavailable; fallback files will be generated.")
    status = "Blocked" if blockers else ("Needs Review" if warnings else "Ready")
    next_actions = ["Resolve blockers before generating output."] if blockers else (["Review warnings, then generate if acceptable."] if warnings else ["Ready to generate output package."])
    return ValidationResult(status, blockers, warnings, next_actions)
