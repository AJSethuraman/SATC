"""Turning real practice state into merge values.

This is the "prefill from what we actually know" piece. It takes plain records —
the client's vault-side name, their de-identified projection, their returns,
their document register, their newest engagement — and produces the merge
dictionary :mod:`satc.comms.render` consumes.

Two constraints hold it in shape:

* **Only facts on file.** A field we hold nothing for is simply absent from the
  returned dict, which is how the renderer knows to mark it unfilled. Nothing
  here fabricates a plausible-looking value.
* **Masked identifiers only.** ``tin_masked`` comes from
  :class:`~satc.models.identity.PublicClient`, which never holds a full TIN. A
  client's name is vault-side and belongs in a letter addressed to them; their
  SSN never does.

Kept free of Flask and of :data:`satc.app.state.STATE` so it tests as a function.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from satc.drake.comms import JURISDICTION_NAMES

# Statuses in the document register that mean "still waiting" / "in hand".
_OUTSTANDING = {"Requested"}
_IN_HAND = {"Received", "Signed"}

_BULLET = "  • "


def _money(amount) -> str:
    """A whole-dollar money string, or ``""`` when there's no amount."""
    if amount is None:
        return ""
    try:
        value = Decimal(str(amount))
    except (ValueError, ArithmeticError):
        return ""
    return f"${value:,.0f}"


def _salutation(client_name: str, entity_type: str = "") -> str:
    """How to address the client: first name for a person, the name for a business."""
    name = (client_name or "").strip()
    if not name:
        return ""
    if entity_type and entity_type != "INDIVIDUAL":
        return name
    return name.split()[0]


def _bullets(lines) -> str:
    """A bullet block, or ``""`` when there's nothing to list."""
    items = [str(line).strip() for line in lines if str(line).strip()]
    return "\n".join(_BULLET + item for item in items)


def _jurisdiction_order(ret) -> tuple[int, str]:
    """Federal leads, then states by name — how a client expects to read it."""
    juris = getattr(ret, "jurisdiction", "")
    return (0 if juris == "US" else 1, JURISDICTION_NAMES.get(juris, juris))


def _jurisdiction_lines(returns) -> list[str]:
    """One plain-language result line per return on file."""
    lines: list[str] = []
    for ret in sorted(returns, key=_jurisdiction_order):
        name = JURISDICTION_NAMES.get(ret.jurisdiction, ret.jurisdiction)
        label = f"{name} ({ret.return_type})"
        refund = _money(getattr(ret, "refund_amount", None))
        balance = _money(getattr(ret, "balance_due_amount", None))
        if refund and refund != "$0":
            lines.append(f"{label}: REFUND {refund}")
        elif balance and balance != "$0":
            lines.append(f"{label}: BALANCE DUE {balance}")
        else:
            # A return with no stored result yet is worth naming, but we do not
            # claim a number Drake hasn't produced.
            lines.append(f"{label}: result pending")
    return lines


def _net_sentence(returns) -> str:
    """The across-all-jurisdictions sentence — only when some result exists."""
    refunds = sum((Decimal(str(r.refund_amount)) for r in returns
                   if getattr(r, "refund_amount", None) is not None), Decimal("0"))
    balances = sum((Decimal(str(r.balance_due_amount)) for r in returns
                    if getattr(r, "balance_due_amount", None) is not None), Decimal("0"))
    if not refunds and not balances:
        return ""
    net = refunds - balances
    if net > 0:
        return f"Across all jurisdictions you have a net refund of {_money(net)}."
    if net < 0:
        return f"Across all jurisdictions you owe a net balance of {_money(-net)}."
    return "Across all jurisdictions your refunds and balances net to zero."


def _client_requests(engagement) -> list[str]:
    """The client-facing asks on an engagement, in the words the client reads."""
    if engagement is None:
        return []
    out: list[str] = []
    for task in getattr(engagement, "tasks", None) or []:
        if getattr(task, "audience", "") != "client":
            continue
        text = (getattr(task, "client_request_text", "") or getattr(task, "title", "")).strip()
        if text and text not in out:
            out.append(text)
    return out


def _doc_lines(documents, statuses: set[str]) -> list[str]:
    out: list[str] = []
    for doc in documents:
        if str(getattr(doc, "status", "")) not in statuses:
            continue
        label = (getattr(doc, "doc_type", "") or "").strip()
        if label and label not in out:
            out.append(label)
    return out


def build_context(
    *,
    client_id: str = "",
    client_name: str = "",
    public_client=None,
    returns=(),
    documents=(),
    engagement=None,
    fee_record=None,
    engagement_name: str = "",
    tax_year: int | None = None,
    today: date | None = None,
    firm_values: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build the merge dictionary for one client.

    Every key is omitted (not blanked) when the practice holds no fact for it, so
    the renderer marks it unfilled rather than sending an empty gap. ``returns``
    and ``documents`` should already be narrowed to this client; when ``tax_year``
    resolves, they are narrowed to that year here.
    """
    values: dict[str, str] = dict(firm_values or {})
    today = today or date.today()
    entity_type = str(getattr(public_client, "entity_type", "") or "")

    # -- identity (masked identifiers only) -----------------------------------
    if client_id:
        values["client_id"] = client_id
    if client_name:
        values["client_name"] = client_name
        values["salutation"] = _salutation(client_name, entity_type)
    masked = str(getattr(public_client, "tin_masked", "") or "")
    if masked:
        values["tin_masked"] = masked

    # -- the year this communication is about ---------------------------------
    year = tax_year
    if year is None:
        year = getattr(engagement, "tax_year", None)
    if year is None:
        years = [r.tax_year for r in returns if getattr(r, "tax_year", None)]
        year = max(years) if years else None
    if year:
        values["tax_year"] = str(year)
        returns = [r for r in returns if getattr(r, "tax_year", None) == year]
        year_docs = [d for d in documents if getattr(d, "tax_year", None) == year]
        # Only narrow the register when that year actually has documents —
        # otherwise a mis-keyed year would silently empty the list.
        documents = year_docs or documents

    values["date"] = today.strftime("%B %d, %Y")

    # -- the engagement -------------------------------------------------------
    if engagement_name:
        values["engagement_name"] = engagement_name
    elif getattr(engagement, "engagement_type", ""):
        values["engagement_name"] = engagement.engagement_type
    due = getattr(engagement, "due_date", None)
    if due is not None:
        from satc.intake.outputs import format_output_date
        formatted = format_output_date(due)
        if formatted:
            values["due_date"] = formatted

    # -- document tracking ----------------------------------------------------
    requests = _bullets(_client_requests(engagement))
    if requests:
        values["requested_items"] = requests
    missing = _bullets(_doc_lines(documents, _OUTSTANDING))
    if missing:
        values["missing_items"] = missing
    received = _bullets(_doc_lines(documents, _IN_HAND))
    if received:
        values["received_items"] = received

    # -- the finished return --------------------------------------------------
    if returns:
        values["jurisdiction_summary"] = "\n".join(_jurisdiction_lines(returns))
    net = _net_sentence(returns)
    if net:
        values["net_result_sentence"] = net

    # -- money ----------------------------------------------------------------
    fee = _money(getattr(fee_record, "fee_amount", None))
    if fee:
        values["fee_amount_text"] = fee

    return values
