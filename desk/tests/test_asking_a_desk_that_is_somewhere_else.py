"""The envelope a doer sends to a desk, and the three things it refuses.

THE FIRM SET THE SHAPE, 8 September 2026: the desk is a session, not a library,
BECAUSE IT IS ON THE FORGE AND HAS A BROWSER THERE. `relay` is the wire. It
sends nothing — the transport is `create_trigger`/`fire_trigger` in the caller's
harness — so what is testable here is exactly what a protocol needs to be: what
a well-formed envelope carries, and what it refuses to carry.

Each rule below is a test because the alternative is a paragraph in a SKILL.md,
and a SKILL.md in this system has been four releases stale in a plugin cache for
a week. LOCAL-LLM-PATTERN rule 6: prose policy is policy one run in three.
"""
import pytest

import relay

ME = "session_01M1pBzTxE9u2xD6d8Yz57dV"
Q = "the bank statement shows a $10 service charge and nothing for it is in the books"


# ------------------------------------------------- a question is answerable

def test_a_question_carries_its_return_address():
    a = relay.ask(Q, reply_to=ME)
    assert a.reply_to == ME
    assert ME in relay.as_prompt(a), "the desk is not told where to send it"


def test_without_one_it_refuses_rather_than_defaulting():
    """THE LEG THIS REPLACES. On the first machine round trip the asking
    session's id reached the desk only because it was typed into the prose. Left
    out, the desk composes its report into its own window and a person carries
    it — which is what V1 removes."""
    with pytest.raises(relay.RelayError, match="nowhere to send"):
        relay.ask(Q, reply_to="the desk session")


@pytest.mark.parametrize("bad", ["", "session_", "sess_01M1pBzTxE9u2xD6d8Yz",
                                 "session_01M1p", "cse_01M1pBzTxE9u2xD6d8Yz57dV"])
def test_a_near_miss_address_is_refused_too(bad):
    """A wrong address fails SILENTLY — delivered somewhere, just not here."""
    with pytest.raises(relay.RelayError):
        relay.ask(Q, reply_to=bad)


def test_an_empty_question_is_not_a_question():
    with pytest.raises(relay.RelayError, match="no question"):
        relay.ask("   ", reply_to=ME)


# ----------------------------------------------------- no identifier crosses

@pytest.mark.parametrize("tin", ["123-45-6789", "12-3456789"])
def test_a_tin_never_reaches_the_wire(tin):
    """THE ENVELOPE BECOMES A LOG. It is stored on the trigger, echoed in its
    record and read back by `list_triggers`. `CLAUDE.md`: real taxpayer PII
    never belongs in artifacts or logs, and this is both."""
    with pytest.raises(relay.RelayError, match="TIN"):
        relay.ask(f"what do I do with {tin}'s bank charge", reply_to=ME)


def test_the_refusal_does_not_echo_the_number_it_refused():
    """A guard that prints the value into the exception has moved it, not
    stopped it — the traceback is a log too."""
    with pytest.raises(relay.RelayError) as e:
        relay.ask("client 123-45-6789 asks about a charge", reply_to=ME)
    assert "45-6789" not in str(e.value)


def test_an_ordinary_question_with_numbers_in_it_still_goes():
    """THE CONTROL. A guard that refused every figure would refuse the job —
    these questions are about money and always carry amounts and dates."""
    a = relay.ask("a $10 charge on 2026-09-30, invoice 4412, what do I do",
                  reply_to=ME)
    assert "4412" in relay.as_prompt(a)


# ------------------------------------------- and it carries no context at all

def test_there_is_nowhere_to_put_context():
    """THE FIRM CUT THIS FIELD, 8 September 2026: *"no- we don't add context to
    it, that defeats the purpose. it falls the same rules and gets the
    de-identified data so it can ensure it answers and asks things
    objectively."*

    It was a second facts channel beside `record.Context`, which already names
    the facts nobody holds instead of leaving them to be assumed. And worse than
    redundant: an asker who writes the context writes the answer, and the desk
    becomes the doer's own reasoning with a citation attached — which is the one
    thing putting it behind a session boundary was for."""
    import inspect
    assert list(inspect.signature(relay.ask).parameters) == ["question", "reply_to"]
    assert not hasattr(relay.ask(Q, reply_to=ME), "facts")


def test_and_the_desk_is_told_the_absence_is_deliberate():
    """Otherwise a desk reads a bare question as an underspecified one and asks
    the doer to fill it in, which reintroduces the framing by the back door."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "No context came with it" in body
    assert "escalate" in body


# ------------------------------------------------- a duplicate is detectable

def test_the_same_question_from_the_same_asker_gets_the_same_ref():
    """STABLE ON PURPOSE. A random id makes a duplicate delivery look like a
    second question, which is the failure the ref exists to catch."""
    assert relay.ask(Q, ME).ref == relay.ask(Q, ME).ref


def test_a_different_question_gets_a_different_one():
    assert relay.ask(Q, ME).ref != relay.ask(Q + " today", ME).ref


def test_two_askers_do_not_collide():
    other = "session_01SSt7177UKKEScqUMBHWpp7"
    assert relay.ask(Q, ME).ref != relay.ask(Q, other).ref


def test_the_reply_is_recognised_by_its_ref():
    a = relay.ask(Q, ME)
    assert relay.reply_opens(f"DESK ANSWER {a.ref}\n\nan entry in the books", a.ref)
    assert not relay.reply_opens("DESK ANSWER deadbeef0000\n\n...", a.ref)


# ------------------------------------- the protocol travels in the envelope

def test_the_envelope_tells_the_desk_to_reply_poke_only():
    """A SKILL.md CAN BE FOUR RELEASES STALE; THIS MESSAGE CANNOT. Measured 8
    September 2026: a trigger with a `run_once_at` that is then poked delivers
    TWICE. On a close that is every question answered twice."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "create_trigger" in body and "fire_trigger" in body
    assert "NO run_once_at" in body and "DELIVERS TWICE" in body


def test_it_warns_that_a_send_is_not_a_delivery():
    """The other half of the same defect: `fire_trigger`'s `last_fired_at` is
    not corroborated by the durable record, so a desk that trusts it reports
    success early, and an asker that chases cannot tell early from failed."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "is NOT delivery" in body


def test_it_tells_the_desk_to_open_with_the_ref():
    a = relay.ask(Q, reply_to=ME)
    assert f"DESK ANSWER {a.ref}" in relay.as_prompt(a)


def test_it_says_a_refusal_is_a_finding():
    """A desk that reads "answer this" as "produce an answer" will produce one."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "a refusal is a finding" in body


def test_it_forbids_writing_to_a_desk():
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "Do not write to a desk" in body


# ------------------------------------------------------------ the two skills

def test_the_asking_skill_does_not_import_the_record():
    """THE BOUNDARY, MECHANISED. `ask-desk` is for the doer, and a doer that
    imports `ask` is holding the record — at which point the citation gate is a
    check it could route around rather than a boundary it cannot."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "ask-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "import relay" in skill
    assert "import ask" not in skill, (
        "the asking side is shown importing the desks; it does not hold them")


def test_the_desk_skill_is_where_the_record_is_read():
    from pathlib import Path
    skill = (Path(__file__).resolve().parents[1] / "skills" / "be-the-desk"
             / "SKILL.md").read_text(encoding="utf-8")
    assert "import ask" in skill


def test_the_envelope_names_the_desk_side_skill_and_not_the_asking_one():
    """SHIPPED WRONG IN 0.8.0 AND CAUGHT WRITING THE END-TO-END RUN.

    `as_prompt` was written while the desk-side skill was still called
    `ask-desk`. The rename split it into two — `ask-desk` for the doer,
    `be-the-desk` for the desk — and the envelope kept telling the desk to use
    the ASKER's skill, which holds no record and would have sent it looking for
    `relay` when it needed `ask`.

    Nothing would have said so: a session told to use a skill that exists reads
    it, finds it is about sending questions, and improvises. The rename was in
    the same commit as this string and neither the tests nor the suite noticed,
    because every assertion about the envelope was about the protocol rather
    than about the instruction."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "`be-the-desk` skill" in body
    assert "NOT `ask-desk`" in body, (
        "a desk that reaches for `ask-desk` finds the asking side and improvises")


def test_the_envelope_is_readable_text_and_not_one_long_line():
    """SHIPPED BROKEN AND FOUND BY PRINTING IT, which is the whole of behaviour
    9. `as_prompt` ended `return "\\\\n".join(out)` — an escaped backslash that
    reached the source verbatim — so every envelope was a single line with the
    two characters `\\n` where its newlines should have been.

    TWENTY-FIVE TESTS PASSED ON IT. Every one asked whether a substring was
    present, and a substring is present either way. Nothing asked whether the
    thing a desk actually reads was legible. A protocol test that never looks at
    the message is testing a dictionary, not a wire."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "\\n" not in body, (
        "literal backslash-n in the envelope: the desk receives one long line")
    assert len(body.splitlines()) > 15
    assert body.splitlines()[0].startswith("DESK REQUEST ")


def test_the_headings_survive_as_headings():
    """Markdown that is not on its own line is not markdown."""
    lines = relay.as_prompt(relay.ask(Q, reply_to=ME)).splitlines()
    for heading in ("## The question", "## How to answer"):
        assert heading in lines, f"{heading!r} is not on a line of its own"


def test_the_reply_snippet_is_a_fenced_block_a_desk_can_copy():
    lines = relay.as_prompt(relay.ask(Q, reply_to=ME)).splitlines()
    assert lines.count("```") == 2, "the create_trigger snippet is not fenced"
    opened = lines.index("```")
    block = lines[opened + 1:lines.index("```", opened + 1)]
    assert any(l.startswith("create_trigger(") for l in block)
    assert any(l.startswith("fire_trigger(") for l in block)


# ------------------------------------------------------- where the desk lives

def test_the_desk_address_comes_from_the_environment():
    assert relay.desk_session({relay.DESK: ME}) == ME


def test_unset_refuses_rather_than_guessing():
    """THE ASKING SKILL COULD NOT BE FOLLOWED WITHOUT THIS. It said "send it to
    the desk session" and left the doer to work out which one — which means
    asking a person, and a step needing a person is the step V1 removes."""
    with pytest.raises(relay.RelayError, match="no desk to ask"):
        relay.desk_session({})


def test_a_wrong_shape_is_caught_before_the_question_goes_nowhere():
    with pytest.raises(relay.RelayError, match="not a session id"):
        relay.desk_session({relay.DESK: "the forge one"})


def test_whitespace_alone_is_unset_not_a_session():
    with pytest.raises(relay.RelayError, match="no desk to ask"):
        relay.desk_session({relay.DESK: "   "})


def test_the_address_is_not_committed_anywhere_in_this_repository():
    """A SESSION ID THAT SHIPPED WITH THE PLUGIN WOULD BE STALE FOR EVERYONE BUT
    THE MACHINE IT WAS WRITTEN ON — the same class of defect as a stale SKILL.md
    in a plugin cache, which has cost four releases. So the value lives in the
    environment and the repository holds only the NAME of the variable.

    The one exception is a decision log quoting a real id in a transcript of
    something that happened; a log is a record and not a configuration."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ids = re.compile(r"session_[A-Za-z0-9]{16,}")
    offenders = []
    for f in list(root.glob("*.py")) + list(root.glob("skills/*/SKILL.md")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if ids.search(line):
                offenders.append(f"{f.relative_to(root)}:{n}")
    assert not offenders, (
        "a session id is committed in code or a skill: " + ", ".join(offenders)
        + f". It is deployment state — read it from ${relay.DESK}")
