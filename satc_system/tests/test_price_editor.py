"""Changing a price through the app has to be the same act as changing it by
hand — same file, same bytes everywhere else, same refusals.

Two failures are being guarded against here, and they are opposite shapes:

  * the LOUD one — a rewritten file. Re-serialising the YAML would drop the
    header essay that explains why a discount is shown rather than hidden, and
    turn a one-line price change into an unreviewable diff.
  * the QUIET one — the wrong entry repriced, or a rate the loader would reject
    landing on disk and taking every quoting screen down with it.

So most of what is asserted below is about the bytes that did NOT change.
"""

import re
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from satc.billing import catalogue, editor
from satc.billing.editor import PriceEditError
from satc.config import ConfigError

REAL_CONFIGS = Path(__file__).resolve().parents[1] / "configs" / "billing"

# A catalogue with the traps in it: a header that must survive, an inline
# comment on a rate, two services whose rates are textually identical, a rate
# in quotes, and prose inside a block scalar that says `standard_rate: 999`.
SERVICES = """\
# SERVICE CATALOGUE — what the practice bills for, and what it is worth.
#
# THE RATE HERE IS THE STANDARD RATE, before any adjustment for what a client
# can afford. This header is the reasoning, and a reformat that loses it is a
# regression rather than a formatting change.

meta:
  currency: USD

services:
  # -- returns --------------------------------------------------------------
  - code: return_1040
    name: "Individual return (1040)"
    client_label: "Your federal individual tax return"
    category: "Tax returns"
    unit: fixed
    standard_rate: 450  # held here since 2024
    description: >-
      Preparing and filing your federal return. This sentence contains
      standard_rate: 999 on purpose, because prose is not a field.

  - code: return_1065
    name: "Partnership return (1065)"
    category: "Tax returns"
    unit: fixed
    standard_rate: 1250

  - code: return_1120s
    name: "S corporation return (1120-S)"
    category: "Tax returns"
    unit: fixed
    standard_rate: 1250

  # -- everything else ------------------------------------------------------
  - code: bookkeeping_cleanup
    name: "Bookkeeping clean-up"
    category: "Bookkeeping"
    unit: per_hour
    standard_rate: "125"
"""

PLANS = """\
# RATE PLANS — what a given client actually pays, and why.
#
# THE DISCOUNT IS SHOWN, NOT HIDDEN. A client on a reduced plan sees what they
# were given. This paragraph is the argument, and it is why this file is not
# re-serialised to change one number.

meta:
  default_plan: standard

plans:
  - key: standard
    name: "Standard"
    discount_pct: 0
    requires_basis: false

  - key: household
    name: "Household rate"
    discount_pct: 25
    requires_basis: true
    note: >-
      Ordinary personal returns for working households.
"""


# --- helpers ----------------------------------------------------------------


def lines_of(raw: bytes) -> list[str]:
    """Split after every newline, keeping the endings — written here rather
    than imported so a bug in the editor's own splitter cannot hide behind it."""
    text = raw.decode("utf-8")
    parts = re.split(r"(?<=\n)", text)
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def the_one_changed_line(before: bytes, after: bytes) -> tuple[str, str]:
    """Assert exactly one line differs, and hand back (old, new).

    Line count must match too: an edit that inserts a line and deletes another
    would otherwise pass a naive comparison.
    """
    old, new = lines_of(before), lines_of(after)
    assert len(old) == len(new), "the edit changed how many lines the file has"
    moved = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
    assert len(moved) == 1, (
        f"expected exactly one changed line, got {len(moved)}: "
        f"{[old[i] for i in moved]} -> {[new[i] for i in moved]}")
    return old[moved[0]], new[moved[0]]


@pytest.fixture
def prices(tmp_path, monkeypatch):
    """A billing config the test owns, wired in where the whole app reads from.

    `CONFIG_ROOT` is patched rather than `billing_dir`, so `billing_dir(root)`
    keeps honouring an explicit root — which is how the editor loads its
    candidate file back through the real loader before saving it.
    """
    folder = tmp_path / "billing"
    folder.mkdir()
    (folder / "services.yaml").write_text(SERVICES, encoding="utf-8", newline="")
    (folder / "rate_plans.yaml").write_text(PLANS, encoding="utf-8", newline="")
    monkeypatch.setattr(catalogue, "CONFIG_ROOT", tmp_path)
    catalogue.forget_prices()
    yield folder
    catalogue.forget_prices()


@pytest.fixture
def real_prices(tmp_path, monkeypatch):
    """The prices this practice actually ships, copied byte for byte.

    The hand-written fixture above is a model of the file; this is the file.
    `services.yaml` is CRLF in this repo and `rate_plans.yaml` is LF, which is
    the mixture that punishes anything reading in default text mode.
    """
    folder = tmp_path / "billing"
    folder.mkdir()
    for name in ("services.yaml", "rate_plans.yaml"):
        shutil.copyfile(REAL_CONFIGS / name, folder / name)
    monkeypatch.setattr(catalogue, "CONFIG_ROOT", tmp_path)
    catalogue.forget_prices()
    yield folder
    catalogue.forget_prices()


# --- the surgical part ------------------------------------------------------


def test_a_rate_change_alters_exactly_one_line(prices):
    before = (prices / "services.yaml").read_bytes()
    edit = editor.set_rate("return_1040", 495)
    after = (prices / "services.yaml").read_bytes()

    old, new = the_one_changed_line(before, after)
    assert "450" in old and "495" in new
    assert edit.line == lines_of(before).index(old) + 1


def test_the_header_and_the_comments_survive_byte_identical(prices):
    """The comments in these files ARE the reasoning. Losing them to change a
    number is the regression this module exists to prevent."""
    before = (prices / "services.yaml").read_bytes()
    editor.set_rate("return_1040", 495)
    after = (prices / "services.yaml").read_bytes()

    old, new = lines_of(before), lines_of(after)
    for index, (was, is_now) in enumerate(zip(old, new)):
        if "standard_rate: 450" in was:
            continue
        assert was == is_now, f"line {index + 1} changed and had no business changing"
    assert b"THE RATE HERE IS THE STANDARD RATE" in after
    assert after.count(b"#") == before.count(b"#")


def test_an_inline_comment_on_the_rate_line_is_kept(prices):
    """`# held here since 2024` is the owner explaining a price to themselves."""
    editor.set_rate("return_1040", 495)
    text = (prices / "services.yaml").read_text(encoding="utf-8")
    assert "standard_rate: 495  # held here since 2024" in text


def test_a_quoted_rate_keeps_its_quotes(prices):
    editor.set_rate("bookkeeping_cleanup", 140)
    text = (prices / "services.yaml").read_text(encoding="utf-8")
    assert 'standard_rate: "140"' in text
    assert catalogue.service("bookkeeping_cleanup").standard_rate == Decimal(140)


def test_the_wrong_service_is_never_repriced(prices):
    """`return_1065` and `return_1120s` both cost 1250, and prose in the first
    service says `standard_rate: 999`. A scan that matches on the value, or one
    that wanders out of the entry it was given, reprices the wrong work."""
    before = (prices / "services.yaml").read_bytes()
    editor.set_rate("return_1120s", 1400)
    after = (prices / "services.yaml").read_bytes()

    old, new = the_one_changed_line(before, after)
    assert old.strip() == "standard_rate: 1250" and new.strip() == "standard_rate: 1400"
    assert catalogue.service("return_1065").standard_rate == Decimal(1250)
    assert catalogue.service("return_1120s").standard_rate == Decimal(1400)
    assert "standard_rate: 999" in after.decode("utf-8"), (
        "prose inside a description is not a field and must not be edited")


def test_the_real_price_list_edits_surgically(real_prices):
    """Against the file the practice actually ships — CRLF and all."""
    path = real_prices / "services.yaml"
    before = path.read_bytes()
    assert b"\r\n" in before, "this test is only meaningful on the CRLF file"

    code = next(iter(catalogue.load_services(real_prices.parent)))
    editor.set_rate(code, Decimal("1234.50"))
    after = path.read_bytes()

    old, new = the_one_changed_line(before, after)
    assert "1234.50" in new and old.split(":")[0] == new.split(":")[0]
    assert after.count(b"\r\n") == before.count(b"\r\n"), (
        "line endings were rewritten — a one-line change became a whole-file diff")


def test_the_lf_file_stays_lf(real_prices):
    path = real_prices / "rate_plans.yaml"
    before = path.read_bytes()
    assert b"\r\n" not in before

    editor.set_discount("household", 30)
    after = path.read_bytes()
    assert b"\r\n" not in after
    the_one_changed_line(before, after)


def test_a_discount_change_alters_exactly_one_line(prices):
    before = (prices / "rate_plans.yaml").read_bytes()
    edit = editor.set_discount("household", 30)
    after = (prices / "rate_plans.yaml").read_bytes()

    old, new = the_one_changed_line(before, after)
    assert old.strip() == "discount_pct: 25" and new.strip() == "discount_pct: 30"
    assert edit.old == "25" and edit.new == "30"
    assert catalogue.plan("household").discount_pct == Decimal(30)


# --- refusals ---------------------------------------------------------------


def untouched(path: Path, before: bytes) -> None:
    assert path.read_bytes() == before, "a refused edit still changed the file"


@pytest.mark.parametrize("bad, expected", [
    (-50, "below zero"),
    ("four hundred", "not a number"),
    ("NaN", "not a number"),
    ("Infinity", "not a number"),
    ("$450", "not a number"),
    ("1,250", "not a number"),
    ("", "blank"),
])
def test_a_rate_that_is_not_money_is_refused_and_nothing_is_written(
        prices, bad, expected):
    before = (prices / "services.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", bad)
    assert expected in str(refusal.value)
    assert "Write" in str(refusal.value), (
        "principle 10 — a refusal names what would have been right")
    untouched(prices / "services.yaml", before)


@pytest.mark.parametrize("bad, expected", [(-5, "surcharge"), (105, "pay the client")])
def test_a_discount_outside_0_to_100_is_refused(prices, bad, expected):
    before = (prices / "rate_plans.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.set_discount("household", bad)
    assert expected in str(refusal.value)
    assert "between 0 and 100" in str(refusal.value)
    untouched(prices / "rate_plans.yaml", before)


def test_0_and_100_are_both_allowed(prices):
    """The edges are real plans — full rate, and no charge."""
    editor.set_discount("household", 0)
    assert catalogue.plan("household").discount_pct == Decimal(0)
    editor.set_discount("household", 100)
    assert catalogue.plan("household").is_free


def test_an_unknown_code_names_the_ones_that_exist(prices):
    before = (prices / "services.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1041", 500)
    message = str(refusal.value)
    assert "return_1041" in message
    assert "return_1040" in message and "bookkeeping_cleanup" in message
    untouched(prices / "services.yaml", before)


def test_an_unknown_plan_names_the_ones_that_exist(prices):
    with pytest.raises(PriceEditError) as refusal:
        editor.set_discount("student", 10)
    assert "household" in str(refusal.value) and "standard" in str(refusal.value)


def test_a_code_that_appears_twice_refuses_rather_than_guessing(prices):
    """YAML keeps both and the loader silently uses the last. Picking one here
    would mean the screen and the loader disagree about which line is the
    price — so it refuses and says which lines to look at."""
    path = prices / "services.yaml"
    path.write_text(SERVICES + """
  - code: return_1040
    name: "Individual return (duplicate)"
    category: "Tax returns"
    unit: fixed
    standard_rate: 600
""", encoding="utf-8", newline="")
    before = path.read_bytes()

    both = [n for n, row in enumerate(lines_of(before), start=1)
            if row.strip() == "- code: return_1040"]
    assert len(both) == 2

    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495)
    message = str(refusal.value)
    assert "appears 2 times" in message
    assert all(str(n) in message for n in both), "the refusal names both lines"
    untouched(path, before)


def test_a_service_with_no_rate_line_refuses_rather_than_inventing_one(prices):
    path = prices / "services.yaml"
    path.write_text("""
services:
  - code: consult
    name: "Consultation"
    unit: per_hour
""", encoding="utf-8", newline="")
    before = path.read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("consult", 200)
    assert "standard_rate" in str(refusal.value)
    untouched(path, before)


def test_a_file_that_moved_under_you_is_refused(prices):
    """The owner opens the prices screen, edits the YAML by hand over lunch,
    then submits the stale form. Silently reverting the hand edit is the exact
    trap this whole design was chosen to avoid."""
    path = prices / "services.yaml"
    seen = editor.file_stamp("services")

    path.write_text(SERVICES.replace("standard_rate: 450", "standard_rate: 475"),
                    encoding="utf-8", newline="")
    before = path.read_bytes()

    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495, expected_stamp=seen)
    assert "changed on disk" in str(refusal.value)
    assert "Reload" in str(refusal.value)
    untouched(path, before)
    assert catalogue.service("return_1040").standard_rate == Decimal(475)


def test_a_change_that_lands_while_the_edit_is_being_checked_is_not_overwritten(
        prices, monkeypatch):
    """The window between reading the file and replacing it is small, but a
    save from another window lands inside it eventually — and losing that save
    would look exactly like the stale-override trap this design rejected."""
    path = prices / "services.yaml"
    honest_loader = catalogue.load_services

    def someone_else_hits_save_during_the_check(root):
        path.write_text(SERVICES.replace("standard_rate: 450", "standard_rate: 475"),
                        encoding="utf-8", newline="")
        return honest_loader(root)

    monkeypatch.setattr(catalogue, "load_services",
                        someone_else_hits_save_during_the_check)

    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495)
    assert "changed on disk" in str(refusal.value)
    assert b"standard_rate: 475" in path.read_bytes()
    assert b"495" not in path.read_bytes(), "the other window's save was thrown away"


def test_the_new_price_shows_even_when_the_clock_cannot_tell(prices, monkeypatch):
    """450 -> 495 does not change the file's SIZE, and two writes a millisecond
    apart can share an mtime. The catalogue's cache key is mtime and size, so
    on an unlucky filesystem it would keep serving 450 — the silent failure
    where the owner invoices at the old rate and never finds out."""
    monkeypatch.setattr(catalogue, "_stamp", lambda path: ("indistinguishable",))
    assert catalogue.service("return_1040").standard_rate == Decimal(450)

    editor.set_rate("return_1040", 495)

    assert catalogue.service("return_1040").standard_rate == Decimal(495)


def test_the_stamp_the_edit_hands_back_lets_the_next_edit_through(prices):
    first = editor.set_rate("return_1040", 495)
    second = editor.set_rate("return_1040", 500, expected_stamp=first.stamp)
    assert second.old == "495" and second.new == "500"


# --- the loader is the gate -------------------------------------------------


def test_a_contingent_fee_service_is_refused_by_the_real_loader(prices):
    """Nothing in this module knows what Circular 230 §10.27 is, and nothing in
    it should — the refusal lives in the loader, and the candidate file is
    loaded through the loader before it is allowed to become the price list."""
    before = (prices / "services.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.add_service({
            "code": "refund_share", "name": "Refund share",
            "client_label": "Our fee — 10% of refund", "category": "Tax returns",
            "unit": "fixed", "standard_rate": 0})
    message = str(refusal.value)
    assert "10.27" in message, "the loader's own words reach the owner"
    assert "NOT saved" in message
    untouched(prices / "services.yaml", before)


@pytest.mark.parametrize("sabotage, expected", [
    ("-5", "negative rate"),
    ('450 "', "non-numeric rate"),
    ('"oops', "not readable as YAML"),
])
def test_a_rate_the_loader_would_reject_never_reaches_disk(
        prices, monkeypatch, sabotage, expected):
    """Mutation test (principle 12): break the writer on purpose and confirm the
    loader catches it. Every pre-check in this module passes here — the caller
    asked for a perfectly good 495 — and the only thing standing between the
    bad bytes and the practice's price list is the reload."""
    before = (prices / "services.yaml").read_bytes()
    monkeypatch.setattr(editor, "_render", lambda value: sabotage)

    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495)
    assert expected in str(refusal.value)
    untouched(prices / "services.yaml", before)
    assert catalogue.service("return_1040").standard_rate == Decimal(450)


def test_a_refusal_from_the_loader_is_a_config_error_too(prices):
    """A screen that already catches "the billing config will not load" catches
    this with the same hand."""
    assert issubclass(PriceEditError, ConfigError)
    with pytest.raises(ConfigError):
        editor.set_rate("nope", 1)


def test_text_and_yaml_must_agree_about_which_entry_is_being_edited(
        prices, monkeypatch):
    """Mutation test for the cross-check. If the parser and the line scan ever
    disagree about what is in the file, the line scan has mislocated something
    — and an edit at the wrong line reprices the wrong service and still looks
    like a tidy one-line diff."""
    before = (prices / "services.yaml").read_bytes()
    monkeypatch.setattr(editor, "_parsed_entries",
                        lambda *a, **k: {"ghost": {"name": "Ghost"}})
    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495)
    assert "one way as YAML and another way as text" in str(refusal.value)
    untouched(prices / "services.yaml", before)


# --- adding a service -------------------------------------------------------


def test_a_new_service_is_appended_and_everything_above_it_is_untouched(prices):
    path = prices / "services.yaml"
    before = path.read_bytes()

    edit = editor.add_service({
        "code": "irs_transcript", "name": "IRS transcript pull",
        "client_label": "Pulling your IRS transcripts", "category": "Advice",
        "unit": "fixed", "standard_rate": Decimal("75.50"),
        "description": "Requesting and reading your account transcripts."})

    after = path.read_bytes()
    old, new = lines_of(before), lines_of(after)
    assert new[:len(old)] == old, "an appended service rewrote what came before it"
    assert len(new) > len(old)

    added = catalogue.service("irs_transcript")
    assert added.standard_rate == Decimal("75.50")
    assert added.unit == "fixed"
    assert added.label_for_client == "Pulling your IRS transcripts"
    assert edit.field == "service" and edit.subject == "irs_transcript"


def test_a_new_service_is_written_in_the_shape_the_file_already_uses(prices):
    editor.add_service({"code": "irs_transcript", "name": "IRS transcript pull",
                        "category": "Advice", "unit": "fixed",
                        "standard_rate": 75})
    text = (prices / "services.yaml").read_text(encoding="utf-8")
    assert "\n  - code: irs_transcript\n" in text
    assert '\n    name: "IRS transcript pull"\n' in text
    assert "\n    standard_rate: 75\n" in text
    assert "client_label" not in text.split("irs_transcript")[1], (
        "a field nobody supplied is left out rather than written as empty")


def test_adding_a_code_that_already_exists_is_refused(prices):
    before = (prices / "services.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.add_service({"code": "return_1040", "name": "Another 1040",
                            "unit": "fixed", "standard_rate": 500})
    assert "already a service called 'return_1040'" in str(refusal.value)
    untouched(prices / "services.yaml", before)


@pytest.mark.parametrize("spec, expected", [
    ({"code": "x", "name": "X", "unit": "fixed"}, "standard_rate"),
    ({"code": "x", "name": "", "unit": "fixed", "standard_rate": 1}, "name"),
    ({"code": "x", "name": "X", "unit": "per_return", "standard_rate": 1}, "not a unit"),
    ({"code": "a b", "name": "X", "unit": "fixed", "standard_rate": 1}, "service code"),
    ({"code": "x", "name": "X", "unit": "fixed", "standard_rate": 1, "rate": 5},
     "no field called 'rate'"),
])
def test_a_service_that_would_load_as_something_else_is_refused(
        prices, spec, expected):
    """A field this editor did not recognise would be silently dropped, and a
    service with no rate loads as FREE — a value invented out of an absence,
    which is principle 1 backwards."""
    before = (prices / "services.yaml").read_bytes()
    with pytest.raises(PriceEditError) as refusal:
        editor.add_service(spec)
    assert expected in str(refusal.value)
    untouched(prices / "services.yaml", before)


def test_a_new_service_on_the_real_file_leaves_the_real_file_alone(real_prices):
    path = real_prices / "services.yaml"
    before = path.read_bytes()
    editor.add_service({"code": "irs_transcript", "name": "IRS transcript pull",
                        "category": "Advice", "unit": "fixed", "standard_rate": 75})
    after = path.read_bytes()
    assert after.startswith(before.rstrip(b"\r\n")), (
        "the shipped catalogue was rewritten rather than appended to")
    assert after.count(b"\n") - after.count(b"\r\n") == 0, (
        "the appended entry used a different line ending from the rest of the "
        "file, which makes the NEXT edit's diff look like a whole-file rewrite")
    assert catalogue.service("irs_transcript").standard_rate == Decimal(75)


# --- what the app sees ------------------------------------------------------


def test_the_running_app_sees_the_new_price_immediately(prices):
    """450 -> 495 is the same number of bytes, so the file's size does not move
    and neither does its length. If the price the app quotes were still 450
    after this, the owner would invoice at the old rate and never find out."""
    assert catalogue.service("return_1040").standard_rate == Decimal(450)
    quoted_before = catalogue.service("return_1040").amount_for(Decimal(1))

    editor.set_rate("return_1040", 495)

    assert catalogue.service("return_1040").standard_rate == Decimal(495)
    assert catalogue.service("return_1040").amount_for(Decimal(1)) != quoted_before
    assert editor.file_stamp("services") != "-"


def test_a_new_service_is_pickable_without_a_restart(prices):
    assert "irs_transcript" not in catalogue.services()
    editor.add_service({"code": "irs_transcript", "name": "IRS transcript pull",
                        "category": "Advice", "unit": "fixed", "standard_rate": 75})
    assert any(svc.code == "irs_transcript"
               for _, group in catalogue.by_category() for svc in group)


# --- the record of the change -----------------------------------------------


def test_the_edit_says_what_changed_from_what_to_what(prices):
    edit = editor.set_rate("return_1040", "495.00")
    assert edit.file.name == "services.yaml"
    assert edit.subject == "return_1040"
    assert edit.field == "standard_rate"
    assert edit.label == "Individual return (1040)", "history reads in words, not codes"
    assert edit.old == "450"
    assert edit.new == "495.00"
    assert edit.is_change


def test_the_diff_is_one_line_and_reviewable(prices):
    edit = editor.set_rate("return_1040", 495)
    removed = [row for row in edit.diff.splitlines()
               if row.startswith("-") and not row.startswith("---")]
    added = [row for row in edit.diff.splitlines()
             if row.startswith("+") and not row.startswith("+++")]
    assert len(removed) == 1 and len(added) == 1
    assert "450" in removed[0] and "495" in added[0]


def test_two_rows_of_history_never_read_the_same(prices):
    """Principle 13. A summary that says "a price changed" trains the owner to
    scroll past the one that mattered."""
    first = editor.set_rate("return_1040", 495).summary()
    second = editor.set_rate("return_1120s", 1400).summary()
    third = editor.set_discount("household", 30).summary()
    assert len({first, second, third}) == 3
    assert "450" in first and "495" in first
    assert "Individual return (1040)" in first
    assert "discount" in third and "25" in third and "30" in third


def test_setting_the_rate_it_already_has_changes_nothing(prices):
    """Principle 8 — re-asking is success. But it is not history and it is not
    a write: rewriting the file would move its mtime, invalidate every cache
    watching it, and put a row in the price log saying nothing happened."""
    path = prices / "services.yaml"
    before = path.read_bytes()
    stamp = editor.file_stamp("services")

    edit = editor.set_rate("return_1040", "450.00")

    assert not edit.is_change
    assert edit.diff == ""
    assert edit.old == edit.new == "450"
    assert edit.stamp == stamp
    untouched(path, before)
    assert "already" in edit.summary()


# --- the packaged build -----------------------------------------------------


def test_a_packaged_build_refuses_to_edit_prices_inside_its_own_bundle(
        prices, monkeypatch):
    """SATC.exe unpacks configs/ to a temp directory that is deleted on exit. A
    price written there shows the new number all afternoon and is gone
    tomorrow, which is the silent-loss failure this module exists to prevent."""
    before = (prices / "services.yaml").read_bytes()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(prices.parent), raising=False)

    with pytest.raises(PriceEditError) as refusal:
        editor.set_rate("return_1040", 495)
    assert "discarded when SATC closes" in str(refusal.value)
    assert "rebuild" in str(refusal.value), "principle 10 — name the next step"
    untouched(prices / "services.yaml", before)
