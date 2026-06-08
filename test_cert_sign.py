#!/usr/bin/env python3
"""Tests for PAdES certificate signing.

The signing test requires pyhanko, cryptography, and PyMuPDF and is skipped when
any are absent. The no-certificate path needs no dependencies.
"""

from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path

import cert_sign

try:
    import fitz  # PyMuPDF
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
    from cryptography.x509.oid import NameOID
    from pyhanko.pdf_utils.reader import PdfFileReader

    HAVE_SIGNING = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_SIGNING = False


def _make_pkcs12(path: Path, password: bytes) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Preparer")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(pkcs12.serialize_key_and_certificates(
        b"test", key, cert, None, BestAvailableEncryption(password)))


class NoCertTests(unittest.TestCase):
    def test_missing_certificate_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("No signing certificate", cert_sign.run_cert_signing(Path(d))["summary"])
            result = cert_sign.run_cert_signing(Path(d), cert_path=str(Path(d) / "nope.p12"))
            self.assertIn("not found", result["summary"])


@unittest.skipUnless(HAVE_SIGNING, "pyhanko/cryptography/PyMuPDF not installed")
class SigningTests(unittest.TestCase):
    def test_signs_input_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            pfx = folder / "id.p12"
            _make_pkcs12(pfx, b"pw")
            document = fitz.open()
            document.new_page().insert_text((72, 700), "Engagement Letter")
            document.save(folder / "letter.pdf")
            document.close()

            result = cert_sign.run_cert_signing(folder, cert_path=str(pfx), cert_password="pw")
            self.assertEqual(result["signed_count"], 1)
            signed = Path(result["signed"][0])
            self.assertTrue(signed.name.startswith("Certified_"))
            with open(signed, "rb") as handle:
                self.assertEqual(len(PdfFileReader(handle).embedded_signatures), 1)

    def test_wrong_password_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            pfx = folder / "id.p12"
            _make_pkcs12(pfx, b"correct")
            result = cert_sign.run_cert_signing(folder, cert_path=str(pfx), cert_password="wrong")
            self.assertIn("Could not load certificate", result["summary"])


if __name__ == "__main__":
    unittest.main()
