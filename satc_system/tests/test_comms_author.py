"""Adding a template should be a sentence, not a YAML expedition.

The library was always config — rewording a letter is a text edit. But ADDING
one meant writing a body file, adding a registry entry, and knowing which merge
fields exist and how they are spelled. This makes it one command, and these
tests guard the thing that makes that safe: a template cannot be born broken.
"""

from __future__ import annotations

import pytest

from satc.comms.author import (
    AuthoredTemplate,
    available_fields,
    slugify,
    strip_unknown_fields,
)


# --- a template cannot be born referencing a field that does not exist --------

def test_an_invented_merge_field_is_stripped():
    """A model writing {client_phone} would produce a letter with a permanent
    "fill in" marker nobody can ever satisfy — unusable, for a reason that is
    not obvious. Better to lose the phrase."""
    body, unknown = strip_unknown_fields(
        "Dear {salutation}, call us on {client_phone} about {tax_year}.")
    assert "{client_phone}" not in body
    assert unknown == ["client_phone"]
    assert "{salutation}" in body and "{tax_year}" in body


def test_real_merge_fields_are_left_alone():
    body, unknown = strip_unknown_fields(
        "Dear {salutation}, your {tax_year} return. {preparer_name}")
    assert unknown == []
    for kept in ("{salutation}", "{tax_year}", "{preparer_name}"):
        assert kept in body


def test_every_available_field_is_actually_declared():
    """The catalogue handed to the model must match the library exactly, or it
    will confidently use a field that renders as a blank forever."""
    from satc.comms import library

    assert set(available_fields()) == set(library().placeholders)


def test_the_catalogue_explains_each_field():
    """A bare name tells a model nothing about when to use it."""
    for name, meaning in available_fields().items():
        assert meaning.strip(), name


# --- keys stay usable ---------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("Estimate reminder", "estimate_reminder"),
    ("Birthday note!", "birthday_note"),
    ("  Year-end planning  ", "year_end_planning"),
    ("???", "untitled"),
])
def test_names_become_sensible_keys(name, expected):
    assert slugify(name) == expected


# --- every template says it is a draft ---------------------------------------

def test_an_authored_template_carries_the_draft_notice():
    """Every template in the library admits it needs reading. A new one must
    too, or the first thing this feature does is create the one letter that
    does not."""
    from satc.comms.author import _DRAFT_NOTICE

    from satc.comms import library

    for tpl in library().templates:
        assert _DRAFT_NOTICE.split("—")[1].strip()[:20] in tpl.body or "DRAFT" in tpl.body


def test_installing_a_duplicate_key_is_refused():
    from satc.comms.author import install

    existing = AuthoredTemplate(
        key="birthday", name="Birthday", kind="email", stage="x",
        description="d", subject="s", body="Dear {salutation},\n")
    with pytest.raises(ValueError, match="already exists"):
        install(existing)


# --- the shipped library ------------------------------------------------------

def test_the_library_covers_the_whole_client_relationship():
    """Onboarding through ending — not just the tax-season middle."""
    from satc.comms import library

    stages = {stage for stage, _ in library().by_stage()}
    for expected in ("Onboarding", "Gathering", "Delivery", "Billing",
                     "Relationship", "Ending"):
        assert any(expected in s for s in stages), expected


def test_the_disengagement_letter_returns_their_records_unconditionally():
    """§10.28(a): a client's own records go back promptly and NOT withheld over
    a fee. Firm-standing wording, deliberately not per-client text anyone can
    soften in the moment."""
    from satc.comms import build_context, library, render
    from satc.obligations.policy import policy

    lib = library()
    values = build_context(client_id="C", client_name="Jordan Rivera",
                           standing_text=policy().standing_text,
                           firm_values=lib.firm_values())
    draft = render(lib.template("disengagement"), values, library=lib)
    assert "regardless of any outstanding fee" in draft.body


def test_the_extension_request_asks_rather_than_announces():
    """Filing one without written permission can destroy a client's
    reasonable-cause defence."""
    from satc.comms import library

    tpl = library().template("extension_request")
    assert "May we" in tpl.subject or "?" in tpl.subject
    # Whitespace-normalised: the phrase wraps a line in the body file, and a
    # test that breaks on rewrapping is a test that punishes editing the letter.
    flat = " ".join(tpl.body.split())
    assert "won't file one without hearing from you" in flat
