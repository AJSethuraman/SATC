#!/usr/bin/env python3
"""Tests for the client summary email tool. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from email import message_from_bytes
from email.policy import default as default_policy
from pathlib import Path

import summary_email


class ContextTests(unittest.TestCase):
    def test_returns_formatted_into_lines(self) -> None:
        client = {"returns": [
            {"return_type": "Federal", "refund_or_balance": "$452 refund", "transaction_method": "DD **6095"},
            {"return_type": "RITA", "refund_or_balance": "nothing owed", "transaction_method": ""},
        ], "efiled_returns": [{"name": "Federal"}]}
        ctx = summary_email.summary_context(client)
        self.assertEqual(ctx["returns_display"][0]["line"], "Federal: $452 refund (DD **6095)")
        self.assertEqual(ctx["returns_display"][1]["line"], "RITA: nothing owed")  # no empty parens
        self.assertTrue(ctx["all_efiled"])

    def test_has_summary_content(self) -> None:
        self.assertTrue(summary_email.has_summary_content({"total": "100.00"}))
        self.assertTrue(summary_email.has_summary_content({"returns": [{"return_type": "Federal"}]}))
        self.assertFalse(summary_email.has_summary_content({"client_name": "A"}))


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = summary_email.run_summary_emails(Path(d))
            self.assertEqual(result["email_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_drafts_readable_summary_email(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([
                {"client_name": "Sam Sample", "email": "sam@x.com", "tax_year": "2025", "total": "130.00",
                 "pay_link": "https://pay.example.com/sam",
                 "returns": [{"return_type": "Federal", "refund_or_balance": "$452 refund", "transaction_method": ""}],
                 "efiled_returns": [{"name": "Federal"}]},
                {"client_name": "No Summary", "email": "n@x.com"},  # nothing to report -> skipped
            ]), encoding="utf-8")
            result = summary_email.run_summary_emails(folder)
            self.assertEqual(result["email_count"], 1)

            msg = message_from_bytes(Path(result["emails"][0]).read_bytes(), policy=default_policy)
            self.assertEqual(msg["To"], "sam@x.com")
            self.assertIn("2025", msg["Subject"])
            body = msg.get_content()
            self.assertIn("Federal: $452 refund", body)
            self.assertIn("e-filed", body)
            self.assertIn("$130.00", body)
            self.assertIn("https://pay.example.com/sam", body)

    def test_skips_when_no_email(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "A", "total": "100.00", "returns": [{"return_type": "Federal"}]}]),
                encoding="utf-8",
            )
            result = summary_email.run_summary_emails(folder)
            self.assertEqual(result["email_count"], 0)
            self.assertEqual(result["skipped_no_email"], 1)


if __name__ == "__main__":
    unittest.main()
