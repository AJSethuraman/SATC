"""Coverage for the smaller Phase-0 patches: intake-folder guard (L8), the
`satc reset` confirmation, and Tesseract resolution / graceful OCR degradation."""

from __future__ import annotations

import pytest

from satc import cli
from satc.ingest import ocr


# -- L8: intake folder guard ------------------------------------------------

@pytest.fixture()
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path / "data"))
    from satc.app.state import AppState
    return AppState()


def test_run_intake_rejects_folder_outside_intake_root(state, tmp_path, monkeypatch):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    monkeypatch.setenv("SATC_INTAKE_ROOT", str(root))
    with pytest.raises(ValueError):
        state.run_intake(str(outside), client_id="SATC-001000", tax_year=2024)


def test_run_intake_allows_folder_inside_intake_root(state, tmp_path, monkeypatch):
    root = tmp_path / "root"
    inside = root / "clientA"
    inside.mkdir(parents=True)
    monkeypatch.setenv("SATC_INTAKE_ROOT", str(root))
    # Empty folder is fine — it just stages nothing; the point is it does NOT raise.
    out = state.run_intake(str(inside), client_id="SATC-001000", tax_year=2024)
    assert isinstance(out, dict)


# -- satc reset confirmation -------------------------------------------------

def _seed_dbs(d):
    d.mkdir(parents=True, exist_ok=True)
    for name in ("satc_vault.db", "satc_mart.db"):
        (d / name).write_bytes(b"x")


def test_reset_aborts_without_typed_confirmation(tmp_path, monkeypatch):
    _seed_dbs(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_: "no")
    rc = cli.main(["reset", "--dir", str(tmp_path)])
    assert rc == 1
    assert (tmp_path / "satc_vault.db").exists()   # untouched


def test_reset_proceeds_on_YES(tmp_path, monkeypatch):
    _seed_dbs(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_: "YES")
    rc = cli.main(["reset", "--dir", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / "satc_vault.db").exists()


def test_reset_yes_flag_skips_prompt(tmp_path):
    _seed_dbs(tmp_path)
    rc = cli.main(["reset", "--dir", str(tmp_path), "--yes"])   # no input() -> would hang if prompted
    assert rc == 0
    assert not (tmp_path / "satc_vault.db").exists()


# -- OCR: Tesseract resolution + graceful degradation ------------------------

def test_tesseract_override_is_honored(tmp_path, monkeypatch):
    fake = tmp_path / "tesseract.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("SATC_TESSERACT", str(fake))
    assert ocr._tesseract_cmd() == str(fake)


def test_ocr_degrades_to_empty_without_tesseract(tmp_path, monkeypatch):
    monkeypatch.delenv("SATC_TESSERACT", raising=False)
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    monkeypatch.setattr(ocr, "_WINDOWS_TESSERACT", ())
    assert ocr.tesseract_available() is False
    assert ocr.ocr_document_text(tmp_path / "nope.png") == ""
