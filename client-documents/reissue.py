"""The re-issue email: what changed on a return after it went to the client.

The firm, 13 Oct 2026: "we should have a re-issue email template - it reminds
them to sign and pay if they have not already and explains what we changed.
some will have to be freehand but this is not - you can figure out what changed
on results then you can summarize what we did".

So this module compares the earlier results summary with the new one (Drake's
table: return, refund or balance due, transaction method), decides from the
figures whether the IRS needs a new signature, and hands `SATC Re-issue
Email.html` its fields. It writes no client-facing sentence of its own: the
email's words are in the template, and the result phrases are in
`registry/results-wording.yaml` (DOCUMENT-TENETS T28).

THE RE-SIGN RULE (IRS Pub 1345). A new Form 8879 is needed if, after the
taxpayer signed, the return changes by more than $50 to total income or AGI,
or by more than $14 to total tax, federal income tax withheld, the refund or
the amount owed. Comparing the figures decides; a missing figure that could
change the answer stops the build rather than letting it guess.
"""
from __future__ import annotations

import email.policy
import html as _html
import re
from email.charset import BASE64, Charset
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import yaml

import merge

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT.parent / "satc-handoff" / "04-TEMPLATES" / "SATC Re-issue Email.html"
WORDING = ROOT / "registry" / "results-wording.yaml"

#: Pub 1345 thresholds -- a change MORE than these needs a new signature.
INCOME_THRESHOLD = 50
TAX_THRESHOLD = 14
INCOME_FIGURES = ("total_income", "agi")
TAX_FIGURES = ("total_tax", "withholding")

#: Drake's "Transaction Method" wording, and what each one means here.
_METHODS = {
    "direct deposit": "deposit", "deposit": "deposit", "dd": "deposit",
    "check": "check", "paper check": "check", "mail check": "check",
    "mail a check": "check", "mail payment": "check",
    "efw": "withdrawal", "withdrawal": "withdrawal",
    "electronic funds withdrawal": "withdrawal", "direct debit": "withdrawal",
    "": "",
}


class ReissueError(ValueError):
    """The inputs cannot produce a correct email; the message says what to supply."""


def _wording() -> dict:
    return yaml.safe_load(WORDING.read_text(encoding="utf-8"))


def _dollars(amount) -> str:
    """Whole dollars when the figure is whole -- Drake rounds returns to the dollar."""
    value = round(float(amount), 2)
    return f"${value:,.0f}" if value == int(value) else f"${value:,.2f}"


def _kind(entry: dict) -> str:
    kind = str(entry.get("result", "")).strip().lower().replace(" due", "")
    if kind not in ("refund", "balance", "none", "nothing"):
        raise ReissueError(f"{entry.get('return')!r}: result must be refund, balance "
                           f"or none, not {entry.get('result')!r}")
    if kind in ("refund", "balance") and not float(entry.get("amount") or 0):
        return "nothing"
    return "nothing" if kind == "none" else kind


def _method(entry: dict) -> str:
    raw = str(entry.get("method", "")).strip().lower()
    if raw not in _METHODS:
        raise ReissueError(f"{entry.get('return')!r}: unknown transaction method {raw!r}")
    return _METHODS[raw]


def summary_line(entry: dict, words: dict | None = None) -> str:
    """One return's result, as the delivery and the summary print it."""
    words = words or _wording()
    kind, method = _kind(entry), _method(entry)
    if kind == "nothing":
        return words["summary"]["nothing"]
    key = {("refund", "deposit"): "refund_deposit", ("refund", "check"): "refund_check",
           ("balance", "check"): "balance_check",
           ("balance", "withdrawal"): "balance_withdrawal"}.get((kind, method))
    if key is None:
        raise ReissueError(f"{entry.get('return')!r}: a {kind} cannot be paid by {method or 'no method'}")
    account = str(entry.get("account") or "")
    if "{account}" in words["summary"][key] and not account:
        raise ReissueError(f"{entry.get('return')!r}: which account does the {kind} use?")
    return words["summary"][key].format(amount=_dollars(entry["amount"]), account=account)


def short_line(entry: dict, words: dict | None = None) -> str:
    words = words or _wording()
    kind = _kind(entry)
    if kind == "nothing":
        return words["short"]["nothing"]
    return words["short"][kind].format(amount=_dollars(entry["amount"]))


def _signed(entry: dict | None) -> tuple[float, float]:
    """(refund, owed) for one return."""
    if not entry:
        return 0.0, 0.0
    kind = _kind(entry)
    amount = float(entry.get("amount") or 0)
    return (amount, 0.0) if kind == "refund" else (0.0, amount) if kind == "balance" else (0.0, 0.0)


def needs_new_signature(before: dict, after: dict) -> bool:
    """Does the IRS need a new Form 8879? From the figures, per Pub 1345.

    ``before``/``after`` are the federal figures: ``total_income``, ``agi``,
    ``total_tax``, ``withholding``, and the federal return's result. A change
    in the refund or amount owed of more than $14 decides it on its own; any
    other answer needs every figure, because a missing one could be the one
    that crossed the line.
    """
    r0, o0 = _signed(before.get("result"))
    r1, o1 = _signed(after.get("result"))
    if abs(r1 - r0) > TAX_THRESHOLD or abs(o1 - o0) > TAX_THRESHOLD:
        return True
    missing = [k for k in INCOME_FIGURES + TAX_FIGURES
               if before.get(k) is None or after.get(k) is None]
    if missing:
        raise ReissueError(
            "the refund and amount owed moved by $14 or less, so whether the IRS "
            "needs a new signature depends on the other figures. Supply the "
            f"earlier and new federal {', '.join(missing)} (from Drake's return summary).")
    if any(abs(float(after[k]) - float(before[k])) > INCOME_THRESHOLD for k in INCOME_FIGURES):
        return True
    return any(abs(float(after[k]) - float(before[k])) > TAX_THRESHOLD for k in TAX_FIGURES)


def _federal(results: dict) -> dict:
    fed = next((r for r in results.get("returns", []) if str(r.get("return", "")).lower().startswith("federal")), None)
    if fed is None:
        raise ReissueError("no federal return in the results summary")
    return {**(results.get("federal") or {}), "result": fed}


def build(record: dict, spec: dict) -> dict:
    """The re-issue email's fields, from the engagement record and the change spec."""
    words = _wording()
    before = {r["return"]: r for r in spec["before"]["returns"]}
    after_list = spec["after"]["returns"]
    reasons = spec.get("reasons") or {}

    changes = []
    for entry in after_list:
        old = before.get(entry["return"])
        if old is None or short_line(old, words) != short_line(entry, words) \
                or summary_line(old, words) != summary_line(entry, words):
            reason = str(reasons.get(entry["return"], "")).strip()
            if not reason:
                raise ReissueError(f"{entry['return']} changed; say why in reasons[{entry['return']!r}]")
            # Same amount, different method (a new account): the short form
            # would read "$310 refund" twice, so show the full lines.
            same_amount = old is not None and short_line(old, words) == short_line(entry, words)
            line = summary_line if same_amount else short_line
            changes.append({"Return": entry["return"], "Reason": reason,
                            "Before": line(old, words) if old else words["short"]["nothing"],
                            "After": line(entry, words)})
    gone = [name for name in before if name not in {e["return"] for e in after_list}]
    if gone:
        raise ReissueError(f"returns in the earlier summary are missing from the new one: {gone}")

    others = [{"Label": o["label"], "Detail": o["detail"]} for o in spec.get("other_changes") or []]
    freehand = str(spec.get("freehand") or "").strip()
    if not (changes or others or freehand):
        raise ReissueError("nothing changed: no result moved, and no other change or explanation was given")

    raised = str(spec.get("client_raised") or "").strip()
    if raised and "client_was_right" not in spec:
        raise ReissueError("the client raised it: say whether they were right (client_was_right)")
    right = bool(spec.get("client_was_right"))

    resign = needs_new_signature(_federal(spec["before"]), _federal(spec["after"]))
    joint = bool(record.get("JointReturn"))

    checks, withdrawals = [], []
    for entry in after_list:
        if _kind(entry) != "balance":
            continue
        for key in ("pay_to", "due_date"):
            if not entry.get(key):
                raise ReissueError(f"{entry['return']} has a balance due: give its {key}")
        item = {"Amount": _dollars(entry["amount"]), "PayTo": entry["pay_to"], "DueDate": entry["due_date"]}
        if _method(entry) == "withdrawal":
            withdrawals.append({**item, "Account": str(entry["account"])})
        else:
            checks.append(item)

    taxpayer = str(record.get("TaxpayerName") or record.get("ClientFullName") or "").strip()
    if not taxpayer:
        raise ReissueError("the engagement record names no taxpayer to address the email to")
    if not spec.get("filing_deadline"):
        raise ReissueError("give filing_deadline: the date the returns are due")

    fields = {
        "TaxYear": str(record.get("TaxYear") or spec.get("tax_year") or ""),
        "ContactFirstName": taxpayer.split()[0],
        "IssueRaised": raised,
        "FreehandNote": freehand,
        "FilingDeadline": spec["filing_deadline"],
        "PreparerFirstName": record.get("PreparerFirstName", ""),
        "ResultChanges": changes,
        "OtherChanges": others,
        "ReturnsDelivered": [{"Return": e["return"], "Detail": summary_line(e, words)} for e in after_list],
        "ChecksDue": checks,
        "WithdrawalsDue": withdrawals,
        "RaisedAndRight": bool(raised) and right,
        "RaisedAndNotRight": bool(raised) and not right,
        "NotRaised": not raised,
        "AlsoUpdated": bool(raised) and len(changes) + len(others) > 1,
        "FreehandExplanation": bool(freehand),
        "ResignBoth": resign and joint,
        "ResignOne": resign and not joint,
        "SignIfNotYetBoth": not resign and joint,
        "SignIfNotYetOne": not resign and not joint,
    }
    if not fields["TaxYear"]:
        raise ReissueError("no tax year on the record")
    return fields


# ── the email ───────────────────────────────────────────────────────────────

_SUBJECT = re.compile(r'<div class="subject">(.*?)</div>\s*', re.S)


def render(fields: dict) -> tuple[str, str, str]:
    """(subject, html, plain) -- merged from the template, nothing typed here."""
    html = merge.render_file(TEMPLATE, fields).html
    m = _SUBJECT.search(html)
    if not m:
        raise ReissueError("the template has no subject line")
    subject = _text(m.group(1)).strip()
    html = html[:m.start()] + html[m.end():]
    return subject, html, to_plain(html)


def _text(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment))


def to_plain(html: str) -> str:
    """The HTML body as plain text: paragraphs, bullets, line breaks."""
    body = re.search(r'<div class="email"[^>]*>(.*)</div>', html, re.S)
    s = body.group(1) if body else html
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "\n• " + _text(m.group(1)).strip(), s, flags=re.S)
    s = re.sub(r"</?ul[^>]*>", "\n", s)
    s = re.sub(r"<p[^>]*>(.*?)</p>", lambda m: "\n\n" + m.group(1).strip(), s, flags=re.S)
    s = _text(s)
    lines = re.sub(r"\n{2,}", "\n\n", "\n".join(ln.rstrip() for ln in s.split("\n"))).split("\n")
    out: list[str] = []
    for ln in lines:
        bullet = ln.startswith("• ")
        if out and bullet and out[-1] == "" and len(out) > 1 and out[-2].startswith("• "):
            out.pop()                      # bullets in one list sit together
        if out and bullet and out[-1] and not out[-1].startswith("• "):
            out.append("")                 # a blank line before a list starts
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def to_eml(subject: str, html: str, plain: str, *, sender: str = "") -> bytes:
    """An unsent draft: X-Unsent, no To, HTML with a plain-text alternative.

    CRLF line endings and base64 bodies: Outlook mis-read an LF file with
    quoted-printable text on 13 Oct 2026 and scattered "=" through a client
    email, broke its payment link and dropped its image.
    """
    cs = Charset("utf-8")
    cs.body_encoding = BASE64

    def part(text: str, sub: str) -> MIMEText:
        p = MIMEText("", sub)
        p.set_charset(cs)
        p.set_payload(text, cs)
        return p

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    if sender:
        msg["From"] = sender
    msg["X-Unsent"] = "1"
    msg.attach(part(plain, "plain"))
    msg.attach(part(html, "html"))
    return msg.as_bytes(policy=email.policy.SMTP)
