"""Turn `firm-settings.yaml` into the merge fields that come from the firm.

The settings file is organised for a human to edit; the templates want a flat
dict of PascalCase field names. This is the one place that mapping lives, so a
renamed setting breaks here loudly rather than silently rendering a blank.

`[CONFIRM: ...]` values are passed through untouched. They are decisions nobody
has made, and `merge.render` refuses to ship one — that refusal is the whole
point of the marker, so this module must not paper over it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / "registry" / "firm-settings.yaml"

# Return type -> the key under `materials_deadlines.<season>`. The templates
# take one MaterialsDeadline; which one depends on what is being filed.
RETURN_TYPES = {
    "individual": "individual_1040",
    "s_corp": "s_corp_1120s",
    "partnership": "partnership_1065",
    "c_corp": "c_corp_1120",
}


def load(path: Path | str = SETTINGS) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def firm_fields(season: str, return_type: str = "individual",
                settings: dict | None = None) -> dict:
    """Every merge field the firm supplies, for one season and return type.

    `season` keys `materials_deadlines` — "2026" is the tax year being filed,
    not the calendar year the letter is written in.
    """
    s = settings if settings is not None else load()

    if return_type not in RETURN_TYPES:
        raise KeyError(
            f"unknown return type {return_type!r}; "
            f"expected one of {', '.join(sorted(RETURN_TYPES))}"
        )

    firm = s.get("firm") or {}
    prep = s.get("preparer") or {}
    bill = s.get("billing") or {}
    deliv = s.get("delivery") or {}
    deadlines = (s.get("materials_deadlines") or {}).get(season) or {}

    if not deadlines:
        raise KeyError(
            f"no materials_deadlines for season {season!r} in firm-settings.yaml — "
            f"add it rather than letting a document print the wrong date"
        )

    return {
        # The firm itself — masthead, footer and sign-off on all ten templates.
        # Typed into each file until 26 Aug 2026; merged from settings since.
        "FirmName": firm.get("name"),
        "FirmLegalName": firm.get("legal_name"),
        "FirmAddress1": firm.get("address1"),
        "FirmCity": firm.get("city"),
        "FirmState": firm.get("state"),
        "FirmZip": firm.get("zip"),
        "FirmWebsite": firm.get("website"),
        "FirmJurisdiction": firm.get("jurisdiction"),
        "PreparerName": prep.get("name"),
        "PreparerTitle": prep.get("title"),
        "PreparerEmail": prep.get("email"),
        "BillingContactName": bill.get("contact_name"),
        "BillingContactEmail": bill.get("contact_email"),
        "PaymentInstruction": deliv.get("payment_instruction"),
        "MaterialsDeadline": deadlines.get(RETURN_TYPES[return_type]),
    }


# Settings that govern POLICY rather than paperwork. A `[CONFIRM:` in one of
# these is a real open question, but it does not stop a document rendering,
# because nothing on a template merges from it.
#
# `hard_no` is the case that revealed the distinction, on 26 August 2026:
# `doctor` reported it under "blocks every REAL render" while real packs were
# rendering perfectly well. A readiness tool that overstates what is broken
# teaches whoever reads it to stop believing the parts that are true.
#
# Add a path here only when you have checked that no template merges from it.
POLICY_ONLY = ("hard_no",)


def blocks_render(path: str) -> bool:
    """Would an unanswered decision at this path stop a document rendering?"""
    return not any(path == p or path.startswith(p + ".") or
                   path.startswith(p + "[") for p in POLICY_ONLY)


def open_decisions(settings: dict | None = None) -> list[tuple[str, str]]:
    """Every `[CONFIRM: ...]` still in the settings, as (path, question).

    What `doctor` reports. Walks the whole tree so a placeholder added in a new
    section is found without this list changing. Whether a given one actually
    gates a render is `blocks_render`, not this -- see POLICY_ONLY above.
    """
    s = settings if settings is not None else load()
    found: list[tuple[str, str]] = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and "[CONFIRM:" in node:
            q = node.split("[CONFIRM:", 1)[1].rsplit("]", 1)[0].strip()
            found.append((path, q))

    walk(s, "")
    return found
