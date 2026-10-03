"""The world: who the clients are and what they will do, drawn once from the seed.

Everything random is drawn HERE, at t0, from one `random.Random(seed)`, and
written to `world.json`. The season that follows is then a script: the same
seed replays the same clients, the same arrival dates, the same silences.
Nothing downstream calls `random` again.

The names are obviously fake ("Testclient Alfa 001"), the emails are
`@example.invalid`, and nothing here is shaped like a taxpayer identifier --
client-documents' TIN guard (`tins.py`) would rightly refuse one.

Which requests a client's satc_system job opens is decided by the real
workflow when the owner generates it, so the world cannot know their ids in
advance. Instead each client carries an ARRIVAL PLAN keyed by the document
type the workflow opens. The doc types are the workflow's own
(`configs/workflows/*.yaml`); only the dates are the world's.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from season_sim.paths import PROJECT

NATO = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel",
        "India", "Juliett", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa",
        "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey",
        "Xray", "Yankee", "Zulu"]

FORM_OF = {
    "on_time": "1040", "late_docs": "1040", "goes_quiet": "1040",
    "missing_8879": "1040", "joint_spouse_missing": "1040", "extension": "1040",
    "k1_gated": "1040", "partnership": "1065", "scorp": "1120S", "ccorp": "1120",
    "disengages": "1040", "never_reengages": "1040", "amended": "1040",
    "requote": "1040", "rental": "1040",
}

# The satc_system workflow each federal form is prepared under. 1120 has none:
# `ENTITY_TYPE_BY_WORKFLOW` (satc/intake/fanout.py:117) carries no C
# corporation, and the simulator reports that rather than inventing one.
SATC_WORKFLOW = {"1040": "personal_1040_core", "1065": "business_partnership_tax",
                 "1120S": "business_scorp_tax"}
SATC_ENTITY = {"1040": "INDIVIDUAL", "1065": "PARTNERSHIP", "1120S": "SCORP",
               "1120": "CCORP"}


def load_scenario(path: Path | None = None) -> dict:
    return yaml.safe_load((path or PROJECT / "scenario.yaml").read_text(encoding="utf-8"))


def _d(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def next_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


@dataclass
class SimClient:
    sim_id: str
    idx: int
    archetype: str
    form: str
    name: str
    email: str
    joint: bool = False
    spouse: str = ""
    returning: bool = False
    prior_gap: bool = False
    pays_by: str = "card"
    features: dict = field(default_factory=dict)
    engage_on: str | None = None          # None: never re-engages for 2026
    letter_sign_lag: int | None = None
    arrival_plan: list = field(default_factory=list)   # [(offset|date|None|"k1")]
    sign_8879_lag: int | None = None
    spouse_8879_lag: int | None = None
    pay_lag: int | None = None
    pay_style: str = "full"               # full | late | never | part | over (the money stream)
    pay_lag2: int | None = None           # part payers: days from the bill to the balance
    disengage_on: str | None = None
    amended_on: str | None = None
    requote_on: str | None = None
    partnership: str | None = None        # k1_gated: the SIM id of the 1065
    k1_lag: int | None = None
    ref: str = ""
    prior_ref: str = ""
    amended_ref: str = ""
    satc_workflows: list = field(default_factory=list)

    @property
    def is_business(self) -> bool:
        return self.form != "1040"


@dataclass
class World:
    seed: int
    scenario_version: int
    billing_door: str
    clients: list[SimClient]
    notes: list[str] = field(default_factory=list)

    def by_id(self) -> dict[str, SimClient]:
        return {c.sim_id: c for c in self.clients}

    def restricted(self, keep: set[str]) -> "World":
        """This world, cut down to some clients and everything they depend on."""
        by = self.by_id()
        closure = set(keep)
        for sid in list(keep):
            c = by.get(sid)
            if c and c.partnership:
                closure.add(c.partnership)
            if c and c.archetype == "partnership":
                closure |= {x.sim_id for x in self.clients if x.partnership == sid}
        return World(seed=self.seed, scenario_version=self.scenario_version,
                     billing_door=self.billing_door,
                     clients=[c for c in self.clients if c.sim_id in closure],
                     notes=self.notes + [f"restricted to {sorted(closure)}"])

    def to_json(self) -> str:
        return json.dumps({"seed": self.seed, "scenario_version": self.scenario_version,
                           "billing_door": self.billing_door, "notes": self.notes,
                           "clients": [asdict(c) for c in self.clients]},
                          indent=1, sort_keys=True, default=str)

    @classmethod
    def from_json(cls, text: str) -> "World":
        raw = json.loads(text)
        return cls(seed=raw["seed"], scenario_version=raw["scenario_version"],
                   billing_door=raw["billing_door"], notes=raw.get("notes", []),
                   clients=[SimClient(**c) for c in raw["clients"]])


def _scaled_mix(mix: dict, n: int) -> list[str]:
    total = sum(mix.values())
    raw = {k: v * n / total for k, v in mix.items()}
    counts = {k: math.floor(v) for k, v in raw.items()}
    # Partnerships feed k1_gated clients: never scale them to zero while any
    # k1_gated client exists.
    left = n - sum(counts.values())
    for k in sorted(raw, key=lambda k: (-(raw[k] - counts[k]), k))[:left]:
        counts[k] += 1
    if counts.get("k1_gated") and not counts.get("partnership"):
        counts["partnership"] = 1
        biggest = max((k for k in counts if k not in ("partnership", "k1_gated")),
                      key=lambda k: (counts[k], k))
        counts[biggest] -= 1
    out: list[str] = []
    for k in sorted(counts):
        out += [k] * counts[k]
    return out


def _between(rng: random.Random, lo: date, hi: date) -> date:
    return lo + timedelta(days=rng.randint(0, (hi - lo).days))


def build(seed: int, *, scenario: dict | None = None, clients: int | None = None,
          billing_door: str | None = None) -> World:
    sc = scenario or load_scenario()
    rng = random.Random(seed)
    n = clients or int(sc["clients"])
    t = sc["timing"]
    tax_year = int(sc["season"]["tax_year"])

    door = billing_door or sc.get("billing_door", "auto")
    if door == "auto":
        door = "satc" if seed % 2 == 0 else "client_documents"

    kinds = _scaled_mix(sc["mix"], n)
    rng.shuffle(kinds)

    core_floor = _d(t["core_income_not_before"])
    out: list[SimClient] = []
    for i, arche in enumerate(kinds, start=1):
        form = FORM_OF[arche]
        nato = NATO[(i - 1) % len(NATO)]
        if form == "1040":
            name = f"Testclient {nato} {i:03d}"
        else:
            suffix = {"1065": "Partners LLC", "1120S": "Simco Inc", "1120": "Simcorp Inc"}[form]
            name = f"Simulated {nato} {i:03d} {suffix}"
        c = SimClient(sim_id=f"SIM-{i:03d}", idx=i, archetype=arche, form=form,
                      name=name, email=f"sim{i:03d}@example.invalid")
        c.ref = f"{tax_year + 1}-{i:04d}"

        if form == "1040":
            c.joint = arche == "joint_spouse_missing" or rng.random() < float(sc["joint_share"])
            if c.joint:
                c.spouse = f"Testspouse {nato} {i:03d}"
            c.returning = arche == "never_reengages" or rng.random() < float(sc["returning_share"])
            c.prior_gap = c.returning and rng.random() < float(sc["prior_gap_share"])
            c.features = {
                "brokerage": (not c.prior_gap) and rng.random() < 0.5,
                "k1": arche == "k1_gated",
                "retirement": rng.random() < 0.3,
                "marketplace": rng.random() < 0.15,
                "rental": arche == "rental",
            }
        c.pays_by = "check" if rng.random() < float(sc["check_payer_share"]) else "card"
        if c.returning:
            c.prior_ref = f"{tax_year}-{i:04d}"

        if arche == "never_reengages":
            c.engage_on = None
            out.append(c)
            continue

        window = t["entity_engage_window"] if c.is_business else t["engage_window"]
        engage = next_weekday(_between(rng, _d(window[0]), _d(window[1])))
        c.engage_on = engage.isoformat()
        c.letter_sign_lag = rng.randint(*t["letter_sign_lag_days"])

        # Up to twelve requests per client across its jobs; the plan is
        # consumed in the order the jobs' doc types sort. Each entry is an
        # absolute ISO date, "k1" (after the partnership's delivery) or None
        # (never arrives).
        plan = []
        for slot in range(12):
            if c.is_business:
                when = _between(rng, _d(t["entity_doc_window"][0]), _d(t["entity_doc_window"][1]))
                when = max(when, engage + timedelta(days=3))
            else:
                when = engage + timedelta(days=rng.randint(*t["doc_lag_days"]))
            if arche == "late_docs" and rng.random() < 0.7:
                when = _between(rng, _d(t["late_doc_window"][0]), _d(t["late_doc_window"][1]))
            plan.append(when.isoformat())
        if arche == "goes_quiet":
            plan = [p if rng.random() < float(t["quiet_share_sent"]) else None for p in plan]
            plan[0] = None                                  # never everything
        if arche == "extension":
            summer = _between(rng, _d(t["summer_doc_window"][0]), _d(t["summer_doc_window"][1]))
            plan[rng.randint(0, 2)] = summer.isoformat()
        if arche == "disengages":
            c.disengage_on = next_weekday(_between(
                rng, _d(t["disengage_window"][0]), _d(t["disengage_window"][1]))).isoformat()
            plan = [p if p and p < c.disengage_on else None for p in plan]
            plan[0] = None                                  # they leave with paper still out
        c.arrival_plan = plan
        c.features["core_income_not_before"] = core_floor.isoformat()

        if arche == "k1_gated":
            c.k1_lag = rng.randint(*t["k1_after_partnership_delivery_days"])
        lag = rng.randint(*t["sign_8879_lag_days"])
        c.sign_8879_lag = None if arche in ("missing_8879", "goes_quiet", "disengages") else lag
        if c.joint:
            c.spouse_8879_lag = None if arche == "joint_spouse_missing" else lag
        c.pay_lag = None if arche in ("goes_quiet", "disengages") else rng.randint(*t["pay_lag_days"])
        if arche == "amended":
            c.amended_on = next_weekday(_d(t["amended_opened"])).isoformat()
            c.amended_ref = f"{tax_year + 1}-{100 + i:04d}"
        if arche == "requote":
            c.requote_on = next_weekday(_between(
                rng, _d(t["requote_window"][0]), _d(t["requote_window"][1]))).isoformat()
            c.features["brokerage"] = True

        if form in SATC_WORKFLOW:
            wf = [SATC_WORKFLOW[form]]
            if arche == "rental":
                wf.append("personal_rental_schedule_e")
            if sc["owner"].get("onboarding_for_new_clients") and not c.returning:
                wf.append("new_client_onboarding")
            c.satc_workflows = wf
        out.append(c)

    # How each client pays, from its OWN stream: adding it changed no other draw.
    money = sc.get("money") or {}
    if money:
        mrng = random.Random(f"{seed}/money")
        late_lag = money["late_pay_lag_days"]
        for c in out:
            roll = mrng.random()
            if c.pay_lag is None:
                continue
            edges = [("late", float(money["late_payer_share"])),
                     ("never", float(money["never_pays_share"])),
                     ("part", float(money["part_payer_share"])),
                     ("over", float(money["overpayer_share"]))]
            acc = 0.0
            for style, share in edges:
                acc += share
                if roll < acc:
                    c.pay_style = style
                    break
            if c.pay_style == "late":
                c.pay_lag = mrng.randint(*late_lag)
            elif c.pay_style == "never":
                c.pay_lag = None
            elif c.pay_style == "part":
                c.pay_lag2 = mrng.randint(*late_lag)

    # Pair k1_gated returns with the partnerships the firm prepares.
    partnerships = [c for c in out if c.archetype == "partnership"]
    gated = [c for c in out if c.archetype == "k1_gated"]
    for j, c in enumerate(gated):
        if partnerships:
            c.partnership = partnerships[j % len(partnerships)].sim_id

    notes = [sc["label"], f"billing door: {door}"]
    return World(seed=seed, scenario_version=int(sc["version"]), billing_door=door,
                 clients=out, notes=notes)
