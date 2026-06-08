#!/usr/bin/env python3
"""Tests for the tool registry: subset selection runs in canonical pipeline order."""

from __future__ import annotations

import unittest

import tax_tools


class OrderedToolKeysTests(unittest.TestCase):
    def test_any_selection_order_runs_in_pipeline_order(self) -> None:
        self.assertEqual(
            tax_tools.ordered_tool_keys(["encyro", "sort", "generate"]),
            ["sort", "generate", "encyro"],
        )

    def test_subset_is_allowed(self) -> None:
        self.assertEqual(tax_tools.ordered_tool_keys(["email"]), ["email"])
        self.assertEqual(
            tax_tools.ordered_tool_keys(["sign", "generate"]), ["generate", "sign"]
        )

    def test_duplicates_are_removed(self) -> None:
        self.assertEqual(tax_tools.ordered_tool_keys(["sort", "sort", "extract"]), ["sort", "extract"])

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            tax_tools.ordered_tool_keys(["sort", "nope"])

    def test_document_tools_need_no_heavy_dependencies(self) -> None:
        # Pure document/data tools must not demand PyMuPDF/Tesseract.
        self.assertFalse(tax_tools.needs_dependencies(["generate", "invoice", "email", "dashboard"]))
        self.assertFalse(tax_tools.needs_dependencies(["validate", "import", "intake", "checklist"]))
        # The PDF/OCR tools do.
        self.assertTrue(tax_tools.needs_dependencies(["sort"]))
        self.assertTrue(tax_tools.needs_dependencies(["generate", "extract"]))
        self.assertTrue(tax_tools.needs_dependencies(["encyro"]))

    def test_canonical_order_matches_registry(self) -> None:
        self.assertEqual(
            tax_tools.ordered_tool_keys(list(tax_tools.DEFAULT_TOOL_KEYS)),
            list(tax_tools.DEFAULT_TOOL_KEYS),
        )


if __name__ == "__main__":
    unittest.main()
