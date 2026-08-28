"""Who has signed what, and the two promises that turn on it.

THE PIPELINE ASSERTS SIGNATURES IT DOES NOT RECORD. Six places in this codebase
already speak of a signed letter as a fact: `packaging.PURPOSE` calls the
engagement letter "the one that is signed", `requote.py` keeps `LetterDate`
frozen because "the client has signed that letter", the re-quote screens say so
to a preparer's face, and `intake` names it "the date the client signed under".
Nothing anywhere recorded that anybody signed anything. That is this
repository's most-repeated bug shape -- a claim in one place, behaviour in
another, and nothing comparing them -- sitting on the one fact the engagement
turns on.

TWO DOCUMENTS PROMISE A CLIENT SOMETHING THAT DEPENDS ON IT, and neither could
be honoured:

  * The delivery letter: *"We cannot transmit anything until the signed
    authorization is back with us. On a joint return, both spouses sign, and
    one signature is not enough to file."*
  * Every engagement letter: *"We will not e-file a return before the invoice
    for it is settled, unless agreed upon in writing."*

Two independent gates on the same act, each stated to the client in writing,
each enforced by nobody.

WHO MUST SIGN IS READ OFF THE DOCUMENTS. Not a list in this file: the templates
carry the signature blocks, and `sigrow` marks each line with a `siglab` naming
whose it is. A list here would go stale the first time a block moved, and go
stale silently -- the register would simply stop asking for a signature the
document still asks for. The spouse's line is conditional in the template and
conditional here, from the same fact.

WHAT THIS IS NOT. It is not an e-signature service and does not pretend a
signature happened. It records what a preparer OBSERVED -- a letter came back,
a client signed in the room, a vendor reported an envelope complete -- with the
date, the means, and a reference to whatever the evidence is. `how` is the
honest part: "in person" and "e-signed through a vendor" are different facts
about how sure we are, and flattening them into a checkbox loses the
difference at exactly the moment somebody asks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from datetime import date
from pathlib import Path

import engagements

# How a signature reached us. The value is the preparer's answer and it is kept
# verbatim on the record, because "he signed it in front of me" and "the portal
# said it completed" are different kinds of knowing.
MEANS = {
    "in-person": "signed in front of you",
    "returned": "came back signed, by email or on paper",
    "e-signed": "signed through a signing service, with its own audit trail",
}

# THE MARKUP A SIGNATURE LINE IS MADE OF, from `satc-doc.css`. Measured against
# every template in the tests rather than assumed, because this is the census
# the whole register counts from: a block this cannot see is a signature nobody
# is waiting for.
_ROW = re.compile(r'<div class="sigrow"[^>]*>')
_LAB = re.compile(r'<div class="siglab">(.*?)</div>', re.S)
_COND = re.compile(r"\[\[(IF|END IF)(?:\s+(\w+))?\]\]")
_FIELD = re.compile(r"&lt;&lt;(\w+)&gt;&gt;")
_TAG = re.compile(r"<[^>]+>")

# A line captioned "Date" is the date beside a signature, not a second person.
# Every block in the set pairs them.
_NOT_A_SIGNER = {"date", ""}


# WHICH SIGNATURE GATES WHAT, and it is not one rule for all of them.
#
# The engagement letter is the instrument the work is done under -- the
# onboarding letter tells the client "Sign the engagement letter first". The
# records release is addressed to the PREVIOUS accountant and gates nothing we
# do; waiting on it would stop an engagement for a document somebody else acts
# on. And the form that gates transmitting is Form 8879, which Drake produces
# and this repository has never held.
GATES_THE_WORK = ("tax-letter", "business-letter", "ccorp-letter",
                  "bookkeeping-letter")


class SigningError(RuntimeError):
    """Something that would record a signature nobody gave."""


@dataclass(frozen=True)
class Line:
    """One signature line on one document, and whose it is.

    `field` is the merge field whose name prints on the line -- `TaxpayerName`,
    `SpouseName`, `SignerName`. It is the identity, because it is stable: the
    caption beside it is this client's name and would be a different key every
    engagement.

    `only_if` is the flag whose block the line sits inside, empty when the line
    is unconditional. The spouse's line is inside `[[IF JointReturn]]` on the
    engagement letter, and the delivery letter says why in as many words: *"On
    a joint return, both spouses sign, and one signature is not enough to
    file."*
    """
    document: str
    field: str
    role: str = ""
    only_if: str = ""

    @property
    def who(self) -> str:
        """What to call this signer, in the registry's own words.

        The caption on the template names the ROLE for the individual letter
        ("Taxpayer", "Spouse") and prints only the merged name on the entity
        ones, so the fallback read "SignerName has not signed" -- the
        software's word for a person. `fields.yaml` already labels all three.
        """
        return self.role or _label(self.field) or "the client"

    def wanted(self, record: dict) -> bool:
        """Is this line on this client's copy of the document?"""
        return not self.only_if or bool(record.get(self.only_if))

    def key(self) -> str:
        return f"{self.document}/{self.field}"

    def __str__(self) -> str:
        return f"{self.document} — {self.who}"


@dataclass(frozen=True)
class Signature:
    """One signature, as observed. Never inferred.

    `how` is the honest part. "He signed it in front of me" and "the portal
    said it completed" are different kinds of knowing, and flattening them into
    a tick loses the difference at exactly the moment somebody asks which it
    was -- which, for anything the IRS governs, is the question.
    """
    document: str
    field: str
    when: str          # the day they signed, as the preparer gives it
    how: str           # a key of MEANS
    reference: str     # an envelope id, a filename; empty in person
    recorded: str      # the day it was written down

    def line(self) -> str:
        ref = f", {self.reference}" if self.reference else ""
        return (f"{self.document} — {self.field}, {self.when} "
                f"({MEANS.get(self.how, self.how)}{ref})")


@lru_cache(maxsize=1)
def _labels() -> dict:
    """Merge field -> what a person calls it. One copy, in the registry."""
    import yaml

    reg = yaml.safe_load(
        (Path(__file__).resolve().parent / "registry" / "fields.yaml")
        .read_text(encoding="utf-8")) or {}
    return {e["field"]: e.get("label") or e["field"]
            for e in reg.get("fields", [])}


def _label(field: str) -> str:
    return _labels().get(field, "")


def lines_in(html: str, document: str) -> list[Line]:
    """Every signature line one template carries, with its condition.

    READS THE DOCUMENT RATHER THAN A LIST. A list in this file would go stale
    the first time a block moved or gained a signer, and go stale SILENTLY --
    the register would simply stop waiting for a signature the document still
    asks for, and an engagement would look complete because nobody was looking.
    """
    out: list[Line] = []
    # Which conditional block each position sits inside. `[[IF X]]` nests in
    # this template set only one deep, so a stack is enough and a stack is what
    # `merge` uses too.
    stack: list[str] = []
    edges = [(m.start(), m.group(1), m.group(2) or "") for m in _COND.finditer(html)]

    def flag_at(pos: int) -> str:
        depth: list[str] = []
        for at, kind, name in edges:
            if at > pos:
                break
            if kind == "IF":
                depth.append(name)
            elif depth:
                depth.pop()
        return depth[-1] if depth else ""

    for row in _ROW.finditer(html):
        # The labels belonging to this row: everything up to the next row.
        nxt = _ROW.search(html, row.end())
        chunk = html[row.end():nxt.start() if nxt else len(html)]
        for label in _LAB.findall(chunk):
            text = " ".join(_TAG.sub(" ", label).split())
            role = text.split("&mdash;")[0].split("—")[0].strip()
            fields = _FIELD.findall(label)
            if role.lower() in _NOT_A_SIGNER and not fields:
                continue
            if not fields:
                continue
            # The name printed on the line is the FIRST merge field; a title
            # after the dash is not a second signer.
            out.append(Line(document=document, field=fields[0],
                            role="" if role.startswith("&lt;") else role,
                            only_if=flag_at(row.start())))
    return out


@dataclass
class Standing:
    """Where one engagement has got to on signatures."""
    ref: str
    expected: list[Line] = field(default_factory=list)
    have: list[Signature] = field(default_factory=list)
    missing: list[Line] = field(default_factory=list)
    deadline: str = ""
    overdue: bool = False

    @property
    def complete(self) -> bool:
        """Everything the pack asks for is signed.

        False on an empty census, deliberately. Nothing to wait for is not the
        same as everything signed, and S2 in the tenets exists because a check
        that examined nothing once reported itself green.
        """
        return bool(self.expected) and not self.missing

    @property
    def examined(self) -> int:
        return len(self.expected)


def expected(record: dict, documents: list[str], template_dir: Path) -> list[Line]:
    """Every signature this client's pack actually asks for.

    `documents` is the pack, from `packaging.documents_for` -- so the census is
    over what was SENT, not over every template that exists. A records release
    goes only to a client with a predecessor, and waiting for a signature on a
    document nobody was given is how a register stops being believed.
    """
    import cli

    out: list[Line] = []
    for doc in documents:
        spec = cli.DOCUMENTS.get(doc)
        if not spec:
            continue
        path = Path(template_dir) / spec[0]
        if not path.exists():
            continue
        for line in lines_in(path.read_text(encoding="utf-8"), doc):
            if line.wanted(record):
                out.append(line)
    return out


def record_signature(ref: str, line: Line, *, when: str, how: str,
                     reference: str = "", store: Path | None = None,
                     today: date | None = None) -> Path:
    """Write down that somebody signed. Append only.

    Refuses a `how` it does not know rather than storing a free-text guess: the
    means is the whole evidentiary value of the record, and "yes" is not a
    means. Same shape as `engagements.record_override` and
    `requote.record_revision`, for the same reason -- a log you can edit is not
    evidence.
    """
    if how not in MEANS:
        raise SigningError(
            f"{how!r} is not a way a signature arrives. It is one of: "
            + "; ".join(f"{k} ({v})" for k, v in MEANS.items())
            + ". The means is the whole value of this record -- it is what "
              "says how sure we are, and it is the first thing anybody asks."
        )
    if not str(when).strip():
        raise SigningError(
            "a signature needs the date they signed, which is not necessarily "
            "today. A letter that arrives on Monday was signed on Friday, and "
            "the date on the page is the one that counts."
        )
    if how == "e-signed" and not reference.strip():
        raise SigningError(
            "a signature taken through a signing service has an audit trail, "
            "and this record is worth having only if it points at one. Give "
            "the envelope or request reference the service issued."
        )
    entry = {
        "document": line.document,
        "field": line.field,
        "when": str(when).strip(),
        "how": how,
        "reference": reference.strip(),
        "recorded": (today or date.today()).isoformat(),
    }
    return _append(ref, entry, store)


def signatures(ref: str, store: Path | None = None) -> list[Signature]:
    """Every signature recorded on this engagement, oldest first."""
    out = []
    for row in _log(ref, store):
        if not isinstance(row, dict) or "document" not in row:
            continue
        out.append(Signature(
            document=row.get("document", ""), field=row.get("field", ""),
            when=row.get("when", ""), how=row.get("how", ""),
            reference=row.get("reference", ""), recorded=row.get("recorded", "")))
    return out


def standing(ref: str, record: dict, documents: list[str], template_dir: Path,
             *, store: Path | None = None, deadline: str = "",
             today: date | None = None) -> Standing:
    """Where this engagement has got to, and what is still out.

    REPORTS ITS DENOMINATOR. `examined` is how many signature lines the pack
    actually asks for, and a `complete` reached from zero of them is not a
    completion -- it is a pack that asks for nothing, which for an engagement
    letter means something is wrong with the census rather than with the
    client.
    """
    want = expected(record, documents, template_dir)
    got = {(s.document, s.field) for s in signatures(ref, store)}
    out = Standing(
        ref=ref, expected=want, have=signatures(ref, store),
        missing=[ln for ln in want if (ln.document, ln.field) not in got],
        deadline=deadline or "",
    )
    out.overdue = bool(out.missing and _past(deadline, today))
    return out


def _past(deadline: str, today: date | None) -> bool:
    """Is the signature deadline behind us? False when there isn't one.

    `SignatureDeadline` has been asked by the delivery event since it was
    built, printed on the letter, and compared against nothing. A date a
    client is given and nobody watches is a date that only ever gets noticed
    after it matters.
    """
    from datetime import datetime

    if not deadline:
        return False
    for shape in ("%B %d, %Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            due = datetime.strptime(deadline.replace(",", ", ").replace("  ", " "),
                                    shape).date()
        except ValueError:
            continue
        return (today or date.today()) > due
    # A date nobody can parse is not a date that has passed. Saying otherwise
    # would raise a false alarm on every engagement whose deadline was typed
    # in a shape this did not expect.
    return False


# ── the two promises ──────────────────────────────────────────────────────

@dataclass
class Filing:
    """May this return be transmitted? Both documents said so first.

    The delivery letter, to the client: *"We cannot transmit anything until
    the signed authorization is back with us."* Every engagement letter, to
    the same client: *"We will not e-file a return before the invoice for it
    is settled."* Two gates on one act, each promised in writing, each
    enforced by nobody until now.
    """
    blockers: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)

    @property
    def clear(self) -> bool:
        return not self.blockers and not self.unknown


def may_file(ref: str, record: dict, documents: list[str], template_dir: Path,
             *, store: Path | None = None, deadline: str = "",
             today: date | None = None) -> Filing:
    """What the two promises say about transmitting this return.

    WHAT IS NOT KNOWN IS SAID, NOT ASSUMED. Nothing in this repository records
    whether an invoice was settled -- `invoicing` writes the bill and stops,
    and it says so. So the second promise is reported as UNKNOWN rather than
    as passed. A gate that quietly treats "we cannot tell" as "fine" is worse
    than no gate: it launders an unanswered question into a green light.
    """
    out = Filing()
    where = standing(ref, record, documents, template_dir, store=store,
                     deadline=deadline, today=today)
    if not where.expected:
        out.unknown.append(
            "no document in this pack carries a signature line, so there is "
            "nothing to have signed. That is a question about the pack, not "
            "about the client.")
    for line in where.missing:
        if line.document in GATES_THE_WORK:
            out.blockers.append(
                f"{line.who} has not signed the {line.document}. The "
                f"onboarding letter tells this client to sign it first, and "
                f"the engagement is what the work is done under.")
        else:
            out.unknown.append(
                f"{line.who} has not signed the {line.document}, which gates "
                f"nothing of ours — the records release is addressed to the "
                f"previous accountant, and it is them who act on it.")
    if where.overdue:
        out.blockers.append(
            f"the date the client was given to sign by — {where.deadline} — "
            f"has passed.")
    # THE FORM THAT ACTUALLY GATES TRANSMITTING IS NOT IN THIS SOFTWARE.
    # The delivery letter's promise -- "we cannot transmit anything until the
    # signed authorization is back with us" -- is about Form 8879, which Drake
    # produces and this repository has never held: none of the twelve
    # templates is one. Reporting it as satisfied because we cannot see it is
    # the exact failure this whole module exists to stop.
    out.unknown.append(
        "whether the e-file authorization is signed. That is Form 8879, it "
        "comes out of Drake, and nothing here has ever seen one. On a joint "
        "return both spouses sign it and one signature is not enough.")
    out.unknown.append(
        "whether the invoice has been settled. The engagement letter says we "
        "will not e-file before it is, and nothing here records a payment — "
        "`invoicing` writes the bill and stops. Check it yourself.")
    return out


# ── the file ──────────────────────────────────────────────────────────────

def _path(ref: str, store: Path | None) -> Path:
    return engagements._dir(store or engagements.STORE, ref) / "signatures.json"


def _log(ref: str, store: Path | None) -> list:
    path = _path(ref, store)
    if not path.exists():
        return []
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return got if isinstance(got, list) else []


def _append(ref: str, entry: dict, store: Path | None) -> Path:
    path = _path(ref, store)
    path.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                log = existing
        except json.JSONDecodeError:
            # A corrupt log is still evidence that something happened. Kept
            # beside the new one rather than overwritten away.
            log = [{"unreadable": path.with_suffix(".corrupt").name}]
            path.replace(path.with_suffix(".corrupt"))
    log.append(entry)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path
