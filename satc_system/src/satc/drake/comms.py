"""Client communication generator (drafts only — NEVER auto-send).

Turns a parsed Drake preparer set into a per-client delivery package:
  * a refund/balance-due SUMMARY aggregating Federal + every state into one
    client-facing breakdown (per jurisdiction: refund or owed, due date, how to
    pay / where to mail if paper-filed, e-file status);
  * a draft DELIVERY EMAIL and a printable COVER LETTER in SATC voice, templated
    with merge fields.

Everything is produced as a DRAFT for preparer review and logged to the document &
communication repository — nothing is transmitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from satc.drake.preparer_set_parser import PreparerSet

_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "configs" / "comms"

_JURIS_NAME = {"US": "Federal", "OH": "Ohio", "MI": "Michigan", "MA": "Massachusetts"}
_PAY_PORTAL = {
    "US": "IRS Direct Pay (irs.gov/payments)",
    "OH": "the Ohio ID Confirmation / OH|TAX eServices portal",
    "MI": "Michigan Treasury Online (MTO)",
    "MA": "MassTaxConnect",
}


@dataclass(slots=True)
class JurisdictionResult:
    jurisdiction: str
    name: str
    form: str
    method: str
    due_date: str
    refund: float | None
    balance_due: float | None
    mail_to: str
    ef_status: str
    pay_instructions: str


@dataclass(slots=True)
class DeliverySummary:
    client_id: str
    tax_year: int
    results: list[JurisdictionResult] = field(default_factory=list)
    net_refund: float = 0.0
    net_balance_due: float = 0.0


def build_delivery_summary(ps: PreparerSet) -> DeliverySummary:
    ef_by_juris = {e.jurisdiction: e for e in ps.ef_statuses}
    summary = DeliverySummary(client_id=ps.client_id, tax_year=ps.tax_year)
    for fi in ps.filing_instructions:
        ef = ef_by_juris.get(fi.jurisdiction)
        if fi.filing_method == "paper":
            pay = (f"Mail your signed return and payment to: {fi.mail_to}" if fi.balance_due
                   else f"Mail your signed return to: {fi.mail_to}")
        else:
            pay = (f"Pay online at {_PAY_PORTAL.get(fi.jurisdiction, 'the state portal')} "
                   f"or mail a payment voucher" if fi.balance_due else "Refund will be direct-deposited / mailed")
        summary.results.append(JurisdictionResult(
            jurisdiction=fi.jurisdiction, name=_JURIS_NAME.get(fi.jurisdiction, fi.jurisdiction),
            form=fi.form, method=fi.filing_method, due_date=fi.due_date,
            refund=fi.refund, balance_due=fi.balance_due, mail_to=fi.mail_to,
            ef_status=(f"{ef.status} {ef.date}".strip() if ef else "pending"),
            pay_instructions=pay))
        summary.net_refund += fi.refund or 0.0
        summary.net_balance_due += fi.balance_due or 0.0
    return summary


def _money(x: float | None) -> str:
    return f"${x:,.0f}" if x else "$0"


def summary_lines(summary: DeliverySummary) -> list[str]:
    """One human-readable line per jurisdiction (Federal + each state)."""
    lines = []
    for r in summary.results:
        if r.refund:
            head = f"{r.name} ({r.form}): REFUND {_money(r.refund)}"
        elif r.balance_due:
            head = f"{r.name} ({r.form}): BALANCE DUE {_money(r.balance_due)} — due {r.due_date}"
        else:
            head = f"{r.name} ({r.form}): no balance due / no refund"
        method = "PAPER FILED" if r.method == "paper" else f"e-file ({r.ef_status})"
        lines.append(f"  • {head}  [{method}]. {r.pay_instructions}.")
    return lines


def _net_sentence(summary: DeliverySummary) -> str:
    net = summary.net_refund - summary.net_balance_due
    if net > 0:
        return f"Across all jurisdictions you have a net refund of {_money(net)}."
    if net < 0:
        return f"Across all jurisdictions you owe a net balance of {_money(-net)}."
    return "Across all jurisdictions your refunds and balances net to zero."


def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_delivery_email(summary: DeliverySummary, *, salutation: str,
                          preparer_name: str = "Your SATC preparer") -> str:
    return _load_template("delivery_email.txt").format(
        tax_year=summary.tax_year, salutation=salutation, preparer_name=preparer_name,
        jurisdiction_summary="\n".join(summary_lines(summary)),
        net_result_sentence=_net_sentence(summary))


def render_cover_letter(summary: DeliverySummary, *, salutation: str,
                        preparer_name: str = "Your SATC preparer",
                        as_of: date | None = None) -> str:
    return _load_template("cover_letter.txt").format(
        date=(as_of or date.today()).strftime("%B %d, %Y"), tax_year=summary.tax_year,
        client_id=summary.client_id, salutation=salutation, preparer_name=preparer_name,
        jurisdiction_summary="\n".join(summary_lines(summary)),
        net_result_sentence=_net_sentence(summary))
