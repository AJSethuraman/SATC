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
