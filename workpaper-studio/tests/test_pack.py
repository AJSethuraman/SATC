"""A pack that is wrong refuses to load and says which file, where, and what to change."""
import json

import pytest

from workpaper_studio.pack import PackError, check, fingerprint, load
from conftest import PACKS


def mutate(tmp_path, fn, name="credit-file-review.json"):
    data = json.loads((PACKS / name).read_text())
    fn(data)
    p = tmp_path / name
    p.write_text(json.dumps(data, indent=1))
    return p


def test_the_three_packs_load(packs):
    assert {p.name for p in packs.values()} == {"Credit file review", "Control test", "Bank reconciliation"}


def test_unknown_key_is_refused_with_file_and_line(tmp_path):
    p = mutate(tmp_path, lambda d: d["tool"]["sections"][3]["blocks"][1].update(colour="red"))
    with pytest.raises(PackError) as e:
        load(p)
    assert e.value.file == "credit-file-review.json"
    assert "colour" in str(e.value) and "sections[3].blocks[1]" in str(e.value)
    line = p.read_text().splitlines()[e.value.line - 1]
    assert '"colour"' in line, (e.value.line, line)


def test_dangling_rule_field_is_refused(tmp_path):
    def f(d):
        d["tool"]["sections"][5]["blocks"][0]["rows"]["items"][-1]["when"]["field"] = "secrity"
    with pytest.raises(PackError, match="'secrity' is not a field"):
        load(mutate(tmp_path, f))


def test_a_section_switched_on_by_its_own_field_is_a_cycle(tmp_path):
    def f(d):
        s = d["tool"]["sections"][2]
        s["mode"], s["rule"] = "conditional", {"field": "hasexc", "values": ["Yes"]}
    with pytest.raises(PackError, match="cycle"):
        load(mutate(tmp_path, f, "control-test.json"))


def test_method_binding_to_a_missing_table_is_refused(tmp_path):
    def f(d):
        for s in d["tool"]["sections"]:
            for b in s["blocks"]:
                if b.get("method") == "dti":
                    b["inputs"]["debts"] = "loans"
    with pytest.raises(PackError, match="'loans' is not a table"):
        load(mutate(tmp_path, f))


def test_unknown_method_is_refused(tmp_path):
    def f(d):
        for s in d["tool"]["sections"]:
            for b in s["blocks"]:
                if b.get("method") == "recon":
                    b["method"] = "magic"
    with pytest.raises(PackError, match="not in the method library"):
        load(mutate(tmp_path, f, "bank-reconciliation.json"))


def test_list_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(PackError, match="no list called"):
        load(mutate(tmp_path, lambda d: d["tool"]["sections"][0]["blocks"][0].update(list="Nobody")))


def test_bad_json_names_the_line(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{\n "pack": {\n  "name": nope\n }\n}')
    with pytest.raises(PackError) as e:
        load(p)
    assert e.value.line == 3   # the bare word


def test_fingerprint_ignores_demo_data_but_not_the_tool(packs):
    d = json.loads(json.dumps(packs["credit-file-review"].data))
    f0 = fingerprint(d)
    d["example"]["borrower"] = "Someone else"
    assert fingerprint(d) == f0
    d["tool"]["sections"][0]["title"] = "Tester"
    assert fingerprint(d) != f0
