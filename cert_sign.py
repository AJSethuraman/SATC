#!/usr/bin/env python3
"""Apply a cryptographic (PAdES) signature to PDFs using a PKCS#12 certificate.

Unlike the Sign Documents tool (which stamps a signature image), this embeds a
tamper-evident digital signature backed by your signing certificate (a .p12/.pfx
file). Signed copies are written to Cert_Signed/.

The certificate password is never stored: pass it via the SATC_CERT_PASSWORD
environment variable (preferred) or transiently through the desktop field. Requires
the 'pyhanko' package (see requirements.txt).
"""

from __future__ import annotations

from pathlib import Path

import sort_tax_docs

CERT_SIGNED_FOLDER_NAME = "Cert_Signed"
DEFAULT_FIELD_NAME = "Signature1"


def _load_signer(cert_path: Path, password: str | None):
    """Load a PKCS#12 signer, with a clear error if pyhanko is missing."""

    try:
        from pyhanko.sign import signers
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "Certificate signing requires the 'pyhanko' package (pip install pyhanko)."
        ) from exc
    passphrase = password.encode("utf-8") if password else None
    return signers.SimpleSigner.load_pkcs12(pfx_file=str(cert_path), passphrase=passphrase)


def sign_pdf(source_pdf: Path, signer, destination: Path, field_name: str = DEFAULT_FIELD_NAME) -> None:
    """Write a PAdES-signed copy of source_pdf to destination."""

    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers

    with open(source_pdf, "rb") as infile, open(destination, "wb") as outfile:
        writer = IncrementalPdfFileWriter(infile)
        signers.sign_pdf(
            writer,
            signers.PdfSignatureMetadata(field_name=field_name),
            signer=signer,
            output=outfile,
        )


def _iter_input_pdfs(input_folder: Path, output_folder: Path):
    for path in sort_tax_docs.iter_supported_files(input_folder, output_folder):
        if path.suffix.lower() == ".pdf":
            yield path


def run_cert_signing(
    input_folder,
    cert_path=None,
    cert_password=None,
    field_name: str = DEFAULT_FIELD_NAME,
    status_callback=None,
) -> dict:
    """Cryptographically sign every input PDF with the given PKCS#12 certificate."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "certsign",
        "output_folder": output_folder,
        "signed_folder": None,
        "signed": [],
        "signed_count": 0,
        "warnings": [],
    }

    if not cert_path:
        return {**base_result, "summary": "No signing certificate provided; nothing certified."}
    cert_path = Path(cert_path).expanduser()
    if not cert_path.is_file():
        return {**base_result, "summary": f"Certificate not found: {cert_path}; nothing certified."}

    try:
        signer = _load_signer(cert_path, cert_password)
    except Exception as exc:
        return {**base_result, "summary": f"Could not load certificate ({exc}); nothing certified."}
    if signer is None:
        # pyhanko returns None (and logs) on a wrong password or unreadable PKCS#12.
        return {**base_result, "summary": "Could not load certificate (wrong password?); nothing certified."}

    signed_folder = output_folder / CERT_SIGNED_FOLDER_NAME
    signed_folder.mkdir(exist_ok=True)

    signed: list[Path] = []
    warnings: list[str] = []
    pdfs = list(_iter_input_pdfs(input_folder, output_folder))
    for index, pdf in enumerate(pdfs, start=1):
        if status_callback:
            status_callback(f"Certifying {index} of {len(pdfs)}: {pdf.name}")
        destination = sort_tax_docs.unique_destination_path(signed_folder, f"Certified_{pdf.name}")
        try:
            sign_pdf(pdf, signer, destination, field_name)
        except Exception as exc:
            warnings.append(f"{pdf.name}: could not sign ({exc}).")
            continue
        signed.append(destination)

    return {
        **base_result,
        "signed_folder": signed_folder,
        "signed": signed,
        "signed_count": len(signed),
        "warnings": warnings,
        "summary": (
            f"Cryptographically signed {len(signed)} PDF(s)"
            + (f"; {len(warnings)} could not be signed." if warnings else ".")
        ),
    }


def main() -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Apply a PAdES signature to PDFs with a PKCS#12 cert.")
    parser.add_argument("input_folder", help="Folder containing PDFs to sign.")
    parser.add_argument("--cert", required=True, help="Path to the PKCS#12 certificate (.p12/.pfx).")
    parser.add_argument("--field", default=DEFAULT_FIELD_NAME, help="Signature field name.")
    parser.add_argument(
        "--password",
        default=os.environ.get("SATC_CERT_PASSWORD"),
        help="Certificate password (prefer the SATC_CERT_PASSWORD env var).",
    )
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    result = run_cert_signing(
        folder, cert_path=args.cert, cert_password=args.password,
        field_name=args.field, status_callback=print,
    )
    print(result["summary"])
    if result["signed_folder"]:
        print(f"Certified documents folder: {result['signed_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
