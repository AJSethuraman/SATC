"""Parser for the Drake "preparer copy" PDF — an OUTPUT / reconcile / seed source.

This is NOT a workpaper input; it never populates intake fields. It parses the
standardized worksheet pages whose TITLES are stable across clients (so we key off
titles, not coordinates):

  * "Filing Instructions" — ONE PER JURISDICTION (Federal + each state): form,
    filing method, due date, refund OR balance due, mail-to address.
  * "Tax Return Comparison" — 3-year: wages, total income, AGI, taxable income,
    total tax, withholding, refund/owed.
  * "Carryover Worksheet" — items carrying to next year.
  * "EF Status / Form 9325" — e-file acknowledgement per jurisdiction.

Every parsed value carries provenance (page + worksheet title) and is also emitted
as StagedFields so it routes through the staging/confirmation gate before it is
trusted. In production the input is ``pdftotext`` output; here we parse the same
text shape from a fixture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from satc.ingest.extractors.base import parse_money
from satc.models.provenance import Provenance, SourceRef
from satc.models.staging import StagedDocument, StagedField

_JURIS_ALIASES = {
    "federal": "US", "irs": "US", "ohio": "OH", "michigan": "MI",
    "massachusetts": "MA", "oh": "OH", "mi": "MI", "ma": "MA", "us": "US",
}


@dataclass(slots=True)
class FilingInstruction:
    jurisdiction: str
    form: str = ""
    filing_method: str = ""          # "e-file" | "paper"
    due_date: str = ""
    refund: float | None = None
    balance_due: float | None = None
    mail_to: str = ""
    page: int = 0


@dataclass(slots=True)
class ComparisonColumn:
    year: int
    values: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CarryoverItem:
    label: str
    kind: str
    amount: float
    to_year: int


@dataclass(slots=True)
class EFStatus:
    jurisdiction: str
    status: str
    date: str = ""


@dataclass(slots=True)
class PreparerSet:
    client_id: str
    tax_year: int
    filing_instructions: list[FilingInstruction] = field(default_factory=list)
    comparison: list[ComparisonColumn] = field(default_factory=list)
    carryovers: list[CarryoverItem] = field(default_factory=list)
    ef_statuses: list[EFStatus] = field(default_factory=list)
    staged: StagedDocument | None = None


# Map a comparison row label to a canonical key.
_COMPARISON_KEYS = {
    "wages": "wages", "total income": "total_income",
    "adjusted gross income": "agi", "taxable income": "taxable_income",
    "total tax": "total_tax", "withholding": "withholding",
    "estimated payments": "estimates", "refund": "refund", "balance due": "balance_due",
}

# Map a carryover label to a data-mart carryforward kind.
_CARRYOVER_KINDS = {
    "long-term capital loss": "CAP_LOSS_LT", "short-term capital loss": "CAP_LOSS_ST",
    "net operating loss": "NOL", "charitable": "CHARITABLE",
    "state overpayment": "STATE_OVERPAYMENT_APPLIED", "section 179": "SEC179_DISALLOWED",
    "passive": "PASSIVE_LOSS", "amt credit": "AMT_CREDIT", "qbi": "QBI_LOSS",
}


def _norm_juris(text: str) -> str:
    return _JURIS_ALIASES.get(text.strip().lower(), text.strip().upper()[:2])


def _money(text: str) -> float | None:
    amt, conf, _ = parse_money(text)
    return float(amt) if amt is not None and conf == "HIGH" else None


def _split_sections(text: str) -> list[tuple[str, int, list[str]]]:
    """Split into (title, page, lines). Page advances on form-feed (\\f)."""
    sections: list[tuple[str, int, list[str]]] = []
    page = 1
    current_title = ""
    current_lines: list[str] = []
    title_re = re.compile(
        r"^(filing instructions|tax return comparison|carryover worksheet|"
        r"ef status|form 9325)\b(.*)$", re.IGNORECASE)

    def flush():
        if current_title:
            sections.append((current_title, page, current_lines.copy()))

    for raw in text.splitlines():
        if "\f" in raw:
            page += raw.count("\f")
        line = raw.replace("\f", "").rstrip()
        m = title_re.match(line.strip())
        if m:
            flush()
            current_title = line.strip()
            current_lines = []
        elif current_title:
            current_lines.append(line)
    flush()
    return sections


def parse_preparer_set(text: str, *, client_id: str, tax_year: int) -> PreparerSet:
    ps = PreparerSet(client_id=client_id, tax_year=tax_year)
    staged = StagedDocument(document_id=f"DRAKE-{client_id}-{tax_year}",
                            client_id=client_id, tax_year=tax_year, doc_type="DRAKE-PREPARER-SET")

    def stage(field_path: str, label: str, text_value: str, amount: float | None,
              page: int, title: str) -> None:
        prov = Provenance(source_kind="DRAKE_OUTPUT", confidence="HIGH",
                          source_ref=SourceRef(worksheet_title=title, page=page, field_label=label),
                          extractor="DrakePreparerSetParser")
        staged.fields.append(StagedField(
            field_id=f"{staged.document_id}:{field_path}", document_id=staged.document_id,
            client_id=client_id, tax_year=tax_year, field_path=field_path, label=label,
            value_text=text_value, provenance=prov,
            value_amount=None if amount is None else __import__("decimal").Decimal(str(amount)),
            status="STAGED"))

    for title, page, lines in _split_sections(text):
        low = title.lower()
        if low.startswith("filing instructions"):
            juris = _norm_juris(title.split("-", 1)[1] if "-" in title else "US")
            fi = FilingInstruction(jurisdiction=juris, page=page)
            for line in lines:
                if ":" not in line:
                    continue
                key, val = (s.strip() for s in line.split(":", 1))
                k = key.lower()
                if "form" in k:
                    fi.form = val
                elif "method" in k:
                    fi.filing_method = "paper" if "paper" in val.lower() else "e-file"
                elif "mail" in k:
                    fi.mail_to = val
                elif "refund" in k:
                    fi.refund = _money(val)
                elif "balance" in k:   # must precede the due-date branch ("balance due")
                    fi.balance_due = _money(val)
                elif "due" in k:
                    fi.due_date = val
            ps.filing_instructions.append(fi)
            amt = fi.refund if fi.refund is not None else (-(fi.balance_due or 0))
            stage(f"fi.{juris}.result", f"{juris} refund/(balance due)", str(amt), amt, page, title)

        elif low.startswith("tax return comparison"):
            years: list[int] = []
            for line in lines:
                yrs = re.findall(r"\b(20\d{2})\b", line)
                if len(yrs) >= 2 and not years:
                    years = [int(y) for y in yrs]
                    ps.comparison = [ComparisonColumn(year=y) for y in years]
                    continue
                if not years:
                    continue
                label_match = re.match(r"^\s*([A-Za-z][A-Za-z /()'-]+?)\s{2,}(.+)$", line)
                if not label_match:
                    continue
                label = label_match.group(1).strip().lower()
                key = next((v for k, v in _COMPARISON_KEYS.items() if k in label), None)
                if key is None:
                    continue
                nums = re.findall(r"\(?-?[\d,]+\)?", label_match.group(2))
                for col, raw in zip(ps.comparison, nums):
                    val = _money(raw)
                    if val is not None:
                        col.values[key] = val
                last = ps.comparison[-1]
                if key in last.values:
                    stage(f"cmp.{key}", f"Comparison {key} ({last.year})",
                          str(last.values[key]), last.values[key], page, title)

        elif low.startswith("carryover"):
            for line in lines:
                m = re.match(r"^\s*([A-Za-z][A-Za-z /()'.-]+?)\s{2,}\(?-?[\$]?([\d,]+)\)?\s*$", line)
                if not m:
                    continue
                label = m.group(1).strip()
                amount = _money(m.group(2))
                if amount is None:
                    continue
                kind = next((v for k, v in _CARRYOVER_KINDS.items() if k in label.lower()), "OTHER")
                ps.carryovers.append(CarryoverItem(label=label, kind=kind, amount=amount,
                                                   to_year=tax_year + 1))
                stage(f"cf.{kind}", f"Carryover: {label}", str(amount), amount, page, title)

        elif low.startswith("ef status") or low.startswith("form 9325"):
            for line in lines:
                if ":" not in line:
                    continue
                juris_text, rest = (s.strip() for s in line.split(":", 1))
                status_match = re.match(r"(\w+)\s*(\d{2}/\d{2}/\d{4})?", rest)
                if status_match:
                    ps.ef_statuses.append(EFStatus(
                        jurisdiction=_norm_juris(juris_text), status=status_match.group(1),
                        date=status_match.group(2) or ""))

    ps.staged = staged
    return ps
