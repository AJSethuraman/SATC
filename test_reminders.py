#!/usr/bin/env python3
"""Tests for the reminder-email tool. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from email import message_from_bytes
from email.policy import default as default_policy
from pathlib import Path

import checklist
import reminders
import status_tracker as st


class OutstandingTests(unittest.TestCase):
    def test_lists_trackers_and_missing_documents(self) -> None:
        client = {"client_name": "X", "expected_documents": ["W-2"]}
        items = reminders.outstanding_for_client(
            client, "X", [], checklist.DEFAULT_DOC_MAP, set()  # nothing received
        )
        self.assertIn("a signed engagement letter", items)
        self.assertIn("a signed Form 8879 (e-file authorization)", items)
        self.assertTrue(any("W-2" in i for i in items))

    def test_nothing_outstanding_when_declared_and_received(self) -> None:
        client = {
            "client_name": "X",
            "expected_documents": ["W-2"],
            "engagement_letter_signed": True,
            "form_8879_signed": True,
        }
        items = reminders.outstanding_for_client(client, "X", [], checklist.DEFAULT_DOC_MAP, {"W2"})
        self.assertEqual(items, [])


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = reminders.run_reminders(Path(d))
            self.assertEqual(result["reminder_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_drafts_reminder_with_outstanding_items(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([
                    {"client_name": "Needs Stuff", "email": "n@x.com", "tax_year": "2024",
                     "expected_documents": ["W-2"]},
                    {"client_name": "All Done", "email": "a@x.com",
                     "engagement_letter_signed": True, "form_8879_signed": True},
                ]),
                encoding="utf-8",
            )
            result = reminders.run_reminders(folder)
            self.assertEqual(result["reminder_count"], 1)
            self.assertEqual(result["skipped_complete"], 1)

            draft = Path(result["reminders"][0])
            message = message_from_bytes(draft.read_bytes(), policy=default_policy)
            self.assertEqual(message["To"], "n@x.com")
            body = message.get_content()
            self.assertIn("engagement letter", body)
            self.assertIn("W-2", body)

    def test_outstanding_but_no_email_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "No Email", "expected_documents": ["W-2"]}]),
                encoding="utf-8",
            )
            result = reminders.run_reminders(folder)
            self.assertEqual(result["reminder_count"], 0)
            self.assertEqual(result["skipped_no_email"], 1)


if __name__ == "__main__":
    unittest.main()
