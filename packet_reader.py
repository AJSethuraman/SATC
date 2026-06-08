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
DEFAULT_FORM_SIGNATURES: list[dict] = [
    {"key": "base_1040", "label": "Federal Income Tax", "type": "return", "patterns": ["form 1040"]},
    {"key": "schedule_a", "label": "", "type": "form", "patterns": ["schedule a (form 1040)", "schedule a—itemized", "schedule a - itemized"]},
    {"key": "schedule_b", "label": "", "type": "form", "patterns": ["schedule b (form 1040)", "schedule b—interest", "schedule b - interest"]},
    {"key": "schedule_c", "label": "", "type": "form", "patterns": ["schedule c (form 1040)", "schedule c—profit", "schedule c - profit"]},
    {"key": "schedule_d", "label": "", "type": "form", "patterns": ["schedule d (form 1040)", "schedule d—capital", "schedule d - capital"]},
    {"key": "schedule_e", "label": "", "type": "form", "patterns": ["schedule e (form 1040)", "schedule e—supplemental", "schedule e - supplemental"]},
    {"key": "schedule_se", "label": "", "type": "form", "patterns": ["schedule se (form 1040)", "self-employment tax"]},
    {"key": "education_8863", "label": "", "type": "form", "patterns": ["form 8863", "education credits"]},
    {"key": "childcare_2441", "label": "", "type": "form", "patterns": ["form 2441", "child and dependent care expenses"]},
    {"key": "hsa_8889", "label": "", "type": "form", "patterns": ["form 8889", "health savings accounts"]},
    {"key": "additional_ctc_8812", "label": "", "type": "form", "patterns": ["schedule 8812", "credits for qualifying children"]},
    # State / local returns (edit form_signatures.json for the ones you file).
    {"key": "state_return", "label": "Ohio Income Tax", "type": "return", "patterns": ["ohio it 1040", "it 1040"]},
    {"key": "state_return", "label": "RITA Income Tax", "type": "return", "patterns": ["rita", "regional income tax", "form 37"]},
]


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
    """Index of the client whose name tokens all appear in the packet text, else None."""

    text_tokens = _tokens(text)
    for index, client in enumerate(clients):
        name_tokens = _tokens(client.get("client_name") or client.get("name") or "")
        if name_tokens and name_tokens <= text_tokens:
            return index
    return None


def apply_detected(client: dict, detected: list[dict]) -> None:
    """Write detected forms onto a client: services, returns, efiled_returns, filed flag."""

    # Count billable forms; several returns can share a key (e.g. 2 state/local returns
    # both bill as state_return -> quantity 2).
    counts = Counter(s["key"] for s in detected if s.get("key") and s["key"] != "base_1040")
    inline = [s for s in (client.get("services") or []) if not isinstance(s, str)]
    kept = [s for s in (client.get("services") or []) if isinstance(s, str) and s not in counts]
    detected_services = [
        ({"service": key, "quantity": count} if count > 1 else key) for key, count in counts.items()
    ]
    client["services"] = list(dict.fromkeys(kept)) + detected_services + inline

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
