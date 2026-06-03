#!/usr/bin/env python3
"""Tests for the email-draft and signature tools.

Email-draft tests use only the standard library. The PDF signing integration
test requires PyMuPDF/Pillow and is skipped when they are absent. No real client
data or signatures are used.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from email import message_from_bytes
from email.policy import default as default_email_policy
from pathlib import Path

import compose_emails
import sign_documents

try:
    import fitz  # PyMuPDF
    from PIL import Image

    HAVE_PDF_DEPS = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_PDF_DEPS = False


class EmailDraftTests(unittest.TestCase):
    def test_split_subject_and_body(self) -> None:
        subject, body = compose_emails.split_subject_and_body("Subject: Hello\n\nDear X,\nBody.")
        self.assertEqual(subject, "Hello")
        self.assertEqual(body, "Dear X,\nBody.")

    def test_split_without_subject_line(self) -> None:
        subject, body = compose_emails.split_subject_and_body("Just a body")
        self.assertEqual(subject, "Your Tax Documents")
        self.assertEqual(body, "Just a body")

    def _setup_folder(self, tmp: Path, client: dict) -> Path:
        (tmp / "clients.json").write_text(json.dumps([client]), encoding="utf-8")
        generated = tmp / "Organized_Tax_Documents" / "Generated_Documents"
        generated.mkdir(parents=True, exist_ok=True)
        slug = compose_emails.generate_documents.client_slug(client)
        (generated / f"{slug}_invoice.html").write_text("<html>invoice</html>", encoding="utf-8")
        return tmp

    def test_draft_created_with_attachment_and_rendered_subject(self) -> None:
        client = {
            "client_name": "Jordan Q. Sample",
            "email": "jordan@example.com",
            "firm_email": "office@firm.example",
            "firm_name": "Test Firm",
            "tax_year": "2024",
            "preparer_name": "A. Preparer",
        }
        with tempfile.TemporaryDirectory() as d:
            folder = self._setup_folder(Path(d), client)
            result = compose_emails.run_email_drafts(folder)

            self.assertEqual(result["draft_count"], 1)
            draft = Path(result["drafts"][0])
            message = message_from_bytes(draft.read_bytes(), policy=default_email_policy)
            self.assertEqual(message["To"], "jordan@example.com")
            self.assertEqual(message["From"], "office@firm.example")
            self.assertEqual(message["Subject"], "Your 2024 Tax Documents from Test Firm")
            attachments = [part.get_filename() for part in message.iter_attachments()]
            self.assertIn("Jordan_Q._Sample_invoice.html", attachments)

    def test_prefix_client_does_not_get_other_clients_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([
                {"client_name": "Jo Sample", "email": "jo@example.com"},
                {"client_name": "Jo Sample Jr", "email": "jr@example.com"},
            ]), encoding="utf-8")
            generated = folder / "Organized_Tax_Documents" / "Generated_Documents"
            generated.mkdir(parents=True)
            (generated / "Jo_Sample_invoice.html").write_text("x", encoding="utf-8")
            (generated / "Jo_Sample_Jr_invoice.html").write_text("x", encoding="utf-8")

            result = compose_emails.run_email_drafts(folder)
            draft = next(Path(p) for p in result["drafts"] if Path(p).name.startswith("Jo_Sample.eml"))
            message = message_from_bytes(draft.read_bytes(), policy=default_email_policy)
            names = [part.get_filename() for part in message.iter_attachments()]
            self.assertIn("Jo_Sample_invoice.html", names)
            self.assertNotIn("Jo_Sample_Jr_invoice.html", names)  # the Jr's PII stays out

    def test_client_without_email_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "No Email"}]), encoding="utf-8"
            )
            result = compose_emails.run_email_drafts(folder)
            self.assertEqual(result["draft_count"], 0)
            self.assertEqual(result["skipped_no_email"], 1)

    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = compose_emails.run_email_drafts(Path(d))
            self.assertEqual(result["draft_count"], 0)
            self.assertIn("No clients", result["summary"])


class SignaturePlacementTests(unittest.TestCase):
    def test_signature_box_sits_above_anchor(self) -> None:
        x0, y0, x1, y1 = sign_documents.signature_box(100.0, 500.0, width=170.0, height=44.0, gap=6.0)
        self.assertEqual((x0, x1), (100.0, 270.0))
        self.assertEqual(y1, 494.0)          # bottom = anchor_y0 - gap
        self.assertEqual(y0, 450.0)          # top = bottom - height
        self.assertLess(y1, 500.0)           # above the anchor line

    def test_find_signature_image_default_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertIsNone(sign_documents.find_signature_image(folder))
            (folder / "signature.png").write_bytes(b"not really a png")
            self.assertEqual(
                sign_documents.find_signature_image(folder).name, "signature.png"
            )


@unittest.skipUnless(HAVE_PDF_DEPS, "PyMuPDF/Pillow not installed")
class SignIntegrationTests(unittest.TestCase):
    def test_signs_pdf_with_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            # A small signature image.
            Image.new("RGBA", (200, 60), (0, 0, 0, 0)).save(folder / "signature.png")
            # A PDF that carries the anchor phrase.
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 600), "Preparer Signature", fontsize=12)
            document.save(folder / "form_8879.pdf")
            document.close()

            result = sign_documents.run_signing(folder)
            self.assertEqual(result["signed_count"], 1)
            signed = Path(result["signed"][0])
            with fitz.open(signed) as signed_doc:
                self.assertTrue(signed_doc[0].get_images())  # an image was stamped

    def test_no_anchor_means_not_signed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            Image.new("RGBA", (200, 60), (0, 0, 0, 0)).save(folder / "signature.png")
            document = fitz.open()
            document.new_page().insert_text((72, 600), "Nothing to sign here", fontsize=12)
            document.save(folder / "plain.pdf")
            document.close()

            result = sign_documents.run_signing(folder)
            self.assertEqual(result["signed_count"], 0)


if __name__ == "__main__":
    unittest.main()
