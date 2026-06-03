"""Template builder — author linesheet templates en masse.

Turns a compact spec (a few lines of `q(...)` / `section(...)`) into a fully
valid template that round-trips through `template_engine.load_template_yaml`.
Includes a small preset library of reusable sections so new templates can be
assembled quickly, and a starter catalog.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .models import Template
from .template_engine import validate_template_structure

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "configs" / "templates"

_OPTIONAL = ("source_field", "applies_if", "exception_if", "warning_if",
             "evidence_required_if", "help_text", "options")


def q(question_id: str, question_text: str, answer_type: str = "yes_no_na",
      required: bool = False, **kw) -> dict:
    """One question. Extra keys: source_field, applies_if, exception_if,
    warning_if, evidence_required_if, severity, options, help_text,
    data_mart_field, export_label."""
    d = {"question_id": question_id, "question_text": question_text,
         "answer_type": answer_type, "required": required}
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


def section(section_id: str, section_name: str, questions: list[dict]) -> dict:
    return {"section_id": section_id, "section_name": section_name, "questions": questions}


CALC_MODULES = ["cash_flow", "dti", "collateral", "dscr", "guarantor", "global", "leverage"]


def build_template(template_id: str, template_name: str, sections: list[dict],
                   version: str = "1.0", modules: list[str] | None = None) -> Template:
    """Assemble and validate a Template from a compact spec. Display orders and
    data_mart_field / export_label defaults are filled in automatically."""
    sec_models = []
    for si, sec in enumerate(sections, start=1):
        qs = []
        for qi, qd in enumerate(sec["questions"], start=1):
            qd = dict(qd)
            qd.setdefault("display_order", qi)
            qd.setdefault("data_mart_field", qd["question_id"].lower())
            qd.setdefault("export_label", qd["question_text"])
            qs.append(qd)
        sec_models.append({"section_id": sec["section_id"], "section_name": sec["section_name"],
                           "display_order": sec.get("display_order", si), "questions": qs})
    template = Template.model_validate({"template_id": template_id, "template_name": template_name,
                                        "version": version, "sections": sec_models, "modules": modules or []})
    validate_template_structure(template)
    return template


def _question_dict(qm) -> dict:
    d = {"display_order": qm.display_order, "question_id": qm.question_id,
         "question_text": qm.question_text, "answer_type": qm.answer_type, "required": qm.required}
    for f in ("source_field", "applies_if", "exception_if", "warning_if", "evidence_required_if"):
        if getattr(qm, f):
            d[f] = getattr(qm, f)
    if (qm.exception_if or qm.warning_if) and qm.severity:
        d["severity"] = qm.severity
    if qm.options:
        d["options"] = list(qm.options)
    if qm.help_text:
        d["help_text"] = qm.help_text
    d["data_mart_field"] = qm.data_mart_field
    d["export_label"] = qm.export_label
    return d


def template_to_dict(template: Template) -> dict:
    d = {"template_id": template.template_id, "template_name": template.template_name,
         "version": template.version}
    if getattr(template, "modules", None):
        d["modules"] = list(template.modules)
    d["sections"] = [{"section_id": s.section_id, "section_name": s.section_name,
                      "display_order": s.display_order,
                      "questions": [_question_dict(x) for x in s.questions]}
                     for s in template.sections]
    return d


def write_template_yaml(template: Template, path: str | Path) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(template_to_dict(template), sort_keys=False,
                                         default_flow_style=False, allow_unicode=True))
    return str(path)


def generate_templates(templates: list[Template], out_dir: str | Path = TEMPLATES_DIR) -> list[str]:
    """Write many templates to YAML at once. Returns the paths written."""
    out_dir = Path(out_dir)
    return [write_template_yaml(t, out_dir / f"{t.template_id}.yaml") for t in templates]


# --- Reusable section presets ------------------------------------------------
def preset_borrower() -> dict:
    return section("borrower", "Borrower / Relationship", [
        q("BR1", "Is the borrower identity documented and consistent with the application?",
          required=True, source_field="borrower_name", exception_if='answer == "No"',
          severity="Finding", evidence_required_if='answer == "No"',
          help_text="Confirm identity against source."),
        q("BR2", "Relationship / background summary", "long_text",
          help_text="Summarize the relationship and purpose."),
    ])


def preset_employment_income() -> dict:
    return section("employment_income", "Employment & Income", [
        q("EI1", "Is income documented and verified (paystub / W-2 / tax returns)?",
          required=True, exception_if='answer == "No"', severity="Finding",
          evidence_required_if='answer == "No"', help_text="Verify per the Cash Flow worksheet."),
        q("EI2", "Income type", "select", required=True,
          options=["Salaried / W-2", "Self-employed", "Mixed", "Fixed / retirement"],
          help_text="Drives the averaging method on the Cash Flow tab."),
        q("EI3", "Qualifying monthly income", "currency", required=True,
          help_text="From the Cash Flow / Income Analysis worksheet."),
    ])


def preset_atr() -> dict:
    return section("ability_to_repay", "Ability to Repay", [
        q("AR1", "Is the back-end DTI within guideline?", required=True,
          warning_if='answer == "No"', severity="Finding",
          help_text="See the Ability-to-Repay (DTI) worksheet."),
        q("AR2", "Is residual income adequate?", required=True,
          warning_if='answer == "No"', severity="Needs Review"),
        q("AR3", "ATR conclusion", "select", required=True,
          options=["Within guidelines", "Exception documented", "Does not qualify"]),
    ])


def preset_collateral_property() -> dict:
    return section("collateral", "Collateral / Property", [
        q("CO1", "Is collateral value supported (appraisal / valuation)?", required=True,
          exception_if='answer == "No"', severity="Finding", evidence_required_if='answer == "No"'),
        q("CO2", "Is LTV / CLTV within policy?", required=True,
          warning_if='answer == "No"', severity="Finding"),
        q("CO3", "Lien position", "select", required=False,
          options=["First", "Second", "Unsecured", "Other"]),
    ])


def preset_documentation() -> dict:
    return section("documentation", "Documentation & Compliance", [
        q("DC1", "Are required disclosures present and timely?", required=True,
          exception_if='answer == "No"', severity="Finding", evidence_required_if='answer == "No"'),
        q("DC2", "Documents reviewed", "multi_select", required=False,
          options=["Application", "Income docs", "Disclosures", "Appraisal", "Title / lien", "Insurance"]),
    ])


def preset_conclusion_signoff() -> dict:
    return section("conclusion", "Conclusion & Signoff", [
        q("CN1", "Does the conclusion support the assigned rating?", required=True,
          exception_if='answer == "No"', severity="Blocked", evidence_required_if='answer == "No"'),
        q("CN2", "Overall review rating", "select", required=True,
          options=["Pass", "Pass with Findings", "Needs Review", "Does Not Qualify"]),
        q("CN3", "Reviewer signoff completed?", required=True,
          exception_if='answer == "No"', severity="Blocked"),
    ])


# --- Starter catalog (demonstrates building custom sheets en masse) -----------
def catalog() -> list[Template]:
    consumer_mortgage = build_template(
        "consumer_mortgage_atr_v1", "Consumer Mortgage — Ability to Repay",
        [preset_borrower(), preset_employment_income(), preset_atr(),
         preset_collateral_property(), preset_documentation(), preset_conclusion_signoff()],
        modules=["cash_flow", "dti", "collateral"])

    heloc = build_template(
        "consumer_heloc_v1", "Consumer HELOC Review",
        [preset_borrower(), preset_employment_income(), preset_atr(),
         section("property", "Property / Equity", [
             q("PR1", "Is combined LTV within HELOC policy?", required=True,
               warning_if='answer == "No"', severity="Finding"),
             q("PR2", "Is the property owner-occupied?", required=True),
             q("PR3", "Available equity", "currency", required=False)]),
         preset_documentation(), preset_conclusion_signoff()],
        modules=["cash_flow", "dti", "collateral"])

    auto = build_template(
        "consumer_auto_v1", "Consumer Auto / Installment",
        [preset_borrower(),
         section("income", "Income", [
             q("IN1", "Is income documented?", required=True, exception_if='answer == "No"',
               severity="Finding", evidence_required_if='answer == "No"'),
             q("IN2", "Qualifying monthly income", "currency", required=True)]),
         preset_atr(),
         section("collateral_auto", "Vehicle / Collateral", [
             q("VA1", "Is the vehicle value supported (book value)?", required=True,
               warning_if='answer == "No"', severity="Finding"),
             q("VA2", "Loan-to-value", "percent", required=True,
               exception_if='value > 120', severity="Finding")]),
         preset_conclusion_signoff()],
        modules=["cash_flow", "dti", "collateral"])

    small_business = build_template(
        "small_business_v1", "Small Business Credit",
        [preset_borrower(),
         section("business_cash_flow", "Business Cash Flow", [
             q("BC1", "Is business cash flow documented (tax returns / K-1)?", required=True,
               exception_if='answer == "No"', severity="Finding", evidence_required_if='answer == "No"'),
             q("BC2", "Global DSCR acceptable?", required=True, warning_if='answer == "No"', severity="Finding"),
             q("BC3", "Qualifying global cash flow (monthly)", "currency", required=True,
               help_text="From the Cash Flow / Income Analysis worksheet (distributions basis).")]),
         preset_collateral_property(),
         section("guarantors", "Guarantors", [
             q("GU1", "Are guarantor obligations documented?", required=True,
               warning_if='answer == "No"', severity="Warning"),
             q("GU2", "Personal guarantee obtained?", required=True)]),
         preset_documentation(), preset_conclusion_signoff()],
        modules=["cash_flow", "dscr", "guarantor", "global", "collateral", "leverage"])

    return [consumer_mortgage, heloc, auto, small_business]


def write_catalog(out_dir: str | Path = TEMPLATES_DIR) -> list[str]:
    return generate_templates(catalog(), out_dir)
