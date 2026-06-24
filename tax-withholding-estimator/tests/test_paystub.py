"""Tests for deterministic paystub parsing logic (no PyMuPDF needed)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from twe.paystub import (
    FieldRule,
    Layout,
    Profile,
    Word,
    _is_orphaned_cents,
    _is_orphaned_cents_split,
    _merge_number_fragments,
    apply_profile,
    apply_rule,
    best_profile,
    build_rules,
    parse_currency,
    parse_date,
    profile_score,
)


# -- number-fragment merging (ADP-style split numbers) ----------------------


def _texts(items):
    return [it[4] for it in _merge_number_fragments(items)]


def test_merge_comma_split_number_lost_comma():
    # "6,653.85" arrives as "6" + "653.85" (comma dropped by reader)
    items = [[10, 100, 16, 110, "6"], [17, 100, 45, 110, "653.85"]]
    assert _texts(items) == ["6653.85"]
    assert parse_currency(_texts(items)[0]) == Decimal("6653.85")


def test_merge_comma_as_its_own_token():
    items = [[10, 100, 16, 110, "6"], [16.5, 100, 18, 110, ","], [19, 100, 47, 110, "653.85"]]
    merged = _texts(items)
    assert parse_currency(merged[0]) == Decimal("6653.85")


def test_merge_multiple_thousands_separators():
    items = [[10, 100, 16, 110, "1"], [17, 100, 40, 110, "234"], [41, 100, 70, 110, "567.89"]]
    assert parse_currency(_texts(items)[0]) == Decimal("1234567.89")


def test_distinct_columns_not_merged():
    # Two complete numbers in separate columns must stay separate.
    items = [[10, 100, 45, 110, "6,653.85"], [120, 100, 150, 110, "1,234.00"]]
    assert _texts(items) == ["6,653.85", "1,234.00"]


def test_label_not_merged_into_number():
    items = [[10, 100, 40, 110, "Federal"], [45, 100, 70, 110, "410.00"]]
    assert _texts(items) == ["Federal", "410.00"]


# -- dropped-decimal regression: orphaned cents must NOT be merged ----------
#
# These guard the bug that regressed repeatedly: a renderer drops the "."
# glyph, so "$5,869.46" arrives as "5,869" + "46" and "$975.36" as "975" + "36".
# Merging the fragments naively yields "586946"/"97536" — off by 100x. The
# merge step must leave them as two tokens; the readers reconstruct the "."
# at read time (see the apply_rule tests below).


def test_orphaned_cents_with_comma_not_merged():
    # "$5,869.46" split as "5,869" + "46" — must stay two tokens (not 586946).
    items = [[10, 100, 40, 110, "5,869"], [42, 100, 56, 110, "46"]]
    assert _texts(items) == ["5,869", "46"]


def test_orphaned_cents_no_comma_not_merged():
    # "$975.36" split as "975" + "36" — must stay two tokens (not 97536).
    items = [[10, 100, 40, 110, "975"], [42, 100, 56, 110, "36"]]
    assert _texts(items) == ["975", "36"]


def test_orphaned_single_digit_cents_not_merged():
    # A single-digit cents fragment is still orphaned cents, not a thousands group.
    items = [[10, 100, 40, 110, "1,200"], [42, 100, 50, 110, "5"]]
    assert _texts(items) == ["1,200", "5"]


def test_thousands_group_still_merges_even_when_one_digit_leads():
    # "6" + "653.85": the right fragment is 3+ digits -> a thousands group, merge it.
    items = [[10, 100, 16, 110, "6"], [17, 100, 45, 110, "653.85"]]
    assert _texts(items) == ["6653.85"]
    assert parse_currency(_texts(items)[0]) == Decimal("6653.85")


def test_period_as_own_glyph_still_merges():
    # The "." emitted as its own token: "5869" + "." + "46" -> 5869.46.
    items = [
        [10, 100, 40, 110, "5869"],
        [40.5, 100, 41, 110, "."],
        [42, 100, 56, 110, "46"],
    ]
    merged = _texts(items)
    assert parse_currency(merged[0]) == Decimal("5869.46")


def test_is_orphaned_cents_predicate():
    assert _is_orphaned_cents("46")
    assert _is_orphaned_cents("6")
    assert not _is_orphaned_cents("653")    # 3 digits -> thousands group
    assert not _is_orphaned_cents("653.85")  # not a bare digit run
    assert not _is_orphaned_cents(",")


def test_is_orphaned_cents_split_predicate():
    # Complete dollars value + bare 1-2 digit cents -> a dropped-"." split.
    assert _is_orphaned_cents_split("5,869", "46")
    assert _is_orphaned_cents_split("975", "36")
    # 3+ digit right fragment is a thousands group, safe to merge.
    assert not _is_orphaned_cents_split("6", "653")
    # A left token still mid-number (ends in a separator) is not "complete".
    assert not _is_orphaned_cents_split("5,", "869")
    assert not _is_orphaned_cents_split("5,869.", "46")
    # A non-currency left token is not a dollars value.
    assert not _is_orphaned_cents_split("Federal", "46")


# -- negative paystub values become magnitudes ------------------------------


def test_negative_withholding_read_as_positive():
    # Paystubs show deductions/withholding as negatives, e.g. -951.36.
    words = [
        Word("Federal", 0.05, 0.20, 0.15, 0.23),
        Word("Tax", 0.16, 0.20, 0.22, 0.23),
        Word("-951.36", 0.40, 0.20, 0.55, 0.23),
    ]
    rule = FieldRule("federal_tax_withheld_per_period", "currency",
                     region=[0.40, 0.20, 0.55, 0.23], label_text="Federal Tax")
    assert apply_rule(words, rule) == "951.36"


def test_parentheses_negative_read_as_positive():
    words = [Word("(1,234.00)", 0.40, 0.20, 0.55, 0.23)]
    rule = FieldRule("federal_tax_withheld_per_period", "currency",
                     region=[0.40, 0.20, 0.55, 0.23], label_text="")
    assert apply_rule(words, rule) == "1234.00"


# -- currency parsing -------------------------------------------------------


@pytest.mark.parametrize("token,expected", [
    ("3,200.00", Decimal("3200.00")),
    ("$1,234.56", Decimal("1234.56")),
    ("410", Decimal("410")),
    ("(50.00)", Decimal("-50.00")),
    ("75.00-", Decimal("-75.00")),
    ("$ 2,000", Decimal("2000")),
    ("0.00", Decimal("0.00")),
])
def test_parse_currency_valid(token, expected):
    assert parse_currency(token) == expected


@pytest.mark.parametrize("token", ["", "Federal", "N/A", "--", "abc", "."])
def test_parse_currency_invalid(token):
    assert parse_currency(token) is None


# -- date parsing -----------------------------------------------------------


@pytest.mark.parametrize("text,iso", [
    ("01/15/2025", "2025-01-15"),
    ("1/5/25", "2025-01-05"),
    ("2025-03-31", "2025-03-31"),
    ("Jan 15, 2025", "2025-01-15"),
    ("Pay date: 06/30/2025", "2025-06-30"),
])
def test_parse_date(text, iso):
    assert parse_date(text) == iso


def test_parse_date_invalid():
    assert parse_date("not a date") is None


# -- a small synthetic paystub layout ---------------------------------------


def _sample_words() -> list[Word]:
    # Two rows: a "Federal Income Tax ... 410.00 ... 4,920.00 (YTD)" style stub.
    return [
        Word("Gross", 0.05, 0.10, 0.15, 0.13),
        Word("Pay", 0.16, 0.10, 0.22, 0.13),
        Word("3,200.00", 0.40, 0.10, 0.52, 0.13),
        Word("38,400.00", 0.70, 0.10, 0.85, 0.13),  # YTD gross, same row
        Word("Federal", 0.05, 0.20, 0.15, 0.23),
        Word("Income", 0.16, 0.20, 0.26, 0.23),
        Word("Tax", 0.27, 0.20, 0.33, 0.23),
        Word("410.00", 0.40, 0.20, 0.50, 0.23),
        Word("4,920.00", 0.70, 0.20, 0.84, 0.23),  # YTD fed wh, same row
        Word("Pay", 0.05, 0.30, 0.11, 0.33),
        Word("Date", 0.12, 0.30, 0.20, 0.33),
        Word("06/30/2025", 0.40, 0.30, 0.55, 0.33),
    ]


def _layout(words) -> Layout:
    return Layout(image_png_b64="", img_width=1000, img_height=1000, words=words)


def test_build_rules_captures_label_and_region():
    words = _sample_words()
    # Field -> indices of the value words clicked by the user.
    assignments = {
        "federal_tax_withheld_per_period": [7],   # "410.00"
        "last_pay_date": [11],                     # "06/30/2025"
    }
    rules = build_rules(words, assignments)
    by_field = {r.field: r for r in rules}

    assert by_field["federal_tax_withheld_per_period"].label_text.lower() == "federal income tax"
    assert by_field["last_pay_date"].label_text.lower() == "pay date"
    assert by_field["last_pay_date"].kind == "date"


def test_apply_rule_label_anchor_reads_value():
    words = _sample_words()
    rule = FieldRule(
        field="federal_tax_withheld_per_period",
        kind="currency",
        region=[0.40, 0.20, 0.50, 0.23],
        label_text="Federal Income Tax",
    )
    # Label anchor picks the first numeric to the right on the same row.
    assert apply_rule(words, rule) == "410.00"


# -- dropped-decimal regression: end-to-end reconstruction through apply_rule


def _dropped_decimal_words() -> list[Word]:
    # "Net Pay 5,869 46" and "Federal Tax 975 36": the "." glyph was dropped, so
    # the cents arrive as a separate adjacent token in each row.
    return [
        Word("Net", 0.05, 0.20, 0.12, 0.23),
        Word("Pay", 0.13, 0.20, 0.20, 0.23),
        Word("5,869", 0.40, 0.20, 0.46, 0.23),
        Word("46", 0.47, 0.20, 0.50, 0.23),
        Word("Federal", 0.05, 0.30, 0.15, 0.33),
        Word("Tax", 0.16, 0.30, 0.22, 0.33),
        Word("975", 0.40, 0.30, 0.45, 0.33),
        Word("36", 0.46, 0.30, 0.49, 0.33),
    ]


def test_dropped_decimal_reconstructed_via_label_anchor():
    words = _dropped_decimal_words()
    net = FieldRule("ytd_taxable_wages", "currency",
                    region=[0.40, 0.20, 0.46, 0.23], label_text="Net Pay")
    fed = FieldRule("federal_tax_withheld_per_period", "currency",
                    region=[0.40, 0.30, 0.45, 0.33], label_text="Federal Tax")
    assert apply_rule(words, net) == "5869.46"
    assert apply_rule(words, fed) == "975.36"


def test_dropped_decimal_reconstructed_via_region_fallback():
    words = _dropped_decimal_words()
    # No label -> region path must also reconstruct the dropped decimal.
    net = FieldRule("ytd_taxable_wages", "currency",
                    region=[0.40, 0.20, 0.50, 0.23], label_text="")
    fed = FieldRule("federal_tax_withheld_per_period", "currency",
                    region=[0.40, 0.30, 0.49, 0.33], label_text="")
    assert apply_rule(words, net) == "5869.46"
    assert apply_rule(words, fed) == "975.36"


def test_dropped_decimal_end_to_end_through_layout():
    words = _dropped_decimal_words()
    profile = Profile(
        name="Dropped-decimal stub",
        rules=[
            FieldRule("ytd_taxable_wages", "currency",
                      region=[0.40, 0.20, 0.46, 0.23], label_text="Net Pay"),
            FieldRule("federal_tax_withheld_per_period", "currency",
                      region=[0.40, 0.30, 0.45, 0.33], label_text="Federal Tax"),
        ],
    )
    result = apply_profile(_layout(words), profile)
    assert result["ytd_taxable_wages"] == "5869.46"
    assert result["federal_tax_withheld_per_period"] == "975.36"


def test_complete_value_not_corrupted_by_distant_cents_column():
    # A complete "410.00" must not absorb a far-away "46" cents token (YTD col).
    words = [
        Word("Federal", 0.05, 0.20, 0.15, 0.23),
        Word("Tax", 0.16, 0.20, 0.22, 0.23),
        Word("410.00", 0.40, 0.20, 0.50, 0.23),
        Word("46", 0.80, 0.20, 0.83, 0.23),
    ]
    rule = FieldRule("federal_tax_withheld_per_period", "currency",
                     region=[0.40, 0.20, 0.50, 0.23], label_text="Federal Tax")
    assert apply_rule(words, rule) == "410.00"


def test_apply_rule_region_fallback():
    words = _sample_words()
    # No label -> must use region. Target the YTD gross box.
    rule = FieldRule(
        field="ytd_taxable_wages",
        kind="currency",
        region=[0.69, 0.09, 0.86, 0.14],
        label_text="",
    )
    assert apply_rule(words, rule) == "38400.00"


def test_apply_profile_end_to_end():
    words = _sample_words()
    profile = Profile(
        name="Acme Biweekly",
        pay_frequency="biweekly",
        rules=build_rules(words, {
            "gross_pay_per_period": [2],
            "federal_tax_withheld_per_period": [7],
            "last_pay_date": [11],
        }),
    )
    result = apply_profile(_layout(words), profile)
    assert result["gross_pay_per_period"] == "3200.00"
    assert result["federal_tax_withheld_per_period"] == "410.00"
    assert result["last_pay_date"] == "2025-06-30"
    assert result["pay_frequency"] == "biweekly"


def test_two_column_current_vs_ytd_disambiguated_by_region():
    # "Gross Pay" labels BOTH the current (3,200) and YTD (38,400) columns.
    words = _sample_words()
    current = FieldRule("gross_pay_per_period", "currency",
                        region=[0.40, 0.10, 0.52, 0.13], label_text="Gross Pay")
    ytd = FieldRule("ytd_taxable_wages", "currency",
                    region=[0.70, 0.10, 0.85, 0.13], label_text="Gross Pay")
    # Same label, different taught column -> different values.
    assert apply_rule(words, current) == "3200.00"
    assert apply_rule(words, ytd) == "38400.00"


def test_apply_profile_is_deterministic():
    words = _sample_words()
    profile = Profile(
        name="x",
        rules=build_rules(words, {"gross_pay_per_period": [2]}),
    )
    layout = _layout(words)
    first = apply_profile(layout, profile)
    second = apply_profile(layout, profile)
    assert first == second  # same input -> identical output


def test_profile_matching_by_labels():
    words = _sample_words()
    profile = Profile(
        name="Acme",
        rules=build_rules(words, {"federal_tax_withheld_per_period": [7]}),
        match_keywords=["Pay Date"],  # both anchors appear in the sample text
    )
    matching_layout = _layout(words)
    other_layout = _layout([Word("Totally", 0.1, 0.1, 0.2, 0.12), Word("Different", 0.3, 0.1, 0.4, 0.12)])

    assert profile_score(matching_layout, profile) == 1.0
    assert best_profile(matching_layout, [profile]) is profile
    assert best_profile(other_layout, [profile]) is None
