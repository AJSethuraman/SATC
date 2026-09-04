#!/usr/bin/env python3
"""Mutation proof: every parity test must be able to fail.

A test that stays green when the code it covers is broken is not a test, it is
decoration -- and a *parity* test that cannot fail is worse than none, because
the whole point of the golden harness is to be the thing that says "a number
moved". So each mutation below deletes or neuters exactly one behaviour and
names the tests that must go red because of it.

    python tools/mutation_check.py            # every mutation
    python tools/mutation_check.py recalc-off # just one
    python tools/mutation_check.py --list

A mutation is applied to the working tree and undone in a ``finally``; the run
starts by demanding a green baseline and ends by re-checking the file is back
byte-for-byte as it was.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
SRC = PKG / "src" / "credit_suite"
GOLDENS = PKG / "tests" / "goldens"


@dataclasses.dataclass(frozen=True)
class Mutation:
    id: str
    path: Path
    old: str
    new: str
    must_fail: tuple[str, ...]
    kills: str
    count: int = 1


T = "tests/test_parity.py::"
M = "tests/test_fred_series_ids.py::"
V = "tests/test_vba_compression.py::"
S = "tests/test_fred_staleness.py::"
L = "tests/test_engine_logic.py::"
C = "tests/test_engine_config.py::"
W = "tests/test_engine_workbook.py::"
F = "tests/test_fred_seam.py::"
I = "tests/test_inliner.py::"
N = "tests/test_conformance.py::"

MUTATIONS: list[Mutation] = [
    Mutation(
        "recalc-off", SRC / "parity.py",
        "computed = recalc(path) if recompute else {}",
        "computed = {}",
        (T + "test_snapshot_stores_the_computed_status_not_the_formula_text",
         T + "test_a_planted_status_change_is_detected_and_named",
         T + "test_a_band_that_turns_from_number_to_text_is_caught_as_a_status_move",
         T + "test_shipped_golden_matches_the_committed_workbook"),
        "statuses are recomputed rather than read as formula text",
    ),
    Mutation(
        "formula-text-blind", SRC / "parity.py",
        '    if isinstance(value, str) and value.startswith("="):\n        return value\n',
        '    if False:\n        return value\n',
        (T + "test_snapshot_stores_the_computed_status_not_the_formula_text",
         T + "test_a_rewritten_formula_is_detected_even_when_the_value_holds",
         T + "test_shipped_golden_matches_the_committed_workbook"),
        "a formula cell is recorded as a formula, not as a literal string",
    ),
    Mutation(
        "value-diff-blind", SRC / "parity.py",
        "            if want[0] != got[0]:",
        "            if False:",
        (T + "test_a_planted_value_change_is_detected_and_named",
         T + "test_a_planted_status_change_is_detected_and_named",
         T + "test_assert_parity_raises_naming_the_cell",
         T + "test_a_band_that_turns_from_number_to_text_is_caught_as_a_status_move"),
        "a moved value or status is reported",
    ),
    Mutation(
        "formula-diff-blind", SRC / "parity.py",
        "            if want_formula != got_formula:",
        "            if False:",
        (T + "test_a_rewritten_formula_is_detected_even_when_the_value_holds",
         T + "test_a_formula_the_engine_cannot_run_is_still_pinned_by_its_source"),
        "a rewritten rule is reported even when its answer holds",
    ),
    Mutation(
        "sheet-diff-blind", SRC / "parity.py",
        'diffs.append(Difference("sheet_removed", sheet, "present", "absent"))',
        "pass",
        (T + "test_a_dropped_tab_is_named",),
        "a tab that vanished is reported",
    ),
    Mutation(
        "defined-name-diff-blind", SRC / "parity.py",
        "        if want != got:\n            diffs.append(Difference(\"defined_name\"",
        "        if False:\n            diffs.append(Difference(\"defined_name\"",
        (T + "test_a_moved_defined_name_is_named",),
        "a threshold band that was re-pointed is reported (L8 territory)",
    ),
    Mutation(
        "ignore-everything", SRC / "parity.py",
        "return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)",
        "return True",
        (T + "test_ignore_forgives_the_named_cell_and_nothing_else",
         T + "test_a_planted_value_change_is_detected_and_named"),
        "--ignore forgives only the cells it names",
    ),
    Mutation(
        "ignore-nothing", SRC / "parity.py",
        "return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)",
        "return False",
        (T + "test_ignore_forgives_the_named_cell_and_nothing_else",),
        "--ignore forgives the cells it names",
    ),
    Mutation(
        "rounding-off", SRC / "parity.py",
        'out = float(f"{value:.12g}")',
        "out = value",
        (T + "test_float_noise_normalises_away_but_a_real_move_does_not",),
        "float noise between openpyxl and the recalc engine is normalised away",
    ),
    Mutation(
        "rounding-too-coarse", SRC / "parity.py",
        'out = float(f"{value:.12g}")',
        'out = float(f"{value:.3g}")',
        (T + "test_float_noise_normalises_away_but_a_real_move_does_not",),
        "rounding is not so coarse that a real move disappears",
    ),
    Mutation(
        "diff-order-alphabetical", SRC / "parity.py",
        "    return (index, row, column, key)",
        "    return (key,)",
        (T + "test_differences_are_reported_in_workbook_reading_order",),
        "differences are listed in the order the workbook reads",
    ),
    Mutation(
        "golden-not-ascii", SRC / "parity.py",
        "ensure_ascii=True",
        "ensure_ascii=False",
        (T + "test_dumps_is_ascii_and_one_cell_per_line_even_for_unicode_content",),
        "the golden is pure ASCII (contract section 11)",
    ),
    Mutation(
        "golden-carries-a-clock", SRC / "parity.py",
        '        \'  "source": %s,\' % _compact(snapshot["source"]),',
        '        \'  "source": %s,\' % _compact(str(__import__("time").time())),',
        (T + "test_snapshot_of_an_unchanged_workbook_is_byte_identical_twice",),
        "a golden carries no clock or host noise",
    ),
    Mutation(
        "capture-order-scrambled", SRC / "parity.py",
        "        for ws in wb.worksheets:\n            for row in ws.iter_rows():",
        "        for ws in reversed(wb.worksheets):\n            for row in reversed(list(ws.iter_rows())):",
        (T + "test_cells_are_ordered_by_sheet_then_row_then_column",),
        "cells are captured in workbook order, not whatever order they came in",
    ),
    # --- the baselines themselves: tamper with the committed data ------------
    Mutation(
        "golden-tampered-value", GOLDENS / "fdic-shipped.json",
        '"Dashboard_AssetQuality!A1": ["Asset Quality Dashboard"]',
        '"Dashboard_AssetQuality!A1": ["Asset Quality Dashbord"]',
        (T + "test_shipped_golden_matches_the_committed_workbook",),
        "the committed baseline still describes the real shipped workbook",
    ),
    Mutation(
        "golden-flags-blanked", GOLDENS / "fred-demo.json",
        '["\\u26a0 ALERT", ', '["", ',
        (T + "test_demo_golden_is_populated_and_its_flags_discriminate",),
        "the demo baseline is not vacuous -- a flag is actually lit in it",
        count=19,
    ),
    Mutation(
        "golden-hides-an-unpinned-cell", GOLDENS / "fdic-demo.json",
        '"Dashboard_AssetQuality!A4": [2, ',
        '"Dashboard_AssetQuality!A4": ["#DIV/0!", ',
        (T + "test_every_unpinned_formula_is_one_the_engine_documents_it_cannot_run",),
        "a formula that stopped resolving is named, not shrugged at",
    ),

    # ======================================================================
    # the engine (issue #165)
    # ======================================================================
    Mutation(
        "threshold-watch-before-alert", SRC / "engine" / "thresholds.py",
        "    if hit(threshold.alert):\n        return ALERT\n"
        "    if hit(threshold.watch):\n        return WATCH\n",
        "    if hit(threshold.watch):\n        return WATCH\n"
        "    if hit(threshold.alert):\n        return ALERT\n",
        (L + "test_status_matches_the_legacy_engine_over_every_combination",
         L + "test_alert_wins_over_watch_when_a_value_passes_both"),
        "a value past both bands reports the worse one",
    ),
    Mutation(
        "threshold-direction-inverted", SRC / "engine" / "thresholds.py",
        'above = threshold.direction != "below"',
        'above = threshold.direction == "below"',
        (L + "test_status_matches_the_legacy_engine_over_every_combination",
         L + "test_direction_below_flags_the_other_way",
         L + "test_only_the_literal_word_below_flips_the_direction"),
        "below-is-bad metrics (capital, coverage) flag the right way round",
    ),
    Mutation(
        "threshold-blank-becomes-a-flag", SRC / "engine" / "thresholds.py",
        "            isinstance(value, float) and math.isnan(value)):\n        return OK",
        "            isinstance(value, float) and math.isnan(value)):\n        return ALERT",
        (L + "test_a_missing_threshold_is_ok_never_a_flag",
         L + "test_status_matches_the_legacy_engine_over_every_combination"),
        "a missing number is never fabricated into a flag",
    ),
    Mutation(
        "gate-admits-everything", SRC / "engine" / "gates.py",
        "    if not spec.entity.admits(row.entity_key):",
        "    if False:",
        (L + "test_the_gate_is_default_deny_not_deny_listed",
         L + "test_one_bad_row_refuses_itself_and_lets_the_rest_land",
         L + "test_entity_refusal_message_is_byte_identical_to_the_legacy_one"),
        "the join-key whitelist is default-deny and actually applied",
    ),
    Mutation(
        "gate-inactive-is-a-refusal", SRC / "engine" / "gates.py",
        "        if not row.active:\n            excluded.append(row)",
        "        if not row.active:\n            refusals.append((row, 'inactive'))",
        # NOT the differential test: the shipped [PEERS] table has no
        # inactive row carrying an entity, so both implementations agree
        # under this mutation. Only the synthetic case can see it.
        (L + "test_an_inactive_row_is_excluded_and_never_refused",),
        "switching an entity off is a choice, not a mistake to go and fix",
    ),
    Mutation(
        "gate-one-typo-kills-the-refresh", SRC / "engine" / "gates.py",
        "            refusals.append((row, entity_refusal_message(row, reasons, spec)))",
        "            return [], [(row, entity_refusal_message(row, reasons, spec))], excluded",
        (L + "test_one_bad_row_refuses_itself_and_lets_the_rest_land",),
        "a bad entity row refuses only itself; the rest still lands",
    ),
    Mutation(
        "gate-class-c-admitted", SRC / "engine" / "gates.py",
        "    if series.source_class not in spec.admitted_source_classes:",
        "    if False:",
        (L + "test_a_non_admitted_metric_class_refuses_the_whole_run",
         L + "test_class_c_is_never_admitted_however_capable_it_claims_to_be",
         L + "test_metric_refusal_message_is_byte_identical_to_the_legacy_one"),
        "a licensed (Class C) feed stays gated until a contract exists",
    ),
    Mutation(
        "capacity-truncates-instead-of-refusing", SRC / "engine" / "gates.py",
        "    if bad:\n        need = max(",
        "    if False:\n        need = max(",
        (L + "test_over_capacity_is_refused_with_a_rebuild_command_never_truncated",),
        "an over-capacity entity list is refused, never silently truncated",
    ),
    Mutation(
        "staleness-no-baseline-invents-a-finding", SRC / "engine" / "staleness.py",
        "    if set_max_period is None:\n        return False",
        "    if set_max_period is None:\n        return True",
        (L + "test_nothing_landed_anywhere_is_not_a_staleness_finding",
         L + "test_staleness_matches_the_legacy_guard_over_every_combination"),
        "with no baseline, staleness is not claimed",
    ),
    Mutation(
        "staleness-unreadable-date-assumed-current", SRC / "engine" / "staleness.py",
        "    except ValueError:\n        return True",
        "    except ValueError:\n        return False",
        (L + "test_an_unreadable_period_is_stale_rather_than_assumed_current",
         L + "test_staleness_matches_the_legacy_guard_over_every_combination"),
        "a date the guard cannot read is a date it does not vouch for",
    ),
    Mutation(
        "staleness-ignores-period-length", SRC / "engine" / "staleness.py",
        "return (newest - last).days > stale_multiplier * period_days",
        "return (newest - last).days > stale_multiplier * 92",
        (L + "test_the_period_length_is_the_monitors_to_set",),
        "a monthly source is not judged on quarterly patience",
    ),
    Mutation(
        "rawlayout-stride-drops-the-gap", SRC / "engine" / "rawlayout.py",
        "stride = HEADER_ROWS + raw_slots + GAP_ROWS",
        "stride = HEADER_ROWS + raw_slots",
        (L + "test_slot_anchors_match_the_legacy_layout_for_every_slot",
         L + "test_an_anchor_depends_only_on_the_slot_not_on_who_occupies_it"),
        "block anchors match the ones every dashboard formula points at",
    ),
    Mutation(
        "rawlayout-oldest-first", SRC / "engine" / "rawlayout.py",
        "                     reverse=True)[:raw_slots]",
        "                     reverse=False)[:raw_slots]",
        (L + "test_only_raw_slots_periods_are_kept_newest_first",
         L + "test_a_field_missing_a_period_blanks_that_cell_rather_than_shifting_rows"),
        "periods land newest-first, which every offset formula assumes",
    ),
    Mutation(
        "rawlayout-intersects-instead-of-unions", SRC / "engine" / "rawlayout.py",
        "    periods = sorted({row.period for rows in field_rows.values() "
        "for row in rows},\n                     reverse=True)[:raw_slots]",
        "    _sets = [{row.period for row in rows} for rows in field_rows.values()]\n"
        "    periods = sorted(set.intersection(*_sets) if _sets else set(),\n"
        "                     reverse=True)[:raw_slots]",
        (L + "test_a_field_missing_a_period_blanks_that_cell_rather_than_shifting_rows",),
        "a field missing one period blanks a cell rather than shifting a column",
    ),
    Mutation(
        "config-coerces-a-malformed-key", SRC / "engine" / "config.py",
        "    return str(value).strip()\n\n\ndef norm_slot",
        "    return \"\".join(c for c in str(value) if c.isdigit())\n\n\ndef norm_slot",
        # NOT the differential test: every seeded cert is already a clean
        # digit string, so tidying one changes nothing it compares.
        (C + "test_a_malformed_key_reaches_the_gate_rather_than_being_coerced",),
        "a malformed key reaches the gate instead of being tidied into a valid one",
    ),
    Mutation(
        "config-tolerates-a-nan-band", SRC / "engine" / "config.py",
        "            if isinstance(raw, float) and raw != raw:",
        "            if False:",
        (C + "test_a_nan_band_an_alert_rule_reads_is_refused_not_coerced",),
        "L8: a band an alert rule reads is refused, not coerced",
    ),
    Mutation(
        "config-comments-become-data", SRC / "engine" / "config.py",
        'if not first or first.startswith("#"):',
        "if not first:",
        (C + "test_a_comment_line_is_never_data",
         C + "test_the_shipped_config_parses_to_something_worth_comparing",
         C + "test_every_entity_row_matches_the_legacy_peer_row"),
        "an in-sheet comment line is never read as data",
    ),

    # --- the workbook writer, the provider seam and the run guards ---------
    Mutation(
        "L7-clearing-is-a-silent-noop", SRC / "engine" / "workbook.py",
        "                ws.cell(row, col).value = None            # L7: assign .value",
        "                ws.cell(row, col, None)",
        (W + "test_clearing_actually_blanks",),
        "L7: cells are blanked by assigning .value -- the historical bug, replanted",
    ),
    Mutation(
        "null-lands-as-zero", SRC / "engine" / "workbook.py",
        "                    None if value is None else float(value)",
        "                    float(value or 0)",
        (W + "test_a_null_value_lands_as_a_blank_not_a_zero",),
        "trap F3 through the write path: a null never becomes 0 in the sheet",
    ),
    Mutation(
        "raw-layout-guard-off", SRC / "engine" / "workbook.py",
        'if existing is not None and str(existing).strip() not in ("", label):',
        "if False:",
        (W + "test_a_relabelled_slot_is_refused_with_the_rebuild_command",),
        "a moved raw layout is refused, not written into cells nothing reads",
    ),
    Mutation(
        "pack-sentinel-guard-off", SRC / "engine" / "workbook.py",
        'if str(found or "").strip() != last:',
        "if False:",
        (W + "test_a_workbook_built_by_another_pack_is_refused",),
        "a workbook from a different metric pack is refused",
    ),
    Mutation(
        "ratio-divides-by-zero", SRC / "engine" / "metrics.py",
        "    if num is None or den is None or den == 0:",
        "    if num is None or den is None:",
        (W + "test_a_zero_denominator_blanks_rather_than_raising",
         W + "test_ratio_matches_the_legacy_one_over_every_combination"),
        "a zero denominator blanks the metric instead of raising",
    ),
    Mutation(
        "total-treats-null-as-zero", SRC / "engine" / "metrics.py",
        "        if value is None:\n            return None\n        out += value",
        "        if value is None:\n            continue\n        out += value",
        (W + "test_a_missing_input_blanks_the_metric_and_never_reads_as_zero",
         W + "test_total_matches_the_legacy_none_propagating_sum"),
        "a null component blanks a composite instead of understating it",
    ),
    Mutation(
        "zero-pull-reported-as-success", SRC / "engine" / "runtime.py",
        '    return not (expected > 0 and status.get("entities_landed", 0) == 0)',
        "    return True",
        (W + "test_zero_pulls_where_pulls_were_expected_is_a_failure",),
        "a total outage is a failure, not a quiet success over a blank workbook",
    ),
    Mutation(
        "secret-invented-when-unset", SRC / "engine" / "provider.py",
        "    return os.environ.get(name) or None",
        '    return os.environ.get(name) or "default-secret"',
        # NOT the keyless test: with no secret_env name, resolve_secret
        # returns before it ever reaches the mutated line.
        (W + "test_the_secret_is_read_by_name_from_the_environment",),
        "a missing secret stays missing rather than becoming a fabricated one",
    ),
    Mutation(
        "licensed-adapter-calls-unauthenticated", SRC / "engine" / "provider.py",
        "        if not secret:\n            raise PermissionError(",
        "        if False:\n            raise PermissionError(",
        (W + "test_a_licensed_adapter_refuses_to_call_without_its_secret",),
        "a Class C adapter never calls without its secret",
    ),
    Mutation(
        "licensed-adapter-fabricates-data", SRC / "engine" / "provider.py",
        'return [NormalizedRow(id=spec.id, period="1900-01-01", value=None,',
        'return [NormalizedRow(id=spec.id, period="1900-01-01", value=0.0,',
        (W + "test_a_licensed_adapter_refuses_to_call_without_its_secret",),
        "the Class C stub returns a valueless row, never fabricated data",
    ),

    # --- FRED's translation onto the contract seam (issue #166) ------------
    Mutation(
        "fred-seam-nan-becomes-zero", SRC / "sources" / "fred" / "runner.py",
        "value=None if pd.isna(value) else float(value),",
        "value=0.0 if pd.isna(value) else float(value),",
        (F + "test_a_missing_observation_survives_as_missing_not_as_zero",
         F + "test_the_round_trip_is_lossless_for_every_seeded_series"),
        "a missing FRED observation stays missing across the seam, never 0",
    ),
    Mutation(
        "fred-seam-loses-the-blank-coming-back",
        SRC / "sources" / "fred" / "runner.py",
        'values = [float("nan") if r.value is None else float(r.value) for r in rows]',
        "values = [0.0 if r.value is None else float(r.value) for r in rows]",
        (F + "test_a_missing_observation_survives_as_missing_not_as_zero",
         F + "test_the_round_trip_is_lossless_for_every_seeded_series"),
        "a blank rebuilt from rows comes back blank, not zero",
    ),
    Mutation(
        "fred-seam-unsorted", SRC / "sources" / "fred" / "runner.py",
        'return pd.Series(values, index=index, dtype="float64").sort_index()',
        'return pd.Series(values, index=index, dtype="float64")',
        (F + "test_rows_come_back_sorted_oldest_first",),
        "rows rebuild in date order, which every offset formula assumes",
    ),
    Mutation(
        "fred-bypasses-the-seam", SRC / "sources" / "fred" / "runner.py",
        "s = rows_to_series(provider.fetch_series(spec))",
        "s = provider.fetch(spec.series_id)",
        (F + "test_the_run_path_actually_goes_through_the_seam",),
        "run() fetches through the contract seam rather than around it",
    ),

    # --- the build-time inliner (issue #167) --------------------------------
    Mutation(
        "bundle-carries-a-clock", SRC / "engine" / "inline.py",
        "compresslevel=9, mtime=0) as gz:",
        "compresslevel=9) as gz:",
        (I + "test_the_encoder_carries_no_clock",
         I + "test_the_bundle_is_byte_identical_run_to_run"),
        "a bundle is byte-identical run to run, so it can be diffed",
    ),
    Mutation(
        "bundle-ships-non-ascii", SRC / "engine" / "inline.py",
        "        if ord(char) >= 128:",
        "        if False:",
        (I + "test_a_non_ascii_payload_is_refused_rather_than_shipped",),
        "a non-ASCII bundle is refused rather than shipped into an email gateway",
    ),
    Mutation(
        "inliner-misses-nested-imports", SRC / "engine" / "inline.py",
        "        for found in _imported_names(tree, name, top_level_only=False,",
        "        for found in _imported_names(tree, name, top_level_only=True,",
        (I + "test_a_module_reachable_only_through_a_function_level_import_is_inlined",),
        "modules imported inside functions are inlined too, or the bundle "
        "dies in the empty folder it was built for",
    ),
    Mutation(
        "inliner-orders-alphabetically", SRC / "engine" / "inline.py",
        "        ready = [n for n in remaining if deps[n] <= placed]",
        "        ready = list(remaining)",
        (I + "test_modules_are_ordered_so_dependencies_execute_first",
         I + "test_the_bundle_builds_and_runs_in_an_empty_folder"),
        "modules execute in dependency order, so `from x import y` finds y",
    ),
    Mutation(
        "code-py-is-not-self-contained",
        SRC / "sources" / "fdic" / "layout.py",
        '                   "python", source_text=code_py)',
        '                   "python")',
        (I + "test_the_code_py_tab_is_now_self_contained",
         "tests/test_fdic_email_sim.py::"
         "test_the_workbook_rebuilds_itself_in_an_empty_folder"),
        "_code_py carries the inlined runner, so the button's output runs alone",
    ),

    # --- the conformance check (issue #168) ---------------------------------
    Mutation(
        "conformance-blind-to-copies", SRC / "conformance.py",
        "        if digest in by_digest:",
        "        if False:",
        (N + "test_a_copied_engine_module_is_caught_and_named",
         N + "test_a_renamed_copy_is_caught_too",
         N + "test_the_outstanding_copies_are_reported_not_hidden"),
        "a copied engine module is caught -- the regression this exists for",
    ),
    Mutation(
        "conformance-name-matches-instead-of-hashing", SRC / "conformance.py",
        "    return hashlib.sha256(\n        path.read_bytes().replace(b\"\\r\\n\", b\"\\n\")).hexdigest()",
        "    return hashlib.sha256(path.name.encode()).hexdigest()",
        (N + "test_a_renamed_copy_is_caught_too",),
        "the check hashes CONTENT, so renaming a copy does not hide it",
    ),
    Mutation(
        "conformance-tolerates-loose-source", SRC / "conformance.py",
        "        if folder in MIGRATED_FOLDERS and not GENERATED.match(path.name):",
        "        if False:",
        (N + "test_loose_source_in_a_migrated_folder_is_caught_even_if_not_a_copy",),
        "a migrated folder carries no hand-written source",
    ),
    Mutation(
        "conformance-hides-the-outstanding-copies", SRC / "conformance.py",
        "            if folder in UNMIGRATED_FOLDERS:\n                pending.append(Finding(",
        "            if True:\n                _unused = (Finding(",
        (N + "test_the_outstanding_copies_are_reported_not_hidden",),
        "outstanding copies are reported, not filtered into silence",
    ),
    Mutation(
        "conformance-accepts-any-tab", SRC / "conformance.py",
        "            if not known:",
        "            if False:",
        (N + "test_an_unknown_tab_is_caught_and_named",),
        "a tab outside the contract's taxonomy is caught",
    ),
    Mutation(
        "conformance-skips-required-tabs", SRC / "conformance.py",
        "            if required not in names:",
        "            if False:",
        (N + "test_a_missing_tab_is_caught_and_named",),
        "a missing required tab is caught",
    ),
    Mutation(
        "conformance-skips-the-gated-lane", SRC / "conformance.py",
        "        if not any(t in WATCHLIST for t in names):",
        "        if False:",
        (N + "test_a_missing_gated_lane_is_caught",),
        "a monitor with no gated lane is caught",
    ),
    Mutation(
        "conformance-ignores-cli-drift", SRC / "conformance.py",
        "            if flag not in options:",
        "            if False:",
        (N + "test_a_cli_missing_a_contract_flag_is_caught_and_named",),
        "a runner that dropped a contract flag is caught",
    ),
    Mutation(
        "conformance-ignores-exit-code-drift", SRC / "conformance.py",
        "        if actual != value:",
        "        if False:",
        (N + "test_a_moved_exit_code_is_caught_and_named",),
        "an exit code that moved is caught",
    ),
    Mutation(
        "conformance-hides-its-denominator", SRC / "conformance.py",
        'lines = ["examined %s" % (counts or "NOTHING")]',
        'lines = ["examined %s" % (counts or "")]',
        (N + "test_the_report_states_what_it_examined",),
        "a check that examined nothing says so in words",
    ),
    # ---- issue #181: the metro series ids ----------------------------------
    # The shipped bug in one line: derive every metro id from the CBSA code.
    # Eleven of eighteen 404 on a live pull and the offline bar stays green, so
    # these mutations are the only thing standing between that and a re-run.
    Mutation(
        "metro-ids-derived-from-cbsa-again", SRC / "sources/fred/series_seed.py",
        'out.append(row(f"ATNHPIUS{area}Q"',
        'out.append(row(f"ATNHPIUS{cbsa}Q"',
        (M + "test_every_metro_series_id_uses_the_verified_area_code",
         M + "test_eleven_metros_are_published_as_divisions"),
        "the exact regression of #181 -- ids re-derived from the CBSA code",
    ),
    Mutation(
        "metro-extension-table-hands-out-cbsa-ids", SRC / "sources/fred/series_seed.py",
        'return [{"cbsa": k, "name": n, "series_id": f"ATNHPIUS{a}Q"}',
        'return [{"cbsa": k, "name": n, "series_id": f"ATNHPIUS{k}Q"}',
        (M + "test_the_extension_table_offers_the_same_ids_it_would_pull",),
        "the copy-into-_config table offers ids that actually resolve",
    ),
    Mutation(
        "metro-keyed-on-the-division", SRC / "sources/fred/series_seed.py",
        '"index", f"cbsa:{cbsa}", False, True,',
        '"index", f"cbsa:{area}", False, True,',
        (M + "test_the_entity_key_stays_the_metro_not_the_division",
         M + "test_every_metro_series_id_uses_the_verified_area_code"),
        "the watchlist stays keyed on the metro, not the division",
    ),
    Mutation(
        "metro-division-note-dropped", SRC / "sources/fred/series_seed.py",
        'f"DIVISION level, so the series is division {area}, not CBSA "',
        'f"level, so the series is {area}, not CBSA "',
        (M + "test_a_division_series_says_so_in_its_notes",),
        "a division-sourced metro says so where the reader can see it",
    ),
    Mutation(
        "metro-set-changed-without-a-live-check", SRC / "sources/fred/series_seed.py",
        # Tampa was this anchor until 4 Sep 2026, when it was retired for having
        # stopped publishing -- and the harness caught its own anchor going
        # stale, which is the behaviour that makes "found 0" a finding rather
        # than a nuisance.
        '    "40140": ("40140", "Riverside-San Bernardino-Ontario, CA"),\n',
        '    "40140": ("40140", "Riverside-San Bernardino-Ontario, CA"),\n'
        '    "41740": ("41740", "San Diego-Chula Vista-Carlsbad, CA"),\n',
        (M + "test_the_seed_covers_exactly_the_verified_metros",),
        "a metro added without confirming its id against FRED is refused",
    ),
    # ---- issue #180: the VBA module stream --------------------------------
    # The shipped bug made every ExtractFiles button dead in every monitor and
    # nothing offline noticed, because olevba decodes the broken output fine.
    # The first mutation IS the shipped bug, restored.
    Mutation(
        "vba-compressor-emits-literals-only", SRC / "engine/vba.py",
        "    if best_length < 3:",
        "    if True:",
        (V + "test_no_non_final_chunk_is_short",
         V + "test_the_compressor_actually_uses_copy_tokens"),
        "the exact regression of #180 -- a literal-only stream Excel refuses",
    ),
    Mutation(
        "vba-match-reaches-into-the-previous-chunk", SRC / "engine/vba.py",
        "    for candidate in range(at - 1, chunk_start - 1, -1):",
        "    for candidate in range(at - 1, -1, -1):",
        (V + "test_every_shipped_macro_round_trips_through_the_reference_decoder",
         V + "test_round_trips_at_and_around_every_chunk_boundary"),
        "a copy token never points outside its own chunk",
    ),
    Mutation(
        "vba-copy-token-bit-split-fixed", SRC / "engine/vba.py",
        "    bit_count = max(int(ceil(log2(difference))), 4) if difference > 0 else 4",
        "    bit_count = 4",
        (V + "test_every_shipped_macro_round_trips_through_the_reference_decoder",),
        "the position-dependent offset/length bit split is computed, not assumed",
    ),
    Mutation(
        "vba-raw-chunk-at-an-illegal-size", SRC / "engine/vba.py",
        "    if consumed == MAX_CHUNK and len(body) >= MAX_CHUNK:",
        "    if len(body) >= MAX_CHUNK:",
        (V + "test_round_trips_incompressible_data",),
        "a RawChunk is emitted only at its one legal size, 4096",
    ),
    # ---- the publication-lag staleness rule --------------------------------
    Mutation(
        "staleness-ignores-the-publication-lag", SRC / "sources/fred/runner.py",
        "    return (asof - last_obs).days > publication_lag_days + days_per * multiplier",
        "    return (asof - last_obs).days > days_per * multiplier",
        (S + "test_a_habitually_late_publisher_is_not_stale",),
        "a habitually late publisher stops being flagged on every run",
    ),
    Mutation(
        "staleness-multiplies-the-lag", SRC / "sources/fred/runner.py",
        "    return (asof - last_obs).days > publication_lag_days + days_per * multiplier",
        "    return (asof - last_obs).days > publication_lag_days * days_per * multiplier",
        (S + "test_the_lag_is_added_not_multiplied",
         S + "test_no_lag_leaves_the_old_behaviour_exactly"),
        "the lag is a fixed offset, not something that scales with cadence",
    ),
    Mutation(
        "staleness-lag-default-invented", SRC / "sources/fred/runner.py",
        '        raw = self.settings.get("lag_days.%s" % (category or "").strip().lower(), 0)',
        '        raw = self.settings.get("lag_days.%s" % (category or "").strip().lower(), 90)',
        (S + "test_an_uncalibrated_category_reads_zero",),
        "an uncalibrated category is unchanged, not quietly more forgiving",
    ),
    Mutation(
        "staleness-junk-setting-crashes", SRC / "sources/fred/runner.py",
        "        except ValueError:\n            return 0.0",
        "        except ValueError:\n            raise",
        (S + "test_a_junk_setting_reads_zero_rather_than_raising",),
        "a typo in a config cell does not take the run down",
    ),
    Mutation(
        "shipped-lag-dropped", SRC / "sources/fred/layout.py",
        '        ["lag_days.g19", "60", "Fed G.19 consumer credit lands ~5 weeks after "\n'
        '         "month end (observed 95 days). Limit becomes 122."],\n',
        "",
        (S + "test_every_category_that_was_permanently_stale_now_ships_a_lag",),
        "a category losing its shipped lag is caught, not silently re-flagged",
    ),
]


#: Extra pytest arguments (``--basetemp=...`` on a machine whose default temp
#: root is not writable). Set by ``main`` from the command line.
_EXTRA_ARGS: list[str] = []


def _purge_bytecode() -> int:
    """Delete every ``__pycache__`` under the package. Returns how many.

    Python validates a cached ``.pyc`` against the source's (mtime-in-SECONDS,
    size). A mutation that swaps equal-length text -- ``{cbsa}`` for ``{area}``,
    ``{a}`` for ``{k}`` -- leaves the size identical, so if it lands inside the
    same second as the last compile, the stale ``.pyc`` is reused and the
    mutation NEVER REACHES THE INTERPRETER. The suite then passes and the
    harness reports a survivor that is really a no-op.

    That is the worst failure this tool can have. It is silent, it is timing
    dependent, and it fails in *both* directions: a genuinely dead test can be
    reported as killed. Two runs of the same mutation set minutes apart reported
    two different survivors, which is how it was found.
    """
    removed = 0
    for cache in PKG.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
        removed += 1
    return removed


def _pytest(node_ids: tuple[str, ...]) -> subprocess.CompletedProcess:
    # Belt and braces: purge what exists, and forbid writing more for the
    # duration, so no run can leave a trap for the next one.
    _purge_bytecode()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "--no-header",
         "-p", "no:cacheprovider", *_EXTRA_ARGS, *node_ids],
        cwd=PKG, capture_output=True, text=True, env=env,
    )


def _apply(mutation: Mutation) -> bytes:
    """Swap the target text in and hand back the original bytes.

    Matching happens on newline-NORMALISED text. The anchors here are written
    with ``\\n``, and on a checkout where ``core.autocrlf`` rewrote the sources
    -- Git's default on Windows -- every multi-line anchor would otherwise miss
    and the harness could not run at all. It failed loudly rather than
    silently, which is the right direction, but "cannot run on a fresh Windows
    clone" is still broken. `.gitattributes` now pins these files to LF as well;
    this is the belt to that pair of braces, because the harness is the one
    thing that must not mis-report.

    The file is written back in whatever convention it already used, so a
    mutation never leaves a whitespace-only diff behind.
    """
    original = mutation.path.read_bytes()
    crlf = b"\r\n" in original
    text = original.replace(b"\r\n", b"\n") if crlf else original

    old = mutation.old.encode("utf-8")
    found = text.count(old)
    if found != mutation.count:
        raise SystemExit(
            "%s: expected %d occurrence(s) of the mutation target in %s, found %d "
            "-- the code moved, so the mutation no longer proves anything"
            % (mutation.id, mutation.count, mutation.path.name, found)
        )
    mutated = text.replace(old, mutation.new.encode("utf-8"))
    mutation.path.write_bytes(mutated.replace(b"\n", b"\r\n") if crlf else mutated)
    return original


def check(mutation: Mutation) -> tuple[bool, str]:
    original = _apply(mutation)
    try:
        result = _pytest(mutation.must_fail)
    finally:
        mutation.path.write_bytes(original)
        assert mutation.path.read_bytes() == original, \
            "failed to restore %s" % mutation.path

    if result.returncode == 0:
        tail = result.stdout.strip().splitlines()[-1:] or [""]
        return False, "SURVIVED -- tests stayed green: %s" % tail[0]
    summary = [ln for ln in result.stdout.splitlines() if "failed" in ln or "error" in ln]
    return True, summary[-1].strip() if summary else "killed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="mutation ids (default: all)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true",
                    help="do not run the full suite first (faster, less safe)")
    ap.add_argument("--basetemp", help="passed through to pytest")
    args = ap.parse_args(argv)

    if args.basetemp:
        _EXTRA_ARGS.append("--basetemp=%s" % args.basetemp)

    by_id = {m.id: m for m in MUTATIONS}
    if args.list:
        for m in MUTATIONS:
            print("%-32s %s" % (m.id, m.kills))
        return 0

    unknown = [i for i in args.ids if i not in by_id]
    if unknown:
        raise SystemExit("unknown mutation id(s): %s" % ", ".join(unknown))
    selected = [by_id[i] for i in args.ids] if args.ids else MUTATIONS

    if not args.skip_baseline:
        print("baseline: running the full suite unmutated ...")
        result = _pytest(())
        if result.returncode != 0:
            print(result.stdout[-4000:])
            raise SystemExit("baseline is not green; fix that before mutating")
        print("  " + (result.stdout.strip().splitlines() or [""])[-1])

    survived = []
    for mutation in selected:
        killed, detail = check(mutation)
        print("%-4s %-32s %s" % ("kill" if killed else "LIVE", mutation.id, detail))
        print("       proves: %s" % mutation.kills)
        if not killed:
            survived.append(mutation.id)

    print("\n%d/%d mutations killed" % (len(selected) - len(survived), len(selected)))
    if survived:
        print("SURVIVING: %s" % ", ".join(survived))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
