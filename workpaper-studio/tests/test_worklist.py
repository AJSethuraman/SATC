"""The work list comes from the master database; every line is a case filled with what the database knows."""
import json
import sqlite3

import pytest

from workpaper_studio import demo, outputs, sources
from workpaper_studio.service import Refused


@pytest.fixture
def master(studio, tmp_path):
    d = tmp_path
    demo.write(d)
    return d, sources.configured(d)


def test_loading_opens_a_case_per_line_filled_and_assigned(studio, master):
    d, cfg = master
    rep = studio.load_work("M. Okafor", "Credit file review", cfg, d)
    assert [l for l, _ in rep["loaded"]] == ["L-1001", "L-1002", "L-1003", "L-1006"]
    refused = dict(rep["refused"])
    assert "Bridge loan" in refused["L-1004"] and "not one of the choices" in refused["L-1004"]
    assert refused["L-1005"] == "Preparer “Z. Nobody” is not set up in Access"   # said once
    cid = dict(rep["loaded"])["L-1001"]
    c = studio.case(cid)
    assert c["preparer"] == "A. Rivera" and c["assigned_reviewer"] == "D. Patel" and c["line_id"] == "L-1001"
    assert c["data"]["borrower"] == "Harbor Millwork LLC (synthetic)"
    assert c["data"]["facilities"]["rows"][1] == {"ftype": "Line of credit", "frating": 5, "commit": 75000, "out": 22500}
    assert c["eval"]["tables"]["facilities"]["totals"]["commit"] == 360000
    assert any(e["kind"] == "loaded" and "master database" in e["source"] for e in c["events"])


def test_loading_again_skips_what_is_loaded_and_never_writes_the_master(studio, master):
    d, cfg = master
    before = (d / "master.db").read_bytes()
    studio.load_work("M. Okafor", "Credit file review", cfg, d)
    rep = studio.load_work("M. Okafor", "Credit file review", cfg, d)
    assert rep["loaded"] == [] and set(rep["skipped"]) == {"L-1001", "L-1002", "L-1003", "L-1006"}
    assert (d / "master.db").read_bytes() == before
    assert len(studio.load_history("Credit file review")) == 2


def test_a_csv_source_works_the_same(studio, master):
    d, cfg = master
    rep = studio.load_work("M. Okafor", "Bank reconciliation", cfg, d)
    assert len(rep["loaded"]) == 3 and not rep["refused"]
    c = studio.case(dict(rep["loaded"])["BR-202"])
    assert c["preparer"] == "J. Moss" and c["data"]["prep"] == "J. Moss" and c["data"]["stmtdate"] == "2026-10-31"


def test_a_list_missing_a_column_loads_nothing(studio, master):
    d, cfg = master
    db = sqlite3.connect(d / "master.db")
    db.execute("ALTER TABLE credit_lines RENAME COLUMN borrower_name TO customer")
    db.commit()
    with pytest.raises(Refused, match="no column 'borrower_name'.*Nothing was loaded"):
        studio.load_work("M. Okafor", "Credit file review", cfg, d)
    assert studio.case_ids() == []


def test_only_access_that_includes_it_loads_and_only_the_assigned_see_their_case(studio, master):
    d, cfg = master
    with pytest.raises(Refused, match="Permission required: Load work lists"):
        studio.load_work("A. Rivera", "Credit file review", cfg, d)
    rep = studio.load_work("M. Okafor", "Credit file review", cfg, d)
    moss = dict(rep["loaded"])["L-1002"]
    with pytest.raises(Refused, match="assigned to J. Moss"):
        studio.set("A. Rivera", moss, "f/scope", "x")
    assert not studio.visible("A. Rivera", studio.case(moss)) and studio.visible("D. Patel", studio.case(moss))


def test_a_correction_to_a_master_value_is_kept_and_shown(studio, master):
    d, cfg = master
    rep = studio.load_work("M. Okafor", "Credit file review", cfg, d)
    cid = dict(rep["loaded"])["L-1001"]
    studio.set("A. Rivera", cid, "g/facilities/1/out", "23,750")
    fd = outputs.feed(studio.case(cid))
    v = next(x for x in fd["values"] if x["path"] == "g/facilities/1/out")
    assert v["value"] == 23750 and v["changed_from_master"] is True and v["master_value"] == 22500
    w = next(x for x in fd["values"] if x["path"] == "g/facilities/0/out")
    assert w["source"] == "master" and w["changed_from_master"] is False
