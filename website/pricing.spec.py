#!/usr/bin/env python3
"""Does the website still match the fee schedule?

    cd website && python3 pricing.spec.py

A number on satcllp.com is a commitment, and the estimate a client gets later
has to agree with it. That is the cost of publishing prices, and this is how it
gets paid.

The strongest check is the first one: `pricing-config.js` is GENERATED from
`client-documents/registry/fee-schedule.yaml`, so this regenerates it and fails
if the committed copy differs. That single check subsumes every "is this figure
right" question — a price cannot be stale, retyped or invented, only correct.

The rest are the things regeneration cannot catch: a withheld price reaching the
page anyway, a qualification the page drops, a page that shows a floor as if it
were a flat price, and the firm's positions on tone.

No browser and no server, so it runs in CI in a couple of seconds.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "client-documents"
CONFIG = HERE / "pricing-config.js"
PAGE = HERE / "pricing.html"
GENERATOR = HERE / "build-pricing-config.py"

sys.path.insert(0, str(ENGINE))

checks: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    checks.append((bool(ok), label))


try:
    import pricing
except ImportError as e:
    sys.exit(f"cannot import the pricing engine ({e}). Run from website/ with pyyaml installed.")

sched = pricing.load()
pub = pricing.publication(sched)
config_src = CONFIG.read_text(encoding="utf-8")
page_src = PAGE.read_text(encoding="utf-8")


# ── 1 · the config is what the generator would write today ────────────────
#
# Rule zero of the pricing brief: read the schedule, do not retype it. A static
# page cannot call Python, so it is generated instead — and this is what makes
# that real rather than a convention.

result = subprocess.run([sys.executable, str(GENERATOR), "--check"],
                        capture_output=True, text=True, cwd=HERE)
check(result.returncode == 0,
      "pricing-config.js is what the schedule generates today"
      + (f" — {result.stdout.strip() or result.stderr.strip()}" if result.returncode else ""))


# ── 2 · parse the config as data ──────────────────────────────────────────

body = config_src.split("window.SATC_PRICING", 1)[1].split("=", 1)[1].strip().rstrip(";")
body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
body = re.sub(r"//[^\n]*", "", body)
body = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', body)
body = re.sub(r",(\s*[}\]])", r"\1", body)
body = re.sub(r"\\'", "\x00", body).replace("'", '"').replace("\x00", "'")
try:
    cfg = json.loads(body)
except json.JSONDecodeError as e:
    sys.exit(f"pricing-config.js no longer parses as data: {e}")


# ── 3 · nothing withheld has reached the page ─────────────────────────────
#
# The schedule decides this, not the page. Each withheld line carries its own
# reason, and `publication()` raises on a line that declares nothing at all.

published_text = json.dumps(cfg, ensure_ascii=False).lower()
for path, line in pub["withhold"]:
    label = str(line.get("label", "")).lower()
    check(label not in published_text,
          f"withheld: {label!r} ({line.get('amount')}) is not on the page — "
          f"{str(line.get('publish_reason', ''))[:60]}")

for word in ("farm", "schedule f", "records sorting", "sorting"):
    check(word not in page_src.lower() and word not in published_text,
          f"the page does not mention {word!r}")

check("[CONFIRM:" not in config_src and "[CONFIRM:" not in page_src,
      "no undecided value reached the page")


# ── 4 · a floor is never shown as a flat price ────────────────────────────
#
# The four 1040 packages are gated on what is on the return, so the price a
# visitor reads is the price they get. An entity base is a floor with the
# balance sheet, the reconciliation and the owner K-1s on top. A bare $950 is
# read as a total.

from_amounts = {line["amount"] for _, line in pub["from"]}
check({e["amount"] for e in cfg["entities"]} == from_amounts,
      "every entity return the schedule marks `from` is on the page")
check(all(e.get("notes") for e in cfg["entities"]),
      "no entity price is published without the notes that say what 'from' means")
check(not (from_amounts & {p["price"] for p in cfg["packages"]}),
      "no package price collides with a from-price, which would blur the two")
check(page_src.count("<i>from</i>") == 0 or "e.amount" in page_src,
      "the 'from' marker renders per entity rather than being typed once")
check("<i>from</i>" in page_src,
      "entity amounts carry a visible 'from' — dropping it makes a floor a promise")

# The packages must NOT be from-prices, and the schedule agrees.
tiers = sched["base"]["1040"]["tiers"]
check(all(t.get("publish") == "yes" for t in tiers.values()),
      "the 1040 packages publish as flat prices, not from-prices")


# ── 5 · qualifications the page must not drop ─────────────────────────────
#
# These are the failures regeneration cannot catch, because the NUMBER is right
# and only the sentence beside it is missing.

foreign = sched["per_unit"]["foreign_account"]
if foreign.get("cap_beyond") == "hourly":
    line = next((x for x in cfg["extras"] if "foreign" in x["label"].lower()), None)
    check(line is not None, "the foreign-account line is on the page")
    detail = (line or {}).get("detail", "").lower()
    check(str(foreign["cap_units"]) in detail,
          "the foreign-account cap says where it stops")
    check("hour" in detail,
          "the foreign-account cap says the time past it is billed — the cap is "
          "SOFT, and 'capped at four' alone is a promise the firm is not making")

ext = next((x for x in cfg["extras"] if "extension" in x["label"].lower()), None)
if ext:
    check("computing" in ext["detail"].lower(),
          "the extension line says it is for computing the payment")
    # The schedule states it in a comment, not as data, so the page carries it
    # as copy: "THE FILING IS FREE. Only the computation is billed."
    check(re.search(r"[Ff]iling an extension is free", page_src) is not None,
          "the page says filing an extension is free — a bare 'Extension, $75' "
          "says the opposite of the decision")

check(any(a["amount"] == 0 for a in cfg["amendment"]),
      "correcting our own error is published as free — the strongest line on the page")
check(any(a.get("reprices") for a in cfg["amendment"]),
      "the amendment that also charges the return's own fee says so")

for word in ("federal", "first state", "first local"):
    check(word in cfg["includedInEvery"].lower(),
          f"the load-bearing sentence still names the {word} return")
check(all(p.get("covers") for p in cfg["packages"]),
      "no package is published as a bare number — every one says what it covers")
check("subject to change" in cfg["currentPrices"].lower(),
      "the page says the prices are for the upcoming tax year and subject to change")

hourly = sched["basis"]["rate"]
check(cfg["hourly"]["rate"] == hourly, f"hourly rate matches the schedule (${hourly})")
check(len(cfg["hourlyApplies"]) == len(sched["assumed"]),
      "every hourly trigger in the schedule is on the page")


# ── 6 · the firm's positions on the page itself ───────────────────────────

# "just let the prices speak" — 26 Aug 2026.
check("</div>" not in page_src.split('class="tiers"')[0].split("<h1")[-1],
      "no explanatory box sits between the headline and the prices")

# "i'm not personally a huge fan of shifting the blame to others."
COMPARATIVE = ("other firms", "other tax", "most tax sites", "most firms",
               "competitor", "elsewhere you", "cheaper than", "big box")
found = [w for w in COMPARATIVE if w in page_src.lower() or w in config_src.lower()]
check(not found, f"the page makes no claim about anyone else's pricing — found {found}")

# A US LLP filing US returns.
BRITISH = ("cancelled", "itemised", "recognise", "licence", "colour", "organis",
           "analyse", "centre", "grey", "whilst", "amongst", "practise", "defence",
           "summarised")
found = [w for w in BRITISH if w in (page_src + config_src).lower()]
check(not found, f"no British spellings in the published copy — found {found}")

# Names render from config so a rename stays a one-line change. One of the four
# has already been renamed once.
for pkg in cfg["packages"]:
    check(not re.findall(rf"\b{re.escape(pkg['name'])}\b", page_src),
          f"{pkg['name']!r} is not hardcoded in the markup — names must stay data")

for mount in ("tiers", "included", "current", "extras", "sits", "sitsHead",
              "amendment", "entities", "hourly", "hourlyApplies"):
    check(f'id="{mount}"' in page_src, f"the page has a mount point for {mount}")


# ── report ────────────────────────────────────────────────────────────────

failed = [label for ok, label in checks if not ok]
for ok, label in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("\nThe site and the fee schedule disagree. The schedule wins — fix the page.")
    sys.exit(1)
print("The published prices match the fee schedule.")
