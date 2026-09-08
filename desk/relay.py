"""Asking a desk that is somewhere else.

THE FIRM SET THE SHAPE, 8 September 2026, and gave the reason:

    "the final check for this for V1 will be to have Forge - Occam install the
    new plugin we are designing and run a close from start to finish on Sarcia
    Services [...] this implies that the skill is able to call for questions and
    receive back answers from Forge - Desk"

    "this is my solution to getting as much info as possible because the
    ask-desk session (in this case Forge - Desk) is on the Forge itself so it
    can use its browser and such."

So the desk stops being a library the doer imports and becomes a session the
doer asks. `docs/THE-DESK-IS-A-SESSION.md` argues why; this is the wire.

WHAT THIS MODULE IS AND IS NOT. It builds and reads the two envelopes and it
REFUSES a malformed one. It sends nothing: the transport is `create_trigger` /
`fire_trigger`, which live in the caller's harness and not in this repository.
Keeping the composition here and the sending there is what makes the protocol
testable at all -- every rule below is a test, not a paragraph somebody is
trusted to have read.

THE THREE RULES, EACH FROM SOMETHING THAT WENT WRONG:

1. A QUESTION CARRIES ITS RETURN ADDRESS OR IT IS NOT A QUESTION. On the first
   machine round trip the desk had to be TOLD the asking session's id in the
   prose of the prompt. Leave it out and the answer has nowhere to go, the desk
   composes a report into its own window, and a person has to carry it -- which
   is the exact leg V1 exists to remove. So `reply_to` is required and checked.

2. EVERY ENVELOPE CARRIES A REF, BECAUSE DELIVERY IS AT-LEAST-ONCE. A trigger
   with a `run_once_at` that is then poked DELIVERS TWICE -- measured on this
   repository's own traffic, 8 September 2026. Poke-only avoids it, and a
   protocol that assumes nobody will ever get that wrong again is a protocol
   that will be got wrong again. The ref makes a second copy DETECTABLE rather
   than answered twice, which on a close is duplicated work at best and
   duplicated entries at worst.

3. NO CLIENT IDENTIFIER CROSSES THE WIRE. The desks never need a name to answer
   whether a deposit is a reconciling item. `CLAUDE.md`: real taxpayer PII never
   belongs in artifacts or logs, and this envelope becomes both -- it is stored
   on the trigger, echoed in its record, and read back by `list_triggers`. This
   is a CHOKE POINT and not advice, for the reason LOCAL-LLM-PATTERN rule 6
   gives: policy written as prose is policy one run in three.

AND THE THING IT DELIBERATELY DOES NOT CARRY: CONTEXT. The first draft of this
module gave the envelope a free-text `facts` field for the asker to fill in. The
firm cut it, 8 September 2026:

    "no- we don't add context to it, that defeats the purpose. it falls the same
    rules and gets the de-identified data so it can ensure it answers and asks
    things objectively"

Correct, and it was a second facts channel beside one that already exists.
`record.Context` is how facts reach a desk, and it is not a blob: `ask.brief`
prints every fact the desk RECORDS, and prints the missing ones BY NAME as
"NOT ON FILE — do not infer it, and do not answer from a rule that needs it".
That discipline is what makes `context_not_on_file` a real escalation instead of
a guess.

A free-text context field bypasses all of it, and worse: it lets the ASKER frame
the question. A doer that already suspects the answer writes the context that
gets it, and the desk agrees with a summary of the facts rather than with the
facts. **The whole reason to put the desk behind a session boundary is so that it
is not the doer's own reasoning coming back with a citation attached.**

So the envelope carries a QUESTION and a RETURN ADDRESS. Nothing else.
"""
from __future__ import annotations

import dataclasses
import hashlib
import re

#: A session id as the harness writes it. Checked, because the failure of a
#: wrong one is silent -- the answer is delivered somewhere, just not here.
SESSION = re.compile(r"^session_[A-Za-z0-9]{16,}$")

#: A TIN as a person types one: 123-45-6789 (SSN) or 12-3456789 (EIN). NOT a
#: general PII detector, and it does not pretend to be -- it is the shape of the
#: identifier this firm handles all day, which is the one most likely to be
#: pasted into a question by an agent trying to be helpful.
TIN = re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{2}-\d{7})\b")


#: Where the desk lives, read from the environment. NOT a default and never a
#: guess: a wrong session id fails SILENTLY -- the question is delivered
#: somewhere, the asker waits, and nothing anywhere says the desk never saw it.
DESK = "SATC_DESK_SESSION"


class RelayError(Exception):
    """The envelope is malformed. Never repaired, never defaulted."""


@dataclasses.dataclass(frozen=True)
class Ask:
    """One question, its return address, and the ref that makes it identifiable.

    NO CONTEXT FIELD, and see the module docstring for why: facts reach a desk
    through `record.Context`, which names the ones it does NOT have, and an
    asker who writes the context writes the answer.
    """
    question: str
    reply_to: str
    ref: str


def ref_for(question: str, reply_to: str) -> str:
    """A stable ref: the same question from the same asker gets the same one.

    STABLE ON PURPOSE. A random id would make a duplicate delivery look like a
    second question, which is the failure this exists to catch. Twelve hex
    characters of a digest -- enough that two different questions colliding is
    not a thing that happens, short enough to read in a log.
    """
    return hashlib.sha256(
        f"{reply_to}\n{question.strip()}".encode()).hexdigest()[:12]


def ask(question: str, reply_to: str) -> Ask:
    """Build a question, or REFUSE. Never a default, never a repair."""
    question = (question or "").strip()
    if not question:
        raise RelayError("no question. A desk answers what it was asked, and "
                         "an empty ask is not a question it can refuse.")
    if not SESSION.match(reply_to or ""):
        raise RelayError(
            f"reply_to {reply_to!r} is not a session id. Without one the desk "
            f"has nowhere to send the answer, composes it into its own window, "
            f"and a person has to carry it — which is the leg this replaces.")
    if found := TIN.search(question):
        raise RelayError(
            f"the question carries what looks like a TIN ({found.group()[:3]}"
            f"…). The envelope is stored on the trigger and read back out of "
            f"its record; no client identifier crosses this wire. Ask the "
            f"question without it — the desks do not need it to answer.")
    return Ask(question=question, reply_to=reply_to,
               ref=ref_for(question, reply_to))


def as_prompt(a: Ask) -> str:
    """The message the desk session receives.

    THE PROTOCOL TRAVELS IN THE ENVELOPE, not only in a SKILL.md. Four releases
    running, the Skill tool served a stale `ask-desk` and an agent following it
    correctly produced the wrong output. A desk reading this message has what it
    needs to answer even if its own skill is months old.
    """
    out = [f"DESK REQUEST {a.ref} — you are the desk. Somebody is doing the "
           f"work and has hit something they cannot settle.", "",
           "## The question", "", a.question, "",
           "**That is the whole of what you were told, and it is deliberate.** "
           "No context came with it. Read the facts off the desk's own record "
           "through `consult`, where the ones we do NOT hold are named as such "
           "— and escalate on a missing one rather than infer it. Nobody has "
           "framed this question for you, which is the point of your being "
           "asked rather than guessed at.", "",
    ]
    out += [
        "## How to answer", "",
        "Use the `be-the-desk` skill — NOT `ask-desk`, which is the skill for "
        "whoever sent you this: `ask.consult` for what a desk will let you "
        "answer from, then `ask.answer(...)` with your conclusion and citation. "
        "`keep=False` unless you are told otherwise. Do not write to a desk, do "
        "not commit, do not push.", "",
        "## How to reply — THIS IS NOT OPTIONAL", "",
        f"Send `print(out)` in full, and your reasoning, back to "
        f"`{a.reply_to}`:", "",
        "```",
        "create_trigger(name=\"Desk answer " + a.ref + "\",",
        f"               persistent_session_id=\"{a.reply_to}\",",
        "               initiation=\"human_schedule\",",
        "               prompt=<your answer>)      # NO run_once_at, NO cron",
        "fire_trigger(<the id it returns>)",
        "```", "",
        "**Omit `run_once_at` and `cron_expression` entirely.** A trigger that "
        "has one and is then poked DELIVERS TWICE — measured 8 September 2026. "
        "Poke-only delivers once, in about eight seconds.", "",
        f"**Open your reply with `DESK ANSWER {a.ref}`** so a duplicate can be "
        f"told from a second question.", "",
        "`fire_trigger` returning success is NOT delivery — its `last_fired_at` "
        "is not corroborated by the durable record. Do not chase your own "
        "message; say what you sent and stop.", "",
        "No client name, TIN or figure in the reply. If you cannot answer, say "
        "so and say what authority is missing — a refusal is a finding.",
    ]
    return "\n".join(out)


def reply_opens(body: str, ref: str) -> bool:
    """Is this the answer to that question? Used to spot a second copy."""
    return body.strip().startswith(f"DESK ANSWER {ref}")


def desk_session(env=None) -> str:
    """Which session holds the desks. REFUSES rather than guessing.

    THE ASKING SKILL COULD NOT BE FOLLOWED WITHOUT THIS. It said "send it to the
    desk session" and left the doer to find out which one that was -- which in
    practice means asking a person, and a step that needs a person in the middle
    is the step V1 exists to remove.

    WHY AN ENVIRONMENT VARIABLE AND NOT A FILE IN THIS REPOSITORY. The desk
    session id is deployment state, not record: it changes when a container is
    replaced, it differs between the firm's machine and a test run, and it is
    the one value that must NOT be the same for everybody who installs the
    plugin. Committing it would make a stale id travel with the release, which
    is the same class of defect as a stale SKILL.md in a plugin cache -- and
    that one has cost four releases.

    NO DEFAULT. There is no sensible fallback: an unset variable means nobody
    has been told where the desk is, and inventing an answer to that produces a
    question sent into a void. `DESIGN-PRINCIPLES.md`: refuse rather than
    default.
    """
    import os
    value = (env if env is not None else os.environ).get(DESK, "").strip()
    if not value:
        raise RelayError(
            f"{DESK} is not set, so there is no desk to ask. It holds the "
            f"session id of the session running `be-the-desk` — export it "
            f"before consulting. It is deployment state and is deliberately "
            f"not committed: an id that shipped with the plugin would be stale "
            f"for everyone but the machine it was written on.")
    if not SESSION.match(value):
        raise RelayError(
            f"{DESK} is {value!r}, which is not a session id. A wrong one fails "
            f"silently — the question goes somewhere, the asker waits, and "
            f"nothing says the desk never saw it.")
    return value
