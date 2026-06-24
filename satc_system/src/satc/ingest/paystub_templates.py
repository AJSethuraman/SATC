"""Learned per-employer / per-layout paystub templates ("training").

The heuristic :class:`~satc.ingest.readers.paystub.PaystubReader` reads any stub.
This layer lets the practice *teach* a specific employer / payroll-provider layout
once — by confirming the figures — then *recognizes* that layout on later uploads
and reads it with high confidence, so corrections trend toward zero.

Privacy: only the **layout** is stored — the anchor phrase that locates each field
and which money-column it sits in — **never** a client's dollar amounts or SSNs.
Templates are practice-wide and stored locally (``~/.satc/data`` in the packaged
app, ``SATC_DATA_DIR`` overrides); nothing is sent anywhere.

Recognition uses both signals the practice asked for: a structural **layout**
signature (the set of label lines, provider-independent) plus the **employer** and
detected payroll **provider**. A saved template matches a new stub when the layout
matches (same provider format) or the employer matches — layout as the base,
employer as the refinement.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.paystub import (
    LABEL_EMPLOYER,
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
    PaystubReader,
    _employer,
)
from satc.ingest.readers.text_anchor import MONEY

# Canonical money fields a template can learn anchors for (frequency is separate).
_MONEY_LABELS = (
    LABEL_GROSS_CURRENT, LABEL_GROSS_YTD,
    LABEL_FED_WH_CURRENT, LABEL_FED_WH_YTD,
    LABEL_RETIREMENT_CURRENT,
)

# Payroll-provider markers (substring, case-insensitive) -> display name.
_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("adp", "ADP"), ("paychex", "Paychex"), ("gusto", "Gusto"), ("workday", "Workday"),
    ("paylocity", "Paylocity"), ("intuit", "QuickBooks"), ("quickbooks", "QuickBooks"),
    ("rippling", "Rippling"), ("trinet", "TriNet"), ("justworks", "Justworks"),
    ("dayforce", "Ceridian Dayforce"), ("ceridian", "Ceridian"), ("bamboohr", "BambooHR"),
    ("zenefits", "Zenefits"), ("ukg", "UKG"), ("kronos", "UKG"), ("sage", "Sage"),
)

_WORD = re.compile(r"[A-Za-z][A-Za-z/()]*")
_SUFFIX = re.compile(r"\b(inc|llc|l\.l\.c|ltd|corp|co|company|pllc|lp|llp|p\.c|pc)\b\.?", re.IGNORECASE)


def _norm_money(text: str) -> str:
    return text.replace(",", "").replace("$", "").strip()


def _dec(text: str | None) -> Decimal | None:
    if text is None:
        return None
    try:
        return Decimal(_norm_money(text))
    except InvalidOperation:
        return None


def _head_label(raw: str) -> str:
    """The normalized label text on a line, up to its first money value."""
    m = MONEY.search(raw)
    head = raw[: m.start()] if m else raw
    return " ".join(_WORD.findall(head.lower()))


def detect_provider(text: str) -> str:
    low = text.lower()
    for needle, name in _PROVIDERS:
        if needle in low:
            return name
    return "unknown"


def employer_key(text: str) -> str:
    """A normalized employer key (suffix-stripped) for matching across stubs."""
    name = _employer(text.splitlines())
    key = _SUFFIX.sub("", name.lower())
    key = re.sub(r"[^a-z0-9 ]", " ", key)
    return re.sub(r"\s+", " ", key).strip()


def layout_signature(text: str) -> str:
    """A stable fingerprint of the stub's layout: its set of money-line labels.

    Independent of the dollar values, so two stubs from the same employer/provider
    (different pay periods) share a signature.
    """
    labels = sorted({_head_label(raw) for raw in text.splitlines()
                     if MONEY.search(raw) and _head_label(raw)})
    if not labels:
        return ""
    return hashlib.sha1("|".join(labels).encode("utf-8")).hexdigest()[:16]


@dataclass(slots=True)
class Fingerprint:
    provider: str
    employer: str
    layout: str


def fingerprint(text: str) -> Fingerprint:
    return Fingerprint(detect_provider(text), employer_key(text), layout_signature(text))


@dataclass(slots=True)
class PaystubTemplate:
    template_id: str
    provider: str
    employer: str
    layout: str
    anchors: dict[str, dict] = field(default_factory=dict)
    label_hint: str = ""
    sample_count: int = 1
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PaystubTemplate":
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


def _locate_value(lines: list[str], value: str) -> tuple[str, int] | None:
    """Find ``value`` on a money line; return (label anchor, money-column index)."""
    target = _dec(value)
    if target is None:
        return None
    for raw in lines:
        decs = [_dec(m.group(1)) for m in MONEY.finditer(raw)]
        for col, d in enumerate(decs):
            if d is not None and d == target:
                anchor = _head_label(raw)
                if anchor:
                    return anchor, col
    return None


def learn(text: str, confirmed: dict[str, str]) -> PaystubTemplate:
    """Derive a template from confirmed raw figures by locating each in the text.

    ``confirmed`` maps canonical ``LABEL_*`` keys to the values exactly as they
    appear on the stub; we record *where* each was found (anchor + column), not the
    value itself.
    """
    fp = fingerprint(text)
    lines = text.splitlines()
    anchors: dict[str, dict] = {}
    for label in _MONEY_LABELS:
        raw_value = confirmed.get(label)
        if not raw_value or not raw_value.strip():
            continue
        loc = _locate_value(lines, raw_value)
        if loc is not None:
            anchor, col = loc
            anchors[label] = {"anchor": anchor, "column": col}
    freq = confirmed.get(LABEL_PAY_FREQUENCY)
    if freq and freq.strip():
        anchors[LABEL_PAY_FREQUENCY] = {"value": freq.strip().lower()}

    now = datetime.now(tz=UTC).isoformat()
    template_id = hashlib.sha1(f"{fp.provider}|{fp.employer}|{fp.layout}".encode("utf-8")).hexdigest()[:16]
    hint = (confirmed.get(LABEL_EMPLOYER) or fp.employer or "this employer").strip() or "this employer"
    if fp.provider != "unknown":
        hint = f"{hint} ({fp.provider})"
    return PaystubTemplate(template_id=template_id, provider=fp.provider, employer=fp.employer,
                           layout=fp.layout, anchors=anchors, label_hint=hint,
                           created_at=now, updated_at=now)


def apply_template(template: PaystubTemplate, text: str) -> ReadResult:
    """Read a stub using a learned template's anchors (trusted, not flagged)."""
    lines = text.splitlines()
    labeled: dict[str, str] = {}
    for label, spec in template.anchors.items():
        if "value" in spec:
            labeled[label] = spec["value"]
            continue
        anchor = spec.get("anchor", "")
        col = int(spec.get("column", 0))
        for raw in lines:
            head = _head_label(raw)
            if head and anchor and anchor in head:
                monies = [_norm_money(m.group(1)) for m in MONEY.finditer(raw)]
                if len(monies) > col:
                    labeled[label] = monies[col]
                break
    return ReadResult(labeled_fields=labeled, uncertain_labels=set(),
                      backend=f"template:{template.template_id}")


def _data_dir() -> Path:
    override = os.environ.get("SATC_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path.home() / ".satc" / "data"
    return Path(__file__).resolve().parents[3] / "build" / "data"


class TemplateLibrary:
    """Practice-wide, local store of learned paystub templates (a JSON file)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else _data_dir() / "paystub_templates.json"

    def _load_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001 - a corrupt store should never crash a read
            return {}

    def save(self, template: PaystubTemplate) -> PaystubTemplate:
        data = self._load_all()
        prior = data.get(template.template_id)
        if prior:
            template.created_at = prior.get("created_at", template.created_at)
            template.sample_count = int(prior.get("sample_count", 1)) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data[template.template_id] = dataclasses.asdict(template)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return template

    def all(self) -> list[PaystubTemplate]:
        return [PaystubTemplate.from_dict(v) for v in self._load_all().values()]

    def match(self, text: str) -> PaystubTemplate | None:
        """Best template for ``text``: layout match (base) or employer match (refine)."""
        fp = fingerprint(text)
        best: dict | None = None
        best_score = 0
        for raw in self._load_all().values():
            score = 0
            if fp.layout and raw.get("layout") == fp.layout:
                score += 3
            if fp.employer and raw.get("employer") == fp.employer:
                score += 2
            if fp.provider != "unknown" and raw.get("provider") == fp.provider:
                score += 1
            if score > best_score:
                best_score, best = score, raw
        if best is None or best_score < 2:  # require at least a layout or employer match
            return None
        return PaystubTemplate.from_dict(best)


def read_with_templates(text: str, library: TemplateLibrary | None = None
                        ) -> tuple[ReadResult, PaystubTemplate | None]:
    """Heuristic read, overlaid with a learned template when one matches.

    Template-supplied fields win and are trusted; anything the template doesn't
    cover falls back to the heuristic reader (and keeps its uncertain flags).
    """
    base = PaystubReader().read_text(text)
    template = (library or TemplateLibrary()).match(text)
    if template is None:
        return base, None
    applied = apply_template(template, text)
    merged = dict(base.labeled_fields)
    merged.update(applied.labeled_fields)
    uncertain = base.uncertain_labels - set(applied.labeled_fields)
    return ReadResult(labeled_fields=merged, uncertain_labels=uncertain,
                      backend=f"template:{template.template_id}"), template
