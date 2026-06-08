#!/usr/bin/env python3
"""Tests for the configuration validator. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sort_tax_docs
import validate_config as vc


def _severities(findings, area=None):
    return [f["severity"] for f in findings if area is None or f["area"] == area]


class PureCheckTests(unittest.TestCase):
    def test_missing_client_name_is_error(self) -> None:
        findings = vc.check_clients([{"email": "a@x.com"}])
        self.assertIn(vc.ERROR, _severities(findings))

    def test_duplicate_email_and_slug_warn(self) -> None:
        findings = vc.check_clients([
            {"client_name": "Jo Sample", "email": "same@x.com"},
            {"client_name": "Jo Sample", "email": "same@x.com"},
        ])
        messages = " ".join(f["message"] for f in findings)
        self.assertIn("is used by 2 clients", messages)
        self.assertIn("share the slug", messages)

    def test_no_clients_is_error(self) -> None:
        self.assertEqual(_severities(vc.check_clients([])), [vc.ERROR])

    def test_fee_schedule_unknown_service_and_bad_price(self) -> None:
        schedule = {"state_return": {"price": "free"}}  # non-numeric price
        clients = [{"client_name": "A", "services": ["schedule_c"]}]  # not in schedule
        findings = vc.check_fee_schedule(schedule, clients)
        sevs = _severities(findings)
        self.assertIn(vc.ERROR, sevs)    # bad price
        self.assertIn(vc.WARNING, sevs)  # unknown service

    def test_inline_service_not_flagged(self) -> None:
        clients = [{"client_name": "A", "services": [{"description": "Custom", "price": 50}]}]
        self.assertEqual(vc.check_fee_schedule({}, clients), [])

    def test_intake_schema_checks(self) -> None:
        findings = vc.check_intake_schema([
            {"name": "ok", "type": "text"},
            {"name": "bad", "type": "wizardry"},
            {"name": "picker", "type": "select"},  # no options
        ])
        self.assertEqual(len(findings), 2)

    def test_checklist_map_unknown_category(self) -> None:
        findings = vc.check_checklist_map({"W-2": ["NotACategory"]}, sort_tax_docs.CATEGORY_FOLDERS.keys())
        self.assertEqual(_severities(findings), [vc.WARNING])
        self.assertEqual(vc.check_checklist_map({"W-2": ["W2"]}, sort_tax_docs.CATEGORY_FOLDERS.keys()), [])


class RunTests(unittest.TestCase):
    def test_run_writes_report_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([{"email": "a@x.com"}]), encoding="utf-8")
            (folder / "fee_schedule.json").write_text("{ not json", encoding="utf-8")
            result = vc.run_validation(folder)
            self.assertGreaterEqual(result["error_count"], 1)  # missing name + bad json
            self.assertTrue(Path(result["report_path"]).exists())

    def test_clean_config_has_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jo Sample", "email": "jo@x.com"}]), encoding="utf-8"
            )
            result = vc.run_validation(folder)
            self.assertEqual(result["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
