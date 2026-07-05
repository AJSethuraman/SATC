"""ASCII-bundle build-on-target (contract §11 pattern).

The bundle is a single pure-ASCII script; run in an empty directory on a
machine with only openpyxl + PyYAML, it rebuilds the engagement workbook
**byte-identical** to a direct build here (the builder is deterministic, so
build-on-target is provably the same deliverable).
"""

import hashlib
import subprocess
import sys

import pytest

from credit_review import build_demo_workbook, workbook_bytes
from credit_review.cli import main
from credit_review.workbook import ENGAGEMENTS_DIR

ENGAGEMENT = ENGAGEMENTS_DIR / "demo_engagement.yaml"


@pytest.fixture(scope="module")
def bundle_path(tmp_path_factory):
    out = tmp_path_factory.mktemp("bundle") / "build_credit_review.py"
    assert main(["bundle", str(ENGAGEMENT), "-o", str(out)]) == 0
    return out


def test_bundle_is_pure_ascii(bundle_path):
    raw = bundle_path.read_bytes()
    raw.decode("ascii")   # raises on any non-ASCII byte
    assert b"\x00" not in raw


def test_bundle_rebuilds_byte_identical_workbook_in_empty_dir(bundle_path, tmp_path):
    # simulate the target machine: empty folder, plain `python <script>`
    workdir = tmp_path / "target"
    workdir.mkdir()
    script = workdir / bundle_path.name
    script.write_text(bundle_path.read_text(encoding="ascii"), encoding="ascii")
    result = subprocess.run([sys.executable, script.name], cwd=workdir,
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr
    built = workdir / "DEMO-2026-01.xlsx"
    assert built.exists()

    wb, *_ = build_demo_workbook()
    direct = workbook_bytes(wb)
    assert hashlib.sha256(built.read_bytes()).hexdigest() \
        == hashlib.sha256(direct).hexdigest()
    # and the script reported the same hash
    assert hashlib.sha256(direct).hexdigest() in result.stdout


def test_bundle_carries_no_crypto_or_ingest_dependencies(bundle_path):
    text = bundle_path.read_text(encoding="ascii")
    assert "cryptography" not in text
    assert "crypto.py" not in text and "cli.py" not in text
    # the runner imports only the build path
    assert "import formulas" not in text.split("FILES")[0]
