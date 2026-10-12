"""peers.roster: the real roster loads as the spec describes it, and every
kind of bad roster is refused with a reason a person can act on."""
import copy
import json

import pytest

from conftest import ROOT
from threshold_engine.peers import roster

PEERS = ROOT / "config" / "peers.json"
REGIONALS = {"6548", "6384", "9846", "6672", "6560", "11063", "57957", "588", "12368", "2270"}


def test_the_real_roster():
    r = roster.load(PEERS)
    assert len(r) == 16
    assert roster.self_bank(r) == {"cert": "17534", "name": "KeyBank NA", "short": "KeyBank",
                                   "group": "self", "regional": False}
    assert len(roster.peers(r)) == 15
    assert "17534" not in {b["cert"] for b in roster.peers(r)}
    assert {b["cert"] for b in roster.regionals(r)} == REGIONALS
    assert [b["short"] for b in r][:2] == ["JPMorgan", "Wells Fargo"]     # file order kept


def write(tmp_path, doc):
    p = tmp_path / "peers.json"
    p.write_text(json.dumps(doc) if not isinstance(doc, str) else doc, encoding="utf-8")
    return p


def real():
    return json.loads(PEERS.read_text(encoding="utf-8"))


def changed(fn):
    doc = copy.deepcopy(real())
    fn(doc["banks"])
    return doc


BAD = [
    ("no self", changed(lambda b: b[8].update(group="peer")), "exactly one.*found 0"),
    ("two selves", changed(lambda b: b[0].update(group="self")), "exactly one.*found 2.*JPMorgan, KeyBank"),
    ("repeated cert", changed(lambda b: b[1].update(cert="628")), "cert '628' appears more than once"),
    ("repeated short", changed(lambda b: b[1].update(short="JPMorgan")), "short 'JPMorgan' appears more"),
    ("bad group", changed(lambda b: b[3].update(group="regional")), "group must be"),
    ("cert as a number", changed(lambda b: b[0].update(cert=628)), "cert must be"),
    ("cert not digits", changed(lambda b: b[0].update(cert="JPM")), "cert must be"),
    # A cert that can never equal a filed CERT: the bank would silently get no data.
    ("cert zero-padded", changed(lambda b: b[1].update(cert="0628")), "cert must be.*no leading zero"),
    ("cert zero", changed(lambda b: b[0].update(cert="0")), "cert must be"),
    ("cert superscript digit", changed(lambda b: b[0].update(cert="²")), "cert must be"),
    ("cert fullwidth digits", changed(lambda b: b[0].update(cert="６２８")), "cert must be"),
    ("empty short", changed(lambda b: b[2].update(short="  ")), "short must be non-empty"),
    ("bank not an object", changed(lambda b: b.__setitem__(4, "PNC")), "bank 5 .* is not an object"),
    ("regional as text", changed(lambda b: b[4].update(regional="yes")), "regional must be true or false"),
    ("missing key", changed(lambda b: b[2].pop("short")), "bank 3 .* has no short"),
    ("empty name", changed(lambda b: b[2].update(name=" ")), "name must be non-empty"),
    ("no banks", {"banks": []}, "no \"banks\" list"),
    ("not a roster", [1, 2], "no \"banks\" list"),
    ("not JSON", "{banks: ", "not valid JSON"),
]


@pytest.mark.parametrize("why,doc,reason", BAD, ids=[b[0] for b in BAD])
def test_a_bad_roster_is_refused_with_the_reason(tmp_path, why, doc, reason):
    with pytest.raises(ValueError, match=reason):
        roster.load(write(tmp_path, doc))


def test_whitespace_around_cert_name_and_short_is_trimmed(tmp_path):
    def pad(banks):
        banks[0].update(cert=" 628 ", name=" JPMorgan Chase Bank NA ", short=" JPMorgan ")
    r = roster.load(write(tmp_path, changed(pad)))
    assert (r[0]["cert"], r[0]["name"], r[0]["short"]) == ("628", "JPMorgan Chase Bank NA", "JPMorgan")


def test_regionals_never_include_the_bank_itself(tmp_path):
    r = roster.load(write(tmp_path, changed(lambda b: b[8].update(regional=True))))
    assert "17534" not in {b["cert"] for b in roster.regionals(r)}
