#!/usr/bin/env python3
"""Tests for firm settings and the practice dashboard. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checklist
import dashboard
import generate_documents as gd
import sort_tax_docs
import status_tracker


class FirmSettingsTests(unittest.TestCase):
    def test_firm_defaults_merge_under_client(self) -> None:
        firm = {"firm_name": "Acme Tax", "preparer_name": "Pat"}
        context = gd.augment_context({"client_name": "Jo", "preparer_name": "Override"}, firm)
        self.assertEqual(context["firm_name"], "Acme Tax")      # from firm
        self.assertEqual(context["preparer_name"], "Override")  # client wins

    def test_load_firm_settings_missing_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(gd.load_firm_settings(Path(d)), {})

    def test_firm_used_in_generation(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jo Sample", "tax_year": "2024"}]), encoding="utf-8"
            )
            (folder / "firm.json").write_text(
                json.dumps({"firm_name": "Acme Tax & Co"}), encoding="utf-8"
            )
            gd.run_generation(folder, templates=["engagement_letter"])
            out = folder / "Organized_Tax_Documents" / "Generated_Documents" / "Jo_Sample_engagement_letter.html"
            self.assertIn("Acme Tax &amp; Co", out.read_text(encoding="utf-8"))


class DashboardTests(unittest.TestCase):
    def _row(self, client, slug, folder, output):
        doc_map, _ = checklist.load_doc_map(folder)
        received = checklist.received_categories(output)
        search = status_tracker.gather_search_files(folder, output)
        return dashboard.client_row(client, slug, folder, output, doc_map, received, search)

    def test_row_states(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            output = sort_tax_docs.setup_output_folders(folder)
            client = {"client_name": "Jo", "email": "j@x.com", "expected_documents": ["W-2"],
                      "line_items": [{"description": "x", "amount": "10.00"}], "total": "10.00"}
            row = self._row(client, "Jo", folder, output)
            self.assertEqual(row["email"][0], dashboard.OK)
            self.assertEqual(row["documents"][0], dashboard.ATTENTION)   # W-2 not received
            self.assertEqual(row["invoice"][0], dashboard.OK)            # has line_items
            self.assertEqual(row["engagement"][0], dashboard.ATTENTION)  # not on file

    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = dashboard.run_dashboard(Path(d))
            self.assertEqual(result["client_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_end_to_end_builds_html_with_summary(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jo Sample", "email": "j@x.com",
                             "expected_documents": ["W-2"]}]),
                encoding="utf-8",
            )
            result = dashboard.run_dashboard(folder)
            self.assertEqual(result["client_count"], 1)
            html = Path(result["dashboard_path"]).read_text(encoding="utf-8")
            self.assertIn("Practice Dashboard", html)
            self.assertIn("Jo Sample", html)
            self.assertIn("Missing docs", html)  # summary chip


if __name__ == "__main__":
    unittest.main()
