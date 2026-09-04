"""The price editor may change a number. It may not change anything else.

`fee-schedule.yaml` is 58 KB and most of it is comments: who set a price, when,
in whose words, and what was rejected on the way. Those comments are the only
record of several decisions in this project. An editor that reformats them
while saving a price is worse than no editor, because the loss is silent and
nobody diffs a file they just used a form to change.
"""

import re

import pytest

import registry_editor as reg


SCHEDULE = reg.SCHEDULE.read_text(encoding="utf-8")


def test_every_price_the_engine_charges_is_offered_for_editing():
    """The list a person sees and the list the engine reads are one list.

    A price missing here is a price that still bills a client and cannot be
    changed except by hand -- which is the situation the firm asked to be rid
    of, and it would come back silently the first time a line was added to the
    schedule.
    """
    offered = {p.path for p in reg.prices()}
    assert "basis.rate" in offered, "the hourly rate is a price"
    assert "per_form" in offered, "the one-price-per-named-form figure is a price"
    for want in ("base.1040.tiers.starter", "base.1040.tiers.business",
                 "base.1065", "per_unit.state_return", "per_unit.brokerage",
                 "amendment.tiers.new_information"):
        assert want in offered, f"{want} is charged but cannot be edited"


@pytest.mark.parametrize("price", reg.prices(), ids=lambda p: p.path)
def test_rewriting_a_price_as_itself_changes_no_byte(price):
    """THE SAFETY PROPERTY, and the whole reason to trust this module.

    A writer that cannot rewrite a value as itself is reformatting something
    on every save. Whatever it reformats will be a comment, because comments
    are most of this file. Checked against every price rather than a sample,
    so a newly-added line with unusual spacing cannot slip past.
    """
    assert reg.set_amount(price.path, price.amount, text=SCHEDULE) == SCHEDULE


@pytest.mark.parametrize("price", reg.prices(), ids=lambda p: p.path)
def test_a_real_change_moves_exactly_one_line(price):
    """One number, one line. Everything else byte-identical."""
    after = reg.set_amount(price.path, price.amount + 7, text=SCHEDULE)
    before_lines, after_lines = SCHEDULE.splitlines(), after.splitlines()
    assert len(before_lines) == len(after_lines), "the line count moved"
    differing = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    assert differing == [price.line - 1], (
        f"expected only line {price.line} to change, got {[i + 1 for i in differing]}"
    )


def test_the_comments_survive_a_save():
    """Counted, not eyeballed. This is the failure the module exists to avoid."""
    def comments(text):
        return [ln for ln in text.splitlines() if ln.lstrip().startswith("#")]
    after = reg.set_amount("base.1040.tiers.standard", 350, text=SCHEDULE)
    assert comments(after) == comments(SCHEDULE)


def test_a_trailing_comment_on_the_price_line_is_kept():
    """Some amounts carry an inline note. It belongs to the price, not to us."""
    text = "basis:\n  rate: 150   # signed 25 Aug\n"
    after = reg.set_amount("basis.rate", 165, text=text)
    assert after == "basis:\n  rate: 165   # signed 25 Aug\n"


def test_a_path_that_names_nothing_refuses_rather_than_guessing():
    """An edit written to the wrong line is worse than an edit that refuses."""
    with pytest.raises(reg.RegistryError) as caught:
        reg.set_amount("per_unit.moon_landing", 5, text=SCHEDULE)
    assert "does not name a price" in str(caught.value)


@pytest.mark.parametrize("bad", [12.5, "300", None, True, -1])
def test_a_price_is_a_whole_number_of_dollars(bad):
    """Money is integers here. A float in a YAML price is how $99.99999 gets
    printed on a client's estimate, and True is 1 in Python."""
    with pytest.raises(reg.RegistryError):
        reg.set_amount("basis.rate", bad, text=SCHEDULE)


def test_the_effect_of_a_change_is_reported_before_it_is_saved():
    """The reason a form beats editing YAML: you see what moved.

    Standard is the demo client's rung below Self-Employed, so raising it
    raises what the demo engagement is quoted. If that ever stops being true
    the report is not telling anyone anything.
    """
    report = reg.effect("base.1040.tiers.business", 560)
    assert report["from"] == 500 and report["to"] == 560
    assert report["published"] is True
    assert not report["problems"]
    # Formatted money, because this is what a person reads in the form. The
    # demo client is on Self-Employed, so its quote moves by exactly the $60.
    assert report["sample_total_before"] == "$645.00"
    assert report["sample_total_after"] == "$705.00"


def test_a_change_that_breaks_the_schedule_is_reported_not_written(tmp_path, monkeypatch):
    """`save` is the last place a broken schedule can be caught before it is on
    disk, and a schedule that does not load takes every document with it."""
    broken = SCHEDULE.replace("base_covers: \"one_included\"", "base_covers: [")
    target = tmp_path / "fee-schedule.yaml"
    target.write_text(broken, encoding="utf-8")
    monkeypatch.setattr(reg, "SCHEDULE", target)
    with pytest.raises(reg.RegistryError):
        reg.save("basis.rate", 160)
    assert target.read_text(encoding="utf-8") == broken, "a refusal wrote anyway"
