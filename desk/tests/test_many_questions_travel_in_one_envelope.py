"""Several questions go to the desk in one envelope, and come back one per ref.

`dec-askside`, 25 September 2026 — the firm, taking the recommendation: send all
the questions in one message.

SARCIA PILOT 2 IS THE REASON. Occam composed seven questions, sent three and
stopped. It gave two reasons of its own: it read "end your turn" as "stop
sending", and each question cost it about 20,000 characters of context because
the platform echoes a trigger's prompt back on every create and fire. One
envelope per question means paying the rules once per question AND having a
"send the next one" step to forget. A batch pays once and has no next one.

MEASURED on the pilot's own seven questions:
    one at a time, today's envelope    21,013 characters
    one batch                           4,237 characters
    one at a time, this morning        ~42,600 characters (6,082 x 7)

THE COST THE FIRM ACCEPTED: answers come back together, so a slow question holds
the rest. Nothing about how any single question is answered changes.
"""
from __future__ import annotations

import pytest

import relay

ME = "session_" + "a" * 20
PILOT_2 = [
    "a payment on a business account shows the vendor but not what was bought "
    "- what is required before it is treated as a deductible business expense?",
    "hand tools are bought for the trade during the year - are they deducted "
    "or capitalized?",
    "a business credit card paid a cash back reward into the account - is "
    "that income?",
    "work clothing bought for a trade could also be worn day to day - is it "
    "deductible?",
    "money leaves the business account to pay a credit card the bookkeeper has "
    "no statements for - how is that payment treated?",
    "deposits arrive in a business account with no invoice or label behind "
    "them - are they all revenue?",
    "the owner ran up a tab at a bar while meeting a customer - is it "
    "deductible?",
]


@pytest.fixture
def batch():
    return relay.ask_many(PILOT_2, ME)


# --- building one -----------------------------------------------------------

def test_every_question_keeps_its_own_ref(batch):
    assert [a.ref for a in batch.asks] == [relay.ref_for(q, ME) for q in PILOT_2]


def test_an_empty_batch_is_refused():
    with pytest.raises(relay.RelayError):
        relay.ask_many([], ME)


def test_one_question_carrying_a_tin_refuses_the_whole_batch():
    """Sending the other six would hand the doer a batch it believes complete."""
    with pytest.raises(relay.RelayError):
        relay.ask_many(PILOT_2[:3] + ["payee 123-45-6789 - is this a 1099?"], ME)


def test_the_same_question_twice_is_refused():
    """It would be answered twice, and the second answer would read as a
    duplicate delivery — the thing refs exist to catch."""
    with pytest.raises(relay.RelayError):
        relay.ask_many([PILOT_2[0], PILOT_2[0]], ME)


# --- the envelope -------------------------------------------------------------

def test_the_envelope_carries_every_question_and_every_ref(batch):
    body = relay.batch_prompt(batch)
    for a in batch.asks:
        assert a.question in body and a.ref in body


def test_the_rules_are_stated_once_not_once_per_question(batch):
    """The whole saving. A batch that repeated the rules per question would be
    seven envelopes stapled together."""
    body = relay.batch_prompt(batch)
    for rule in ("judging.Judgment(", "DELIVERS TWICE", "a refusal is a finding",
                 "NOTHING YOU CAN SEE TELLS YOU WHETHER IT LANDED"):
        assert body.count(rule) == 1, f"{rule!r} appears {body.count(rule)} times"


def test_a_batch_of_seven_costs_less_than_two_single_envelopes(batch):
    single = len(relay.as_prompt(relay.ask(PILOT_2[0], ME)))
    assert len(relay.batch_prompt(batch)) < 2 * single


def test_the_desk_is_told_to_answer_each_one_and_send_one_reply(batch):
    body = relay.batch_prompt(batch)
    assert "Answer EACH one separately" in body
    assert "Send ONE reply holding every answer" in body
    assert "comes back to the asker as unanswered" in body


def test_every_fence_in_the_batch_is_closed(batch):
    lines = relay.batch_prompt(batch).splitlines()
    assert lines.count("```") % 2 == 0


# --- reading what comes back ---------------------------------------------------

def _reply(batch):
    """Answers out of order, one of them mangled by a console, one refused, one
    served, one unreadable, and the rest never answered at all."""
    r = [a.ref for a in batch.asks]
    return r, "\n".join([
        f"DESK ANSWER {r[2]}",
        "THE DESK DID NOT ANSWER - context_not_on_file  -  corpus",
        "    the detail", "",
        f"DESK ANSWER {r[0]}",
        "THE DESK DID NOT ANSWER: authority_permits_choice  |  corpus",
        "    the detail", "",
        f"DESK ANSWER {r[1]}",
        "deducted",
        "",
        "    26 CFR 1.162-3(c)(1)(iv)",
        "    primary | the firm treats as binding | confirmed 2026-09-05", "",
        f"DESK ANSWER {r[3]}",
        "I think it is probably deductible.", "",
    ])


def test_each_answer_is_handed_back_under_its_own_ref(batch):
    refs, body = _reply(batch)
    got = relay.read_batch(body, refs)
    assert got.answers[refs[0]].reason == "authority_permits_choice"
    assert got.answers[refs[2]].reason == "context_not_on_file"
    assert got.answers[refs[1]].answered and got.answers[refs[1]].binding


def test_an_answer_that_cannot_be_placed_is_kept_apart_not_read_as_a_no(batch):
    refs, body = _reply(batch)
    got = relay.read_batch(body, refs)
    assert refs[3] in got.unreadable and refs[3] not in got.answers


def test_a_ref_the_desk_never_answered_is_reported_missing(batch):
    """Folding it into "refused" would say the desk said no when it said
    nothing — and the pilot's own four unsent questions were exactly that."""
    refs, body = _reply(batch)
    got = relay.read_batch(body, refs)
    assert set(got.missing) == set(refs[4:])
    assert not got.complete


def test_an_empty_reply_is_not_a_set_of_refusals(batch):
    with pytest.raises(relay.RelayError):
        relay.read_batch("   ", [a.ref for a in batch.asks])


# --- a marker the asker did not send -------------------------------------------

def test_a_mistyped_ref_does_not_swallow_the_answer_before_it(batch):
    """Found by Codex on #397. The reader split only on the refs it asked for,
    so a block opening with a mistyped ref ran on into the answer above it. A
    served answer followed by a refusal under a bad ref then carried both a
    grade line and a refusal banner, and the good answer was lost as
    unreadable while the mistyped one was reported missing."""
    r = [a.ref for a in batch.asks]
    body = "\n".join([
        f"DESK ANSWER {r[0]}",
        "deducted",
        "",
        "    26 CFR 1.162-3(c)(1)(iv)",
        "    primary | the firm treats as binding | confirmed 2026-09-05", "",
        "DESK ANSWER 0123456789ab",
        "THE DESK DID NOT ANSWER: authority_permits_choice  |  corpus",
        "    the detail", "",
    ])
    got = relay.read_batch(body, r[:2])
    assert got.answers[r[0]].answered
    assert r[0] not in got.unreadable
    assert got.missing == (r[1],)
    assert got.unexpected == ("0123456789ab",)
    assert not got.complete


def test_a_ref_answered_twice_is_not_read_as_either_answer(batch):
    """Picking one would be guessing which the desk meant."""
    r = [a.ref for a in batch.asks]
    body = "\n".join([
        f"DESK ANSWER {r[0]}",
        "THE DESK DID NOT ANSWER: authority_permits_choice  |  corpus", "",
        f"DESK ANSWER {r[0]}",
        "THE DESK DID NOT ANSWER: context_not_on_file  |  corpus", "",
    ])
    got = relay.read_batch(body, r[:1])
    assert r[0] in got.unreadable and r[0] not in got.answers
    assert not got.complete


# --- text no marker claims ---------------------------------------------------------

SERVED = ["deducted", "",
          "    26 CFR 1.162-3(c)(1)(iv)",
          "    primary | the firm treats as binding | confirmed 2026-09-05", ""]


def test_an_answer_whose_marker_was_dropped_is_not_reported_as_silence(batch):
    """Found by Codex on #397. Text before the first marker was never looked
    at, so an unmarked first answer came back as "missing" — the desk said
    nothing — when the desk had in fact answered. With unmarked text in the
    reply, nobody can say which ref it belongs to: a person reads it."""
    r = [a.ref for a in batch.asks]
    body = "\n".join(SERVED + [
        f"DESK ANSWER {r[1]}",
        "THE DESK DID NOT ANSWER: authority_permits_choice  |  corpus", ""])
    got = relay.read_batch(body, r[:2])
    assert r[0] not in got.missing
    assert r[0] in got.unreadable
    assert "deducted" in got.stray
    assert not got.complete


def test_a_preamble_does_not_spoil_a_reply_that_answered_everything(batch):
    """The envelope asks for reasoning too. Words before the first answer are
    harmless when every ref is accounted for, and are still kept."""
    r = [a.ref for a in batch.asks]
    body = "\n".join(["Two answers below.", "", f"DESK ANSWER {r[0]}"] + SERVED)
    got = relay.read_batch(body, r[:1])
    assert got.complete and got.answers[r[0]].answered
    assert got.stray == "Two answers below."


def test_the_skill_does_not_say_to_discard_a_second_answer():
    """Found by Codex on #397: the skill said "read one and discard the other",
    which is the guess `read_batch` refuses to make."""
    from pathlib import Path
    text = (Path(relay.__file__).parent / "skills/ask-desk/SKILL.md").read_text(encoding="utf-8")
    assert "read one and discard the other" not in text
