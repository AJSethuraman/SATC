#!/usr/bin/env python3
"""Tests for pre-run input checks. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import preflight


class PrecheckTests(unittest.TestCase):
    def test_clients_required_tools_warn_when_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            issues = preflight.precheck(Path(d), ["generate", "invoice"])
            self.assertEqual(len(issues), 1)  # aggregated into one message
            self.assertIn("need client data", issues[0])
            self.assertIn("generate", issues[0])

    def test_no_warning_when_clients_present(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([{"client_name": "A"}]), encoding="utf-8")
            self.assertEqual(preflight.precheck(folder, ["dashboard"]), [])

    def test_sign_without_signature_warns_and_with_warns_not(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertTrue(any("signature" in i for i in preflight.precheck(folder, ["sign"])))
            (folder / "signature.png").write_bytes(b"x")
            self.assertEqual(preflight.precheck(folder, ["sign"]), [])

    def test_certsign_requires_cert_path(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertTrue(any("certificate" in i for i in preflight.precheck(folder, ["certsign"])))
            cert = folder / "id.p12"
            cert.write_bytes(b"x")
            self.assertEqual(preflight.precheck(folder, ["certsign"], cert_path=str(cert)), [])

    def test_import_without_source_warns(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any("client_list" in i for i in preflight.precheck(Path(d), ["import"])))

    def test_diagnostics_without_extract_warns_unless_extract_selected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertTrue(any("extracted data" in i for i in preflight.precheck(folder, ["diagnostics"])))
            # selecting extract in the same run suppresses the warning
            self.assertEqual(
                [i for i in preflight.precheck(folder, ["diagnostics", "extract"]) if "extracted data" in i],
                [],
            )

    def test_pdftools_without_pdfs_warns(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any("PDF_Tools" in i for i in preflight.precheck(Path(d), ["pdftools"])))

    def test_labels_used_in_messages(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            issues = preflight.precheck(Path(d), ["generate"], {"generate": "Generate Documents"})
            self.assertIn("Generate Documents", issues[0])


if __name__ == "__main__":
    unittest.main()
