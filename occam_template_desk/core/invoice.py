from __future__ import annotations

from .template_scanner import normalize_field_name

INVOICE_FIELDS = {
    "invoice number",
    "invoice amount",
    "invoice date",
    "due date",
    "service description",
}


def template_requires_invoice(placeholders: list[str], template_name: str = "") -> bool:
    normalized = {normalize_field_name(field) for field in placeholders}
    return bool(normalized & INVOICE_FIELDS) or "invoice" in template_name.lower()


def invoice_selection_state(invoices: list[dict], requires_invoice: bool) -> dict:
    if not requires_invoice:
        return {"status": "not_required", "selected_invoice": None, "requires_user_selection": False, "message": "Invoice selection is not required for this template."}
    if not invoices:
        return {"status": "none", "selected_invoice": None, "requires_user_selection": False, "message": "No invoices found for this client."}
    if len(invoices) == 1:
        return {"status": "auto_selected", "selected_invoice": invoices[0], "requires_user_selection": False, "message": "One invoice found and auto-selected."}
    return {"status": "multiple", "selected_invoice": None, "requires_user_selection": True, "message": "Multiple invoices found; select the invoice for this run."}
