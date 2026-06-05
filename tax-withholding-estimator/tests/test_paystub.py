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


def test_missing_decimal_period_not_merged_to_wrong_magnitude():
    # The "586946" bug: PDF omits the "." glyph so "5,869" and "46" arrive as
    # adjacent tokens.  They must NOT be merged to "5,86946" here; instead the
    # reader's _try_decimal_join is responsible for reconstructing "5869.46".
    h = 10  # token height
    items = [
        [10, 100, 42, 100 + h, "5,869"],
        [42, 100, 54, 100 + h, "46"],   # immediately adjacent (gap ≈ 0)
    ]
    result = _texts(items)
    assert result == ["5,869", "46"], f"expected kept separate, got {result}"


def test_missing_decimal_no_comma_not_merged():
    # "97536" bug: "975" + "36" with no comma in the left token.
    h = 10
    items = [
        [10, 100, 30, 100 + h, "975"],
        [30, 100, 42, 100 + h, "36"],
    ]
    result = _texts(items)
    assert result == ["975", "36"], f"expected kept separate, got {result}"


def test_period_as_own_glyph_merges_correctly():
    # Decimal period emitted as a separate glyph: "975" + "." + "36" → "975.36"
    h = 10
    items = [
        [10, 100, 30, 100 + h, "975"],
        [31, 100, 33, 100 + h, "."],
        [33, 100, 45, 100 + h, "36"],
    ]
    result = _texts(items)
    assert len(result) == 1
    assert parse_currency(result[0]) == Decimal("975.36")


def test_orphaned_cents_predicate():
    # Complete currency value followed by 1-2 digits → True
    assert _is_orphaned_cents("5,869", "46") is True
    assert _is_orphaned_cents("975", "36") is True
    assert _is_orphaned_cents("100", "5") is True
    # Separators are always pass-through
    assert _is_orphaned_cents("975", ".") is False
    assert _is_orphaned_cents("975", ",") is False
    # Left already ends in separator → not orphaned (we're mid-number)
    assert _is_orphaned_cents("975.", "36") is False
    assert _is_orphaned_cents("975,", "36") is False
    # 3+ digit right fragment → thousands group, not cents
    assert _is_orphaned_cents("6", "653") is False
    assert _is_orphaned_cents("1", "234") is False


# -- negative paystub values become magnitudes ------------------------------


def test_decimal_reconstruction_via_apply_rule():
    # Simulates the "586946" / "97536" bug: PDF omits the decimal separator so
    # the value token and cents token stay separate after _merge_number_fragments.
    # _try_decimal_join should reconstruct the correct decimal at read time.
    words = [
        Word("Federal", 0.05, 0.20, 0.15, 0.23),
        Word("Tax", 0.16, 0.20, 0.22, 0.23),
        Word("5,869", 0.40, 0.20, 0.52, 0.23),   # left token (no decimal emitted)
        Word("46",    0.52, 0.20, 0.56, 0.23),    # adjacent cents token
    ]
    rule = FieldRule("federal_tax_withheld_per_period", "currency",
                     region=[0.40, 0.20, 0.56, 0.23], label_text="Federal Tax")
    assert apply_rule(words, rule) == "5869.46"


def test_decimal_reconstruction_no_comma():
    # "975" + "36" (no thousands comma in left token)
    words = [
        Word("Tax", 0.16, 0.20, 0.22, 0.23),
        Word("975", 0.40, 0.20, 0.49, 0.23),
        Word("36",  0.49, 0.20, 0.53, 0.23),
    ]
    rule = FieldRule("federal_tax_withheld_per_period", "currency",
                     region=[0.40, 0.20, 0.53, 0.23], label_text="Tax")
    assert apply_rule(words, rule) == "975.36"


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
