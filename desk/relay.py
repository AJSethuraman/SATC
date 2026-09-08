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


def _version() -> str:
    """The running code's version, for stamping onto an envelope."""
    try:
        import record
        return record.VERSION or "(unknown)"
    except Exception:
        return "(unknown)"


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
           f"*Composed by desk {_version()}. If the skill you are following "
           f"says otherwise, follow THIS message: it came from the code that "
           f"is running, and a stale skill cannot know it is stale.*", "",
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
        "so and say what authority is missing — a refusal is a finding.", "",
        "## Say which desks this reached", "",
        "Name every desk `consult` routed to. **And if the question as phrased "
        "reaches fewer desks than an obvious rephrasing of the same question "
        "would, say that too, and name what it missed.**", "",
        "THE ASKER CANNOT SEE THIS AND YOU CAN. On 8 September a doer asked "
        "*\"what do I do with it\"* about a forklift and reached ONE desk; the "
        "same transaction as *\"is the invoice price deducted or capitalized?\"* "
        "reaches TWO, and the one dropped holds the most on-point paragraph. "
        "Their words: *\"My phrasing was the natural working one and it got "
        "strictly less authority. I did not know that when I wrote it, and a "
        "doer has no way to tell.\"* You are the only party that can tell them.",
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


# ---------------------------------------------------------------------------
# ANSWERING WHAT THE DESK ASKED, and why this is not the context field the firm
# cut.
#
# THE LOOP STOPPED HALF WAY. A desk that cannot answer now asks — `MUST_ASK`,
# 0.9.0 — and nothing carried the answer back. Ask, refuse-with-question, dead
# end. The firm, 8 September 2026: *"this keeps stopping before it actually
# fills the holes."*
#
# WHY THIS IS NOT `facts` RETURNING. The field the firm cut let the ASKER write
# whatever context it liked, and an asker who writes the context writes the
# answer. Here the DESK named the fields. It asked for `invoice_amount`; it gets
# `invoice_amount`. The asker chooses nothing but the values, which is the same
# authority a preparer has when they fill in a file — and every name is checked
# against what the desk actually asked for, so a fact nobody wanted cannot ride
# along.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class FollowUp:
    """Answers to the questions ONE desk asked, against the ref it asked under.

    AND IT NAMES THE DESK, because the ref alone does not identify a refusal.
    `ref_for` is a digest of the question and the asker, so every desk a
    question routes to shares one. The forklift routed to TWO on 8 September and
    refused twice for DIFFERENT reasons — `context_not_on_file` from
    capitalization-and-de-minimis, `facts_not_established` from fixed-assets —
    wanting different facts. A follow-up carrying only the shared ref cannot say
    which of those it answers, and applying it to the wrong branch can even
    report a spurious `no_field_for_this_fact` against a desk that never asked.

    Found by Codex on #339 before this ever ran twice.
    """
    ref: str
    desk: str
    facts: dict


def follow_up(ref: str, desk: str, facts: dict, asked_for=()) -> FollowUp:
    """Build a reply to ONE desk's follow-up, or REFUSE.

    `asked_for` is what the desk said it needed. Empty means it named no fields
    and nothing can be checked — which is allowed, because a desk may ask in
    prose, but the caller is then on their honour and the envelope says so.
    """
    if not (ref or "").strip():
        raise RelayError(
            "no ref. A follow-up that does not say which question it answers "
            "is a new question wearing an answer's clothes.")
    if not (desk or "").strip():
        raise RelayError(
            f"no desk on the follow-up for {ref}. A question reaches more than "
            f"one, and they refuse for different reasons wanting different "
            f"facts — the ref is shared, so it cannot say which refusal this "
            f"answers. `Refusal.desk` names it; pass that.")
    facts = {str(k).strip().lower(): str(v).strip()
             for k, v in (facts or {}).items() if str(v).strip()}
    if not facts:
        raise RelayError(
            f"no facts for {ref}. If the answer is that nobody knows, say THAT "
            f"to the desk in words — a silent empty reply reads as an answer.")
    for name, value in facts.items():
        if TIN.search(value):
            raise RelayError(
                f"the value for {name!r} looks like a TIN. The desks answer "
                f"without identity and this envelope is stored on a trigger.")
    if asked_for:
        wanted = {a.strip().lower() for a in asked_for}
        if extra := sorted(set(facts) - wanted):
            raise RelayError(
                f"the desk did not ask for {', '.join(extra)}. It asked for "
                f"{', '.join(sorted(wanted))}. A fact riding along uninvited is "
                f"the asker framing the question, which is what the desk being "
                f"a separate session exists to stop.")
    return FollowUp(ref=ref.strip(), desk=desk.strip(), facts=facts)


def follow_up_prompt(f: FollowUp) -> str:
    """The message that carries the answers back to the desk."""
    out = [f"DESK FOLLOW-UP {f.ref} — for the **{f.desk}** desk. You asked for "
           f"these and here they are.", "",
           f"**This answers {f.desk}'s refusal and no other.** The same question "
           f"may have reached other desks, which refuse for their own reasons "
           f"and want their own facts; the ref is shared between them and the "
           f"desk name is what tells them apart. Re-run it for {f.desk}.", "",
           "## What was answered", ""]
    out += [f"- **{name}:** {value}" for name, value in sorted(f.facts.items())]
    out += ["", "## Now answer the original question", "",
            f"Re-run it with these on file — `ask.answer(..., context="
            f"record.Context(facts={{...}}))` — and reply exactly as before, "
            f"opening with `DESK ANSWER {f.ref}`.", "",
            "**Only these were answered.** Anything you asked for that is not "
            "listed above is STILL not on file: refuse on it again rather than "
            "treat this reply as permission to assume it. A follow-up that "
            "fills three of four holes and is read as filling four is worse "
            "than no reply at all.", "",
            "If these change nothing — if they were not in fact what the "
            "question turned on — say so plainly. That is a finding about the "
            "question you asked, not a failure."]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# WHEN NOBODY HOLDS THE RULE: sending the question on to be RESEARCHED.
#
# The firm, 8 September 2026: *"the skill also has to direct questions to this
# container when they need research, obviously"*.
#
# `run-down-a-question` has existed since 5 September and is the right skill. It
# was never CONNECTED: nothing said which session runs it, and nothing carried an
# `authority_absent` refusal to that session. A doer got "nothing this desk holds
# reaches the question", and the trail stopped — the gap went into
# `unsupported/` for somebody to find later, if anybody ever looked.
#
# WHY THIS IS THE THIRD ENVELOPE AND NOT A FLAG ON THE FIRST. A question asks
# "what does the record say"; this asks "go and find what nobody has". They have
# different answers (a passage nobody has admitted yet, versus a served
# conclusion), a different destination (the session that can reach a publisher),
# and a different disposition — **nothing found this way enters the record**.
# The searcher PROPOSES; the firm admits. Making it a flag would have let a
# lookup return as though it were an answer.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Research:
    """A gap no desk could reach, sent to the session that can go and look."""
    ref: str
    question: str
    refused_by: tuple


def research(question: str, reply_to: str, refused_by=()) -> Research:
    """Send an `authority_absent` gap to be run down, or REFUSE to send it.

    `refused_by` is `((desk, reason), ...)` from the refusals that produced the
    gap. It is REQUIRED and it is checked, because the one thing that must not
    happen here is a question being researched that a desk could already answer:
    a search that finds authority the record already holds costs the firm a
    source-admission decision it does not need to make, and a search launched
    because an agent did not like the answer it got is not research.
    """
    a = ask(question, reply_to)                    # same refusals, same TIN gate
    rows = tuple((str(d).strip(), str(r).strip()) for d, r in (refused_by or ()))
    if not rows:
        raise RelayError(
            "nothing refused this. A gap is what a DESK could not reach, and "
            "`refused_by` is the evidence — without it this is a search for "
            "authority nobody has established is missing.")
    if wrong := sorted({r for _, r in rows if r != "authority_absent"}):
        raise RelayError(
            f"refused {', '.join(wrong)}, which is not a gap in the record. "
            f"`authority_absent` is the only refusal this answers — the others "
            f"are answered by a person, by the firm, or by asking a different "
            f"desk, and searching for authority instead is how a refusal gets "
            f"talked out of.")
    return Research(ref=a.ref, question=a.question, refused_by=rows)


def research_prompt(r: Research, reply_to: str) -> str:
    """The message the researching session receives."""
    out = [f"RUN DOWN {r.ref} — no desk holds the rule for this, and you are "
           f"the session that can go and look.", "",
           "## The question", "", r.question, "",
           "## What already refused it, and why", ""]
    out += [f"- **{desk}** — `{reason}`" for desk, reason in r.refused_by]
    out += ["",
            "Every one of these said `authority_absent`: not that the answer is "
            "hard, but that **the record does not contain the rule**. That is "
            "what you are looking for.", "",
            "## How", "",
            "Use `run-down-a-question`. Search anywhere. **Verify every find "
            "against the publisher's own page** — a citation that only exists "
            "in a search result is not a find.", "",
            "## The two things that are not yours to decide", "",
            "1. **Nothing you find enters the record.** Propose it. The firm "
            "admits a source; a session never does. `keep=False`, no commit, no "
            "write into any desk.",
            "2. **A licence is a wall, not an obstacle.** Where a publisher "
            "gates its text behind a CAPTCHA, a terms click or a sign-in, "
            "NAME THE WALL EXACTLY and stop. Do not solve it, do not accept "
            "terms on the firm's behalf, do not route around it. Whether the "
            "firm holds a licence is their answer to give.", "",
            "## What to send back", "",
            f"Reply poke-only to `{reply_to}` — `create_trigger` with NO "
            f"`run_once_at` and NO `cron_expression`, then one `fire_trigger` — "
            f"opening with `FOUND {r.ref}` or `LOOKED {r.ref}`.", "",
            "**`LOOKED` is a real answer and I want it.** *\"I searched, here is "
            "where, and the authority is not reachable\"* is a finding: it turns "
            "a gap nobody has examined into a gap somebody has, which is the "
            "difference between a queue and a pile. Say where you looked either "
            "way.", "",
            "No client name, TIN or figure in the reply."]
    return "\n".join(out)
