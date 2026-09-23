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
    """The other half of the same defect: a 200 from `fire_trigger` is not
    delivery, so a desk that trusts it reports success early, and an asker that
    chases cannot tell early from failed."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "is not delivery" in body


def test_and_that_the_durable_record_is_not_the_fallback_either():
    """MEASURED BOTH WAYS ON 8 SEPTEMBER, on the reply to this very envelope.

    The desk fired, went to the durable record to check itself — the right
    instinct — and found no `last_fired_at`, no run row, and `updated_at` equal
    to `created_at`. It reported a delivery failure. The message had arrived
    five seconds after the fire and was sitting undelivered in the asker's
    notification queue.

    So the rule is not "trust the record instead of the return value". Neither
    one knows. An envelope that warned about the 200 and stopped there sends a
    careful desk to the second wrong oracle, which is what happened."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "not evidence of non-delivery" in body.replace("\n", " ")
    assert "Only the recipient knows" in body


def test_it_tells_the_desk_to_open_with_the_ref():
    a = relay.ask(Q, reply_to=ME)
    assert f"DESK ANSWER {a.ref}" in relay.as_prompt(a)


def test_it_says_a_refusal_is_a_finding():
    """A desk that reads "answer this" as "produce an answer" will produce one."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "a refusal is a finding" in body


def test_it_forbids_writing_to_the_record():
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "Do not write to the record" in body


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


def test_the_envelope_asks_the_desk_to_say_what_the_phrasing_reached():
    """WHAT THE RETRIEVAL DID IS INVISIBLE TO THE ASKER AND VISIBLE TO THE DESK.

    On 8 September a doer asked "what do I do with it" about a forklift and
    reached ONE desk. The same transaction phrased as "is the invoice price
    deducted or capitalized?" reached TWO — and the one dropped, `fixed-assets`,
    held the most on-point paragraph. The doer: *"My phrasing was the natural
    working one and it got strictly less authority. I did not know that when I
    wrote it, and a doer has no way to tell."*

    Nothing in the engine was wrong there — `routing.route` was a comparison and
    it compared correctly. What was missing is that the only party who can see
    what the question reached was not asked to report it. That is still true
    with the desks gone, and `test_the_envelopes_measurement_is_still_the_truth`
    is what stops the envelope's own numbers going stale."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "Name the citations it came back with" in body
    assert "reaches authority this one did not" in body


def test_the_envelopes_measurement_is_still_the_truth():
    """THE ENVELOPE QUOTES A NUMBER, SO THE NUMBER IS RECOMPUTED HERE.

    It tells the answerer that the forklift asked the natural way now reaches
    NOTHING while the explicit phrasing reaches eight — measured 11 September
    2026, and worse than the one-desk-of-two it replaced. A figure in a message
    an agent reads at runtime is the worst place for a stale one: it is quoted
    as evidence and nobody re-checks it.

    IF THIS GOES RED THE RETRIEVAL MOVED. Down to a smaller gap is the pool
    learning the natural phrasing — good, and the envelope's sentence has to
    move with it. Anything else is a regression nobody asked for.
    """
    import ask
    from conftest import CORPUS

    natural = "what do i do with it? we bought a forklift"
    explicit = ("we bought a forklift - is the invoice price deducted or "
                "capitalized?")
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))

    assert len(ask.looked(natural, CORPUS)) == 0, (
        "the natural phrasing reaches something now; the envelope still says "
        "it reaches NOTHING AT ALL. Fix the sentence in `relay.as_prompt`.")
    assert len(ask.looked(explicit, CORPUS)) == 8
    assert "0 passages against 8" in body


def test_and_says_why_the_asker_cannot_do_it_themselves():
    """Without the reason a desk reads this as bookkeeping and skips it."""
    body = relay.as_prompt(relay.ask(Q, reply_to=ME))
    assert "THE ASKER CANNOT SEE THIS AND YOU CAN" in body


# ------------------------------------- answering what the desk actually asked

def test_a_follow_up_carries_the_facts_the_desk_named():
    f = relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "18,400"},
                        asked_for=("invoice_amount",))
    assert f.ref == "abc123" and f.facts == {"invoice_amount": "18,400"}


def test_a_fact_the_desk_did_not_ask_for_is_refused():
    """THE DISTINCTION THAT MAKES THIS NOT THE CONTEXT FIELD THE FIRM CUT.

    That field let the ASKER write whatever context it liked, and an asker who
    writes the context writes the answer. Here the DESK named the fields; the
    asker supplies only values. A fact riding along uninvited is the asker
    framing the question again, through a narrower door."""
    with pytest.raises(relay.RelayError, match="did not ask for"):
        relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "18,400",
                                   "trade": "plumber"},
                        asked_for=("invoice_amount",))


def test_a_follow_up_with_no_ref_is_a_new_question():
    with pytest.raises(relay.RelayError, match="no ref"):
        relay.follow_up("", "fixed-assets", {"invoice_amount": "1"}, asked_for=("invoice_amount",))


def test_an_empty_reply_is_refused_rather_than_read_as_an_answer():
    """"Nobody knows" has to be SAID. Silence reads as resolution."""
    with pytest.raises(relay.RelayError, match="no facts"):
        relay.follow_up("abc123", "fixed-assets", {}, asked_for=("invoice_amount",))


def test_a_blank_value_does_not_count_as_answered():
    with pytest.raises(relay.RelayError, match="no facts"):
        relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "   "},
                        asked_for=("invoice_amount",))


def test_no_tin_rides_in_on_a_value_either():
    with pytest.raises(relay.RelayError, match="TIN"):
        relay.follow_up("abc123", "fixed-assets", {"taxpayer": "123-45-6789"})


def test_the_reply_tells_the_desk_the_unanswered_ones_are_still_open():
    """A FOLLOW-UP THAT FILLS THREE OF FOUR HOLES MUST NOT READ AS FOUR. The
    reply arrives as permission to answer, and a desk reading it as permission
    to assume is the whole failure re-entering by the back door."""
    body = relay.follow_up_prompt(
        relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "18,400"}))
    assert "STILL not on file" in body
    assert "refuse on it again" in body


def test_and_invites_the_desk_to_say_the_facts_changed_nothing():
    body = relay.follow_up_prompt(
        relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "18,400"}))
    assert "say so plainly" in body
    assert "not a failure" in body


def test_a_follow_up_must_name_the_desk_it_answers():
    """THE REF IS SHARED BETWEEN EVERY DESK A QUESTION REACHED.

    `ref_for` digests the question and the asker, so a question routing to two
    desks produces ONE ref. The forklift did exactly that on 8 September and
    refused twice for different reasons wanting different facts —
    `context_not_on_file` from capitalization-and-de-minimis,
    `facts_not_established` from fixed-assets. A follow-up carrying only the ref
    cannot say which it answers, and applied to the wrong branch it can report a
    spurious `no_field_for_this_fact` against a desk that never asked for it.

    Found by Codex on #339, before it ever ran on two desks at once."""
    with pytest.raises(relay.RelayError, match="no desk on the follow-up"):
        relay.follow_up("abc123", "", {"invoice_amount": "18,400"})


def test_and_the_reply_says_which_desk_it_is_for():
    body = relay.follow_up_prompt(
        relay.follow_up("abc123", "fixed-assets", {"invoice_amount": "1"}))
    assert "for the **fixed-assets** desk" in body
    assert "answers fixed-assets's refusal and no other" in body


def test_two_desks_on_one_question_share_a_ref():
    """THE PREMISE, pinned. If refs ever became per-desk this guard is dead
    weight and someone should know why it was there."""
    a = relay.ask(Q, reply_to=ME)
    assert relay.ask(Q, reply_to=ME).ref == a.ref


# --------------------------------- sending a gap to be researched

GAP = (("capitalization-and-de-minimis", "authority_absent"),
       ("vehicle-expense", "authority_absent"))
LEASE = "how do I know if a lease should be booked as an asset?"


def test_a_gap_can_be_sent_to_be_run_down():
    """THE FIRM ASKED FOR THIS IN AS MANY WORDS, 8 September 2026: *"the skill
    also has to direct questions to this container when they need research,
    obviously"*.

    `run-down-a-question` had existed since 5 September and was never CONNECTED:
    nothing said which session runs it, and nothing carried an `authority_absent`
    refusal there. A doer was told "nothing this desk holds reaches the question"
    and the trail stopped."""
    r = relay.research(LEASE, ME, refused_by=GAP)
    assert r.question == LEASE
    assert r.refused_by == GAP


def test_a_gap_needs_the_refusals_that_prove_it_is_one():
    """A search nobody's refusal asked for is a search for authority nobody has
    established is missing."""
    with pytest.raises(relay.RelayError, match="nothing refused this"):
        relay.research(LEASE, ME, refused_by=())


@pytest.mark.parametrize("reason", ["facts_not_established", "context_not_on_file",
                                    "wrong_body_of_authority",
                                    "contradicts_ratified_position"])
def test_only_authority_absent_is_a_gap(reason):
    """THE ONE THAT MATTERS. Every other refusal is answered by a person, by the
    firm, or by asking a different desk. Sending those to a searcher is how a
    refusal gets talked out of — the desk said no, so go and find something that
    says yes."""
    with pytest.raises(relay.RelayError, match="not a gap in the record"):
        relay.research(LEASE, ME, refused_by=(("some-desk", reason),))


def test_a_gap_carries_the_same_tin_refusal_as_a_question():
    """It is the same envelope on the same wire and gets the same gate."""
    with pytest.raises(relay.RelayError, match="TIN"):
        relay.research("what about 123-45-6789's lease", ME, refused_by=GAP)


def test_the_envelope_names_every_desk_that_refused():
    body = relay.research_prompt(relay.research(LEASE, ME, refused_by=GAP), ME)
    for desk, _ in GAP:
        assert desk in body


def test_it_says_nothing_found_enters_the_record():
    """PROPOSE, NEVER DISPOSE. A searcher that stored what it found would be
    admitting sources on the firm's behalf."""
    body = relay.research_prompt(relay.research(LEASE, ME, refused_by=GAP), ME)
    assert "Nothing you find enters the record" in body
    assert "The firm admits a source; a session never does" in body


def test_it_forbids_crossing_a_licence_rather_than_leaving_it_to_judgement():
    """FASB ASC is gated by a CAPTCHA, a terms click and a sign-in. On 8
    September a desk hit exactly that, named it, and stopped — because it was
    told to. This is the instruction that made it stop."""
    body = relay.research_prompt(relay.research(LEASE, ME, refused_by=GAP), ME)
    assert "NAME THE WALL EXACTLY and stop" in body
    assert "do not accept terms on the firm's behalf" in body
    assert "their answer to give" in body


def test_looked_and_did_not_find_is_asked_for_as_a_result():
    """A gap nobody has examined and a gap somebody has examined are different
    things, and only one of them is a queue."""
    body = relay.research_prompt(relay.research(LEASE, ME, refused_by=GAP), ME)
    assert "LOOKED" in body
    assert "is a real answer and I want it" in body


def test_the_reply_is_poke_only_here_too():
    body = relay.research_prompt(relay.research(LEASE, ME, refused_by=GAP), ME)
    assert "NO `run_once_at`" in body and "NO `cron_expression`" in body
