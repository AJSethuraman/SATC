"""What a field is ALLOWED to hold, as opposed to how sure the reader was.

D9, found by walking the product on 5 September 2026. Reading a W-2 line
``Box 17  State income tax  2,679.00`` put the string **"income tax"** into
**Box 15 — State**, whose only legal values are the two-letter codes.

It was caught — staged LOW, left for review — but it was caught by *confidence*,
not by *validity*. Nothing on the row knew a state field cannot hold a verb
phrase. **Had the same read come back HIGH, "income tax" would have been
auto-confirmed as the state**, gone into the Drake input as ``box15_state``, and
from there onto a return.

Confidence answers "how sure was the reader"; a shape answers "could this be
right at all". They are different questions and only one of them was being
asked. A reader that is confidently wrong is the case that matters, because it
is the only one nothing else stops.

WHY THE SHAPES ARE DECLARED IN THE CONFIG rather than matched on field names
here: `configs/extraction/*.yaml` is already where a field says whether it is
money and whether it is sensitive. Inferring "this looks like a state field from
its path" would work for `w2.box15_state` and quietly not for the next form's
state box, which is how a check ends up guarding the one door somebody walked.

WHAT A FAILING SHAPE DOES, AND WHAT IT DOES NOT. It forces the field to
NEEDS_REVIEW at UNCERTAIN with a note naming what was expected. It does NOT
discard the value or substitute one: the preparer has to see what the document
actually said in order to decide. Refusing rather than defaulting is
`docs/DESIGN-PRINCIPLES.md`, and a blanked field would lose the evidence that
the reader went wrong.
"""

from __future__ import annotations

# The 50 states, DC, and the territories that issue W-2s and withhold.
STATE_CODES = frozenset("""
AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO
MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY
DC AS GU MP PR VI
""".split())


def _fits_state(text: str) -> bool:
    return text.strip().upper() in STATE_CODES


# What each declared shape accepts, and the sentence a preparer reads when it
# does not. The sentence says what was expected -- "not a state" tells somebody
# nothing they did not already suspect.
SHAPES = {
    "state": (_fits_state,
              "a two-letter state or territory code (OH, PA, DC)"),
}


def known(shape: str) -> bool:
    return shape in SHAPES


def fits(shape: str, text: str) -> bool:
    """Whether `text` could legitimately be this field's value.

    An UNDECLARED shape fits everything -- a field nobody has described has no
    rule to break, and inventing one here would reject values on a guess. An
    EMPTY value fits everything too: a box the reader found nothing in is an
    ordinary state of a document, and failing it would bury the real failures.
    """
    if not shape or shape not in SHAPES:
        return True
    if not str(text).strip():
        return True
    return SHAPES[shape][0](str(text))


def expected(shape: str) -> str:
    """The sentence naming what the field can hold. Empty for an unknown shape."""
    return SHAPES[shape][1] if shape in SHAPES else ""


def refusal(shape: str, text: str) -> str:
    """Why this value cannot be that field's, in words a preparer can act on."""
    want = expected(shape)
    return (f"{text.strip()!r} is not {want}" if want
            else f"{text.strip()!r} does not fit this field")
