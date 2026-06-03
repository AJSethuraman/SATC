#!/usr/bin/env python3
"""Tests for the client-list importer. Standard library only (CSV path)."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import import_clients as ic


class MappingTests(unittest.TestCase):
    def test_common_headers_map_to_fields(self) -> None:
        row = {"Client Name": "Jo Sample", "E-mail": "jo@x.com", "Phone #": "555"}
        # "Phone #" isn't a default header; it is kept snake-cased, not dropped.
        client = ic.map_row(row, ic.DEFAULT_HEADER_MAP)
        self.assertEqual(client["client_name"], "Jo Sample")
        self.assertEqual(client["email"], "jo@x.com")
        self.assertIn("phone_#", client)

    def test_blank_cells_dropped_and_unknown_kept(self) -> None:
        row = {"Name": "A", "Tax Year": "", "Spouse Name": "B"}
        client = ic.map_row(row, ic.DEFAULT_HEADER_MAP)
        self.assertNotIn("tax_year", client)       # blank dropped
        self.assertEqual(client["spouse_name"], "B")  # unknown column preserved

    def test_build_clients_skips_nameless_rows(self) -> None:
        rows = [{"Name": "A", "Email": "a@x.com"}, {"Email": "b@x.com"}]
        clients, warnings = ic.build_clients(rows, ic.DEFAULT_HEADER_MAP)
        self.assertEqual([c["client_name"] for c in clients], ["A"])
        self.assertEqual(len(warnings), 1)

    def test_import_map_override(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / ic.IMPORT_MAP_FILENAME).write_text(
                json.dumps({"Taxpayer Email": "email"}), encoding="utf-8"
            )
            mapping = ic.load_mapping(folder)
            self.assertEqual(ic.header_to_field("Taxpayer Email", mapping), "email")


class RunTests(unittest.TestCase):
    def _write_csv(self, folder: Path, rows: list[dict]) -> None:
        with (folder / "client_list.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_no_source(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("No client list", ic.run_import(Path(d))["summary"])

    def test_import_creates_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self._write_csv(folder, [
                {"Name": "Jo Sample", "Email": "jo@x.com"},
                {"Name": "Riley Carter", "Email": "riley@x.com"},
            ])
            result = ic.run_import(folder)
            self.assertEqual(result["added"], 2)
            clients = json.loads((folder / "clients.json").read_text())
            self.assertEqual([c["client_name"] for c in clients], ["Jo Sample", "Riley Carter"])

            # Re-running imports nothing new (deduped by email/name).
            again = ic.run_import(folder)
            self.assertEqual(again["added"], 0)
            self.assertEqual(again["skipped"], 2)


if __name__ == "__main__":
    unittest.main()
