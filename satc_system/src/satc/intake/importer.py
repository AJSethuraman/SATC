"""Smart client import — turn a roster (CSV, Drake export, paste) into clients.

One engine feeds every import path the practice picked:

  * **CSV / spreadsheet** upload — flexible header matching (first/last/name,
    legal/company name, ssn/ein/tin, email, phone, state, entity type).
  * **Drake / prior-year export** — the same engine; Drake's client export is just
    a CSV with its own column names, which the header matcher already understands.
  * **Smarter single-add** — :func:`parse_one` applies the same person/business
    detection and TIN normalization to a single typed entry.

For each row it: detects person vs business (explicit column or name hints like
"LLC"/"Inc"), normalizes the SSN/EIN, infers entity/return type, and flags likely
duplicates against the existing client list. Nothing is created here — the caller
previews the result, then commits.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

# Header aliases -> canonical field. Lowercased, non-alphanumerics stripped on match.
_HEADER_ALIASES: dict[str, str] = {
    "first": "first_name", "firstname": "first_name", "fname": "first_name",
    "last": "last_name", "lastname": "last_name", "lname": "last_name", "surname": "last_name",
    "name": "name", "clientname": "name", "fullname": "name", "taxpayer": "name",
    "legalname": "legal_name", "company": "legal_name", "companyname": "legal_name",
    "businessname": "legal_name", "entityname": "legal_name", "business": "legal_name",
    "ssn": "tin", "ein": "tin", "tin": "tin", "taxid": "tin", "ssnein": "tin",
    "ssnorein": "tin", "ssneinortin": "tin", "socialsecurity": "tin", "id": "tin",
    "email": "email", "emailaddress": "email", "e": "email",
    "phone": "phone", "phonenumber": "phone", "telephone": "phone", "mobile": "phone", "cell": "phone",
    "state": "state", "homestate": "state", "residentstate": "state", "st": "state",
    "type": "entity_type", "entitytype": "entity_type", "clienttype": "entity_type",
    "entity": "entity_type", "returntype": "entity_type", "filingtype": "entity_type",
}

# Tokens in a name that signal a business entity (and, where clear, its type).
_BUSINESS_TOKENS = ("llc", "l.l.c", "inc", "incorporated", "corp", "corporation", "co.",
                    "company", "ltd", "limited", "lp", "llp", "pllc", "pc", "p.c",
                    "partners", "partnership", "associates", "group", "holdings",
                    "enterprises", "trust", "foundation", "&")

_ENTITY_MAP = {
    "scorp": "SCORP", "scorporation": "SCORP", "s": "SCORP", "1120s": "SCORP", "1120-s": "SCORP",
    "partnership": "PARTNERSHIP", "1065": "PARTNERSHIP", "llp": "PARTNERSHIP", "lp": "PARTNERSHIP",
    "ccorp": "CCORP", "ccorporation": "CCORP", "c": "CCORP", "1120": "CCORP", "corporation": "CCORP",
    "individual": "INDIVIDUAL", "person": "INDIVIDUAL", "1040": "INDIVIDUAL",
}


@dataclass(slots=True)
class ParsedClient:
    """One previewed import row — detected, normalized, and dedup-checked."""

    kind: str = "person"                 # "person" | "business"
    first_name: str = ""
    last_name: str = ""
    legal_name: str = ""
    entity_type: str = "INDIVIDUAL"      # vault EntityType
    tin: str = ""                        # digits only (vault stores; mart masks)
    email: str = ""
    phone: str = ""
    state: str = ""
    status: str = "new"                  # "new" | "duplicate" | "review"
    issues: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.legal_name if self.kind == "business" else f"{self.first_name} {self.last_name}".strip()

    @property
    def tin_last4(self) -> str:
        return self.tin[-4:] if len(self.tin) >= 4 else ""


def _norm_key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (header or "").lower())


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def looks_like_business(name: str) -> bool:
    low = f" {(name or '').lower()} "
    return any(tok in low for tok in _BUSINESS_TOKENS)


def _infer_entity_type(name: str, explicit: str) -> str:
    key = _norm_key(explicit)
    if key in _ENTITY_MAP:
        return _ENTITY_MAP[key]
    low = (name or "").lower()
    if any(t in low for t in (" lp", " llp", "partners", "partnership")):
        return "PARTNERSHIP"
    return "SCORP"                       # most common small-business default


def _remap_row(row: dict) -> dict:
    """Map arbitrary CSV headers onto canonical fields."""
    out: dict[str, str] = {}
    for header, value in row.items():
        canon = _HEADER_ALIASES.get(_norm_key(header))
        if canon and str(value or "").strip():
            out[canon] = str(value).strip()
    return out


def _build(row: dict) -> ParsedClient:
    """Turn one canonicalized row into a detected, normalized ParsedClient."""
    name = row.get("name", "")
    explicit_type = row.get("entity_type", "")
    has_business_signal = bool(row.get("legal_name")) or _norm_key(explicit_type) in (
        "scorp", "partnership", "ccorp", "business", "1120s", "1065", "1120")
    is_business = has_business_signal or (not row.get("first_name") and looks_like_business(name))

    pc = ParsedClient()
    pc.tin = _digits(row.get("tin", ""))
    pc.email = row.get("email", "")
    pc.phone = row.get("phone", "")
    pc.state = row.get("state", "").upper()[:2]

    if is_business:
        pc.kind = "business"
        pc.legal_name = row.get("legal_name") or name
        pc.entity_type = _infer_entity_type(pc.legal_name, explicit_type)
        if not pc.legal_name:
            pc.issues.append("missing business name")
    else:
        pc.kind = "person"
        pc.entity_type = "INDIVIDUAL"
        if row.get("first_name") or row.get("last_name"):
            pc.first_name, pc.last_name = row.get("first_name", ""), row.get("last_name", "")
        elif name:
            parts = name.replace(",", " ").split()
            pc.first_name = parts[0] if parts else ""
            pc.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not (pc.first_name or pc.last_name):
            pc.issues.append("missing name")

    if pc.tin and len(pc.tin) != 9:
        pc.issues.append(f"TIN has {len(pc.tin)} digits (expected 9)")
    return pc


def _mark_duplicates(parsed: list[ParsedClient],
                     existing: list[tuple[str, str]] | None) -> None:
    """Flag rows that match an existing client (by name) or repeat within the batch."""
    seen_names = {name.lower() for name, _ in (existing or [])}
    seen_last4 = {l4 for _, l4 in (existing or []) if l4}
    batch: set[str] = set()
    for pc in parsed:
        key = pc.display_name.lower()
        if key in seen_names or (pc.tin_last4 and pc.tin_last4 in seen_last4) or key in batch:
            pc.status = "duplicate"
        elif pc.issues:
            pc.status = "review"
        batch.add(key)


def parse_rows(rows: list[dict], *, existing: list[tuple[str, str]] | None = None) -> list[ParsedClient]:
    """Parse already-dict rows (e.g. from a spreadsheet) into previewed clients."""
    parsed = [_build(_remap_row(r)) for r in rows if any(str(v or "").strip() for v in r.values())]
    _mark_duplicates(parsed, existing)
    return parsed


def parse_csv(text: str, *, existing: list[tuple[str, str]] | None = None) -> list[ParsedClient]:
    """Parse raw CSV text (a spreadsheet 'Save as CSV', or a Drake client export)."""
    reader = csv.DictReader(io.StringIO(text))
    return parse_rows(list(reader), existing=existing)


def parse_one(*, name: str = "", first_name: str = "", last_name: str = "",
              tin: str = "", entity_type: str = "", email: str = "", phone: str = "",
              state: str = "") -> ParsedClient:
    """Smart single-add: detect + normalize one typed entry (no dedup)."""
    row = {"name": name, "first_name": first_name, "last_name": last_name, "tin": tin,
           "entity_type": entity_type, "email": email, "phone": phone, "state": state}
    return _build({k: v for k, v in row.items() if v})


# A ready-to-use template so the user knows what columns to provide.
CSV_TEMPLATE = ("name,entity_type,ssn_or_ein,email,phone,state\n"
                "Dana Reyes,individual,123-45-6789,dana@example.com,555-0142,OH\n"
                "Reyes Studio LLC,s-corp,31-0009999,info@reyesstudio.com,555-0188,OH\n")
