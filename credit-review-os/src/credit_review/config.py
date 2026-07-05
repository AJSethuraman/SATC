"""Two-layer review configuration: portable program + engagement overlay.

Layer 1 — **program** (``programs/<lob>.yaml``): the portable, client-agnostic
review program for one line of business. Declares the rating framework, the
linesheet sections/rows, and (from later slices) evidence, exception rules and
the regulatory crosswalk. It must never carry a client's thresholds or data.

Layer 2 — **engagement overlay** (``engagements/<name>.yaml``): the thin
per-client-bank layer: client identity, rating-scale map, policy thresholds,
scope, reviewer/independence, and a pointer to the loan list.

PII rule (binding, see PRD §7): taxpayer identification numbers are stored and
shown as **last-4 only**. Loaders reject full-TIN fields and full-TIN-shaped
values outright so a real TIN can never enter the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REVIEW_MODES = ("loan_level", "product_conformance")  # product_conformance: reserved, not built in v1

# Row kinds the linesheet renders. `evidence` is part of the schema vocabulary
# (PRD §6) but arrives with the exception engine's staleness tests; configs
# using it are accepted by the schema and refused by the builder with a clear
# error until then.
RENDERABLE_KINDS = (
    "input", "input_num", "input_text", "rating_input",
    "computed", "exception", "subhead", "note", "spacer",
)
RESERVED_KINDS = ("evidence",)
KNOWN_KINDS = RENDERABLE_KINDS + RESERVED_KINDS

# Exception model (PRD R6 + R5): three exception classes from the research's
# taxonomy, plus `rating` as the first-class finding an independent-validation
# disagreement raises (interagency 2020 independence expectation).
EXCEPTION_CLASSES = ("documentation", "policy", "compliance", "rating")
EXCEPTION_SUBTYPES = ("approved_with_mitigant", "unapproved")
EXCEPTION_STATUSES = ("open", "cleared", "waived")

# Keys that would make a program client-specific — they belong in the overlay.
_PROGRAM_FORBIDDEN_KEYS = ("client", "thresholds", "rating_scale_map", "scope", "reviewer", "loans")

# An evidence item is currency-tested exactly one way: against a staleness
# window from the overlay, by reviewer condition-judgment (appraisals per the
# 2010 Interagency Appraisal Guidelines), or by bare presence-in-file.
_EVIDENCE_MODES = ("staleness_key", "condition_driven", "presence_required")

# Full-TIN shapes we refuse anywhere in loaded data: dashed SSN, dashed EIN,
# or 9 consecutive digits in a TIN-named field.
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
_TIN_KEY_RE = re.compile(r"(?:^|_)(tin|ssn|ein|taxpayer_id)$")
_LOAN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,27}$")  # "LS_" + id must fit Excel's 31-char sheet cap


class ConfigError(Exception):
    """Raised when a program, overlay, or loan fixture fails validation."""


def mask_tin_last4(value: Any) -> Any:
    """Defense-in-depth: reduce any TIN-shaped value to its last 4 digits.

    Loaders already refuse full TINs; this guards the builder API itself so a
    programmatically-passed full TIN can never render into a cell.
    """
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) > 4:
        return digits[-4:]
    return value


def _require(mapping: dict, key: str, where: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ConfigError(f"{where}: missing required key '{key}'")
    return mapping[key]


def _reject_full_tins(obj: Any, where: str) -> None:
    """Walk a loaded YAML tree and refuse anything shaped like a full TIN."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            if _TIN_KEY_RE.search(key.lower()):
                raise ConfigError(
                    f"{where}: field '{key}' would hold a full TIN — store last-4 only "
                    f"(use 'tin_last4')")
            _reject_full_tins(v, f"{where}.{key}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_full_tins(v, f"{where}[{i}]")
    elif isinstance(obj, str):
        if _SSN_RE.search(obj) or _EIN_RE.search(obj):
            raise ConfigError(f"{where}: value looks like a full SSN/EIN — last-4 only")


# ---------------------------------------------------------------------------
# Program (layer 1)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Program:
    lob: str
    review_mode: str
    title: str
    buckets: tuple[str, ...]
    criticized: tuple[str, ...]
    classified: tuple[str, ...]
    sections: tuple[dict, ...]   # includes the synthesized evidence section
    evidence: tuple[dict, ...]
    crosswalk: tuple[dict, ...]  # element -> interagency requirement + citation
    products: tuple[dict, ...]   # Mode B only: tests resolved from the library
    raw: dict = field(repr=False)


def _evidence_rows(item: dict, where: str) -> list[dict]:
    """Expand one evidence item into linesheet rows (inputs + the currency test)."""
    etype = item.get("type")
    if not etype or not re.fullmatch(r"[a-z0-9_]+", str(etype)):
        raise ConfigError(f"{where}: evidence item needs a snake_case 'type'")
    modes = [m for m in _EVIDENCE_MODES if item.get(m)]
    if len(modes) != 1:
        raise ConfigError(
            f"{where}: evidence '{etype}' must set exactly one of {list(_EVIDENCE_MODES)}")
    mode = modes[0]
    label = item.get("label", etype.replace("_", " ").capitalize())
    severity = item.get("severity", "medium")
    asof_id = f"ev_{etype}_asof"
    rows: list[dict] = [
        {"id": asof_id, "kind": "input", "fmt": "date", "label": f"{label} — as-of date"}]
    if item.get("quality_tiers"):
        rows.append({"id": f"ev_{etype}_tier", "kind": "input_text",
                     "label": f"{label} — quality tier",
                     "note": "tiers: " + " / ".join(item["quality_tiers"])})
    if mode == "staleness_key":
        rows.append({
            "id": f"ev_{etype}_exc", "kind": "exception", "class": "documentation",
            "severity": severity, "label": f"{label} stale or missing",
            "when": (f'OR({{{asof_id}}}="",'
                     f'([ASOF]-{{{asof_id}}})>[POL {item["staleness_key"]}])')})
    elif mode == "condition_driven":
        valid_id = f"ev_{etype}_valid"
        rows.append({"id": valid_id, "kind": "input_text",
                     "label": f"{label} — still valid for current conditions? (yes/no)",
                     "note": "Condition-driven; re-order when no longer valid, "
                             "not on a fixed clock (2010 Interagency Appraisal Guidelines)."})
        rows.append({
            "id": f"ev_{etype}_exc", "kind": "exception", "class": "documentation",
            "severity": severity, "label": f"{label} no longer valid",
            "when": f'{{{valid_id}}}="no"'})
    else:  # presence_required
        rows.append({
            "id": f"ev_{etype}_exc", "kind": "exception", "class": "documentation",
            "severity": severity, "label": f"{label} missing from file",
            "when": f'{{{asof_id}}}=""'})
    return rows


def load_program(path: str | Path) -> Program:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name}: program YAML must be a mapping")
    where = path.name

    for key in _PROGRAM_FORBIDDEN_KEYS:
        if key in data:
            raise ConfigError(
                f"{where}: '{key}' is client-specific and belongs in the engagement "
                f"overlay — the program must stay portable/client-agnostic")

    meta = _require(data, "meta", where)
    lob = _require(meta, "lob", f"{where}.meta")
    review_mode = _require(meta, "review_mode", f"{where}.meta")
    title = _require(meta, "title", f"{where}.meta")
    if review_mode not in REVIEW_MODES:
        raise ConfigError(
            f"{where}.meta: review_mode {review_mode!r} not one of {list(REVIEW_MODES)}")

    if review_mode == "product_conformance":
        # Mode B: products + shared test library instead of linesheet sections.
        from credit_review.config_mode_b import validate_mode_b_program

        products = validate_mode_b_program(data, where)
        crosswalk = tuple(data.get("crosswalk", ()))
        for i, entry in enumerate(crosswalk):
            cwhere = f"{where}.crosswalk[{i}]"
            for key in ("element", "requirement", "source"):
                if not entry.get(key):
                    raise ConfigError(f"{cwhere}: crosswalk entry needs a non-empty "
                                      f"'{key}' — every program element must be cited")
        _reject_full_tins(data, where)
        return Program(lob=lob, review_mode=review_mode, title=title,
                       buckets=(), criticized=(), classified=(),
                       sections=(), evidence=(), crosswalk=crosswalk,
                       products=products, raw=data)

    rf = _require(data, "rating_framework", where)
    buckets = tuple(_require(rf, "buckets", f"{where}.rating_framework"))
    criticized = tuple(rf.get("criticized", ()))
    classified = tuple(rf.get("classified", ()))
    for name, subset in (("criticized", criticized), ("classified", classified)):
        stray = [b for b in subset if b not in buckets]
        if stray:
            raise ConfigError(f"{where}.rating_framework: {name} {stray} not in buckets")

    sections = list(_require(data, "sections", where))
    evidence = tuple(data.get("evidence", ()))
    if evidence:
        sections.append({
            "title": "Evidence & documentation (currency-tested)",
            "rows": [row for i, item in enumerate(evidence)
                     for row in _evidence_rows(item, f"{where}.evidence[{i}]")]})
    sections = tuple(sections)
    seen_ids: set[str] = set()
    for si, section in enumerate(sections):
        swhere = f"{where}.sections[{si}]"
        _require(section, "title", swhere)
        for ri, row in enumerate(_require(section, "rows", swhere)):
            rwhere = f"{swhere}.rows[{ri}]"
            kind = row.get("kind", "input")
            if kind not in KNOWN_KINDS:
                raise ConfigError(f"{rwhere}: unknown row kind {kind!r}")
            if kind in ("subhead", "note") and not row.get("label"):
                raise ConfigError(f"{rwhere}: '{kind}' row needs a label")
            if kind == "computed" and not row.get("formula"):
                raise ConfigError(f"{rwhere}: computed row needs a formula")
            if kind == "exception":
                if not row.get("when"):
                    raise ConfigError(f"{rwhere}: exception row needs a 'when' condition")
                if row.get("class") not in EXCEPTION_CLASSES:
                    raise ConfigError(
                        f"{rwhere}: exception class {row.get('class')!r} not one of "
                        f"{list(EXCEPTION_CLASSES)}")
                if not row.get("severity"):
                    raise ConfigError(f"{rwhere}: exception row needs a severity tier")
                subtype = row.get("subtype")
                if subtype is not None and subtype not in EXCEPTION_SUBTYPES:
                    raise ConfigError(
                        f"{rwhere}: exception subtype {subtype!r} not one of "
                        f"{list(EXCEPTION_SUBTYPES)}")
            rid = row.get("id")
            if rid:
                if rid in seen_ids:
                    raise ConfigError(f"{rwhere}: duplicate row id {rid!r}")
                seen_ids.add(rid)
            elif kind not in ("subhead", "note", "spacer"):
                raise ConfigError(f"{rwhere}: '{kind}' row needs an id")

    crosswalk = tuple(data.get("crosswalk", ()))
    for i, entry in enumerate(crosswalk):
        cwhere = f"{where}.crosswalk[{i}]"
        for key in ("element", "requirement", "source"):
            if not entry.get(key):
                raise ConfigError(f"{cwhere}: crosswalk entry needs a non-empty '{key}' "
                                  f"— every program element must be cited")

    _reject_full_tins(data, where)
    return Program(lob=lob, review_mode=review_mode, title=title, buckets=buckets,
                   criticized=criticized, classified=classified,
                   sections=sections, evidence=evidence, crosswalk=crosswalk,
                   products=(), raw=data)


# ---------------------------------------------------------------------------
# Engagement overlay (layer 2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Engagement:
    client_name: str
    engagement_id: str
    review_as_of: date
    rating_scale_map: dict[str, str]      # Mode A; empty for Mode B
    thresholds: dict[str, float]
    scope: dict
    reviewer: dict
    loans_path: Path | None               # Mode A
    samples_path: Path | None = None      # Mode B
    overlay_products: dict = field(default_factory=dict)   # Mode B
    tolerances: dict = field(default_factory=dict)         # Mode B, per test class
    raw: dict = field(repr=False, default_factory=dict)


def load_engagement(path: str | Path) -> Engagement:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name}: engagement YAML must be a mapping")
    where = path.name

    client = _require(data, "client", where)
    client_name = _require(client, "name", f"{where}.client")
    engagement_id = _require(client, "engagement_id", f"{where}.client")

    review_as_of = _require(data, "review_as_of", where)
    if not isinstance(review_as_of, date):
        raise ConfigError(f"{where}: review_as_of must be a date (YYYY-MM-DD), "
                          f"got {review_as_of!r}")

    is_mode_b = "samples" in data
    if is_mode_b:
        scale_map: dict[str, str] = {}
    else:
        scale_map = {str(k): str(v)
                     for k, v in _require(data, "rating_scale_map", where).items()}
    thresholds = dict(_require(data, "thresholds", where))
    for k, v in thresholds.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ConfigError(f"{where}.thresholds.{k}: must be numeric, got {v!r}")
    scope = dict(_require(data, "scope", where))
    reviewer = dict(_require(data, "reviewer", where))
    _require(reviewer, "name", f"{where}.reviewer")
    if "independent" not in reviewer:
        raise ConfigError(f"{where}.reviewer: missing required key 'independent'")

    def _resolve(ref: str) -> Path:
        return (path.parent / ref).resolve() if not Path(ref).is_absolute() else Path(ref)

    if is_mode_b:
        from credit_review.config_mode_b import validate_mode_b_overlay_products

        overlay_products = validate_mode_b_overlay_products(data, where)
        samples_path = _resolve(_require(data, "samples", where))
        loans_path = None
        tolerances = dict(data["tolerances"])
    else:
        loans_path = _resolve(_require(data, "loans", where))
        samples_path = None
        overlay_products = {}
        tolerances = {}

    _reject_full_tins(data, where)
    return Engagement(client_name=client_name, engagement_id=engagement_id,
                      review_as_of=review_as_of, rating_scale_map=scale_map,
                      thresholds=thresholds, scope=scope, reviewer=reviewer,
                      loans_path=loans_path, samples_path=samples_path,
                      overlay_products=overlay_products, tolerances=tolerances,
                      raw=data)


def check_overlay_fits_program(engagement: Engagement, program: Program) -> None:
    """Every internal grade must map to exactly one of the program's buckets."""
    stray = {g: b for g, b in engagement.rating_scale_map.items() if b not in program.buckets}
    if stray:
        raise ConfigError(
            f"rating_scale_map maps grades {sorted(stray)} to buckets outside the "
            f"program framework {list(program.buckets)}: {stray}")


# ---------------------------------------------------------------------------
# Loans (synthetic fixture in-repo; the bank's list on a real engagement)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Loan:
    loan_id: str
    values: dict[str, Any]   # linesheet row_id -> prefilled value

    @property
    def sheet_name(self) -> str:
        return f"LS_{self.loan_id}"


def load_loans(path: str | Path) -> list[Loan]:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    where = path.name
    if not isinstance(data, dict) or not isinstance(data.get("loans"), list):
        raise ConfigError(f"{where}: expected a mapping with a 'loans' list")
    _reject_full_tins(data, where)

    loans: list[Loan] = []
    seen: set[str] = set()
    for i, entry in enumerate(data["loans"]):
        lwhere = f"{where}.loans[{i}]"
        loan_id = str(_require(entry, "loan_id", lwhere))
        if not _LOAN_ID_RE.match(loan_id):
            raise ConfigError(
                f"{lwhere}: loan_id {loan_id!r} must be 1-27 chars of [A-Za-z0-9_-] "
                f"so 'LS_<loan_id>' fits an Excel sheet name")
        if loan_id in seen:
            raise ConfigError(f"{lwhere}: duplicate loan_id {loan_id!r}")
        seen.add(loan_id)
        values = {str(k): v for k, v in entry.items() if k != "loan_id"}
        tin4 = values.get("tin_last4")
        if tin4 is not None and not re.fullmatch(r"\d{4}", str(tin4)):
            raise ConfigError(f"{lwhere}: tin_last4 must be exactly 4 digits, got {tin4!r}")
        loans.append(Loan(loan_id=loan_id, values=values))
    return loans
