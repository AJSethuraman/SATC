#!/usr/bin/env python3
"""Tests for the Clients editor.

Pure load/serialize logic needs no GUI. A second class drives the real Qt dialog
offscreen and is skipped when PySide6 (or its display libraries) are unavailable.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import clients_editor as ce


class PureLogicTests(unittest.TestCase):
    def test_round_trip_preserves_hidden_fields(self) -> None:
        original = {
            "client_name": "Jo Sample", "email": "jo@x.com",
            "expected_documents": ["W-2", "1099-INT"], "services": ["state_return"],
            "total": "305.00", "line_items": [{"x": 1}], "form_8879_signed": True,  # hidden
        }
        cells = ce.client_to_row(original)
        self.assertEqual(cells[0], "Jo Sample")
        self.assertEqual(cells[5], "W-2, 1099-INT")  # list joined for display
        rebuilt = ce.row_to_client(cells, original)
        # editable fields survive...
        self.assertEqual(rebuilt["expected_documents"], ["W-2", "1099-INT"])
        # ...and so do fields the editor never showed
        self.assertEqual(rebuilt["total"], "305.00")
        self.assertEqual(rebuilt["line_items"], [{"x": 1}])
        self.assertTrue(rebuilt["form_8879_signed"])

    def test_cleared_cell_removes_field(self) -> None:
        client = ce.row_to_client(["Jo", "", "", "", "", "", ""])
        self.assertEqual(client, {"client_name": "Jo"})

    def test_dict_services_render_as_keys(self) -> None:
        self.assertEqual(ce.join_list([{"service": "state_return"}, "schedule_c"]),
                         "state_return, schedule_c")

    def test_save_backs_up_existing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([{"client_name": "Old"}]), encoding="utf-8")
            ce.save_clients(folder, [{"client_name": "New"}])
            self.assertEqual(json.loads((folder / "clients.json").read_text())[0]["client_name"], "New")
            self.assertTrue((folder / ce.BACKUP_FILENAME).exists())  # original preserved

    def test_load_from_csv_when_no_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.csv").write_text("client_name,email\nJo,jo@x.com\n", encoding="utf-8")
            clients = ce.load_clients(folder)
            self.assertEqual(clients[0]["client_name"], "Jo")


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from importlib.machinery import SourceFileLoader

    _app = QApplication.instance() or QApplication([])
    _mod = SourceFileLoader("satc_app", "tax_doc_sorter_app.pyw").load_module()
    HAVE_GUI = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_GUI = False


@unittest.skipUnless(HAVE_GUI, "PySide6/display not available")
class DialogTests(unittest.TestCase):
    def test_dialog_loads_edits_and_saves(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jo Sample", "email": "jo@x.com", "total": "100.00"}]),
                encoding="utf-8",
            )
            dialog = _mod.ClientsEditorDialog(folder)
            self.assertEqual(dialog.table.rowCount(), 1)
            # edit the email cell, add a brand-new client, then save
            dialog.table.item(0, 1).setText("new@x.com")
            dialog._append_row({})
            dialog.table.setItem(1, 0, _mod.QTableWidgetItem("Riley Carter"))
            dialog._save()

            saved = json.loads((folder / "clients.json").read_text())
            self.assertEqual(saved[0]["email"], "new@x.com")
            self.assertEqual(saved[0]["total"], "100.00")  # hidden field preserved
            self.assertEqual(saved[1]["client_name"], "Riley Carter")

    def test_blank_new_rows_are_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            dialog = _mod.ClientsEditorDialog(folder)
            dialog._append_row({})  # empty row, no name
            dialog._save()
            self.assertEqual(json.loads((folder / "clients.json").read_text()), [])


if __name__ == "__main__":
    unittest.main()
