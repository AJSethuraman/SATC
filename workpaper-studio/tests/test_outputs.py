"""What leaves the application: a feed that never turns missing into zero and never carries a personal value."""
import json

import pytest

from conftest import fill
from workpaper_studio import outputs


def released_bank(studio, packs):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", dict(packs["bank-reconciliation"].data["example"], prep="A. Rivera"), packs["bank-reconciliation"])
    return cid


def test_missing_is_null_with_state_never_zero(studio):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    studio.set("A. Rivera", cid, "f/gl", "0")
    fd = outputs.feed(studio.case(cid))
    by = {v["path"]: v for v in fd["values"]}
    assert by["f/stmt"]["value"] is None and by["f/stmt"]["state"] == "missing"
    assert by["f/gl"]["value"] == 0 and by["f/gl"]["state"] == "zero"
    rec = fd["calculations"][0]
    assert rec["result"] is None and rec["status"] == "not_calculated"
    assert "Not calculated" not in json.dumps(fd["values"])


def test_personal_fields_are_masked_everywhere_that_leaves(studio, packs, tmp_path):
    cid = released_bank(studio, packs)
    secret = packs["bank-reconciliation"].data["example"]["account"]
    c = studio.case(cid)
    fd = outputs.feed(c)
    text = json.dumps(fd) + outputs.feed_csv(fd)
    assert secret not in text
    assert any(v["masked"] and v["value"].startswith(secret[0]) for v in fd["values"])
    # and the subject shown in the worklist is masked too
    assert secret not in c["subject"]


def test_released_files_are_what_was_fingerprinted(studio, packs):
    import hashlib
    cid = released_bank(studio, packs)
    studio.submit("A. Rivera", cid)
    studio.approve("D. Patel", cid)
    studio.release("D. Patel", cid)
    for o in studio.released_outputs(cid):
        data = (studio.out_dir / cid / o["name"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == o["sha256"]
    fd = json.loads((studio.out_dir / cid / f"{cid}.feed.json").read_text())
    assert fd["approved_by"] == "D. Patel" and fd["pack_fingerprint"] == studio.case(cid)["fingerprint"]


def test_workbook_export_opens_and_carries_the_case(studio, packs, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    cid = released_bank(studio, packs)
    studio.mark("A. Rivera", cid, "g/items/4", "excluded", "Fee reversed")
    p = outputs.workbook(studio.case(cid), tmp_path / "x.xlsx")
    wb = openpyxl.load_workbook(p)
    assert "Workpaper" in wb.sheetnames
    about = [[c.value for c in r] for r in wb["About"].iter_rows()]
    flat = json.dumps(about, default=str)
    assert cid in flat and "excluded (Fee reversed)" in flat
    # the excluded row is not in the workbook's items
    sheet, coord = next(iter(wb.defined_names["Field_stmt"].destinations))
    assert wb[sheet][coord.replace("$", "")].value == 185600.55


def _all_text(xlsx):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(xlsx)
    return " ".join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None), wb


def test_released_files_carry_no_personal_value_and_say_released(studio, packs):
    cid = studio.new_case("A. Rivera", "Credit file review")
    ex = json.loads(json.dumps(packs["credit-file-review"].data["example"]))
    ex["qs1"]["6.01"] = {"r": "Effective"}
    ex["summary"] = "Synthetic summary."
    fill(studio, cid, "A. Rivera", ex, packs["credit-file-review"])
    studio.record_exception("A. Rivera", cid, "calc_dti", "Compensating strength documented", "Liquidity covers two years (synthetic).")
    studio.submit("A. Rivera", cid)
    studio.raise_point("D. Patel", cid, "fac", "Confirm the balance date.")
    studio.reply_point("A. Rivera", cid, "P1", "October statement.")
    studio.clear_point("D. Patel", cid, "P1")
    studio.acknowledge("D. Patel", cid, "E1")
    studio.approve("D. Patel", cid)
    studio.release("D. Patel", cid)
    folder = studio.out_dir / cid
    secret = ex["borrower"]
    for f in folder.iterdir():
        text = _all_text(f)[0] if f.suffix == ".xlsx" else f.read_text()
        assert secret not in text, f.name
    fd = json.loads((folder / f"{cid}.feed.json").read_text())
    assert fd["status"] == "Released" and fd["released_by"] == "D. Patel"
    text, wb = _all_text(folder / f"{cid}.xlsx")
    assert "Review" in wb.sheetnames
    for said in ("Liquidity covers two years", "Acknowledged by D. Patel", "Confirm the balance date", "October statement", "Cleared by D. Patel", "Approved"):
        assert said in text, said
