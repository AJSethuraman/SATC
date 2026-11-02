"""Access the organization defines, and the two rules it cannot take away."""
import json
import sqlite3

import pytest

from conftest import fill
from workpaper_studio.service import Refused


def edit(st, fn, by="M. Okafor"):
    v, body = st.access()
    fn(body)
    return st.set_access(by, body, "test")


def bank_case(st, packs, who="A. Rivera"):
    cid = st.new_case(who, "Bank reconciliation")
    fill(st, cid, who, dict(packs["bank-reconciliation"].data["example"], prep=who), packs["bank-reconciliation"])
    return cid


def test_the_organization_names_levels_and_what_they_do(studio, packs):
    # a firm where reviewers may also start cases, and a new "QC lead" level that only releases
    edit(studio, lambda b: (b["levels"]["Reviewer"].append("start_case"), b["levels"].update({"QC lead": ["release", "see_all"]}),
                            b["people"].update({"Q. Lead": ["QC lead"]})))
    assert studio.can("D. Patel", "start_case")
    cid = bank_case(studio, packs)
    studio.submit("A. Rivera", cid)
    studio.approve("D. Patel", cid)
    with pytest.raises(Refused, match="does not let you approve"):
        studio.approve("Q. Lead", cid)
    assert studio.release("Q. Lead", cid)["status"] == "Released"


def test_taking_an_action_away_takes_it_away_everywhere(studio, packs):
    edit(studio, lambda b: b["levels"]["Preparer"].remove("record_exception"))
    cid = studio.new_case("A. Rivera", "Credit file review")
    fill(studio, cid, "A. Rivera", packs["credit-file-review"].data["example"], packs["credit-file-review"])
    with pytest.raises(Refused, match="does not let you record an exception.*Nobody"):
        studio.record_exception("A. Rivera", cid, "calc_dti", "Compensating strength documented", "x")


def test_rule_one_survives_any_grant(studio, packs):
    """Give a person every action there is: they still cannot review a case they entered work in."""
    from workpaper_studio.access import ACTIONS
    edit(studio, lambda b: (b["levels"].update({"Everything": list(ACTIONS)}), b["people"].update({"J. Moss": ["Everything"]})))
    cid = bank_case(studio, packs)
    studio.set("J. Moss", cid, "f/account", "Payroll ··9921")       # J. Moss enters one value in A. Rivera's case
    studio.submit("A. Rivera", cid)
    with pytest.raises(Refused, match="You entered work in this case, so you cannot review it"):
        studio.approve("J. Moss", cid)
    assert studio.approve("D. Patel", cid)["status"] == "Approved"


def test_a_second_person_for_limits_when_the_organization_asks(studio):
    edit(studio, lambda b: (b["rules"].update(two_person_limits=True), b["levels"]["Reviewer"].append("set_limits")))
    studio.confirm_limit("M. Okafor", "Bank reconciliation", "calc_rec", 5)
    pol = studio.policy()[1]["Bank reconciliation"]["calc_rec"]
    assert pol["confirmed"] is False and pol["proposed_by"] == "M. Okafor"
    with pytest.raises(Refused, match="You proposed this limit"):
        studio.confirm_limit("M. Okafor", "Bank reconciliation", "calc_rec", 5)
    studio.confirm_limit("D. Patel", "Bank reconciliation", "calc_rec", 5)
    pol = studio.policy()[1]["Bank reconciliation"]["calc_rec"]
    assert pol["confirmed"] is True and pol["by"] == "D. Patel" and pol["proposed_by"] == "M. Okafor"


def test_access_cannot_lock_everyone_out_or_name_nonsense(studio):
    with pytest.raises(Refused, match="Nobody would be left able to change access"):
        edit(studio, lambda b: b["levels"]["Admin"].remove("manage_access"))
    with pytest.raises(Refused, match="does not exist"):
        edit(studio, lambda b: b["people"].update({"X": ["Wizard"]}))
    with pytest.raises(Refused, match="does not let you change levels"):
        edit(studio, lambda b: None, by="A. Rivera")


def test_access_changes_are_versioned_and_cannot_be_rewritten(studio):
    v = edit(studio, lambda b: b["people"].update({"N. New": ["Preparer"]}))
    assert studio.access()[0] == v and "N. New" in studio.users
    assert studio.access_history()[0]["by"] == "M. Okafor"
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sqlite3.connect(studio.db_path).execute("DELETE FROM access")
