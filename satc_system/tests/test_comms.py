"""Client-communication library: config validity, merging, and prefill.

Guards three promises the area makes (see :mod:`satc.comms`):
  * every template on disk loads and declares every merge field it uses;
  * a field with no fact behind it is marked visibly, never guessed or blanked;
  * prefill comes from real client state, and carries no full TIN.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from satc.comms import build_context, library, placeholder_names, render, render_key
from satc.comms.library import load_library
from satc.models.identity import PublicClient
from satc.models.work import Job, Task
from satc.models.mart import ReturnRecord
from satc.models.work import Engagement

# The set the practice runs on. A new template is a deliberate act — adding one
# means updating this list, which is the point.
EXPECTED_KEYS = [
    "interview_invite", "engagement_letter", "document_request",
    "missing_items", "prior_year_check", "return_delivery", "cover_letter",
    "invoice_cover",
]


@pytest.fixture(scope="module")
def lib():
    return library()


# --- the config on disk ------------------------------------------------------

def test_every_template_loads(lib):
    assert lib.keys() == EXPECTED_KEYS


def test_templates_are_well_formed(lib):
    for tpl in lib.templates:
        assert tpl.name, f"{tpl.key} has no name"
        assert tpl.description, f"{tpl.key} has no description"
        assert tpl.body.strip(), f"{tpl.key} has an empty body"
        assert tpl.kind in ("email", "letter")
        if tpl.is_email:
            assert tpl.subject, f"{tpl.key} is an email with no subject"


def test_every_merge_field_used_is_declared(lib):
    """A body can never reference a slot nothing knows how to fill."""
    for tpl in lib.templates:
        for name in placeholder_names(tpl):
            assert lib.placeholder(name) is not None, (
                f"{tpl.key} uses {{{name}}}, which configs/comms/templates.yaml "
                f"does not declare")


def test_declared_placeholders_have_a_known_source(lib):
    for p in lib.placeholders.values():
        assert p.source in ("state", "config", "preparer"), p


def test_every_template_says_it_is_a_draft(lib):
    """No draft may read as if the app already sent it."""
    for tpl in lib.templates:
        assert "DRAFT" in tpl.body, f"{tpl.key} lacks its draft notice"


def test_no_template_asks_for_an_unmasked_tin(lib):
    """The only identifier a draft may carry is the masked one."""
    for tpl in lib.templates:
        used = placeholder_names(tpl)
        assert "tin" not in used and "ssn" not in used and "ein" not in used, tpl.key


def test_registry_reads_the_seed_files_without_changing_them(lib):
    """The two seed files still serve satc.drake.comms — we only borrowed them."""
    delivery = lib.template("return_delivery")
    assert delivery.body_file == "delivery_email.txt"
    # Its Subject: first line is lifted into the subject, leaving the body clean.
    assert delivery.subject.startswith("Your {tax_year} tax return is ready")
    assert not delivery.body.lower().startswith("subject:")


def test_stage_grouping_covers_every_template(lib):
    grouped = [t.key for _stage, tpls in lib.by_stage() for t in tpls]
    assert sorted(grouped) == sorted(lib.keys())


def test_load_library_rejects_a_missing_registry(tmp_path):
    from satc.config import ConfigError

    with pytest.raises(ConfigError):
        load_library(tmp_path)


# --- rendering ---------------------------------------------------------------

def test_filled_values_are_merged(lib):
    draft = render_key("document_request", {
        "salutation": "Jordan", "tax_year": "2024", "firm_name": "SATC",
        "requested_items": "  • Your W-2", "due_date": "Apr 15, 2025",
        "preparer_name": "A. Sethuraman", "firm_email": "hello@example.com",
    }, library=lib)
    assert "Dear Jordan," in draft.body
    assert "Your W-2" in draft.body
    assert "2024" in draft.subject
    assert "tax_year" in draft.filled


def test_an_unknown_value_is_marked_not_guessed(lib):
    draft = render_key("document_request", {"salutation": "Jordan"}, library=lib)
    assert "[[ Requested items: fill in ]]" in draft.body
    assert "requested_items" in draft.unfilled
    assert not draft.is_complete
    # The bare slot is gone — a draft never goes out looking like a template.
    assert "{requested_items}" not in draft.body


def test_a_blank_value_counts_as_unfilled(lib):
    """An empty string means "we hold no fact", not "send an empty line"."""
    draft = render_key("document_request", {"requested_items": "   "}, library=lib)
    assert "requested_items" in draft.unfilled


def test_a_block_keeps_its_indentation(lib):
    """Every bullet lines up — including the first, which sits at the slot."""
    draft = render_key("missing_items", {
        "missing_items": "  • 1099-DIV\n  • Form 8879"}, library=lib)
    assert "\n  • 1099-DIV\n  • Form 8879\n" in draft.body


def test_a_single_line_value_is_still_tidied(lib):
    draft = render_key("document_request", {"salutation": "  Jordan  "}, library=lib)
    assert "Dear Jordan," in draft.body


def test_a_complete_draft_reports_itself_complete(lib):
    tpl = lib.template("interview_invite")
    values = {name: f"value for {name}" for name in placeholder_names(tpl)}
    draft = render(tpl, values, library=lib)
    assert draft.is_complete
    assert draft.unfilled == []
    assert "[[" not in draft.body


def test_prose_braces_are_left_alone(lib):
    from satc.comms.library import CommsTemplate

    tpl = CommsTemplate(key="t", name="T", kind="email", description="d",
                        body="Set {THIS} aside; keep {client_name}.", subject="s")
    draft = render(tpl, {"client_name": "Jordan"}, library=lib)
    assert draft.body == "Set {THIS} aside; keep Jordan."


def test_draft_text_puts_the_subject_first(lib):
    draft = render_key("missing_items", {"tax_year": "2024"}, library=lib)
    assert draft.text.startswith("Subject: Still need a few things")


def test_every_template_renders_with_nothing_on_file(lib):
    """The worst case still produces a usable, honestly-marked draft."""
    for tpl in lib.templates:
        draft = render(tpl, {}, library=lib)
        assert draft.body.strip()
        assert "{" not in draft.subject
        assert set(draft.unfilled) == set(placeholder_names(tpl))


# --- prefill from real state -------------------------------------------------

def _public_client(entity_type="INDIVIDUAL"):
    return PublicClient(client_id="SATC-001000", entity_type=entity_type,
                        display_label="Client SATC-001000 (INDIVIDUAL)",
                        tin_last4="1234", tin_masked="***-**-1234",
                        default_return_type="1040", home_state="OH")


def _engagement():
    return Job(
        job_id="ENG-1", client_id="SATC-001000", workflow_key="personal_1040_core",
        engagement_type="1040", tax_year=2024, due_date=date(2025, 4, 15),
        tasks=[
            Task(task_id="T1", job_id="ENG-1", template_id="w2", title="W-2",
                       audience="client", client_request_text="Your W-2 from each employer"),
            Task(task_id="T2", job_id="ENG-1", template_id="rev", title="Review",
                       audience="internal", internal_instructions="Preparer only"),
        ])


def test_context_prefills_from_client_and_engagement():
    values = build_context(
        client_id="SATC-001000", client_name="Jordan Rivera",
        public_client=_public_client(), engagement=_engagement(),
        engagement_name="Individual 1040 — core", today=date(2025, 3, 1))

    assert values["salutation"] == "Jordan"
    assert values["client_name"] == "Jordan Rivera"
    assert values["tax_year"] == "2024"
    assert values["due_date"] == "Apr 15, 2025"
    assert values["date"] == "March 01, 2025"
    assert values["requested_items"] == "  • Your W-2 from each employer"


def test_internal_tasks_never_reach_a_client_draft():
    values = build_context(client_id="SATC-001000", engagement=_engagement())
    assert "Preparer only" not in values["requested_items"]
    assert "Review" not in values["requested_items"]


def test_a_business_is_addressed_by_its_name():
    values = build_context(client_name="Rivera Holdings LLC",
                           public_client=_public_client(entity_type="SCORP"))
    assert values["salutation"] == "Rivera Holdings LLC"


def test_context_omits_what_the_practice_does_not_know():
    """Absent facts stay absent — that is what drives the unfilled marker."""
    values = build_context(client_id="SATC-001000")
    for key in ("requested_items", "missing_items", "fee_amount_text",
                "jurisdiction_summary", "due_date"):
        assert key not in values


def test_the_two_registers_stay_separate_in_a_draft():
    from satc.models.evidence import ReceivedDocument, RequestedItem

    requested = [RequestedItem(request_id="R1", client_id="C", tax_year=2024,
                               doc_type="W-2")]
    received = [
        ReceivedDocument(document_id="D2", client_id="C", tax_year=2024,
                         doc_type="1099-INT"),
        ReceivedDocument(document_id="D3", client_id="C", tax_year=2024,
                         doc_type="Form 8879"),
    ]
    values = build_context(requested=requested, received=received, tax_year=2024)
    assert values["missing_items"] == "  • W-2"
    assert "1099-INT" in values["received_items"]
    assert "Form 8879" in values["received_items"]
    assert "W-2" not in values["received_items"]


def test_return_results_become_a_client_readable_summary():
    returns = [
        ReturnRecord(return_key="R2", client_id="C", tax_year=2024, return_type="1040",
                     jurisdiction="OH", balance_due_amount=Decimal("300")),
        ReturnRecord(return_key="R1", client_id="C", tax_year=2024, return_type="1040",
                     jurisdiction="US", refund_amount=Decimal("1200")),
    ]
    values = build_context(returns=returns, tax_year=2024)
    summary = values["jurisdiction_summary"]
    assert "Federal (1040): REFUND $1,200" in summary
    assert "Ohio (1040): BALANCE DUE $300" in summary
    # Federal leads regardless of the order the records came off the mart.
    assert summary.index("Federal") < summary.index("Ohio")
    assert values["net_result_sentence"] == (
        "Across all jurisdictions you have a net refund of $900.")


def test_a_return_with_no_result_yet_is_not_given_one():
    """Drake produces the numbers; we never invent one to fill the sentence."""
    returns = [ReturnRecord(return_key="R1", client_id="C", tax_year=2024,
                            return_type="1040", jurisdiction="US")]
    values = build_context(returns=returns, tax_year=2024)
    assert "result pending" in values["jurisdiction_summary"]
    assert "net_result_sentence" not in values


def test_returns_are_narrowed_to_the_communication_year():
    returns = [
        ReturnRecord(return_key="R1", client_id="C", tax_year=2023, return_type="1040",
                     jurisdiction="US", refund_amount=Decimal("500")),
        ReturnRecord(return_key="R2", client_id="C", tax_year=2024, return_type="1040",
                     jurisdiction="US", refund_amount=Decimal("1200")),
    ]
    values = build_context(returns=returns, tax_year=2024)
    assert "$1,200" in values["jurisdiction_summary"]
    assert "$500" not in values["jurisdiction_summary"]


def test_fee_prefills_from_the_engagement_record():
    rec = Engagement(client_id="C", tax_year=2024, fee_amount=Decimal("1250"))
    assert build_context(fee_record=rec)["fee_amount_text"] == "$1,250"


def test_firm_values_come_from_config(lib):
    firm = lib.firm_values()
    assert firm["firm_name"] == "Sethuraman Accounting, Tax & Consulting"
    assert firm["preparer_name"]
    values = build_context(firm_values=firm)
    assert values["firm_tagline"] == "Complex work, made clear."


# --- the PII boundary --------------------------------------------------------

def test_a_rendered_draft_carries_no_full_tin(lib):
    """Seam-3: a full SSN/EIN must never reach an outgoing artifact."""
    import re

    values = build_context(
        client_id="SATC-001000", client_name="Jordan Rivera",
        public_client=_public_client(), engagement=_engagement(),
        firm_values=lib.firm_values())
    for tpl in lib.templates:
        draft = render(tpl, values, library=lib)
        assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", draft.text), tpl.key
        assert not re.search(r"\b\d{2}-\d{7}\b", draft.text), tpl.key


def test_the_masked_tin_is_what_reaches_the_engagement_letter(lib):
    values = build_context(client_id="SATC-001000", client_name="Jordan Rivera",
                           public_client=_public_client())
    draft = render(lib.template("engagement_letter"), values, library=lib)
    assert "***-**-1234" in draft.body
