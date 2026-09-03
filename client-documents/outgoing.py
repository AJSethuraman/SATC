"""The pack, addressed and ready to go — one press away from sent.

WHAT THIS IS FOR. `sending.build` writes a pack to a folder and stops; it has no
recipient and no covering note, and said so in as many words. So the last step
of getting an engagement out was a human opening a portal, finding the client,
attaching four files and typing a covering note from memory. That is three
minutes of clicking per client and one of them, eventually, goes to the wrong
person.

WHAT IT IS NOT. It does not send. Nothing here opens a connection, holds a
credential, or drives anybody's website. It assembles a MESSAGE -- who it is
to, what it says, what travels with it -- and writes it as a `.eml`, which is
the ordinary interchange format for one email. Double-click that file and it
opens in the mail client already addressed, already attached, already written.
The human reads it and presses send.

WHY THAT SHAPE, AND NOT AUTOMATION OF THE SEND ITSELF. Three reasons, and only
the third is about Encyro:

  * the same `Message` is what an SMTP relay would take, what a portal API
    would take, and what a human presses send on. Composing it is the part
    every route needs, and the part none of them can skip.
  * the send is the one irreversible step in the whole pipeline. A pre-send
    gate that blocks nine ways and is then followed by an automatic send has
    moved the risk rather than removed it.
  * which automated route Encyro actually offers is not established. Building
    the message now costs nothing if a relay turns up later; guessing the
    route now costs the work twice.

THE WORDS ARE THE FIRM'S. The covering note lives in `registry/signing.yaml`
behind a `[CONFIRM: ]`, and this refuses to compose until somebody has accepted
or rewritten it. An agent writing to a client over the firm's name, in prose
nobody approved, is the failure `CLAUDE.md` puts above all the others.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

CONFIRM = re.compile(r"\[CONFIRM:\s*(.*?)\s*\]", re.S)
_TOKEN = re.compile(r"<<(\w+)>>")

# What travels with the pack. HTML is a fallback: a client should get the PDF,
# and a machine with no PDF engine should still be able to compose something
# rather than silently attaching nothing.
PREFERRED = (".pdf", ".html")


class OutgoingError(RuntimeError):
    """Something that would put a message in front of a client uncomposed."""


@dataclass(frozen=True)
class Message:
    """One email, assembled and not yet sent."""
    to: str
    subject: str
    body: str
    attachments: list[Path] = field(default_factory=list)
    ref: str = ""

    def summary(self) -> str:
        return (f"to {self.to} — {self.subject} "
                f"({len(self.attachments)} attachment(s))")


def _unconfirmed(text: str) -> str:
    """The question inside a `[CONFIRM: ]`, or empty if there is none."""
    found = CONFIRM.search(text or "")
    return found.group(1) if found else ""


def _fill(text: str, record: dict) -> str:
    """`<<Field>>` -> the record's value. Refuses on a token it cannot fill.

    The same rule `merge` holds and for the same reason: a covering note that
    greets a client by `<<ClientFullName>>` is worse than one that never went.
    """
    missing = [name for name in _TOKEN.findall(text or "")
               if not str(record.get(name, "")).strip()]
    if missing:
        raise OutgoingError(
            f"the covering note needs {', '.join(sorted(set(missing)))}, which "
            f"this engagement has no value for. A note that greets a client by "
            f"the name of a field is worse than one that never went."
        )
    return _TOKEN.sub(lambda m: str(record.get(m.group(1), "")), text or "")


def attachments_in(pack: Path) -> list[Path]:
    """What the client should receive, best format first, one per document.

    A pack folder holds the PDF and the HTML of each document plus the
    stylesheet and the manifest. Sending all of it would attach the firm's own
    working notes to a client's email.
    """
    if not pack or not Path(pack).is_dir():
        return []
    best: dict[str, Path] = {}
    for path in sorted(Path(pack).iterdir()):
        if path.suffix.lower() not in PREFERRED or path.name.startswith("_"):
            continue
        if path.name.upper().startswith("MANIFEST"):
            continue
        rank = PREFERRED.index(path.suffix.lower())
        held = best.get(path.stem)
        if held is None or rank < PREFERRED.index(held.suffix.lower()):
            best[path.stem] = path
    return [best[k] for k in sorted(best)]


def compose(record: dict, pack: Path | None, *, registry: dict) -> Message:
    """The engagement plus its pack -> the message that carries it.

    Refuses three things rather than producing a message somebody has to
    notice is wrong: a covering note nobody has approved, a client with no
    email address on file, and a pack with nothing in it to attach.
    """
    note = (registry or {}).get("covering_note") or {}
    for part in ("subject", "body"):
        question = _unconfirmed(str(note.get(part, "")))
        if question:
            raise OutgoingError(
                f"the covering note's {part} has not been written yet — "
                f"`registry/signing.yaml` carries a draft and it is waiting on "
                f"the firm.\n\nWhat it proposes:\n\n"
                + "\n".join("    " + line
                            for line in question.splitlines()) +
                "\n\nAccept it by deleting the `[CONFIRM: ` and its closing "
                "`]`, or replace the words. Nothing goes to a client in the "
                "firm's name until somebody has read it."
            )

    to = str(record.get("ClientEmail", "")).strip()
    if not to:
        raise OutgoingError(
            "this engagement has no email address for the client, so there is "
            "nobody to address it to. The interview asks for one; an "
            "engagement created without it can be corrected there."
        )

    files = attachments_in(pack) if pack else []
    if not files:
        raise OutgoingError(
            f"there is nothing in {pack} to attach. Build the pack first — a "
            f"covering note with no documents on it is a message the client "
            f"has to reply to in order to find out what was meant."
        )

    # The Outlook add-in's keyword, where the firm has turned it on. Prefixed
    # rather than appended: the add-in reads the subject line, and a keyword
    # after eighty characters of subject is a keyword in a truncated field.
    keyword = str((registry or {}).get("secure_keyword", "")).strip()
    subject = " ".join(_fill(str(note.get("subject", "")), record).split())
    return Message(
        to=to,
        subject=f"{keyword} {subject}".strip() if keyword else subject,
        body=_fill(str(note.get("body", "")), record).strip() + "\n",
        attachments=files,
        ref=str(record.get("EngagementRef", "")),
    )


def as_eml(message: Message, *, sender: str = "", today=None) -> bytes:
    """One message as an ordinary `.eml`.

    RFC 5322, which every mail client on earth opens. No credential, no
    connection, no vendor: the file is the handoff, and the human is the send
    button.
    """
    mail = EmailMessage()
    mail["To"] = message.to
    if sender:
        mail["From"] = sender
    mail["Subject"] = message.subject
    mail["Date"] = formatdate(localtime=True) if today is None else today
    if message.ref:
        # WHICH ENGAGEMENT THIS IS, put here rather than borrowed from the
        # subject line. The subject is the firm's copy and carries a `[CONFIRM:`
        # until they accept it; software that needs the ref must not depend on
        # what they choose to write there, and a test that asserted the ref
        # appeared in the subject was pinning their wording through the back
        # door.
        #
        # HONEST LIMIT: a custom header does not survive the client's REPLY --
        # only "Re: <subject>" comes back. So this makes the outgoing message
        # findable in the firm's own mailbox and machine-readable; it does not
        # thread a reply to an engagement. If the firm wants that, the ref has
        # to be in the subject and they have to be willing for a client to see
        # it. That is their call, and it is written up rather than assumed.
        mail["X-SATC-Engagement"] = message.ref
    mail.set_content(message.body)
    for path in message.attachments:
        data = Path(path).read_bytes()
        kind = "pdf" if path.suffix.lower() == ".pdf" else "html"
        mail.add_attachment(data, maintype="application", subtype=kind,
                            filename=path.name)
    return mail.as_bytes()


def write(message: Message, outdir: Path, *, sender: str = "") -> Path:
    """The `.eml` beside the pack it carries, named for the engagement."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{message.ref or 'engagement'} — ready to send.eml"
    path.write_bytes(as_eml(message, sender=sender))
    return path
