"""Wording the model CHOOSES between, never writes.

DESIGN-PRINCIPLES §6a: wherever a human picks from a list, the model picks from
the same list. The practice writes the sentences; the model returns a KEY and
the engine looks up the text.

The property these tests exist for: **every sentence that can reach a client is
in a file a person can read.** Not "is filtered afterwards" — is enumerable.
"""

from __future__ import annotations

from satc.comms.wording import Choice, choose, load_wording, wording


def test_variants_load_with_their_text_and_when():
    slots = wording()
    assert {"scope_of_services", "fee_terms", "proposed_times"} <= set(slots)
    for slot in slots.values():
        for variant in slot.variants:
            assert variant.key, slot.name
            assert variant.text, variant.key
            assert variant.when, variant.key      # the only thing the model judges


def test_every_client_facing_sentence_is_enumerable():
    """THE point. You can read the entire output space in a minute.

    Free generation cannot make this promise at any size, which is why it was
    removed rather than filtered."""
    sentences = [v.text for slot in wording().values() for v in slot.variants]
    assert sentences
    assert len(sentences) < 50, "the set should stay small enough to actually read"
    for text in sentences:
        assert text == text.strip()


def test_no_variant_states_an_amount():
    """A figure can only appear if the PRACTICE wrote one — and none did.

    Checks for AMOUNTS, not digits: "K-1", "1099" and "1040" are form names and
    belong in a client letter. An earlier version banned every digit and failed
    on "K-1s", which is the same over-strict mistake as the composer's first
    money guard.
    """
    import re

    money = re.compile(r"[$£€%]|\d+\.\d\d|\d{1,3},\d{3}")
    for slot in wording().values():
        for variant in slot.variants:
            assert not money.search(variant.text), f"{variant.key}: {variant.text}"


def test_an_unknown_key_falls_back_to_the_default_never_to_prose():
    """A model that answers with something not on the list gets a sentence the
    practice approved. The worst case is 'slightly wrong variant'."""
    slot = wording()["fee_terms"]
    assert slot.get("something_invented") is slot.default
    assert slot.get("") is slot.default


def test_the_default_is_the_first_variant_so_ordering_is_a_decision():
    for slot in wording().values():
        assert slot.default is slot.variants[0]


def test_choosing_works_with_no_model_at_all():
    """Absent Ollama the default is used — a real answer, not a blank."""
    picked = choose(["scope_of_services", "fee_terms"],
                    context="anything", host="http://127.0.0.1:9", timeout=1)
    assert set(picked) == {"scope_of_services", "fee_terms"}
    for name, choice in picked.items():
        assert choice.text
        assert not choice.chosen_by_model
        assert choice.text in [v.text for v in wording()[name].variants]


def test_a_chosen_text_is_always_one_of_the_variants():
    """The structural guarantee, stated as a test."""
    picked = choose(["proposed_times"], context="x",
                    host="http://127.0.0.1:9", timeout=1)
    allowed = {v.text for v in wording()["proposed_times"].variants}
    assert picked["proposed_times"].text in allowed


def test_an_unknown_slot_is_skipped_rather_than_invented():
    assert choose(["not_a_slot"], host="http://127.0.0.1:9", timeout=1) == {}


def test_missing_config_is_empty_not_a_crash(tmp_path):
    assert load_wording(tmp_path) == {}
