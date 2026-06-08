#!/usr/bin/env python3
"""Read a filed return packet and detect which forms/returns it contains.

Tax software exports little, but the finished return packet (the PDF print set) is
authoritative. This tool reads each client's packet, finds the form numbers in it
(Form 1040, the schedules, state and local returns), matches the packet to a client
by the name on it, and writes back what was filed:

  * ``services`` -- the billable forms detected (so the invoice bills exactly what was
    prepared, not what was guessed at intake);
  * ``returns`` / ``efiled_returns`` -- the returns by name (Federal / State / local);
  * ``return_filed: true`` -- which lights up the Filing Tracker and dashboard.

Detection is deterministic substring matching on standard form numbers, configured by
an editable ``form_signatures.json`` (so you can add your states/locals). It records
*which* forms were filed, not the refund/balance dollar amounts. Uses PyMuPDF text
extraction (same as the other readers); assistive -- verify against the packet.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import generate_documents
import sort_tax_docs

SIGNATURES_FILENAME = "form_signatures.json"

# Each signature: key (fee-schedule key for billing), label (return name, for returns),
# type ("return" or "form"), and patterns (lowercase substrings that identify it).
_FEDERAL_SIGNATURES: list[dict] = [
    {"key": "base_1040", "label": "Federal Income Tax", "type": "return", "patterns": ["form 1040", "u.s. individual income tax return"]},
    {"key": "amended_1040x", "label": "", "type": "form", "patterns": ["form 1040-x", "form 1040x", "amended u.s. individual income tax"]},
    {"key": "schedule_a", "label": "", "type": "form", "patterns": ["schedule a (form 1040)", "schedule a—itemized", "schedule a - itemized"]},
    {"key": "schedule_b", "label": "", "type": "form", "patterns": ["schedule b (form 1040)", "schedule b—interest", "schedule b - interest"]},
    {"key": "schedule_c", "label": "", "type": "form", "patterns": ["schedule c (form 1040)", "schedule c—profit", "schedule c - profit"]},
    {"key": "schedule_d", "label": "", "type": "form", "patterns": ["schedule d (form 1040)", "schedule d—capital", "schedule d - capital"]},
    {"key": "schedule_e", "label": "", "type": "form", "patterns": ["schedule e (form 1040)", "schedule e—supplemental", "schedule e - supplemental"]},
    {"key": "schedule_se", "label": "", "type": "form", "patterns": ["schedule se (form 1040)", "self-employment tax"]},
    {"key": "schedule_eic", "label": "", "type": "form", "patterns": ["schedule eic", "earned income credit"]},
    {"key": "education_8863", "label": "", "type": "form", "patterns": ["form 8863", "education credits"]},
    {"key": "childcare_2441", "label": "", "type": "form", "patterns": ["form 2441", "child and dependent care expenses"]},
    {"key": "hsa_8889", "label": "", "type": "form", "patterns": ["form 8889", "health savings accounts"]},
    {"key": "additional_ctc_8812", "label": "", "type": "form", "patterns": ["schedule 8812", "credits for qualifying children"]},
    {"key": "energy_5695", "label": "", "type": "form", "patterns": ["form 5695", "residential energy"]},
]

# Resident individual income-tax return form for each state that has one (and DC).
# No-income-tax states (AK, FL, NV, SD, TN, TX, WA, WY, NH) are omitted.
_STATE_FORMS: list[tuple[str, str]] = [
    ("Alabama", "40"), ("Arizona", "140"), ("Arkansas", "AR1000F"), ("California", "540"),
    ("Colorado", "DR 0104"), ("Connecticut", "CT-1040"), ("Delaware", "200-01"),
    ("District of Columbia", "D-40"), ("Georgia", "500"), ("Hawaii", "N-11"), ("Idaho", "40"),
    ("Illinois", "IL-1040"), ("Indiana", "IT-40"), ("Iowa", "IA 1040"), ("Kansas", "K-40"),
    ("Kentucky", "740"), ("Louisiana", "IT-540"), ("Maine", "1040ME"), ("Maryland", "502"),
    ("Massachusetts", "1"), ("Michigan", "MI-1040"), ("Minnesota", "M1"), ("Mississippi", "80-105"),
    ("Missouri", "MO-1040"), ("Montana", "2"), ("Nebraska", "1040N"), ("New Jersey", "NJ-1040"),
    ("New Mexico", "PIT-1"), ("New York", "IT-201"), ("North Carolina", "D-400"), ("North Dakota", "ND-1"),
    ("Ohio", "IT 1040"), ("Oklahoma", "511"), ("Oregon", "OR-40"), ("Pennsylvania", "PA-40"),
    ("Rhode Island", "RI-1040"), ("South Carolina", "SC1040"), ("Utah", "TC-40"), ("Vermont", "IN-111"),
    ("Virginia", "760"), ("West Virginia", "IT-140"), ("Wisconsin", "1"),
]
# Bare 3-digit form numbers that do NOT collide with any federal form (safe to match as
# "form NNN"); others (40, 1, 2, 540->5405, M1) are left to the title-phrase patterns.
_SAFE_NUMERIC_FORMS = {"140", "500", "502", "511", "740", "760"}


def _form_code_pattern(code: str) -> str | None:
    lowered = code.lower()
    if " " in lowered:                                  # e.g. "it 1040", "dr 0104"
        return lowered
    if len(lowered) >= 4 and (any(c.isalpha() for c in lowered) or "-" in lowered):
        return lowered                                  # e.g. "il-1040", "200-01", "1040n"
    if lowered in _SAFE_NUMERIC_FORMS:
        return f"form {lowered}"                         # anchored, no federal collision
    return None


def _state_signatures() -> list[dict]:
    signatures = []
    for state, code in _STATE_FORMS:
        s = state.lower()
        patterns = [
            f"{s} individual income tax", f"{s} resident income tax",
            f"{s} personal income tax", f"{s} income tax return",
        ]
        code_pattern = _form_code_pattern(code)
        if code_pattern:
            patterns.insert(0, code_pattern)
        signatures.append({"key": "state_return", "label": f"{state} Income Tax", "type": "return", "patterns": patterns})
    return signatures


# Common local/municipal returns (edit form_signatures.json to add yours).
_LOCAL_SIGNATURES: list[dict] = [
    {"key": "state_return", "label": "RITA Income Tax", "type": "return", "patterns": ["regional income tax agency", "form 37"]},
    {"key": "state_return", "label": "CCA Municipal Tax", "type": "return", "patterns": ["central collection agency"]},
    {"key": "state_return", "label": "Ohio School District Tax", "type": "return", "patterns": ["sd 100", "school district income tax"]},
]

DEFAULT_FORM_SIGNATURES: list[dict] = _FEDERAL_SIGNATURES + _state_signatures() + _LOCAL_SIGNATURES


def load_signatures(input_folder: Path) -> list[dict]:
    """Return the form signatures, preferring an editable override in the folder."""

    path = input_folder / SIGNATURES_FILENAME
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except json.JSONDecodeError:
            pass
    path.write_text(json.dumps(DEFAULT_FORM_SIGNATURES, indent=2), encoding="utf-8")
    return DEFAULT_FORM_SIGNATURES


def detect_forms(text: str, signatures: list[dict]) -> list[dict]:
    """Return the signatures whose patterns appear in the packet text (deduped)."""

    lowered = text.lower()
    found: list[dict] = []
    seen: set[tuple] = set()
    for signature in signatures:
        if any(pattern.lower() in lowered for pattern in signature.get("patterns", [])):
            identity = (signature.get("key"), signature.get("label", ""))
            if identity not in seen:
                seen.add(identity)
                found.append(signature)
    return found


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if len(t) >= 2}


def match_client(text: str, clients: list[dict]) -> int | None:
    """Index of the most specific client whose name tokens all appear in the packet.

    'Most specific' (largest matching token set) so that, with both 'Jo Sample' and
    'Jo Sample Jr', a packet for the Jr matches the Jr and not the prefix client.
    """

    text_tokens = _tokens(text)
    best_index, best_size = None, 0
    for index, client in enumerate(clients):
        name_tokens = _tokens(client.get("client_name") or client.get("name") or "")
        if name_tokens and name_tokens <= text_tokens and len(name_tokens) > best_size:
            best_index, best_size = index, len(name_tokens)
    return best_index


def _service_key_quantity(service) -> tuple[str | None, int]:
    """Return (key, quantity) for a non-inline service, or (None, 0) for inline/unknown."""

    if isinstance(service, str):
        return service, 1
    if isinstance(service, dict):
        if "description" in service and "price" in service:
            return None, 0  # inline custom line, preserved separately
        return (service.get("service") or service.get("key")), int(service.get("quantity", 1) or 1)
    return None, 0


def apply_detected(client: dict, detected: list[dict]) -> None:
    """Write detected forms onto a client: services, returns, efiled_returns, filed flag."""

    existing = client.get("services") or []
    inline = [s for s in existing if isinstance(s, dict) and "description" in s and "price" in s]

    # Start from existing keyed services, then let the packet (ground truth) set the
    # quantity for any key it detected -- so a re-detected key is not duplicated, and
    # several returns sharing a key (e.g. two state/local returns) bill as quantity 2.
    order: list[str] = []
    quantities: dict[str, int] = {}
    for service in existing:
        key, qty = _service_key_quantity(service)
        if key and key not in quantities:
            order.append(key)
            quantities[key] = qty
    for key, count in Counter(s["key"] for s in detected if s.get("key") and s["key"] != "base_1040").items():
        if key not in quantities:
            order.append(key)
        quantities[key] = count  # packet is authoritative for what was filed
    client["services"] = [
        ({"service": key, "quantity": quantities[key]} if quantities[key] > 1 else key) for key in order
    ] + inline

    return_labels = [s["label"] for s in detected if s.get("type") == "return" and s.get("label")]
    if return_labels:
        client["returns"] = [{"return_type": label, "refund_or_balance": "", "transaction_method": ""}
                             for label in return_labels]
        client["efiled_returns"] = [{"name": label} for label in return_labels]
        client["return_filed"] = True


def run_packet_reader(input_folder, status_callback=None) -> dict:
    """Read filed packets in the folder and record what was filed for each client."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "packet",
        "output_folder": output_folder,
        "clients_file": None,
        "clients_updated": 0,
        "unmatched": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; nothing to update."}

    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {**base_result, "summary": "Reading packets needs PyMuPDF (pip install PyMuPDF)."}

    clients = generate_documents.load_clients(data_file)
    signatures = load_signatures(input_folder)
    detected_by_client: dict[int, list[dict]] = {}
    warnings: list[str] = []
    unmatched = 0

    for pdf in sort_tax_docs.iter_supported_files(input_folder, output_folder):
        if pdf.suffix.lower() != ".pdf":
            continue
        if status_callback:
            status_callback(f"Reading packet {pdf.name}")
        try:
            with fitz.open(pdf) as document:
                text = "\n".join(page.get_text() for page in document)
        except Exception as exc:
            warnings.append(f"{pdf.name}: could not read ({exc}).")
            continue
        index = match_client(text, clients)
        if index is None:
            unmatched += 1
            warnings.append(f"{pdf.name}: no matching client name found; skipped.")
            continue
        detected_by_client.setdefault(index, [])
        for signature in detect_forms(text, signatures):
            if signature not in detected_by_client[index]:
                detected_by_client[index].append(signature)

    for index, detected in detected_by_client.items():
        if detected:
            apply_detected(clients[index], detected)

    clients_file = input_folder / "clients.json"
    clients_file.write_text(json.dumps(clients, indent=2), encoding="utf-8")

    return {
        **base_result,
        "clients_file": clients_file,
        "clients_updated": len(detected_by_client),
        "unmatched": unmatched,
        "warnings": warnings,
        "summary": (
            f"Read filed forms for {len(detected_by_client)} client(s)"
            + (f"; {unmatched} packet(s) unmatched." if unmatched else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Detect filed forms/returns from client return packets.")
    parser.add_argument("input_folder", help="Folder with clients.json and the filed packet PDFs.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_packet_reader(folder, status_callback=print)
    print(result["summary"])
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
