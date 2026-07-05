"""Slice 8 (issue #67): encryption-at-rest + the command line.

Round-trip, ciphertext-on-disk (no readable zip/xlsx markers), key-file
permissions at the ``satc_system`` bar, and a CLI smoke test over the
synthetic demo engagement.
"""

import json
import os
import stat
import sys

import pytest

from credit_review import build_demo_workbook, workbook_bytes
from credit_review import crypto
from credit_review.cli import main
from credit_review.workbook import ENGAGEMENTS_DIR

ENGAGEMENT = ENGAGEMENTS_DIR / "demo_engagement.yaml"


def test_encrypt_decrypt_round_trip(tmp_path):
    key = crypto.load_or_create_key(tmp_path)
    wb, *_ = build_demo_workbook()
    plain = workbook_bytes(wb)
    blob = crypto.encrypt_bytes(plain, key)
    assert blob != plain and crypto.is_encrypted(blob)
    assert crypto.encrypt_bytes(blob, key) == blob            # idempotent
    assert crypto.decrypt_bytes(blob, key) == plain
    assert crypto.decrypt_bytes(plain, key) == plain          # plaintext passthrough


def test_ciphertext_carries_no_readable_markers(tmp_path):
    key = crypto.load_or_create_key(tmp_path)
    wb, *_ = build_demo_workbook()
    plain = workbook_bytes(wb)
    # `strings`-visible markers in a plain xlsx: zip member names + magic
    assert b"[Content_Types].xml" in plain and plain[:2] == b"PK"
    blob = crypto.encrypt_bytes(plain, key)
    assert b"[Content_Types].xml" not in blob
    assert b"xl/worksheets" not in blob
    assert b"Blue Heron" not in blob


def test_key_file_is_sealed_and_restricted(tmp_path):
    crypto.load_or_create_key(tmp_path)
    key_path = tmp_path / "credit_review.key"
    assert key_path.exists()
    if sys.platform != "win32":
        assert key_path.read_bytes().startswith(b"RAW\x00")
        mode = stat.S_IMODE(os.stat(key_path).st_mode)
        assert mode == 0o600, oct(mode)
    # stable across loads
    assert crypto.load_or_create_key(tmp_path) == crypto.load_or_create_key(tmp_path)


def test_wrong_key_fails_closed(tmp_path):
    key = crypto.load_or_create_key(tmp_path / "a")
    other = crypto.load_or_create_key(tmp_path / "b")
    blob = crypto.encrypt_bytes(b"confidential", key)
    with pytest.raises(Exception):
        crypto.decrypt_bytes(blob, other)


def test_cli_build_writes_encrypted_workbook(tmp_path, capsys):
    out = tmp_path / "demo.xlsx.enc"
    rc = main(["--key-dir", str(tmp_path), "build", str(ENGAGEMENT),
               "-o", str(out)])
    assert rc == 0
    blob = out.read_bytes()
    assert crypto.is_encrypted(blob)
    assert b"[Content_Types].xml" not in blob
    assert "encrypted" in capsys.readouterr().out


def test_cli_ingest_round_trips_encrypted_workbook(tmp_path, capsys):
    out = tmp_path / "demo.xlsx.enc"
    report = tmp_path / "findings.json"
    assert main(["--key-dir", str(tmp_path), "build", str(ENGAGEMENT),
                 "-o", str(out)]) == 0
    assert main(["--key-dir", str(tmp_path), "ingest", str(out),
                 "--json", str(report)]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["mart"]["engagement_id"] == "DEMO-2026-01"
    assert len(payload["mart"]["rows"]) == 4
    assert payload["portfolio_findings"]["total_open"] == 18
    assert payload["portfolio_findings"]["criticized_dollars"] == 4300000


def test_cli_plain_flag_is_demo_only_plaintext(tmp_path, capsys):
    out = tmp_path / "demo.xlsx"
    assert main(["--key-dir", str(tmp_path), "build", str(ENGAGEMENT),
                 "-o", str(out), "--plain"]) == 0
    data = out.read_bytes()
    assert data[:2] == b"PK" and not crypto.is_encrypted(data)
    assert "synthetic demo only" in capsys.readouterr().out
