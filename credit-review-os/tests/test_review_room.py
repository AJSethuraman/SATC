"""Review Room slice 1 (issue #75): launcher security, store, card, build.

Seams per the PRD: the Flask test client; preview-vs-recalc parity and
store-vs-fixture byte parity; store crypto/PII.
"""

import json

import pytest
import yaml

from credit_review import workbook_bytes
from credit_review.app import create_app
from credit_review.config import ConfigError, load_engagement, load_program
from credit_review.evaluate import evaluate_file
from credit_review.store import EngagementStore
from credit_review.workbook import (
    ENGAGEMENTS_DIR,
    PROGRAMS_DIR,
    build_demo_retail_workbook,
)

from recalc import Recalc
from test_mode_b import GRID, PS


@pytest.fixture()
def room(tmp_path):
    program = load_program(PROGRAMS_DIR / "retail.yaml")
    engagement = load_engagement(ENGAGEMENTS_DIR / "demo_retail_engagement.yaml")
    store = EngagementStore(program, engagement,
                            store_dir=tmp_path / "stores", key_dir=tmp_path / "keys")
    app = create_app(store)
    app.config["TESTING"] = True
    return app.test_client(), store


def _fixture_data():
    return yaml.safe_load(
        (ENGAGEMENTS_DIR / "demo_retail_samples.yaml").read_text(encoding="utf-8"))


def _auto_file(loan="AU-90001", segment="rand_large", **over):
    entry = {"loan_number": loan, "segment": segment, "attr_balance": "20000",
             "attr_score": "700",
             "attr_dti": "0.35", "attr_ltv": "0.9", "attr_term_months": "60",
             "test_credit_report_reviewed": "pass", "test_income_verified": "pass",
             "test_contract_docs_complete": "pass",
             "test_reg_z_disclosures_present": "pass"}
    entry.update(over)
    return entry


# ---------------------------------------------------------------------------
# Security posture
# ---------------------------------------------------------------------------
def test_host_guard_rejects_non_loopback(room):
    client, _ = room
    assert client.get("/", headers={"Host": "evil.example:5060"}).status_code == 403
    assert client.get("/", headers={"Host": "127.0.0.1:5060"}).status_code == 200


# ---------------------------------------------------------------------------
# File card: validation identical to the samples loader
# ---------------------------------------------------------------------------
def test_valid_file_persists_encrypted(room, tmp_path):
    client, store = room
    resp = client.post("/p/indirect_auto/file", data=_auto_file())
    assert resp.status_code == 302
    assert store.get_file("indirect_auto", "AU-90001")["score"] == 700
    assert store.get_file("indirect_auto", "AU-90001")["balance"] == 20000
    raw = store.path.read_bytes()
    assert raw.startswith(b"CROSENC1")          # ciphertext on disk
    assert b"AU-90001" not in raw               # loan number unreadable
    assert oct(store.path.stat().st_mode)[-3:] == "600"


def test_invalid_entries_are_refused_like_the_loader(room):
    client, store = room
    page = client.post("/p/indirect_auto/file",
                       data=_auto_file(segment="not_a_segment"))
    assert b"sample plan" in page.data
    page = client.post("/p/indirect_auto/file",
                       data=_auto_file(**{"test_income_verified": "yes"}))
    assert b"attestation" in page.data or b"pass" in page.data
    assert store.get_file("indirect_auto", "AU-90001") is None


def test_person_name_keys_refused_at_the_store(room):
    _, store = room
    with pytest.raises(ConfigError, match="loan number only"):
        store.upsert_file("indirect_auto",
                          {**{k.replace("attr_", "").replace("test_", ""): v
                              for k, v in _auto_file().items()},
                           "borrower_name": "A Person"})


# ---------------------------------------------------------------------------
# Live evaluation parity (preview == workbook formulas)
# ---------------------------------------------------------------------------
def test_preview_matches_recalc_on_every_demo_file(room):
    client, store = room
    wb, *_ = build_demo_retail_workbook()
    rc = Recalc(workbook_bytes(wb))
    product = store.product("indirect_auto")
    computed = [t["id"] for t in product["tests"] if t["kind"] == "computed"]
    col = {"dti_within_policy": "H", "score_at_or_above_floor": "I",
           "ltv_within_policy": "J", "term_within_policy": "K"}
    for f in _fixture_data()["products"]["indirect_auto"]["files"]:
        resp = client.post("/p/indirect_auto/preview", json={
            "attributes": {a["id"]: f[a["id"]] for a in product["attributes"]}})
        assert resp.status_code == 200
        preview = resp.get_json()
        row = GRID[f["loan_number"]]
        for tid in computed:
            assert preview["tests"][tid] == rc.value(PS, f"{col[tid]}{row}"), \
                (f["loan_number"], tid)
        assert preview["fringe"] == (rc.value(PS, f"S{row}") == "FRINGE"), \
            f["loan_number"]


# ---------------------------------------------------------------------------
# Byte parity: store-entered data == fixture-built workbook
# ---------------------------------------------------------------------------
def test_store_build_is_byte_identical_to_fixture_build(room, tmp_path):
    client, store = room
    data = _fixture_data()
    for pid, block in data["products"].items():
        for f in block["files"]:
            store.upsert_file(pid, dict(f))
        store.set_pool(pid, block["pool"])
    out = tmp_path / "out.xlsx"
    resp = client.post("/build", data={"path": str(out), "plain": "1"})
    assert resp.status_code == 302
    fixture = workbook_bytes(build_demo_retail_workbook()[0])
    assert out.read_bytes() == fixture


def test_build_refuses_until_pools_are_keyed(room, tmp_path):
    client, store = room
    store.upsert_file("indirect_auto", {
        k.replace("attr_", "").replace("test_", ""):
            (int(v) if v.isdigit() else v)
        for k, v in _auto_file().items()})
    resp = client.post("/build", data={"path": str(tmp_path / "x.xlsx"),
                                       "plain": "1"})
    assert resp.status_code == 409
    assert b"pool" in resp.data


# ---------------------------------------------------------------------------
# Store round-trip + tracking
# ---------------------------------------------------------------------------
def test_store_persists_across_reopen(room, tmp_path):
    _, store = room
    fixture = _fixture_data()["products"]["indirect_auto"]["files"][0]
    store.upsert_file("indirect_auto", dict(fixture))
    store.set_tracking("indirect_auto", "income_verified",
                       {"status": "waived", "owner": "SATC"})
    reopened = EngagementStore(store.program, store.engagement,
                               store_dir=store.store_dir, key_dir=store.key_dir)
    assert reopened.get_file("indirect_auto", fixture["loan_number"]) == fixture
    assert reopened.block("indirect_auto")["tracking"]["income_verified"] == \
        {"status": "waived", "owner": "SATC"}
    with pytest.raises(ConfigError, match="status"):
        reopened.set_tracking("indirect_auto", "income_verified",
                              {"status": "maybe"})
