"""The one line that reaches the firm when a question is parked.

THE FIRM ASKED FOR THIS DIRECTLY, 8 September 2026: *"Nothing stops if it isn't
a blocker. I'm addition, I want a good way for me to be directly notified so I
can answer as quickly as I can"*. Parking a question is not the end of it -- a
queue nobody is told about is the same silence `ask.consult_or_file` was built
to end, one layer further in.

WHY THE LINE IS COMPOSED HERE AND NOT IN THE SKILL. The desk runs as a Claude
Code session and only that session can send a push; the engine cannot. The
temptation is therefore to write "notify the firm" in `be-the-desk` and stop.
This repository already knows what that costs -- the README's own reason for
putting the citation rule in the engine is that the same policy written as skill
prose was obeyed *"100%, 4%, 0% of runs"*. So the split is: the ENGINE decides
what the firm is told and writes the exact characters; the SKILL carries them
verbatim and composes nothing. A sentence the model may not rewrite is a
sentence a test can hold.

THE PII RULE IS THE HARD ONE, and it is why this file is not a format string.
`CLAUDE.md` is unambiguous -- *"Only masked/last-4 values belong in artifacts,
logs, and workbooks -- never real taxpayer PII"* -- and a push notification is
the most escaping artifact in the system: it leaves the machine, crosses a
vendor, and lands on a lock screen that anybody near the phone can read. The
question a doer parks is written by a doer mid-close and may name anything. So
this REFUSES to send a line it cannot vouch for rather than truncating one and
hoping, and `looks_like_pii` is the check the tests break on purpose.

WHAT THE FIRM SEES FIRST. `PushNotification`'s own guidance -- lead with what
they would act on, under 200 characters, one line, no markdown. The question
comes first because that is the thing they answer; the reference comes last
because it is what they quote back.
"""
from __future__ import annotations

import re

#: Mobile operating systems truncate, so this is a hard ceiling rather than a
#: target. A line that would exceed it is shortened at a word boundary and the
#: reference is preserved, because a truncated reference cannot be quoted back.
LIMIT = 200

#: What a taxpayer identifier looks like, loosely enough to catch a near miss.
#: Deliberately over-eager: a false positive costs one un-pushed notification
#: (the queue still holds the question), a false negative puts a client's SSN on
#: a lock screen. The asymmetry decides the tuning.
_SSN = re.compile(r"\b\d{3}[-– ]?\d{2}[-– ]?\d{4}\b")
_EIN = re.compile(r"\b\d{2}[-– ]?\d{7}\b")
_ACCT = re.compile(r"\b\d{8,}\b")


def looks_like_pii(text: str) -> str:
    """The reason this text may not leave the machine, or "" if it may.

    A REASON RATHER THAN A BOOLEAN, so a refusal can say what it saw without
    repeating the thing it refused to send.
    """
    if _SSN.search(text):
        return "it contains something shaped like a social security number"
    if _EIN.search(text):
        return "it contains something shaped like an employer identification number"
    if _ACCT.search(text):
        return "it contains a long digit run that could be an account number"
    return ""


def _flatten(text: str) -> str:
    """One line, no markdown. Notifications render neither.

    THE UNDERSCORE IS NOT MARKDOWN HERE, and stripping it was a real defect
    caught by running the real path rather than the unit test: the reason code
    `authority_absent` reached the firm as `authorityabsent`. Every machine
    reason in this system is written that way -- `context_not_on_file`,
    `contradicts_ratified_position` -- and they are exactly the words the firm
    recognises and quotes back. An italic that renders as a literal underscore
    costs nothing; a mangled reason code costs the reader the meaning.
    """
    text = re.sub(r"[*`#>]", "", text)
    return " ".join(text.split())


def _fit(question: str, tail: str) -> str:
    """The question, shortened at a word boundary so the tail always survives.

    THE WORD BOUNDARY IS NOT TAKEN AT ANY COST, and the first version of this
    took it at any cost. `line("x" * 400, ref="q-0008")` came back as
    `"Desk parked… [q-0008]"` -- 21 characters of a 200-character budget --
    because `rindex` found the space after "parked:" and cut there. A question
    carrying one long unbroken token (a url, a base64 blob, a pasted account
    string) is exactly the question that would do that, and the firm would get a
    notification that says nothing at all.

    So a boundary is used only when it keeps most of the room; otherwise the cut
    is hard. A word broken mid-way reads worse than a sentence deleted.
    """
    room = LIMIT - len(tail)
    if len(question) <= room:
        return question + tail
    cut = question[:room - 1]
    if " " in cut:
        at = cut.rindex(" ")
        if at >= int(room * 0.6):
            cut = cut[:at]
    return cut.rstrip(" ,;:.") + "\u2026" + tail


def line(question: str, *, ref: str, why: str = "") -> str:
    """The exact characters the desk sends, or raise if it must not send them.

    `ref` is how the firm names this one back -- a queue id, not a client. `why`
    is the short reason it is parked, shown only when there is room for it,
    because the question is what gets answered and the reason is context.
    """
    question, ref, why = _flatten(question), _flatten(ref), _flatten(why)
    if not question:
        raise ValueError("nothing to notify about: the question is empty")
    if not ref:
        raise ValueError("a notification with no reference cannot be answered")
    for part in (question, why):
        reason = looks_like_pii(part)
        if reason:
            raise ValueError(
                f"refusing to send this notification because {reason}; "
                f"the question is still in the queue as {ref}")
    tail = f" [{ref}]"
    if why:
        candidate = _fit(f"Desk parked: {question} — {why}", tail)
        if len(candidate) <= LIMIT:
            return candidate
    return _fit(f"Desk parked: {question}", tail)


def for_entry(entry) -> str:
    """The line for a question the queue has just taken.

    THE SKILL'S WHOLE JOB IS TO SEND WHAT THIS RETURNS. `ask.consult_or_file`
    hands back the entry it filed; this turns it into characters. Nothing about
    the wording is left to the session, which is the point -- a model composing
    its own notification is a model deciding what the firm gets told.
    """
    return line(getattr(entry, "question", ""),
                ref=getattr(entry, "id", ""),
                why=getattr(entry, "failed_because", ""))
