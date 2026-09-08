"""THIS TEST PINS A DEFECT, NOT A BEHAVIOUR ANYONE WANTS.

It is green because the defect is live. It goes red the day the routing
mechanism changes, which is exactly when this incident should be re-read. Do
not "fix" it by editing the assertions.

MEASURED 8 September 2026, on the deposits round of the first live close.
Forge-Occam put five natural phrasings of one question -- what to do with
deposits nobody can identify -- to the desks, and reported: *"The word that
saved me was 'bank'."*

Re-measured here against all seven desks. It is worse than silence:

  "how should unidentified deposits be treated?"        -> NO DESK
  "a deposit nobody can identify"                       -> NO DESK
  "unexplained deposits in the operating account"       -> NO DESK
  "what do we do with deposits we can't tie to
   an invoice?"                                         -> capitalization-and-de-minimis
  "are unidentified deposits gross receipts?"           -> meals-and-entertainment,
                                                           rewards-and-information-returns
  "are unidentified bank deposits taxable income?"      -> cash-and-bank   (correct, on `bank`)

THE MIS-ROUTES ARE THE FINDING, NOT THE SILENCE. Silence is at least a declared
result -- `routing`'s own docstring argues for it, and `ask.consult_or_file`
files the question as a hole so nothing is lost. A wrong desk is not a declared
result. A question about money arriving in a bank account reaches the MEALS
desk, and it reaches it deterministically, every time, with no signal to the
doer that anything went wrong.

WHY IT CANNOT BE PATCHED IN THE WORD LIST. The collision is two senses of one
word, both correctly declared by the desk that owns them:

  meals-and-entertainment  S4  `receipts`        the paper you keep -- documentary evidence
  rewards-and-information  S7  `gross receipts`  revenue

Neither desk is wrong. A matcher that compares words to words has nothing to
read the sense with, so it cannot prefer one. Widening `cash-and-bank` to fire
on `deposit` does not repair this either: it would add a third desk to the same
answer, and that desk's only source is Pub. 583 on reconciling a checking
account, which does not say whether a deposit is income. Declaring a subject a
desk holds no source for is inventing the authority the desk exists to refuse
without.

ON THE DOCKET AS M1 -- keep the desks or replace them with one pool -- and the
firm decides it, not this file.
"""
from pathlib import Path

import routing

DESKS = Path(__file__).resolve().parent.parent / "desks"


def _route(question):
    return sorted(r.desk for r in routing.route(question, routing.registry(DESKS)))


def test_three_of_six_deposit_phrasings_reach_no_desk():
    for question in ("how should unidentified deposits be treated?",
                     "a deposit nobody can identify",
                     "unexplained deposits in the operating account"):
        assert _route(question) == [], (
            f"{question!r} now reaches a desk. If routing changed on purpose, "
            f"read this file's docstring before editing it -- it is the record "
            f"of why the change was needed.")


def test_a_deposits_question_reaches_the_meals_desk():
    """The one to read out loud when M1 is decided."""
    assert "meals-and-entertainment" in _route(
        "are unidentified deposits gross receipts?")


def test_the_word_that_saved_it_was_bank():
    """Change one noun and the same question finds the right desk. That is the
    whole margin the current mechanism runs on."""
    assert _route("are unidentified bank deposits taxable income?") == ["cash-and-bank"]
