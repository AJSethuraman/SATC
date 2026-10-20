"""The re-issue email: built from two results summaries, signed only when the IRS says so.

The firm, 13 Oct 2026: "we should have a re-issue email template - it reminds
them to sign and pay if they have not already and explains what we changed ...
you can figure out what changed on results then you can summarize what we did".

These tests assert decisions and structure -- which branch, which figures, what
is refused -- never the firm's wording (DOCUMENT-TENETS T28). All data invented.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from email import message_from_bytes, policy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import reissue  # noqa: E402

SPEC = json.loads((ROOT / "samples" / "reissue-changes.json").read_text(encoding="utf-8"))


@pytest.fixture()
def record():
    return cli.build_record(json.loads((ROOT / "samples" / "tax-opening-package.json")
                                       .read_text(encoding="utf-8")))


def _spec(**over):
    s = copy.deepcopy(SPEC)
    s.update(over)
    return s


def _fed(result, amount, **figures):
    base = {"total_income": 100000, "agi": 95000, "total_tax": 8000, "withholding": 8200}
    base.update(figures)
    return {**base, "result": {"return": "Federal", "result": result, "amount": amount,
                               "method": "direct deposit", "account": "1111"}}


# ── the IRS rule, at its edges ──────────────────────────────────────────────

@pytest.mark.parametrize("figure,delta,needed", [
    ("total_income", 50, False), ("total_income", 51, True),
    ("agi", 50, False), ("agi", 50.01, True),
    ("total_tax", 14, False), ("total_tax", 15, True),
    ("withholding", 14, False), ("withholding", 14.01, True),
])
def test_pub_1345_thresholds_are_more_than_not_at_least(figure, delta, needed):
    before = _fed("refund", 200)
    after = _fed("refund", 200, **{figure: before[figure] + delta})
    assert reissue.needs_new_signature(before, after) is needed


@pytest.mark.parametrize("old,new,needed", [(200, 214, False), (200, 215, True), (200, 186, False)])
def test_the_refund_alone_can_decide(old, new, needed):
    assert reissue.needs_new_signature(_fed("refund", old), _fed("refund", new)) is needed


def test_a_refund_that_becomes_a_balance_needs_a_signature():
    assert reissue.needs_new_signature(_fed("refund", 10), _fed("balance", 10)) is False
    assert reissue.needs_new_signature(_fed("refund", 10), _fed("balance", 20)) is True


def test_a_big_refund_change_decides_without_the_other_figures():
    before = {"result": _fed("refund", 200)["result"]}
    after = {"result": _fed("refund", 500)["result"]}
    assert reissue.needs_new_signature(before, after) is True


def test_a_small_refund_change_with_a_missing_figure_refuses_to_guess():
    before = _fed("refund", 200)
    after = _fed("refund", 205)
    del after["agi"]
    with pytest.raises(reissue.ReissueError, match="agi"):
        reissue.needs_new_signature(before, after)


# ── building the email ──────────────────────────────────────────────────────

def _flags(fields, names):
    return [n for n in names if fields[n]]


OPENINGS = ("RaisedAndRight", "RaisedAndNotRight", "NotRaised")
SIGNING = ("ResignBoth", "ResignOne", "SignIfNotYetBoth", "SignIfNotYetOne")


def test_the_example_builds_the_sample_payload(record):
    """The FIELDS doc's example is what the engine produces."""
    sample = json.loads((ROOT / "samples" / "reissue-email.json").read_text(encoding="utf-8"))
    sample.pop("_comment")
    assert reissue.build(record, SPEC) == sample


@pytest.mark.parametrize("raised,right,expected", [
    ("the penalty question", True, "RaisedAndRight"),
    ("the penalty question", False, "RaisedAndNotRight"),
    ("", None, "NotRaised"),
])
def test_exactly_one_opening(record, raised, right, expected):
    spec = _spec(client_raised=raised)
    if right is None:
        spec.pop("client_was_right")
    else:
        spec["client_was_right"] = right
    assert _flags(reissue.build(record, spec), OPENINGS) == [expected]


@pytest.mark.parametrize("joint,resign,expected", [
    (True, True, "ResignBoth"), (False, True, "ResignOne"),
    (True, False, "SignIfNotYetBoth"), (False, False, "SignIfNotYetOne"),
])
def test_exactly_one_signing_branch(record, joint, resign, expected):
    record["JointReturn"] = joint
    spec = _spec()
    if not resign:                                  # a $5 federal change, figures unchanged
        spec["after"]["returns"][0]["amount"] = spec["before"]["returns"][0]["amount"] + 5
        spec["after"]["federal"] = dict(spec["before"]["federal"])
    assert _flags(reissue.build(record, spec), SIGNING) == [expected]


def test_a_changed_return_with_no_reason_is_refused(record):
    with pytest.raises(reissue.ReissueError, match="Federal"):
        reissue.build(record, _spec(reasons={}))


def test_nothing_changed_is_refused(record):
    spec = _spec(other_changes=[], freehand="")
    spec["after"] = copy.deepcopy(spec["before"])
    with pytest.raises(reissue.ReissueError, match="nothing changed"):
        reissue.build(record, spec)


def test_freehand_alone_is_enough(record):
    spec = _spec(other_changes=[], freehand="I re-ran the depreciation schedule.", client_raised="")
    spec.pop("client_was_right")
    spec["after"] = copy.deepcopy(spec["before"])
    fields = reissue.build(record, spec)
    assert fields["FreehandExplanation"] and not fields["ResultChanges"]
    assert _flags(fields, SIGNING) == ["SignIfNotYetBoth"]


def test_a_balance_needs_a_payee_and_a_date(record):
    spec = _spec()
    del spec["after"]["returns"][3]["pay_to"]
    with pytest.raises(reissue.ReissueError, match="pay_to"):
        reissue.build(record, spec)


def test_a_withdrawal_is_not_asked_for_as_a_check(record):
    spec = _spec()
    rita = spec["after"]["returns"][3]
    rita.update(method="EFW", account="4417")
    spec["reasons"]["RITA"] = "Now withdrawn rather than mailed."
    fields = reissue.build(record, spec)
    assert fields["ChecksDue"] == []
    assert fields["WithdrawalsDue"] == [{"Amount": "$85", "PayTo": "RITA",
                                         "DueDate": "October 15, 2027", "Account": "4417"}]


def test_a_method_only_change_shows_the_full_lines(record):
    spec = _spec()
    spec["after"]["returns"][1]["account"] = "9999"
    spec["reasons"]["Ohio"] = "The refund now goes to the new account."
    ohio = next(c for c in reissue.build(record, spec)["ResultChanges"] if c["Return"] == "Ohio")
    assert "4417" in ohio["Before"] and "9999" in ohio["After"]


def test_the_email_is_addressed_to_one_person(record):
    assert " " not in reissue.build(record, SPEC)["ContactFirstName"]


# ── the .eml ────────────────────────────────────────────────────────────────

def test_the_eml_is_an_unsent_draft_with_no_recipient_and_no_attachment(record):
    subject, html, plain = reissue.render(reissue.build(record, SPEC))
    raw = reissue.to_eml(subject, html, plain, sender="A <a@example.com>")
    msg = message_from_bytes(raw, policy=policy.default)
    assert msg["X-Unsent"] == "1"
    assert msg["To"] is None
    assert msg["Subject"] == subject and subject
    parts = [p.get_content_type() for p in msg.walk() if not p.is_multipart()]
    assert parts == ["text/plain", "text/html"]
    # Outlook mis-read an LF, quoted-printable file on 13 Oct 2026.
    assert b"\n" not in raw.replace(b"\r\n", b"") and b"quoted-printable" not in raw


def test_the_subject_is_not_left_in_the_body(record):
    subject, html, plain = reissue.render(reissue.build(record, SPEC))
    assert 'class="subject"' not in html
    assert not plain.startswith(subject)


def test_the_plain_text_carries_every_figure_and_no_markup(record):
    fields = reissue.build(record, SPEC)
    _, html, plain = reissue.render(fields)
    assert "<" not in plain and "&amp;" not in plain
    for line in fields["ReturnsDelivered"]:
        assert line["Detail"] in plain
    for change in fields["ResultChanges"]:
        assert change["Before"] in plain and change["After"] in plain
    assert plain.count("•") == len(fields["ReturnsDelivered"]) + len(fields["ResultChanges"]) \
        + len(fields["OtherChanges"]) + len(fields["ChecksDue"]) + 1   # +1: the signing ask


@pytest.mark.parametrize("resign", [True, False])
def test_exactly_one_signing_ask_reaches_the_client(record, resign):
    spec = _spec()
    if not resign:
        spec["after"]["returns"][0]["amount"] = spec["before"]["returns"][0]["amount"]
        spec["after"]["federal"] = dict(spec["before"]["federal"])
        spec["reasons"] = {}
    _, html, _ = reissue.render(reissue.build(record, spec))
    need = html.split("<ul>")[-1]                        # the What I need list
    assert len(re.findall(r"<li>", need)) == 1 + len(reissue.build(record, spec)["ChecksDue"])


def test_the_cli_writes_the_draft_into_a_temp_store(tmp_path):
    store = tmp_path / "store" / "2027-0114"
    store.mkdir(parents=True)
    (store / "record.json").write_text((ROOT / "samples" / "tax-opening-package.json")
                                       .read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "out" / "reissue.eml"
    rc = cli.main(["reissue", "--engagement", "2027-0114", "--store", str(tmp_path / "store"),
                   "--changes", str(ROOT / "samples" / "reissue-changes.json"), "--out", str(out)])
    assert rc == 0 and out.exists()


def test_the_cli_writes_nothing_when_it_refuses(tmp_path):
    store = tmp_path / "store" / "2027-0114"
    store.mkdir(parents=True)
    (store / "record.json").write_text((ROOT / "samples" / "tax-opening-package.json")
                                       .read_text(encoding="utf-8"), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_spec(reasons={})), encoding="utf-8")
    out = tmp_path / "out" / "reissue.eml"
    rc = cli.main(["reissue", "--engagement", "2027-0114", "--store", str(tmp_path / "store"),
                   "--changes", str(bad), "--out", str(out)])
    assert rc == 1 and not out.exists()
