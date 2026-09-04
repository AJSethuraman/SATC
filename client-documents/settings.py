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
    materials = _materials_deadline(season, RETURN_TYPES[return_type], deadlines)

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
        "MaterialsDeadline": materials,
    }


def _spoken(day) -> str:
    """A date the way the firm writes it. "March 5, 2027", never "March 05"."""
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def _materials_deadline(season: str, key: str, typed: dict) -> str:
    """The date the client's papers are due, from the file or from the statute.

    THE FILE USED TO BE THE ONLY SOURCE, four dates typed by hand under a
    comment telling a PERSON to "CHECK THIS AGAINST THE IRS CALENDAR each season
    before rolling it forward". `deadlines.py` now derives them from IRC 6072 and
    7503, so there are two answers where there was one -- and this is the thing
    that compares them, which is the whole lesson of the last week.

    THE TYPED DATE WINS when both exist. It is what a client was told, and a
    letter already read is not corrected by a better rule. But a DISAGREEMENT is
    refused rather than resolved: it means either the file is stale or the
    policy moved, and printing either one silently is how a client gets a date
    nobody chose.

    WITH NO TYPED DATE the statute answers, rather than raising as this used to.
    That is the annual chore gone: a new season needs no edit, and the first
    year a deadline shifts for a weekend or Emancipation Day it shifts here too.
    """
    import deadlines as taxcal

    try:
        computed = taxcal.materials_deadline(key, int(season))
    except (KeyError, ValueError):
        computed = None                      # a return type or season it cannot derive

    said = typed.get(key)
    if not said:
        if computed is None:
            raise KeyError(
                f"no materials deadline for {key!r} in season {season!r}: not in "
                f"firm-settings.yaml and not derivable — add it rather than "
                f"letting a document print the wrong date"
            )
        return _spoken(computed)

    if computed is not None and _spoken(computed) != said:
        raise ValueError(
            f"the materials deadline for {key} in season {season} does not agree "
            f"with the statute: firm-settings.yaml says {said}, and "
            f"{taxcal.MATERIALS_LEAD_DAYS} days before the filing date "
            f"({taxcal.filing_date(key, int(season))}) is {_spoken(computed)}. "
            f"Either the file is stale or the policy changed; nothing is printed "
            f"until one of them is corrected."
        )
    return said


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
