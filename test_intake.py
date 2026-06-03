#!/usr/bin/env python3
"""Tests for the dynamic client intake tool. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import intake


class FormBuildingTests(unittest.TestCase):
    def test_form_includes_every_field_and_download_script(self) -> None:
        html = intake.build_form_html(intake.DEFAULT_SCHEMA)
        for field in intake.DEFAULT_SCHEMA:
            self.assertIn(f"data-field='{field['name']}'", html)
        self.assertIn("downloadAnswers", html)
        self.assertIn("_intake.json", html)

    def test_checkbox_group_uses_data_group(self) -> None:
        schema = [{"name": "docs", "label": "Docs", "type": "checkboxes", "options": ["W-2", "K-1"]}]
        html = intake.build_form_html(schema)
        self.assertIn("data-group='docs'", html)
        self.assertIn("value='W-2'", html)

    def test_schema_default_is_created_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            schema, path = intake.load_schema(folder)
            self.assertTrue(path.exists())
            self.assertEqual(schema, intake.DEFAULT_SCHEMA)
            # An edited schema is honored on the next load.
            path.write_text(json.dumps([{"name": "only", "label": "Only", "type": "text"}]), encoding="utf-8")
            schema2, _ = intake.load_schema(folder)
            self.assertEqual([f["name"] for f in schema2], ["only"])


class ResponseCompilationTests(unittest.TestCase):
    def _write_response(self, folder: Path, name: str, record: dict) -> None:
        (folder / f"{name}_intake.json").write_text(json.dumps(record), encoding="utf-8")

    def test_compile_skips_records_without_name(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self._write_response(folder, "good", {"client_name": "A", "email": "a@x.com"})
            self._write_response(folder, "bad", {"email": "b@x.com"})
            clients, warnings = intake.compile_responses(sorted(folder.glob("*_intake.json")))
            self.assertEqual([c["client_name"] for c in clients], ["A"])
            self.assertEqual(len(warnings), 1)

    def test_merge_appends_only_new_clients(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            clients_file = Path(d) / "clients.json"
            clients_file.write_text(json.dumps([{"client_name": "A", "email": "a@x.com"}]), encoding="utf-8")
            added, skipped = intake._merge_into_clients(
                clients_file,
                [{"client_name": "A", "email": "a@x.com"}, {"client_name": "B", "email": "b@x.com"}],
            )
            self.assertEqual((added, skipped), (1, 1))
            data = json.loads(clients_file.read_text())
            self.assertEqual([c["client_name"] for c in data], ["A", "B"])

    def test_end_to_end_builds_form_and_clients(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self._write_response(folder, "Jordan_Sample", {"client_name": "Jordan Sample", "email": "j@x.com"})
            result = intake.run_intake(folder)

            self.assertTrue(Path(result["form_path"]).exists())
            self.assertEqual(result["clients_added"], 1)
            clients = json.loads((folder / "clients.json").read_text())
            self.assertEqual(clients[0]["client_name"], "Jordan Sample")
            # Re-running does not duplicate the client.
            again = intake.run_intake(folder)
            self.assertEqual(again["clients_added"], 0)


if __name__ == "__main__":
    unittest.main()
