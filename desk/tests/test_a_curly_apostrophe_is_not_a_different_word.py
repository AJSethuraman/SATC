"""Typography normalises; meaning does not. `dec-apostrophe`, 10 September 2026.

THE INCIDENT. Forge-Occam, running a real close on the installed plugin, had a
submission refused `contradicts_ratified_position` -- *"a position is the firm's
word and a desk does not revise it"* -- because the position came back carrying
`’` where the record holds `'`. Two characters that are indistinguishable on a
screen, one of which Word, phones and most editors insert automatically. It cost
a round, and the cause was invisible to the person hitting it.

Offered the choice between normalising and staying byte-exact, the firm:
**"Normalise."**

THE PRINCIPLE IS UNCHANGED AND THIS FILE IS WHAT KEEPS IT THAT WAY. A desk does
not revise the firm's word, and the reason normalising is defensible is that a
curly apostrophe is not a different word -- it is a different way of typing the
same one. Everything that could change meaning must still fail, so half of this
file asserts the refusals rather than the passes: it is a test of the loosening
staying small, which is the direction the risk runs in.
"""

import pytest

import engine


@pytest.mark.parametrize("given, known, why", [
    ("the firm’s word", "the firm's word", "curly vs straight apostrophe"),
    ("the firm‘s word", "the firm's word", "opening single quote"),
    ("the firm´s word", "the firm's word", "acute accent as apostrophe"),
    ("the firm`s word", "the firm's word", "backtick as apostrophe"),
    ("say “no”", 'say "no"', "smart double quotes"),
    ("flag it — ask the client", "flag it - ask the client", "em dash"),
    ("flag it – ask the client", "flag it - ask the client", "en dash"),
    ("flag it − ask the client", "flag it - ask the client", "minus sign"),
    ("  Flag It  ", "flag it", "case and surrounding space, as before"),
])
def test_a_different_keystroke_is_the_same_word(given, known, why):
    assert engine._same(given, known), why


@pytest.mark.parametrize("given, known, why", [
    ("do book it to owner draws", "do not book it to owner draws",
     "a dropped negation is the whole answer reversed"),
    ("is deductible", "is not deductible", "negation"),
    ("$2,500", "$5,000", "a changed number"),
    ("flag it for attention", "flag it for review",
     "a synonym is a revision, and the firm's word is the firm's"),
    ("ask the client", "ask the client what was bought",
     "a truncation drops the part that matters"),
    ("capitalise it", "capitalize it",
     "spelling is not typography -- these are two words the firm might mean "
     "differently, and normalising them would be a judgement"),
])
def test_anything_that_could_change_meaning_still_fails(given, known, why):
    assert not engine._same(given, known), why


def test_the_normalising_table_stays_small():
    """A guard on the direction of travel, not on the current contents.

    Every entry is a crack in a rule that is otherwise absolute. The table is
    quotes and dashes, which is what the firm approved; a later addition that
    silently widened it -- stripping punctuation, folding whitespace, mapping
    accented letters -- would turn "does not revise it" into "mostly does not
    revise it" without anybody deciding to.
    """
    mapped = {chr(k): v for k, v in engine._TYPOGRAPHY.items()}
    assert set(mapped.values()) <= {"'", '"', "-"}, (
        f"the table now normalises to something other than a quote or a dash: "
        f"{sorted(set(mapped.values()))}"
    )
    assert len(mapped) <= 20, (
        f"{len(mapped)} characters are being normalised; this list is closed "
        "and short by design"
    )
    for source in mapped:
        assert not source.isalnum(), (
            f"{source!r} is a letter or a digit, and folding one of those is a "
            "change to a word rather than to how it was typed"
        )


def test_a_non_breaking_space_is_known_and_still_refused():
    """Recorded rather than fixed, so the next person finds a note not a mystery.

    U+00A0 is the same class of invisible hazard as a curly apostrophe and it is
    NOT normalised: the firm approved quotes and dashes, and widening past what
    they approved is exactly the failure this check exists to prevent. If this
    test starts failing because somebody added it, that is a decision the firm
    has to have made.
    """
    assert not engine._same("flag it", "flag it")
