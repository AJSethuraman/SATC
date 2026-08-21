"""Reconcile the templates, the field registry and the interview schema.

The point of these tests is that the three cannot drift apart silently. A
template gaining a field, or the interview gaining a question nothing consumes,
fails the build here rather than at a client.

Run:  cd client-documents && python -m pytest -q
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from merge import tokens_in  # noqa: E402

TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"

# Registry name -> template file. Kept explicit so a renamed template fails
# loudly instead of silently dropping out of the reconciliation.
TEMPLATES = {
    "tax-letter": "SATC Engagement Letter - Tax Preparation.html",
    "bookkeeping-letter": "SATC Engagement Letter - Bookkeeping.html",
    "fee-estimate": "SATC Fee Estimate.html",
    "invoice": "SATC Invoice.html",
    "onboarding-letter": "SATC Onboarding Letter.html",
    "organizer-letter": "SATC Organizer Cover Letter.html",
}


@pytest.fixture(scope="module")
def registry():
    return yaml.safe_load((ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def interview():
    return yaml.safe_load((ROOT / "registry" / "interview.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parsed():
    out = {}
    for name, filename in TEMPLATES.items():
        path = TEMPLATE_DIR / filename
        assert path.exists(), f"template missing: {filename}"
        out[name] = tokens_in(path.read_text(encoding="utf-8"))
    return out


def _registry_fields(registry):
    return {e["field"]: e for e in registry["fields"]}


# ── every token has a home ────────────────────────────────────────────────

def test_every_template_field_is_registered(parsed, registry):
    known = set(_registry_fields(registry))
    missing = {}
    for name, tok in parsed.items():
        gap = tok["fields"] - known
        if gap:
            missing[name] = sorted(gap)
    assert not missing, (
        "templates use fields the registry does not know about — add them, "
        f"do not silently ignore: {missing}"
    )


def test_every_flag_and_list_is_registered(parsed, registry):
    flags = {e["flag"] for e in registry["flags"]}
    lists = {e["list"] for e in registry["lists"]}
    for name, tok in parsed.items():
        assert not (tok["flags"] - flags), f"{name}: unregistered flags {tok['flags'] - flags}"
        assert not (tok["lists"] - lists), f"{name}: unregistered lists {tok['lists'] - lists}"


def test_registry_records_the_right_templates(parsed, registry):
    """A field's `templates` list must match where it is actually used."""
    wrong = {}
    for entry in _registry_fields(registry).values():
        actual = {n for n, tok in parsed.items() if entry["field"] in tok["fields"]}
        claimed = set(entry["templates"])
        if actual != claimed:
            wrong[entry["field"]] = {"claimed": sorted(claimed), "actual": sorted(actual)}
    assert not wrong, f"registry disagrees with the templates: {wrong}"


def test_no_orphan_registry_fields(parsed, registry):
    used = set().union(*(t["fields"] for t in parsed.values()))
    orphans = set(_registry_fields(registry)) - used
    assert not orphans, f"registry lists fields no template uses: {sorted(orphans)}"


# ── the interview and the registry agree, in both directions ──────────────

def _interview_questions(interview):
    for section in interview["sections"]:
        for q in section["questions"]:
            yield section["id"], q


def test_every_interview_field_has_a_question(registry, interview):
    """A field the registry says a human supplies must actually be asked."""
    supplied = set()
    for _, q in _interview_questions(interview):
        supplied.update(q.get("supplies") or [])

    expected = {
        e.get("field") or e.get("flag")
        for e in registry["fields"] + registry["flags"]
        if e.get("source") == "interview"
        # Bookkeeping-only signatory fields are registered but out of scope for
        # the tax interview; they are asked when that interview is built.
        and (e.get("field") or e.get("flag")) not in {"SignerName", "SignerTitle"}
    }
    missing = expected - supplied
    assert not missing, f"registry marks these `interview` but nothing asks for them: {sorted(missing)}"


def _registry_targets(registry):
    """Everything a question may legitimately supply: fields, flags and lists."""
    return (set(_registry_fields(registry))
            | {e["flag"] for e in registry["flags"]}
            | {e["list"] for e in registry["lists"]})


def test_every_question_earns_its_place(registry, interview):
    """No question exists that no template consumes, unless tagged internal."""
    known = _registry_targets(registry)
    stray = []
    for section_id, q in _interview_questions(interview):
        supplies = q.get("supplies") or []
        if supplies:
            unknown = set(supplies) - known
            assert not unknown, f"{q['id']} supplies unknown fields {sorted(unknown)}"
            continue
        if q.get("feeds"):          # feeds a computed list, e.g. LineItems
            continue
        if q.get("internal"):
            assert q.get("internal_reason"), f"{q['id']} is internal with no reason given"
            continue
        stray.append(f"{section_id}.{q['id']}")
    assert not stray, (
        "questions that supply nothing and are not tagged internal — either map "
        f"them to a field or say why they exist: {stray}"
    )


def test_showif_references_a_real_question(interview):
    ids = {q["id"] for _, q in _interview_questions(interview)}
    bad = []
    for _, q in _interview_questions(interview):
        cond = q.get("showIf")
        if not cond:
            continue
        referenced = set(re.findall(r"\b([a-z][a-z0-9_]*)\b", cond)) - {"in", "and", "or", "not"}
        if not (referenced & ids):
            bad.append((q["id"], cond))
    assert not bad, f"showIf conditions referencing no known question: {bad}"


# ── the PII guard ─────────────────────────────────────────────────────────

TIN_PATTERNS = re.compile(r"ssn|itin|\bein\b|\btin\b|taxid|tax_id|social.?security", re.I)
TIN_VALUE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{2}-\d{7}\b")


def test_no_field_can_hold_a_tin(registry, interview):
    """A guard, not a convention.

    The record lives in OneDrive. Identifiers belong in Drake and in
    satc_system's encrypted vault, per CLAUDE.md — never here.
    """
    offenders = [e["field"] for e in registry["fields"] if TIN_PATTERNS.search(e["field"])]
    for _, q in _interview_questions(interview):
        blob = " ".join(str(q.get(k, "")) for k in ("id", "question", "help"))
        if TIN_PATTERNS.search(blob):
            offenders.append(q["id"])
    assert not offenders, f"fields or questions that could carry a TIN: {offenders}"


def test_no_sample_contains_a_real_looking_tin():
    for path in (ROOT / "samples").glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not TIN_VALUE.search(text), f"{path.name} contains something shaped like a TIN"


# ── naming ────────────────────────────────────────────────────────────────

def test_field_names_are_pascal_case(registry):
    """The authoring contract requires PascalCase, no spaces, no underscores."""
    bad = [e["field"] for e in registry["fields"]
           if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", e["field"])]
    assert not bad, f"field names violating the authoring contract: {bad}"


def test_shared_fields_are_named_identically(parsed):
    """The same concept under two names is the failure this catches."""
    lowered = {}
    for tok in parsed.values():
        for f in tok["fields"]:
            lowered.setdefault(f.lower(), set()).add(f)
    clashes = {k: sorted(v) for k, v in lowered.items() if len(v) > 1}
    assert not clashes, f"same field, different spellings across templates: {clashes}"
