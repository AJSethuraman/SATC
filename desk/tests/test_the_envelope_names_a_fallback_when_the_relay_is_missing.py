"""An envelope that names one transport must name what to do without it.

    `dec-relay`, 10 September 2026 -- "Name the fallback."

THE INCIDENT. Forge-Occam ran a real year-end close against the installed plugin
on 9 September and had neither `create_trigger` nor `fire_trigger` in their
toolset. They improvised correctly -- each desk run as a subagent, its answer
handed back as a report -- and then reported what that meant:

    "the envelope's reply protocol is not self-sufficient -- an answerer that
     follows it literally, in an environment without those tools, is stuck with
     no path and no diagnosis."

They were right, and it is the leg V1 turns on: the whole point of the relay is
that a question reaches a desk and the ANSWER COMES BACK. A protocol with one
transport and no named alternative converts a missing tool into silence, and
silence is indistinguishable from the desk having nothing to say.

WHY THE TEST IS SHAPED THIS WAY. It does not check for a sentence. It checks the
RULE: any envelope that instructs the reader to use `create_trigger` must also
tell them what to do when it is absent. That holds for the envelopes written
today and for the next one somebody adds, which is the failure mode -- the
paragraph was missing from both envelopes for the same reason, that whoever
wrote the second copied the shape of the first.
"""

import relay


#: A real session id, because `relay.ask` refuses anything else -- the refusal
#: exists so a desk is never handed an envelope with nowhere to send the answer.
REPLY_TO = "session_01M1pBzTxE9u2xD6d8Yz57dV"


def _envelopes() -> dict:
    """Every envelope this module can render, by name."""
    ask = relay.ask("is a trailer depreciated or expensed?", REPLY_TO)
    out = {"answer": relay.as_prompt(ask)}
    # `research` refuses without a refusal behind it: a gap is what a DESK
    # could not reach, and without that evidence it is a search for authority
    # nobody has established is missing.
    research = relay.research(
        "whether a deposit with no payer is revenue", REPLY_TO,
        refused_by=(("cash-and-bank", "authority_absent"),))
    out["research"] = relay.research_prompt(research, reply_to=REPLY_TO)
    return out


def test_every_envelope_that_names_the_relay_names_the_fallback():
    for name, text in _envelopes().items():
        if "create_trigger" not in text:
            continue
        lowered = text.lower()
        assert "not in your toolset" in lowered or "toolset?" in lowered, (
            f"the {name} envelope tells the reader to use `create_trigger` and "
            "never says what to do when they do not have it -- an answerer "
            "following it literally is stranded with no path and no diagnosis"
        )


def test_the_fallback_says_to_return_the_answer_by_hand():
    """Naming the fallback is not enough; it has to say WHAT to do.

    "There is a fallback" is the shape of an instruction without being one. The
    thing Occam actually did -- hand the reply back as their output -- is what
    the envelope has to say, or the reader improvises and some of them will
    improvise into silence.
    """
    for name, text in _envelopes().items():
        if "create_trigger" not in text:
            continue
        lowered = text.lower()
        assert "final output" in lowered, (
            f"the {name} envelope names the missing-tools case but never says "
            "to return the reply as your output to whoever invoked you"
        )


def test_the_fallback_forbids_silence_and_forbids_inventing_a_transport():
    """The two wrong ways out, both named. A reader who cannot send may either
    say nothing or reach for some other channel; the first loses the answer and
    the second puts client-adjacent text somewhere nobody agreed to."""
    text = _envelopes()["answer"].lower()
    assert "not stay silent" in text or "never stay silent" in text
    assert "invent another transport" in text


def test_the_fallback_does_not_soften_the_delivery_warning():
    """The envelope's honesty about delivery is load-bearing and predates this.

    A fallback that let a reader conclude "the relay is unreliable, so use the
    fallback" would quietly retire the transport V1 is measured on. Both
    paragraphs must be present: the relay is the path, and the fallback is for
    not having it -- not for not trusting it.
    """
    text = _envelopes()["answer"]
    assert "NOTHING YOU CAN SEE TELLS YOU WHETHER IT LANDED." in text
    assert "create_trigger" in text
