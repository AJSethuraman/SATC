#!/usr/bin/env python3
"""Does the website still match the fee schedule?

A number on satcllp.com is a commitment, and the estimate a client gets later
has to agree with it. That is the specific cost of publishing prices, and this
script is how it gets paid:

    cd website && python3 pricing.spec.py

It reads client-documents/registry/fee-schedule.yaml and website/pricing-config.js
and fails if they have drifted apart, if something the schedule withholds has
reached the page, or if a price is published without what it covers.

No web framework, no browser, same shape as intake.spec.py. Run it before
merging any change to either file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEDULE = HERE.parent / "client-documents" / "registry" / "fee-schedule.yaml"
CONFIG = HERE / "pricing-config.js"
PAGE = HERE / "pricing.html"

checks: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    checks.append((bool(ok), label))


# ── load both sides ───────────────────────────────────────────────────────

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is needed: pip install pyyaml")

sched = yaml.safe_load(SCHEDULE.read_text(encoding="utf-8"))
config_src = CONFIG.read_text(encoding="utf-8")
page_src = PAGE.read_text(encoding="utf-8")

# The config is a JS assignment of one object literal. Strip the wrapper and the
# comments, quote the keys, and it is JSON. Fragile in principle; in practice the
# file is written to stay parseable and this check is why it must.
body = config_src.split("window.SATC_PRICING", 1)[1].split("=", 1)[1].strip().rstrip(";")
body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
body = re.sub(r"//[^\n]*", "", body)
body = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
body = re.sub(r",(\s*[}\]])", r"\1", body)
body = body.replace("'", '"')
try:
    cfg = json.loads(body)
except json.JSONDecodeError as e:
    sys.exit(f"pricing-config.js no longer parses as data: {e}\nKeep it a plain object literal.")

tiers = sched["base"]["1040"]["tiers"]
units = sched["per_unit"]


# ── 1 · every published package price matches the schedule ────────────────

for pkg in cfg["packages"]:
    tier = tiers.get(pkg["id"])
    check(tier is not None, f"package {pkg['id']!r} exists in the schedule")
    if tier:
        check(tier["amount"] == pkg["price"],
              f"{pkg['name']}: page says ${pkg['price']}, schedule says ${tier['amount']}")

check([p["id"] for p in cfg["packages"]] == ["starter", "essentials", "standard", "business"],
      "packages are published cheapest to dearest, in the schedule's own order")

prices = [p["price"] for p in cfg["packages"]]
check(prices == sorted(prices), "prices ascend down the page")


# ── 2 · every published extra matches the schedule ────────────────────────
#
# Keyed by the schedule path each figure comes from, so a renamed label does not
# quietly detach a price from its source.

EXTRA_SOURCES = {
    "Each state return after the first": units["state_return"]["amount"],
    "Each local return after the first": units["local_return"]["amount"],
    "Rental schedule, covering up to three properties": units["rental"]["form_fee"],
    "Each rental property past those three": units["rental"]["amount"],
    "Each K&#8209;1 past the two Standard covers": units["k1"]["amount"],
    "Each brokerage statement after the first": units["brokerage"]["amount"],
    "Each brokerage statement we have to key in by hand": units["brokerage_keyed"]["amount"],
    "Each additional gig Schedule C": units["schedule_c"]["tiers"]["simple"]["amount"],
    "Each additional full Schedule C": units["schedule_c"]["tiers"]["standard"]["amount"],
    "Each foreign account, capped at four": units["foreign_account"]["amount"],
    "Earned income credit, with the due diligence it needs":
        sched["per_form"]["forms"]["earned_income_credit"]["amount"],
    "Any one of the situations below": sched["per_form"]["amount"],
}

published = {x["label"]: x["amount"] for x in cfg["extras"]}
check(set(published) == set(EXTRA_SOURCES),
      "every published extra is one this script knows the source of "
      f"(unsourced: {sorted(set(published) - set(EXTRA_SOURCES))})")
for label, expected in EXTRA_SOURCES.items():
    if label in published:
        check(published[label] == expected,
              f"{label!r}: page says ${published[label]}, schedule says ${expected}")

check(units["rental"]["form_covers"] == 3,
      "the rental schedule still covers three properties, as the page says")
check(units["foreign_account"]["cap_units"] == 4,
      "foreign accounts are still capped at four, as the page says")


# ── 3 · the withheld figures have not reached the page ────────────────────
#
# Each of these is a real charge the firm made a decision NOT to publish. A
# number appearing here is the failure this whole script exists to catch.

WITHHELD = {
    # what it is                     the amount    words that would give it away
    "the farm schedule":            (units["farm"]["amount"], ("farm", "schedule f")),
    "the records-sorting fee":      (units["records_sorting"]["amount"], ("sorting", "unsorted")),
    "the K-1 issued per owner":     (units["owner_k1"]["amount"], ("per owner", "issued")),
}

# Only the DATA counts, not the comments — pricing-config.js names each withheld
# item precisely so a later editor knows not to add it, and that must not read
# as a leak.
published_labels = " ".join(
    [x["label"] for x in cfg["extras"]]
    + [p["name"] + " " + p["who"] + " " + " ".join(p["covers"]) for p in cfg["packages"]]
    + cfg["situations"] + cfg["hourlyApplies"]
).lower()

for what, (amount, giveaways) in WITHHELD.items():
    # An amount match alone is not evidence — $200 is both the farm schedule and
    # the full Schedule C. It is an amount published under a naming label that
    # would be the leak.
    named = [g for g in giveaways if g in published_labels]
    check(not named, f"{what} (${amount}) has not been published — found {named}")

for word in ("farm", "Schedule F", "records sorting", "sorting"):
    check(word.lower() not in page_src.lower(),
          f"the page does not mention {word!r} — priced, taken, never advertised")

for figure in (sched["base"]["1065"], sched["base"]["1120S"], sched["base"]["1120"]):
    check(f"${figure}" not in page_src and str(figure) not in config_src,
          f"no entity return figure (${figure}) appears on the page")

check("quoted after a conversation" in page_src,
      "entity returns get the sentence rather than a gap the visitor fills in")


# ── 4 · the rules that make a price readable ──────────────────────────────

check(sched["base_covers"] == "one_included",
      "the schedule still includes the first state and locality in the base")
for word in ("federal", "first state", "first local"):
    check(word in cfg["includedInEvery"].lower(),
          f"the load-bearing sentence still names the {word} return")

check(all(p.get("covers") for p in cfg["packages"]),
      "no package is published as a bare number — every one says what it covers")

check(cfg["minimum"]["amount"] == 200 and cfg["minimum"]["exceptionId"] == "starter",
      "the $200 minimum is published with its one exception attached")

check(cfg["hourly"]["rate"] == sched["basis"]["rate"],
      f"hourly rate matches the schedule (${sched['basis']['rate']})")
check(sched["basis"]["round_time_to"] == 0.25,
      "still billed to the quarter hour, as the page says")

check("[CONFIRM:" not in config_src and "[CONFIRM:" not in page_src,
      "no undecided value reached the page")


# ── 5 · the page renders what the config holds ────────────────────────────

for element in ("tiers", "included", "extras", "sits", "hourly", "hourlyApplies",
                "sumSelect", "sumMin"):
    check(f'id="{element}"' in page_src, f"the page has a mount point for {element}")

check("pricing-config.js" in page_src, "the page loads the config it renders from")
for pkg in cfg["packages"]:
    # Word-boundary, so the "Businesses" section heading — which is about entity
    # returns, not about the package — is not mistaken for a hardcoded name.
    hits = re.findall(rf"\b{re.escape(pkg['name'])}\b", page_src)
    check(not hits,
          f"{pkg['name']!r} is not hardcoded in the markup — names must stay data")


# ── report ────────────────────────────────────────────────────────────────

failed = [label for ok, label in checks if not ok]
for ok, label in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("\nThe site and the fee schedule disagree. The schedule wins — fix the page.")
    sys.exit(1)
print("The published prices match the fee schedule.")
