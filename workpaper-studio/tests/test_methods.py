"""The method library: vectors pass, every declared treatment is load-bearing, and no incomplete input ever yields a number."""
import copy
import random

import pytest

from workpaper_studio.methods import METHODS, vectors


def check(key, v, method=None):
    r = (method or METHODS[key]).run(copy.deepcopy(v["inputs"]))
    e = v["expect"]
    assert r.status == e["status"], v["name"]
    if e["value"] is None:
        assert r.value is None, v["name"]
    else:
        assert r.value == pytest.approx(e["value"], abs=1e-9), v["name"]
    assert r.parts.get("Inputs still missing", 0) == e["missing"], v["name"]
    if "disclosures" in e:
        assert len(r.disclosures) == e["disclosures"], v["name"]
    if "says" in e:   # the explanation is part of the result: "rejected" and "missing" block alike but say different things
        for said in ([e["says"]] if isinstance(e["says"], str) else e["says"]):
            assert said in " | ".join(r.missing + r.disclosures), (v["name"], r.missing, r.disclosures)


ALL = [(k, v) for k in METHODS for v in vectors(k)["vectors"]]


@pytest.mark.parametrize("key,v", ALL, ids=[f"{k}: {v['name']}" for k, v in ALL])
def test_vector(key, v):
    check(key, v)


@pytest.mark.parametrize("key", list(METHODS))
def test_every_state_treatment_is_load_bearing(key):
    """Change any single declared treatment and at least one of the method's own vectors must fail.
    A treatment no vector notices is a claim nobody checks."""
    m = METHODS[key]
    alternatives = ["block", "counts", "reject", "omit"]
    unnoticed = []
    for inp, table in m.treatment.items():
        for state, action in table.items():
            if state == "entered":
                continue
            for alt in alternatives:
                if alt == action:
                    continue
                mutant = copy.copy(m)
                mutant.treatment = copy.deepcopy(m.treatment)
                mutant.treatment[inp][state] = alt
                caught = False
                for v in vectors(key)["vectors"]:
                    try:
                        check(key, v, mutant)
                    except (AssertionError, TypeError, ValueError):
                        caught = True
                        break
                if not caught:
                    unnoticed.append(f"{inp}.{state}: {action} -> {alt}")
    # States an input can never be in, named: a table row is excluded but never "not applicable", a field is marked
    # not applicable but never excluded, and a test attribute is a word, never a number. Nothing else may go unnoticed.
    unreachable = {"dti": {"income.na", "debts.na", "proposed.excluded"}, "recon": {"items.na", "bank.excluded", "books.excluded"},
                   "devrate": {"attribute.na", "attribute.zero"}}[key]
    really = [u for u in unnoticed if u.split(":")[0] not in unreachable]
    assert not really, f"treatments no vector notices: {really}"


def test_key_treatments_are_caught_by_mutation():
    """The four that matter most, named: missing blocks, NA is rejected, excluded is omitted, zero counts."""
    for key, inp, state, alt in [("dti", "income", "missing", "counts"), ("dti", "proposed", "na", "counts"),
                                 ("dti", "income", "excluded", "counts"), ("dti", "debts", "zero", "block"),
                                 ("recon", "books", "na", "counts"), ("recon", "items", "excluded", "counts"),
                                 ("recon", "books", "missing", "counts")]:
        m = copy.copy(METHODS[key]); m.treatment = copy.deepcopy(m.treatment); m.treatment[inp][state] = alt
        failed = 0
        for v in vectors(key)["vectors"]:
            try:
                check(key, v, m)
            except (AssertionError, TypeError, ValueError):
                failed += 1
        assert failed, f"{key}.{inp}.{state} -> {alt} went unnoticed"


def gen_dti(rng):
    def cell(v):
        return rng.choice([v, v, v, "", 0])
    inc = [{"label": f"Income {i+1}", "source": rng.choice(["Salary", "", "Rent"]), "amount": cell(rng.randint(1, 9000)),
            "per": rng.choice(["Monthly", "Annual", ""]), "excluded": rng.random() < .1, "reason": "x"} for i in range(rng.randint(0, 4))]
    debts = [{"label": f"Debt {i+1}", "creditor": rng.choice(["Card", ""]), "payment": cell(rng.randint(1, 900)), "excluded": rng.random() < .1} for i in range(rng.randint(0, 3))]
    prop = rng.choice([{"state": "entered", "value": cell(rng.randint(1, 3000))}, {"state": "na", "reason": "r"}])
    return {"income": inc, "debts": debts, "proposed": prop}


def test_deterministic_and_never_a_number_when_incomplete():
    rng = random.Random(7)
    for _ in range(1000):
        x = gen_dti(rng)
        a, b = METHODS["dti"].run(copy.deepcopy(x)), METHODS["dti"].run(copy.deepcopy(x))
        assert (a.status, a.value, a.parts, a.missing) == (b.status, b.value, b.parts, b.missing)
        rev = copy.deepcopy(x); rev["income"].reverse(); rev["debts"].reverse()
        c = METHODS["dti"].run(rev)
        assert c.status == a.status and (a.value is None or c.value == pytest.approx(a.value))
        if a.missing and a.status != "no_result":
            assert a.value is None and a.status == "not_calculated"
            assert all(v is None for k, v in a.parts.items() if k != "Inputs still missing")
        if x["proposed"].get("state") == "na":
            assert a.value is None
