#!/usr/bin/env python3
"""Apply the preparer's signature image to PDFs automatically.

Fifth tool in the suite. It finds an anchor phrase on each PDF page (by default
"Preparer Signature") and stamps a signature image just above it, writing a
signed copy to Signed_Documents/. This automates your own repetitive signing on
PDFs that carry the anchor text; it is fully local.

This is a visual stamp, not a cryptographic signature and not a client
e-signature. For tamper-evident signing use a certificate (PAdES); for binding
client e-signatures use a compliant service (such as Encyro).
"""

from __future__ import annotations

from pathlib import Path

import sort_tax_docs

SIGNED_FOLDER_NAME = "Signed_Documents"
DEFAULT_SIGNATURE_FILENAME = "signature.png"
DEFAULT_ANCHOR = "Preparer Signature"
SIGNATURE_WIDTH = 170.0
SIGNATURE_HEIGHT = 44.0
SIGNATURE_GAP = 6.0


def signature_box(
    anchor_x0: float,
    anchor_y0: float,
    width: float = SIGNATURE_WIDTH,
    height: float = SIGNATURE_HEIGHT,
    gap: float = SIGNATURE_GAP,
) -> tuple[float, float, float, float]:
    """Rectangle (x0, y0, x1, y1) to place the signature just above an anchor line."""

    bottom = anchor_y0 - gap
    return (anchor_x0, bottom - height, anchor_x0 + width, bottom)


def find_signature_image(input_folder: Path, signature_path=None) -> Path | None:
    if signature_path:
        candidate = Path(signature_path).expanduser()
        return candidate if candidate.is_file() else None
    default = input_folder / DEFAULT_SIGNATURE_FILENAME
    return default if default.is_file() else None


def _iter_input_pdfs(input_folder: Path, output_folder: Path):
    for path in sort_tax_docs.iter_supported_files(input_folder, output_folder):
        if path.suffix.lower() == ".pdf":
            yield path


def sign_pdf(source_pdf: Path, signature_image: Path, anchor: str, destination: Path) -> int:
    """Stamp the signature above every anchor occurrence. Returns number stamped."""

    import fitz  # PyMuPDF

    stamped = 0
    with fitz.open(source_pdf) as document:
        for page in document:
            for rect in page.search_for(anchor):
                box = fitz.Rect(*signature_box(rect.x0, rect.y0))
                page.insert_image(box, filename=str(signature_image), keep_proportion=True)
                stamped += 1
        if stamped:
            document.save(destination)
    return stamped


def run_signing(input_folder, signature_path=None, anchor=DEFAULT_ANCHOR, status_callback=None) -> dict:
    """Stamp the signature onto every input PDF that contains the anchor phrase."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "sign",
        "output_folder": output_folder,
        "signed_folder": None,
        "signed": [],
        "signed_count": 0,
        "warnings": [],
    }

    signature_image = find_signature_image(input_folder, signature_path)
    if signature_image is None:
        return {
            **base_result,
            "summary": (
                f"No signature image found (expected {DEFAULT_SIGNATURE_FILENAME} in the folder "
                "or a path passed in); nothing signed."
            ),
        }

    signed_folder = output_folder / SIGNED_FOLDER_NAME
    signed_folder.mkdir(exist_ok=True)

    signed: list[Path] = []
    warnings: list[str] = []
    pdfs = list(_iter_input_pdfs(input_folder, output_folder))
    for index, pdf in enumerate(pdfs, start=1):
        if status_callback:
            status_callback(f"Signing {index} of {len(pdfs)}: {pdf.name}")
        destination = sort_tax_docs.unique_destination_path(signed_folder, f"Signed_{pdf.name}")
        try:
            stamped = sign_pdf(pdf, signature_image, anchor, destination)
        except Exception as exc:  # Keep going through the rest of the folder.
            warnings.append(f"{pdf.name}: error while signing ({exc}).")
            continue
        if stamped:
            signed.append(destination)
        else:
            warnings.append(f"{pdf.name}: anchor '{anchor}' not found; not signed.")

    return {
        **base_result,
        "signed_folder": signed_folder,
        "signed": signed,
        "signed_count": len(signed),
        "warnings": warnings,
        "summary": (
            f"Signed {len(signed)} PDF(s) at the '{anchor}' anchor"
            + (f"; {len(warnings)} had no anchor or errored." if warnings else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Stamp a preparer signature image onto PDFs at an anchor phrase."
    )
    parser.add_argument("input_folder", help="Folder containing PDFs to sign.")
    parser.add_argument("--signature", default="", help="Path to the signature image (PNG).")
    parser.add_argument("--anchor", default=DEFAULT_ANCHOR, help="Anchor text to place the signature above.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    result = run_signing(
        folder, signature_path=args.signature or None, anchor=args.anchor, status_callback=print
    )
    print(result["summary"])
    if result["signed_folder"]:
        print(f"Signed documents folder: {result['signed_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
