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


def line(question: str, *, ref: str, why: str = "",
         verb: str = "Desk parked") -> str:
    """The exact characters the desk sends, or raise if it must not send them.

    `ref` is how the firm names this one back -- a queue id, not a client. `why`
    is the short reason it is parked, shown only when there is room for it,
    because the question is what gets answered and the reason is context.

    `verb` is what the desk DID, and it is a parameter because `dec-fields`
    added a second thing it can do: a field proposal is a decision waiting on
    the firm, not a question waiting on an answer, and telling them apart in the
    first three words is the difference between a notification they act on and
    one they file. Kept as a fixed set here rather than free text -- see
    `for_entry`, which is the only caller that changes it.
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
        candidate = _fit(f"{verb}: {question} — {why}", tail)
        if len(candidate) <= LIMIT:
            return candidate
    return _fit(f"{verb}: {question}", tail)


def for_entry(entry) -> str:
    """The line for a question the queue has just taken.

    THE SKILL'S WHOLE JOB IS TO SEND WHAT THIS RETURNS. `ask.consult_or_file`
    hands back the entry it filed; this turns it into characters. Nothing about
    the wording is left to the session, which is the point -- a model composing
    its own notification is a model deciding what the firm gets told.

    A FIELD PROPOSAL IS NOT A PARKED QUESTION AND MUST NOT READ AS ONE.
    `dec-fields`, 10 September 2026 -- the firm, refusing both options offered
    and naming a third:

        "I have said before I want the desk to propose fields that are clearly
         holes. I can sign off on them in the same way as a position. [...] I
         don't want the list, I want this part of the process -- it sends me the
         notification or whatever saying there's something for me to decide
         which in this case would be 'do we add this field' I think."

    So where the entry names a field, the line says WHAT THERE IS TO DECIDE
    rather than what somebody asked. "Desk parked: what is the threshold --
    no_field_for_this_fact" tells the firm a question stalled; "Desk proposes a
    field: capitalization_rule -- POS1 needs it and nothing records it" tells
    them the decision that is theirs. Same queue, same id, same reply path.

    IT IS COMPOSED HERE RATHER THAN BY THE SESSION for the reason the docstring
    above already gives, and the field name is the DESK'S OWN vocabulary -- it
    comes from a position's `Unless:` line, never from anything a client said,
    so the PII check below has nothing to catch and still runs.
    """
    field = getattr(entry, "needs_field", "")
    by = getattr(entry, "asked_by", "")
    if field:
        return line(f"add a field for {field}?",
                    ref=getattr(entry, "id", ""),
                    why=(f"{by} needs it and nothing records it" if by
                         else "a position needs it and nothing records it"),
                    verb="Desk proposes")
    return line(getattr(entry, "question", ""),
                ref=getattr(entry, "id", ""),
                why=getattr(entry, "failed_because", ""))


#: What a queue reference looks like in a message the firm typed. `U` and
#: digits, because that is what `unsupported.next_id` produces and what
#: `line` puts in the brackets. Deliberately not a general id pattern: a
#: looser one matches things the firm never meant as a reference.
_REF = re.compile(r"\bU(\d+)\b", re.I)


def reply_in(text: str, *, sent: str = "") -> tuple:
    """`(uid, answer)` from a message the firm sent back, or `("", "")`.

    THE MIRROR OF `line`, AND IT LIVES BESIDE IT ON PURPOSE. `line` decides what
    the firm is told; this decides what the desk heard. Both are the engine's,
    for the reason the README gives about the citation rule: the same policy
    written as skill prose was obeyed *"100%, 4%, 0% of runs"*. A model asked to
    "work out which question they answered" will work out something.

    THE FIRM CONFIRMED THE TRANSPORT EXISTS, 9 September 2026, when asked
    whether they could reply to a session from a phone notification:
    *"Of course I can, that's how I'm talking to you now."* So there is no pipe
    to build -- the push already carries the sending session's name, they reply
    to that session, and the desk reads the reply. This function is the whole
    remaining seam.

    THE ANSWER IS THEIR MESSAGE, VERBATIM. The first version cut the reference
    out of the text and tidied around it, and running it showed what that costs:
    *"For [U1]: treat it as income."* came back as *"For [ ]: treat it as
    income."* -- an empty bracket that was never in what they typed -- and a
    message quoting the whole notification back had words removed from the
    middle. **The record's job is to show what the firm said**, and a stray
    "U1" left in a sentence is truthful where a hole in it is not. So the
    reference is used to FIND the entry and nothing is deleted to do it.

    IT RETURNS EMPTY RATHER THAN GUESSING, and that is the important half. Most
    messages a desk session receives are not answers to parked questions, so a
    function that always found one would settle the wrong entry with somebody's
    passing remark. No reference, no answer.

    TWO REFERENCES IS A REFUSAL, not a choice. *"U1 and U2 are both income"* is
    a real thing a person types and there is no honest way to split it into two
    entries -- the words belong to both and to neither. It comes back empty so
    the desk asks, rather than filing half a sentence twice.

    A BARE REFERENCE IS NOT AN ANSWER. *"[U1]"* on its own carries no decision,
    and `unsupported.settle` refuses an empty answer anyway; catching it here
    means the desk can tell the difference between "they have not answered" and
    "they answered and it would not save".

    NEITHER IS THE NOTIFICATION QUOTED BACK, and a test caught that this needs
    `sent` to know. Tapping the notification quotes the line, and the line
    contains the QUESTION -- so a reply carrying nothing but the echo looked
    like substance to a check that only stripped the reference. **A question is
    not an answer to itself.** Pass what was sent and an echo with nothing added
    comes back empty; omit `sent` and it cannot be told apart, which is why the
    skill passes it.
    """
    if not text or not text.strip():
        return "", ""
    found = {m.group(0).upper() for m in _REF.finditer(text)}
    if len(found) != 1:
        return "", ""
    # SUBSTANCE IS TESTED ON A STRIPPED COPY; the answer returned is the
    # original. Removing the reference, the label the firm quoted back and the
    # punctuation around them is how you tell "[U1]" from a real reply -- it is
    # not how the answer is stored.
    rest = _REF.sub(" ", text)
    rest = re.sub(r"desk parked:?", " ", rest, flags=re.I)
    if sent:
        # WORD BY WORD, NOT AS A SUBSTRING. A quoted notification comes back
        # re-wrapped, re-punctuated, sometimes with the em dash swapped -- so
        # `sent in text` misses it. What is left after removing the words that
        # were sent is what the firm added.
        for word in _REF.sub(" ", re.sub(r"desk parked:?", " ", sent, flags=re.I)).split():
            rest = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", " ", rest, count=1)
    if not re.search(r"[A-Za-z0-9]", rest):
        return "", ""
    # THE ORIGINAL, NOT THE SANITISED COPY. `_flatten` strips `*`, backticks,
    # `#` and `>` and collapses whitespace -- it exists to decide what a
    # NOTIFICATION may carry, and a notification renders no markdown. An answer
    # is not a notification. Returning the flattened text stored
    # "U1 use **income** and `loan`" as "U1 use income and loan", which is a
    # quieter version of the mangling this function was already rewritten once
    # to stop, and it contradicted the word "verbatim" in this very docstring.
    # Caught by a review; `rest` above is the sanitised copy and its only job is
    # deciding whether anything was added.
    return found.pop(), text.strip()
