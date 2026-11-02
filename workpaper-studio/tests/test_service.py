"""Who may do what, held by the service whatever route asks; and a record that cannot be rewritten."""
import json
import sqlite3

import pytest

from conftest import fill
from workpaper_studio.engine import EntryError
from workpaper_studio.service import Refused


def credit_case(st, packs, complete=True):
    cid = st.new_case("A. Rivera", "Credit file review")
    ex = json.loads(json.dumps(packs["credit-file-review"].data["example"]))
    if complete:
        ex["qs1"]["6.01"] = {"r": "Effective"}
        ex["summary"] = "Synthetic summary."
    fill(st, cid, "A. Rivera", ex, packs["credit-file-review"])
    return cid


def test_entries_rebuild_the_example_exactly(studio, packs):
    cid = credit_case(studio, packs, complete=False)
    c = studio.case(cid)
    calc = c["eval"]["calcs"]["calc_dti"]
    assert calc["value"] == pytest.approx(6487 / 12650)
    assert calc["verdict"] == "Above limit"
    assert c["eval"]["missing"] == 2


def test_blank_is_never_zero_and_bad_entries_are_refused(studio):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    studio.set("A. Rivera", cid, "f/stmt", "")
    assert studio.case(cid)["eval"]["fields"]["stmt"]["state"] == "missing"
    with pytest.raises(EntryError, match="not a number"):
        studio.set("A. Rivera", cid, "f/stmt", "about ten")
    with pytest.raises(EntryError, match="not one of the choices"):
        studio.set("A. Rivera", cid, "f/interco", "Maybe")
    studio.set("A. Rivera", cid, "f/stmt", "0")
    assert studio.case(cid)["eval"]["fields"]["stmt"]["state"] == "zero"


def test_reviewer_cannot_change_an_entry(studio, packs):
    cid = credit_case(studio, packs)
    with pytest.raises(Refused, match="Only a preparer"):
        studio.set("D. Patel", cid, "f/borrower", "Changed by reviewer")
    with pytest.raises(Refused):
        studio.mark("D. Patel", cid, "f/scope", "na", "x")
    assert studio.case(cid)["data"]["borrower"] == "Harbor Millwork LLC"


def test_submission_needs_nothing_missing(studio, packs):
    cid = credit_case(studio, packs, complete=False)
    with pytest.raises(Refused, match="still missing"):
        studio.submit("A. Rivera", cid)


def test_preparer_cannot_review_or_approve_own_case(studio, packs):
    cid = credit_case(studio, packs)
    studio.submit("A. Rivera", cid)
    with pytest.raises(Refused, match="Only a reviewer"):
        studio.approve("A. Rivera", cid)
    studio.users["A. Rivera"] = ["preparer", "reviewer"]
    with pytest.raises(Refused, match="You prepared this case"):
        studio.approve("A. Rivera", cid)


def test_entries_lock_in_review_and_unlock_when_returned(studio, packs):
    cid = credit_case(studio, packs)
    studio.submit("A. Rivera", cid)
    with pytest.raises(Refused, match="locked"):
        studio.set("A. Rivera", cid, "f/scope", "Other")
    studio.return_case("D. Patel", cid)
    studio.set("A. Rivera", cid, "f/scope", "Other")
    assert studio.case(cid)["data"]["scope"] == "Other"


def test_above_limit_needs_an_acknowledged_exception_and_the_result_is_untouched(studio, packs):
    cid = credit_case(studio, packs)
    studio.submit("A. Rivera", cid)
    with pytest.raises(Refused, match="Record an exception"):
        studio.approve("D. Patel", cid)
    with pytest.raises(Refused, match="organization's list"):
        studio.record_exception("A. Rivera", cid, "calc_dti", "Because", "note")
    studio.record_exception("A. Rivera", cid, "calc_dti", "Compensating strength documented", "Strong liquidity (synthetic).")
    with pytest.raises(Refused, match="waiting for the reviewer"):
        studio.approve("D. Patel", cid)
    studio.acknowledge("D. Patel", cid, "E1")
    c = studio.approve("D. Patel", cid)
    assert c["status"] == "Approved"
    assert c["eval"]["calcs"]["calc_dti"]["value"] == pytest.approx(6487 / 12650)
    assert c["eval"]["calcs"]["calc_dti"]["verdict"] == "Above limit"


def test_open_review_point_blocks_approval(studio, packs):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", packs["bank-reconciliation"].data["example"], packs["bank-reconciliation"])
    studio.submit("A. Rivera", cid)
    studio.raise_point("D. Patel", cid, "s2", "Item 4 is over 90 days old. Why is it still outstanding?")
    with pytest.raises(Refused, match="Review points"):
        studio.approve("D. Patel", cid)
    with pytest.raises(Refused, match="Only a reviewer"):
        studio.clear_point("A. Rivera", cid, "P1")
    studio.reply_point("A. Rivera", cid, "P1", "Vendor confirmed it was lost; reissued in November.")
    studio.clear_point("D. Patel", cid, "P1")
    assert studio.approve("D. Patel", cid)["status"] == "Approved"


def test_release_only_after_approval_and_outputs_are_fingerprinted(studio, packs):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", packs["bank-reconciliation"].data["example"], packs["bank-reconciliation"])
    with pytest.raises(Refused, match="release check is not clear"):
        studio.release("D. Patel", cid)
    studio.submit("A. Rivera", cid)
    with pytest.raises(Refused, match="Approved by a reviewer"):
        studio.release("D. Patel", cid)
    studio.approve("D. Patel", cid)
    with pytest.raises(Refused):
        studio.release("A. Rivera", cid)
    c = studio.release("D. Patel", cid)
    assert c["status"] == "Released"
    names = {o["name"] for o in studio.released_outputs(cid)}
    assert {f"{cid}.feed.json", f"{cid}.feed.csv", f"{cid}.xlsx"} <= names
    with pytest.raises(Refused, match="already been released"):
        studio.release("D. Patel", cid)


def test_unconfirmed_limit_blocks_submission(studio):
    v = studio.confirm_limit("M. Okafor", "Bank reconciliation", "calc_rec", 0, confirmed=False)
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    c = studio.case(cid)
    assert c["policy_version"] == v
    assert c["eval"]["calcs"]["calc_rec"]["verdict"] == "Not tested: limit not confirmed"


def test_the_log_cannot_be_rewritten(studio, packs):
    cid = credit_case(studio, packs)
    db = sqlite3.connect(studio.db_path)
    for sql in ("UPDATE events SET body='{}' WHERE case_id=?", "DELETE FROM events WHERE case_id=?"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(sql, (cid,))
    for t in ("packs", "policy", "pack_approvals"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(f"DELETE FROM {t}")


def test_case_keeps_its_pack_and_limits_after_both_change(studio, packs, tmp_path):
    cid = credit_case(studio, packs, complete=False)
    before = studio.case(cid)["eval"]
    # the designer changes the tool and an admin moves the limit
    p = studio.packs_dir / "credit-file-review.json"
    d = json.loads(p.read_text())
    d["tool"]["sections"][1]["blocks"][1]["req"] = True
    d["pack"]["version"] = "1.2"
    p.write_text(json.dumps(d))
    studio.approve_pack("K. Owens", studio.propose("M. Okafor", "credit-file-review.json"))
    studio.confirm_limit("M. Okafor", "Credit file review", "calc_dti", 0.6)
    after = studio.case(cid)["eval"]
    assert json.dumps(before, sort_keys=True, default=str) == json.dumps(after, sort_keys=True, default=str)
    new = studio.case(studio.new_case("A. Rivera", "Credit file review"))
    assert new["version"] == "1.2" and new["policy"]["calc_dti"]["limit"] == 0.6


def test_pack_approval_is_maker_checker(studio, tmp_path):
    p = studio.packs_dir / "control-test.json"
    d = json.loads(p.read_text())
    d["pack"]["version"] = "2.1"
    p.write_text(json.dumps(d))
    fp = studio.propose("M. Okafor", "control-test.json")
    with pytest.raises(Refused, match="Only a approver|Only an approver|Only a approver"):
        studio.approve_pack("M. Okafor", fp)
    studio.users["M. Okafor"] = ["designer", "approver"]
    with pytest.raises(Refused, match="You proposed this version.*K. Owens can"):
        studio.approve_pack("M. Okafor", fp)
    with pytest.raises(Refused, match="Only a designer"):
        studio.propose("A. Rivera", "control-test.json")


def test_conditional_section_keeps_entries_while_it_does_not_apply(studio, packs):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    studio.set("A. Rivera", cid, "f/interco", "Yes")
    studio.set("A. Rivera", cid, "g/ic/0/party", "Bramble Farms (synthetic)")
    studio.set("A. Rivera", cid, "g/ic/0/amt", "1200")
    assert studio.case(cid)["eval"]["sections"][4]["status"] == "Complete"
    studio.set("A. Rivera", cid, "f/interco", "No")
    c = studio.case(cid)
    assert c["eval"]["sections"][4]["status"] == "Not applicable"
    assert c["data"]["ic"]["rows"][0] == {"party": "Bramble Farms (synthetic)", "amt": 1200}
    studio.set("A. Rivera", cid, "f/interco", "Yes")
    assert studio.case(cid)["eval"]["sections"][4]["status"] == "Complete"


def test_not_applicable_and_excluded_need_a_reason_and_are_honoured(studio, packs):
    cid = studio.new_case("A. Rivera", "Bank reconciliation")
    fill(studio, cid, "A. Rivera", packs["bank-reconciliation"].data["example"], packs["bank-reconciliation"])
    with pytest.raises(Refused, match="needs a reason"):
        studio.mark("A. Rivera", cid, "g/items/4", "excluded", " ")
    c = studio.mark("A. Rivera", cid, "g/items/4", "excluded", "Fee reversed by the bank")
    k = c["eval"]["calcs"]["calc_rec"]
    assert k["value"] == pytest.approx(-85.0) and k["verdict"] == "Above limit"
    assert any("left out: Fee reversed" in d for d in k["disclosures"])
    c = studio.mark("A. Rivera", cid, "f/gl", "na", "no ledger yet")
    assert c["eval"]["calcs"]["calc_rec"]["status"] == "not_calculated"
    c = studio.mark("A. Rivera", cid, "f/gl", None)
    assert c["eval"]["calcs"]["calc_rec"]["status"] == "calculated"


def test_replaying_the_log_reconstructs_the_case(studio, packs):
    cid = credit_case(studio, packs)
    c = studio.case(cid)
    from workpaper_studio import engine
    data = {}
    for e in studio.events(cid):
        if e["kind"] == "set":
            engine.set_value(c["pack"], data, e["path"], e["new"])
    assert data == c["data"]
