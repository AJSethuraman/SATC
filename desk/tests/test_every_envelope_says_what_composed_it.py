"""Three envelopes leave this module. Every one of them names the code that wrote it.

WHY THIS IS A TEST AND NOT A CONVENTION. The stamp went onto `as_prompt` in
0.10.1 with an argument that has nothing to do with which envelope is being
read: a SKILL.md can be four releases stale in a plugin cache -- measured, six
times -- and a stale skill cannot know it is stale, so the message on the wire
has to out-rank it. That argument covers a follow-up and a research handoff
exactly as well, and both shipped without the line. Nothing noticed, because
"put it on the envelope" is the kind of rule that gets applied to the envelope
you happen to be editing.

SO THE TEST ENUMERATES THE MODULE RATHER THAN LISTING WHAT EXISTS TODAY. A
fourth envelope added next week either appears in SPECIMENS -- and is checked --
or fails `test_the_registry_covers_every_envelope`. A list of three assertions
would have passed silently on the fourth, which is the same defect one release
later.
"""
import inspect

import record
import relay

ME = "session_01M1pBzTxE9u2xD6d8Yz57dV"
Q = "we signed a 36-month lease on a piece of equipment. is it an asset?"


def _ask():
    return relay.as_prompt(relay.ask(Q, reply_to=ME))


def _follow_up():
    ref = relay.ref_for(Q, ME)
    return relay.follow_up_prompt(
        relay.follow_up(ref, "fixed-assets", {"cost": "over the threshold"}))


def _research():
    gap = relay.research(Q, reply_to=ME,
                         refused_by=(("fixed-assets", "authority_absent"),))
    return relay.research_prompt(gap, reply_to=ME)


#: Every envelope this module composes, and how to compose one.
SPECIMENS = {
    "as_prompt": _ask,
    "follow_up_prompt": _follow_up,
    "research_prompt": _research,
}


def _envelopes():
    """Every public function in `relay` whose job is to compose a message."""
    return {name for name, obj in vars(relay).items()
            if name.endswith("_prompt") and not name.startswith("_")
            and inspect.isfunction(obj)}


def test_the_registry_covers_every_envelope():
    """THE GUARD ON THE GUARD. Without this, adding a fourth envelope leaves the
    stamp unchecked on it and every assertion below still green."""
    assert _envelopes() == set(SPECIMENS), (
        "an envelope exists that this file does not compose; add it to "
        "SPECIMENS so the stamp is checked on it too")


def test_there_really_are_three_of_them():
    """A registry that emptied itself would satisfy the equality above."""
    assert len(SPECIMENS) == 3


def test_every_envelope_says_what_composed_it():
    for name, compose in sorted(SPECIMENS.items()):
        text = compose()
        assert f"Composed by desk {record.VERSION}" in text, (
            f"{name} does not say which code wrote it")


def test_every_envelope_says_why_that_line_is_there():
    """The version alone is a number. What makes it act on is the next clause:
    follow THIS message over the skill you are holding."""
    for name, compose in sorted(SPECIMENS.items()):
        text = compose()
        assert "follow THIS message" in text, f"{name} states a version and no rule"
        assert "a stale skill cannot know it is stale" in text, name


def test_the_stamp_is_one_line_and_the_same_line_everywhere():
    """Three wordings would drift, and a reader who learned to skip one would
    not recognise the others."""
    lines = set()
    for compose in SPECIMENS.values():
        got = [ln for ln in compose().splitlines() if "Composed by desk" in ln]
        assert len(got) == 1, "the stamp appears more than once in one envelope"
        lines.add(got[0])
    assert len(lines) == 1, f"the stamp is worded {len(lines)} different ways"


def test_the_stamp_names_the_running_version_not_a_literal():
    """It reads `record.VERSION`, which reads `plugin.json` beside the module.
    A hard-coded string would be right until the next release and wrong after."""
    assert record.VERSION in relay._stamp()
    assert relay._stamp() != relay._stamp().replace(record.VERSION, "0.0.0")


def test_it_says_unknown_rather_than_guessing_when_it_cannot_tell(monkeypatch):
    """A version it cannot read is not a version it may invent."""
    monkeypatch.setattr(relay, "_version", lambda: "(unknown)")
    assert "Composed by desk (unknown)" in relay._stamp()


def test_the_stamp_sits_near_the_top_of_each_envelope():
    """Below the headline, above the content. A reader deciding whether to trust
    their own skill has to hit it before they act on anything."""
    for name, compose in sorted(SPECIMENS.items()):
        lines = compose().splitlines()
        where = next(i for i, ln in enumerate(lines) if "Composed by desk" in ln)
        assert where <= 3, f"{name} buries the stamp {where} lines down"
