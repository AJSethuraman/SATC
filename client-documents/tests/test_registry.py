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
    "business-letter": "SATC Engagement Letter - Business Return.html",
    "bookkeeping-letter": "SATC Engagement Letter - Bookkeeping.html",
    "fee-estimate": "SATC Fee Estimate.html",
    "invoice": "SATC Invoice.html",
    "onboarding-letter": "SATC Onboarding Letter.html",
    "organizer-letter": "SATC Organizer Cover Letter.html",
    "delivery-letter": "SATC Tax Return Delivery Letter.html",
    "extension-notice": "SATC Extension Notice.html",
    "disengagement-letter": "SATC Disengagement Letter.html",
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


# ── the FIELDS docs agree with the templates ──────────────────────────────

# Registry name -> the companion FIELDS doc. §7 of the authoring contract makes
# the pair the unit of work: a template without its spec is not done.
FIELDS_DOCS = {
    "tax-letter": "FIELDS - Engagement Letter - Tax Preparation.md",
    "business-letter": "FIELDS - Engagement Letter - Business Return.md",
    "bookkeeping-letter": "FIELDS - Engagement Letter - Bookkeeping.md",
    "fee-estimate": "FIELDS - Fee Estimate.md",
    "invoice": "FIELDS - Invoice.md",
    "onboarding-letter": "FIELDS - Onboarding Letter.md",
    "organizer-letter": "FIELDS - Organizer Cover Letter.md",
    "delivery-letter": "FIELDS - Tax Return Delivery Letter.md",
    "extension-notice": "FIELDS - Extension Notice.md",
    "disengagement-letter": "FIELDS - Disengagement Letter.md",
}


@pytest.fixture(scope="module")
def body_fields():
    """The fields a template actually merges, ignoring its on-screen crib.

    `parsed` reads the whole file, and the `<div class="ref">` block at the
    bottom quotes every token in a table. That block is stripped before a
    client ever sees the document (`merge._REF_BLOCK`), so it is the wrong
    thing to hold the specification to.
    """
    out = {}
    for name, filename in TEMPLATES.items():
        html = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
        out[name] = tokens_in(html.split('<div class="ref">')[0])["fields"]
    return out


@pytest.mark.parametrize("name", sorted(FIELDS_DOCS))
def test_the_fields_doc_names_every_field_its_template_merges(name, body_fields):
    """The spec is what a person reads before wiring anything to a template.

    It went stale the moment the firm block moved out of the templates and
    into settings: ten specs still said the address was "not a variable" while
    eight new fields merged it. Nothing caught that, because nothing had ever
    compared the two.
    """
    doc = (TEMPLATE_DIR / FIELDS_DOCS[name]).read_text(encoding="utf-8")
    named = set(re.findall(r"<<([A-Za-z][\w.]*)>>", doc))
    named |= set(re.findall(r'"([A-Z]\w+)":', doc))      # the example payload
    missing = sorted(body_fields[name] - named)
    assert not missing, (
        f"{FIELDS_DOCS[name]} does not mention fields the template merges: {missing}"
    )


@pytest.mark.parametrize("name", sorted(FIELDS_DOCS))
def test_the_fields_doc_field_count_is_true(name, body_fields):
    """A stated total is a claim, and every one of the ten was wrong.

    They drifted by one to three as fields were added and retired over the
    build. The number is small enough to look authoritative and nobody
    recounts it, which is exactly the kind of thing to pin.
    """
    doc = (TEMPLATE_DIR / FIELDS_DOCS[name]).read_text(encoding="utf-8")
    stated = re.search(r"\*\*Total: (\d+) fields", doc)
    assert stated, f"{FIELDS_DOCS[name]} states no total"
    assert int(stated.group(1)) == len(body_fields[name]), (
        f"{FIELDS_DOCS[name]} claims {stated.group(1)} fields; the template "
        f"merges {len(body_fields[name])}"
    )


@pytest.mark.parametrize("name", sorted(FIELDS_DOCS))
def test_a_fields_doc_does_not_call_a_merged_value_hardcoded(name):
    """Every spec carried a "Not variables:" line listing what is typed into
    the template. All ten listed the firm's name, address and website, which
    are now merge fields. The line is useful; a false one is worse than none.
    """
    doc = (TEMPLATE_DIR / FIELDS_DOCS[name]).read_text(encoding="utf-8")
    line = next((l for l in doc.splitlines() if l.startswith("Not variables")), None)
    assert line, f"{FIELDS_DOCS[name]} has no 'Not variables' line"
    for claim in ("firm name", "firm legal name", "office address", "remit-to address",
                  "website", "Ohio LLP footer"):
        assert claim not in line, (
            f"{FIELDS_DOCS[name]} still calls the {claim} hardcoded; it merges "
            f"from firm-settings.yaml"
        )


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
        # Entity signatory fields. Registered and used by the bookkeeping and
        # business-return letters, but out of scope for the tax interview,
        # which covers individual return preparation. They are asked when the
        # entity interview is built.
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


def test_registry_records_the_right_item_fields(parsed, registry):
    """A list's sub-fields must match what its EACH block actually uses.

    `templates` reconciliation catches a renamed field. This catches a renamed
    *sub*-field, which is the same bug one level down and was invisible until a
    template carried two lists with different shapes.
    """
    wrong = {}
    for entry in registry["lists"]:
        for tname in entry["templates"]:
            actual = parsed[tname]["list_items"].get(entry["list"])
            claimed = sorted(entry["item_fields"])
            if actual is None:
                wrong[f"{tname}.{entry['list']}"] = "registered but no EACH block uses it"
            elif sorted(actual) != claimed:
                wrong[f"{tname}.{entry['list']}"] = {"claimed": claimed, "actual": sorted(actual)}
    assert not wrong, f"registry disagrees with the templates about list sub-fields: {wrong}"


def test_every_template_list_is_registered_for_that_template(parsed, registry):
    """A list registered against one template is not registered against another.

    `LineItems` is deliberately listed twice, once per template. The failure
    this catches is a new template using an existing list name and inheriting
    another document's entry by accident.
    """
    registered = {(e["list"], t) for e in registry["lists"] for t in e["templates"]}
    missing = {(l, n) for n, tok in parsed.items() for l in tok["lists"]} - registered
    assert not missing, f"lists used by a template but not registered against it: {sorted(missing)}"


def test_no_registry_has_a_duplicate_key():
    """YAML takes the LAST of two identical keys, silently.

    Found on 26 August 2026 in the rental block: a restructure left the old
    `amount: 45` in place under the new one, so the file said 45 twice, the
    fee writer changed the first and the loader read the second. Nothing
    failed. The price simply would not have moved.

    Cheap to check and impossible to spot by reading a two-thirds-comment
    file, which is exactly the kind of thing a test should hold.
    """
    import collections
    import yaml as _yaml

    seen = []

    class _Loader(_yaml.SafeLoader):
        pass

    def _mapping(loader, node):
        keys = [loader.construct_object(k) for k, _ in node.value]
        seen.extend(k for k, n in collections.Counter(keys).items() if n > 1)
        return loader.construct_mapping(node)

    _Loader.add_constructor(
        _yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

    for path in sorted((ROOT / "registry").glob("*.yaml")):
        seen.clear()
        _yaml.load(path.read_text(encoding="utf-8"), _Loader)
        assert not seen, f"{path.name} declares {sorted(set(seen))} twice"


def test_a_policy_decision_does_not_claim_to_block_a_render():
    """`doctor` reported `hard_no` under "blocks every REAL render" while real
    packs were rendering perfectly well.

    Found 26 August 2026. A readiness tool that overstates what is broken
    teaches whoever reads it to stop believing the parts that are true — and
    this one is the first thing anybody runs.
    """
    import settings as firm

    assert not firm.blocks_render("hard_no")
    assert not firm.blocks_render("hard_no[1]")
    assert firm.blocks_render("delivery.payment_instruction")
    assert firm.blocks_render("materials_deadlines.2026.individual_1040")


def test_nothing_in_POLICY_ONLY_is_merged_by_a_template():
    """The one thing that would make the split a lie.

    A setting listed as policy-only that some template actually merges from
    would render blank or carry a [CONFIRM: to a client, and `doctor` would
    say nothing was wrong.
    """
    import settings as firm

    fields = yaml.safe_load(
        (ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8"))
    named = {f["field"].lower() for f in fields["fields"]}
    for path in firm.POLICY_ONLY:
        leaf = path.split(".")[-1].replace("_", "")
        assert leaf not in named, (
            f"{path} is treated as policy-only but a template merges a field "
            f"by that name — doctor would call it harmless when it is not"
        )


def test_the_template_directory_holds_only_templates():
    """A rendered onboarding letter — real-looking name, street address and all
    — sat in `04-TEMPLATES` for a day, committed by the signing-package work.

    Found 26 August 2026. Nothing caught it because `TEMPLATES` above is an
    explicit dict: every test asks the directory for files it already knows the
    names of, so an extra file is invisible to all of them. A rendered document
    in the template library is one careless copy away from being edited as the
    template, and it is filled with a client's details.

    A template is identifiable without a whitelist: it still carries the
    markers the merge engine substitutes. A render has none left, by
    definition — that is what rendering means, and `render_file` refuses to
    finish while a token survives.
    """
    known = set(TEMPLATES.values()) | {"_SKELETON.html"}
    strays = []
    for path in sorted(TEMPLATE_DIR.glob("*.html")):
        if path.name in known:
            continue
        found = tokens_in(path.read_text(encoding="utf-8"))
        if not (found["fields"] or found["flags"] or found["lists"]):
            strays.append(path.name)
    assert not strays, (
        f"rendered output in the template library: {strays}. "
        "Renders belong in an output directory, not beside the templates."
    )


def _fields_specs():
    """Every list a FIELDS spec declares, as {list name: cardinality phrase}."""
    out = {}
    for path in sorted(TEMPLATE_DIR.glob("FIELDS - *.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*`\[\[EACH (\w+)\]\]`\s*\|([^|]*)\|([^|]*)\|", line)
            if m and m.group(1) != "List":
                out[m.group(1)] = m.group(3).strip().lower()
    return out


def test_every_list_the_spec_calls_one_or_more_is_required_or_says_why():
    """All twelve FIELDS specs say "one or more". Only eight lists were marked
    `required: true`, and nothing recorded whether the other four were decided
    or forgotten.

    Found 26 August 2026. `WorkStatus` was one of the four, on the
    disengagement letter — the document with the most legal exposure in the
    set. Emptied, section 02 "What we completed, and what we did not" renders
    as a heading with no rows, and the sentence under it survives intact:
    "Anything not marked complete above is not filed, not lodged, and not being
    worked on by us. Treat every incomplete item as yours." It points at
    nothing. That is the empty-`RequestList` bug again, on the letter where it
    costs most.

    A list may still be legitimately empty — an extension notice with nothing
    outstanding is a real document. This test does not forbid that. It forbids
    the *silence*: disagree with the spec and write down why, in
    `may_be_empty`, so the next reader can tell a decision from an oversight.
    """
    spec = yaml.safe_load(
        (ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8"))
    declared = _fields_specs()
    assert declared, "no FIELDS specs parsed — the table shape must have changed"

    unexplained = []
    for entry in spec.get("lists") or []:
        name = entry["list"]
        if "one or more" not in declared.get(name, ""):
            continue
        if entry.get("required"):
            continue
        if str(entry.get("may_be_empty") or "").strip():
            continue
        unexplained.append(name)

    assert not unexplained, (
        f"{unexplained}: the FIELDS spec says one or more, the registry does "
        "not require it, and nothing says why. Mark it `required: true`, or "
        "give `may_be_empty:` a reason."
    )


def test_the_disengagement_letter_refuses_an_empty_work_status():
    """The specific instance of the above, pinned so it cannot come back."""
    import merge

    template = (TEMPLATE_DIR / TEMPLATES["disengagement-letter"]).read_text(encoding="utf-8")
    spec = yaml.safe_load(
        (ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8"))
    required = tuple(e["list"] for e in spec["lists"]
                     if e.get("required") and "disengagement-letter" in e["templates"])
    assert "WorkStatus" in required

    payload = json.loads(
        (TEMPLATE_DIR / "FIELDS - Disengagement Letter.md")
        .read_text(encoding="utf-8").split("```json")[1].split("```")[0])
    payload["WorkStatus"] = []
    with pytest.raises(merge.MergeError, match="WorkStatus"):
        merge.render(template, payload, strict=True, required_lists=required)


def test_no_decision_is_still_open_anywhere():
    """26 August 2026: the last `[CONFIRM:` in the firm settings closed, so
    `doctor` reads clean for the first time.

    Pinned deliberately. A readiness tool with one permanent warning on it
    teaches whoever runs it to ignore warnings, and `doctor` is the first
    thing anybody runs. If a new decision opens, this test says so at the
    moment it opens rather than after somebody stops reading the output.

    To open one on purpose: add the `[CONFIRM:` and change this test in the
    same commit, so the choice is visible in the diff.
    """
    import pricing
    import settings as firm

    assert firm.open_decisions() == [], "an unanswered decision is back in the settings"
    assert pricing.open_amounts() == [], "an unpriced item is back in the schedule"
