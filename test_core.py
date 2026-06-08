#!/usr/bin/env python3
"""Tests for the shared core primitives. Standard library only."""

from __future__ import annotations

import unittest

import core


class EscapeTests(unittest.TestCase):
    def test_escapes_html_metacharacters(self) -> None:
        self.assertEqual(core.escape_html("a & b < c > d"), "a &amp; b &lt; c &gt; d")

    def test_quote_option(self) -> None:
        self.assertNotIn('"', core.escape_html('say "hi"', quote=True))
        self.assertIn('"', core.escape_html('say "hi"'))  # default leaves quotes


class MoneyTests(unittest.TestCase):
    def test_parse_money_variants(self) -> None:
        self.assertEqual(core.parse_money("$1,234.56"), 1234.56)
        self.assertEqual(core.parse_money("100"), 100.0)
        self.assertEqual(core.parse_money(42.5), 42.5)
        self.assertEqual(core.parse_money("not money"), 0.0)
        self.assertEqual(core.parse_money(None), 0.0)

    def test_format_money(self) -> None:
        self.assertEqual(core.format_money(1234.5), "1,234.50")
        self.assertEqual(core.format_money(0), "0.00")


class OwnershipTests(unittest.TestCase):
    def test_longer_slugs(self) -> None:
        self.assertEqual(
            core.longer_slugs("Jo_Sample", ["Jo_Sample", "Jo_Sample_Jr", "Other"]),
            ["Jo_Sample_Jr"],
        )

    def test_file_belongs_to_other_client(self) -> None:
        longer = core.longer_slugs("Jo_Sample", ["Jo_Sample", "Jo_Sample_Jr"])
        self.assertTrue(core.file_belongs_to_other_client("Jo_Sample_Jr_invoice.html", longer))
        self.assertTrue(core.file_belongs_to_other_client("Signed_Jo_Sample_Jr_8879.pdf", longer))
        self.assertFalse(core.file_belongs_to_other_client("Jo_Sample_invoice.html", longer))
        self.assertFalse(core.file_belongs_to_other_client("Jo_Sample_invoice.html", []))


class AppendClientsTests(unittest.TestCase):
    def test_dedupe_by_email_then_name(self) -> None:
        existing = [{"client_name": "A", "email": "a@x.com"}]
        new = [
            {"client_name": "A", "email": "a@x.com"},   # dup email
            {"client_name": "A"},                        # dup name (no email)
            {"client_name": "B", "email": "b@x.com"},    # new
        ]
        merged, added, skipped = core.append_new_clients(existing, new)
        self.assertEqual(added, 1)
        self.assertEqual(skipped, 2)
        self.assertEqual([c["client_name"] for c in merged], ["A", "B"])

    def test_does_not_mutate_input(self) -> None:
        existing = [{"client_name": "A"}]
        core.append_new_clients(existing, [{"client_name": "B"}])
        self.assertEqual(len(existing), 1)  # original untouched


if __name__ == "__main__":
    unittest.main()
