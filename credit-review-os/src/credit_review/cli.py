"""Command-line front door.

``credit-review build <engagement.yaml>``  -> the encrypted engagement workbook
``credit-review ingest <workbook>``        -> de-identified mart + findings JSON

The build writes ciphertext by default (``--plain`` opts out for the synthetic
demo); ingest accepts either an encrypted or a plain workbook.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

from credit_review import crypto
from credit_review.config import load_engagement, load_loans, load_program
from credit_review.ingest import ingest_workbook
from credit_review.workbook import (
    PROGRAMS_DIR,
    build_engagement_workbook,
    workbook_bytes,
)


def _resolve_program(spec: str) -> Path:
    """A path to a program YAML, or a packaged LOB name like ``c_and_i``."""
    p = Path(spec)
    if p.exists():
        return p
    packaged = PROGRAMS_DIR / f"{spec}.yaml"
    if packaged.exists():
        return packaged
    raise SystemExit(f"program not found: {spec!r} "
                     f"(no such file, and no packaged program {packaged.name})")


def _cmd_build(args: argparse.Namespace) -> int:
    engagement = load_engagement(args.engagement)
    program = load_program(_resolve_program(args.program))
    loans = load_loans(engagement.loans_path)
    wb = build_engagement_workbook(program, engagement, loans)
    data = workbook_bytes(wb)

    if args.plain:
        out = Path(args.output) if args.output else Path(f"{engagement.engagement_id}.xlsx")
        out.write_bytes(data)
    else:
        key = crypto.load_or_create_key(args.key_dir)
        out = Path(args.output) if args.output \
            else Path(f"{engagement.engagement_id}.xlsx.enc")
        out.write_bytes(crypto.encrypt_bytes(data, key))
    print(f"wrote {out}  ({len(loans)} loans, "
          f"{'plaintext — synthetic demo only' if args.plain else 'AES-256-GCM encrypted'})")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    blob = Path(args.workbook).read_bytes()
    if crypto.is_encrypted(blob):
        key = crypto.load_or_create_key(args.key_dir)
        blob = crypto.decrypt_bytes(blob, key)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as fh:
        fh.write(blob)
        tmp = Path(fh.name)
    try:
        mart, findings = ingest_workbook(tmp)
    finally:
        tmp.unlink()

    payload = {
        "mart": {"engagement_id": mart.engagement_id, "lob": mart.lob,
                 "rows": list(mart.rows)},
        "portfolio_findings": dataclasses.asdict(findings) | {
            "records": list(findings.records)},
    }
    text = json.dumps(payload, indent=2, default=str)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
        print(f"wrote {args.json}")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="credit-review",
        description="Credit Review OS — build and re-ingest engagement workbooks.")
    parser.add_argument("--key-dir", type=Path, default=None,
                        help="key directory (default: ~/.credit-review)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="build the engagement workbook (encrypted)")
    p_build.add_argument("engagement", help="engagement overlay YAML")
    p_build.add_argument("--program", default="c_and_i",
                         help="program YAML path or packaged LOB name (default: c_and_i)")
    p_build.add_argument("-o", "--output", default=None)
    p_build.add_argument("--plain", action="store_true",
                         help="write plaintext .xlsx (synthetic demo only)")
    p_build.set_defaults(func=_cmd_build)

    p_ingest = sub.add_parser("ingest",
                              help="re-ingest a filled workbook -> de-identified JSON")
    p_ingest.add_argument("workbook", help=".xlsx or encrypted .xlsx.enc")
    p_ingest.add_argument("--json", default=None, help="write output to this file")
    p_ingest.set_defaults(func=_cmd_ingest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
