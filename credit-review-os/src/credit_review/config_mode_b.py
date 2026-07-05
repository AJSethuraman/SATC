"""Mode B (product-conformance) configuration: schema + loaders.

Layer 1 — the **retail program**: a shared ``test_library`` (the largely-
uniform retail test set, defined once) plus ``products[]``; each product names
its URCCP ``classification_type``, its keyed ``attributes``, its ``tests``
(library references or inline definitions), and its buy-box ``fringe_rules``.

Layer 2 — the **engagement overlay** gains, per product: ``population``, a
``sample_plan`` of named segments (stratified random and judgmental both
first-class), and points at a **samples fixture** (the sampled files + pool
delinquency buckets).

PII rule (binding, stricter than Mode A): Mode B artifacts identify files by
**loan/account number only** — the loaders refuse any person-name-shaped key
in sample data, and TIN keys are refused globally by the base loader.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from credit_review.config import ConfigError, _reject_full_tins, _require

CLASSIFICATION_TYPES = ("closed_end", "open_end", "residential_secured")
TEST_KINDS = ("attestation", "computed")
TEST_CLASSES = ("policy", "documentation", "compliance")
SEGMENT_METHODS = ("random", "judgmental")
ATTESTATION_VALUES = ("pass", "fail", "na")

# Mode B carries data on individual people — person names never enter.
_PERSON_NAME_KEY_RE = re.compile(r"name|borrower|applicant|guarantor", re.IGNORECASE)

# Delinquency buckets, in order (keyed from the bank's servicing report).
BUCKETS = ("current", "dpd_30_59", "dpd_60_89", "dpd_90_119", "dpd_120_179",
           "dpd_180_plus")


def _reject_person_name_keys(obj: Any, where: str) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _PERSON_NAME_KEY_RE.search(str(k)):
                raise ConfigError(
                    f"{where}: field {k!r} — Mode B artifacts identify files by "
                    f"loan number only; person names never enter (PRD PII rule)")
            _reject_person_name_keys(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_person_name_keys(v, f"{where}[{i}]")


# ---------------------------------------------------------------------------
# Program (layer 1) — validation called from config.load_program
# ---------------------------------------------------------------------------
def validate_mode_b_program(data: dict, where: str) -> tuple[dict, ...]:
    """Validate test_library + products; return products with tests resolved."""
    library: dict[str, dict] = {}
    for i, entry in enumerate(data.get("test_library", ())):
        lwhere = f"{where}.test_library[{i}]"
        tid = _require(entry, "id", lwhere)
        if tid in library:
            raise ConfigError(f"{lwhere}: duplicate test id {tid!r}")
        _validate_test(entry, lwhere)
        library[tid] = entry

    products = data.get("products")
    if not products:
        raise ConfigError(f"{where}: product_conformance program needs 'products'")
    resolved: list[dict] = []
    seen: set[str] = set()
    for i, product in enumerate(products):
        pwhere = f"{where}.products[{i}]"
        pid = _require(product, "id", pwhere)
        if not re.fullmatch(r"[a-z0-9_]{1,24}", pid):
            raise ConfigError(f"{pwhere}: product id {pid!r} must be short snake_case "
                              f"so 'PS_<id>' fits an Excel sheet name")
        if pid in seen:
            raise ConfigError(f"{pwhere}: duplicate product id {pid!r}")
        seen.add(pid)
        _require(product, "label", pwhere)
        ctype = _require(product, "classification_type", pwhere)
        if ctype not in CLASSIFICATION_TYPES:
            raise ConfigError(f"{pwhere}: classification_type {ctype!r} not one of "
                              f"{list(CLASSIFICATION_TYPES)}")
        attributes = tuple(product.get("attributes", ()))
        attr_ids = set()
        for j, attr in enumerate(attributes):
            aid = _require(attr, "id", f"{pwhere}.attributes[{j}]")
            _require(attr, "label", f"{pwhere}.attributes[{j}]")
            attr_ids.add(aid)

        tests: list[dict] = []
        test_ids: set[str] = set()
        for j, ref in enumerate(_require(product, "tests", pwhere)):
            twhere = f"{pwhere}.tests[{j}]"
            if isinstance(ref, str):
                if ref not in library:
                    raise ConfigError(f"{twhere}: {ref!r} not in test_library")
                test = dict(library[ref])
            elif isinstance(ref, dict):
                base = library.get(ref.get("id", ""), {})
                test = {**base, **ref}          # inline definition / override wins
                _validate_test(test, twhere)
            else:
                raise ConfigError(f"{twhere}: test must be a library id or a mapping")
            if test["id"] in test_ids:
                raise ConfigError(f"{twhere}: duplicate test {test['id']!r}")
            test_ids.add(test["id"])
            tests.append(test)

        fringe_rules = tuple(product.get("fringe_rules", ()))
        for j, rule in enumerate(fringe_rules):
            fwhere = f"{pwhere}.fringe_rules[{j}]"
            attr = _require(rule, "attribute", fwhere)
            if attr not in attr_ids:
                raise ConfigError(f"{fwhere}: unknown attribute {attr!r}")
            _require(rule, "limit_key", fwhere)
            _require(rule, "band_key", fwhere)
            if rule.get("direction") not in ("floor", "ceiling"):
                raise ConfigError(f"{fwhere}: direction must be floor or ceiling")

        resolved.append({**product, "attributes": attributes,
                         "tests": tuple(tests), "fringe_rules": fringe_rules})
    return tuple(resolved)


def _validate_test(test: dict, where: str) -> None:
    _require(test, "id", where)
    _require(test, "label", where)
    if test.get("class") not in TEST_CLASSES:
        raise ConfigError(f"{where}: test class {test.get('class')!r} not one of "
                          f"{list(TEST_CLASSES)}")
    if not test.get("severity"):
        raise ConfigError(f"{where}: test needs a severity tier")
    kind = test.get("kind")
    if kind not in TEST_KINDS:
        raise ConfigError(f"{where}: test kind {kind!r} not one of {list(TEST_KINDS)}")
    if kind == "computed" and not test.get("when"):
        raise ConfigError(f"{where}: computed test needs a 'when' breach condition")


# ---------------------------------------------------------------------------
# Overlay (layer 2) per-product block — validation called from load_engagement
# ---------------------------------------------------------------------------
def validate_mode_b_overlay_products(data: dict, where: str) -> dict[str, dict]:
    products = data.get("products")
    if not isinstance(products, dict) or not products:
        raise ConfigError(f"{where}: Mode B overlay needs a 'products' mapping")
    tolerances = _require(data, "tolerances", where)
    for cls in TEST_CLASSES:
        if cls not in tolerances or isinstance(tolerances[cls], bool) \
                or not isinstance(tolerances[cls], (int, float)):
            raise ConfigError(f"{where}.tolerances: needs numeric '{cls}' rate")

    for pid, block in products.items():
        pwhere = f"{where}.products.{pid}"
        population = _require(block, "population", pwhere)
        for key in ("count", "dollars"):
            if not isinstance(population.get(key), (int, float)):
                raise ConfigError(f"{pwhere}.population: needs numeric '{key}'")
        plan = _require(block, "sample_plan", pwhere)
        segments = _require(plan, "segments", f"{pwhere}.sample_plan")
        seen: set[str] = set()
        for i, seg in enumerate(segments):
            swhere = f"{pwhere}.sample_plan.segments[{i}]"
            sid = _require(seg, "id", swhere)
            if sid in seen:
                raise ConfigError(f"{swhere}: duplicate segment id {sid!r}")
            seen.add(sid)
            if seg.get("method") not in SEGMENT_METHODS:
                raise ConfigError(f"{swhere}: method must be one of "
                                  f"{list(SEGMENT_METHODS)} — stratified random "
                                  f"and judgmental are both first-class")
            if not isinstance(seg.get("size"), int) or seg["size"] < 1:
                raise ConfigError(f"{swhere}: needs integer size >= 1")
            _require(seg, "basis", swhere)
    return dict(products)


# ---------------------------------------------------------------------------
# Samples fixture (sampled files + pool buckets per product)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProductSample:
    product_id: str
    files: tuple[dict, ...]     # loan_number, segment, attributes, attestations
    pool: dict                  # bucket -> {count, dollars} (+ branch-specific keys)


def load_samples(path: str | Path, program_products: tuple[dict, ...],
                 overlay_products: dict[str, dict]) -> dict[str, ProductSample]:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    where = path.name
    if not isinstance(data, dict) or not isinstance(data.get("products"), dict):
        raise ConfigError(f"{where}: expected a mapping with a 'products' mapping")
    _reject_full_tins(data, where)
    _reject_person_name_keys(data, where)

    by_id = {p["id"]: p for p in program_products}
    out: dict[str, ProductSample] = {}
    for pid, block in data["products"].items():
        pwhere = f"{where}.products.{pid}"
        if pid not in by_id:
            raise ConfigError(f"{pwhere}: product not in the program")
        if pid not in overlay_products:
            raise ConfigError(f"{pwhere}: product not in the engagement overlay")
        program_product = by_id[pid]
        segment_ids = {s["id"] for s in
                       overlay_products[pid]["sample_plan"]["segments"]}
        attr_ids = [a["id"] for a in program_product["attributes"]]
        attest_ids = [t["id"] for t in program_product["tests"]
                      if t["kind"] == "attestation"]

        files = tuple(block.get("files", ()))
        seen: set[str] = set()
        for i, f in enumerate(files):
            fwhere = f"{pwhere}.files[{i}]"
            number = str(_require(f, "loan_number", fwhere))
            if number in seen:
                raise ConfigError(f"{fwhere}: duplicate loan_number {number!r}")
            seen.add(number)
            seg = _require(f, "segment", fwhere)
            if seg not in segment_ids:
                raise ConfigError(f"{fwhere}: segment {seg!r} not in the sample plan "
                                  f"({sorted(segment_ids)})")
            for tid in attest_ids:
                value = f.get(tid)
                if value is not None and value not in ATTESTATION_VALUES:
                    raise ConfigError(f"{fwhere}.{tid}: attestation must be one of "
                                      f"{list(ATTESTATION_VALUES)}, got {value!r}")
            stray = set(f) - {"loan_number", "segment"} - set(attr_ids) - set(attest_ids)
            if stray:
                raise ConfigError(f"{fwhere}: unknown fields {sorted(stray)} — files "
                                  f"carry loan_number, segment, attributes, and "
                                  f"attestation values only")

        pool = dict(block.get("pool", {}))
        required = list(BUCKETS)
        if program_product["classification_type"] == "residential_secured":
            # URCCP residential: Substandard is the keyed qualifying >=90-DPD
            # slice (LTV above the policy line); Loss is keyed writedowns.
            required += ["qualifying_90_ltv60", "writedown_loss"]
        for bucket in required:
            entry = pool.get(bucket)
            if not isinstance(entry, dict) or \
                    not isinstance(entry.get("count"), (int, float)) or \
                    not isinstance(entry.get("dollars"), (int, float)):
                raise ConfigError(f"{pwhere}.pool.{bucket}: needs count + dollars")

        out[pid] = ProductSample(product_id=pid, files=files, pool=pool)

    missing = set(by_id) - set(out)
    if missing:
        raise ConfigError(f"{where}: no samples for program products {sorted(missing)}")
    return out
