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


def _strings(node):
    """Every string anywhere in the config — the copy, wherever it is nested."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


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

# The page groups the extras; most checks only care that a line exists at all.
cfg["extras"] = [r for g in cfg["extraGroups"] for r in g["rows"]]


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
check("'<i>from</i>' + money(e.amount)" in page_src,
      "entity amounts carry a visible 'from' — dropping it makes a floor a promise")
check("tier ent" in page_src or "' ent'" in page_src,
      "entity cards carry a modifier class, so they are never styled identically "
      "to the flat packages")

# The packages must NOT be from-prices, and the schedule agrees.
tiers = sched["base"]["1040"]["tiers"]
check(all(t.get("publish") == "yes" for t in tiers.values()),
      "the 1040 packages publish as flat prices, not from-prices")


# ── 5 · qualifications the page must not drop ─────────────────────────────
#
# These are the failures regeneration cannot catch, because the NUMBER is right
# and only the sentence beside it is missing.

# These test the MEANING, not a phrase. The wording is the firm's and changes;
# what may not change is that the qualification is still there.
WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

foreign = sched["per_unit"]["foreign_account"]
if foreign.get("cap_beyond") == "hourly":
    line = next((x for x in cfg["extras"] if "foreign" in x["label"].lower()), None)
    check(line is not None, "the foreign-account line is on the page")
    said = ((line or {}).get("label", "") + " " + (line or {}).get("detail", "")).lower()
    cap = foreign["cap_units"]
    check(str(cap) in said or WORD.get(cap, "\0") in said,
          "the foreign-account line says where the cap stops")
    check(("bill" in said and "time" in said) or "hour" in said,
          "the foreign-account line says the time past the cap is billed — the "
          "cap is SOFT, and naming it without that is a promise the firm is not making")

ext = next((x for x in cfg["extras"] if "extension" in (x["label"] + x["detail"]).lower()), None)
check(ext is not None, "the extension line is on the page")
if ext:
    said = (ext["label"] + " " + ext["detail"]).lower()
    check("free" in said,
          "the extension line says filing one is free — the fee is only for "
          "working out the payment, and a bare 'Extension, $75' says the opposite")

sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import importlib.util as _il
_spec = _il.spec_from_file_location("gen", GENERATOR)
_gen = _il.module_from_spec(_spec); _spec.loader.exec_module(_gen)
_AMEND_PUBLISHED = _gen.AMENDMENT_PUBLISH

# The firm's call, 26 Aug 2026: "literally do not specify stuff like we fix our
# own errors for free. we don't need to say that." It stays in the schedule and
# on a client's estimate; it does not go on a price page.
# Keyed off the schedule, not off the word "amend" appearing in a label — the
# label is the firm's copy and it changes.
amend_tiers = sched["amendment"]["tiers"]
_published_amend = {amend_tiers[t]["amount"] for t in _AMEND_PUBLISHED}
free_tier = next((t for t in amend_tiers.values() if t["amount"] == 0), None)
published_amounts = {r["amount"] for r in cfg["extras"]}
check(_published_amend <= published_amounts, "the amendment prices are published")
check(free_tier is not None and free_tier["amount"] not in published_amounts,
      "the no-charge correction of our own error is NOT published")
amend_rows = [r for r in cfg["extras"] if r["amount"] in _published_amend]
check("our error" not in page_src.lower() and "our error" not in config_src.lower()
      and "no charge" not in page_src.lower(),
      "the page makes no claim about correcting our own mistakes")
check(any(r.get("reprices") for r in amend_rows),
      "the amendment that also charges the return's own fee says so")

# Individuals and entities are priced on different principles, so they get a
# panel each rather than one list that blurs a flat price with a floor.
for tab, panel in (("tabInd", "panelInd"), ("tabBiz", "panelBiz")):
    check(f'id="{tab}"' in page_src and f'id="{panel}"' in page_src,
          f"the {tab}/{panel} pair exists")
check('role="tablist"' in page_src and page_src.count('role="tab"') == 2,
      "the switch is a real tablist, not two styled divs")
check('aria-controls="panelInd"' in page_src and 'aria-controls="panelBiz"' in page_src,
      "each tab names the panel it controls")
check("hidden = j !== i" in page_src,
      "panels start visible and JS hides one — with JS off every price still shows")
check(len(cfg["extraGroups"]) == 3,
      "the menu still has three panels — the layout places them explicitly "
      f"(found {len(cfg['extraGroups'])})")
# The entity cards carry no list now — a C corporation had nothing to put in
# one — so the band beneath them is the only place that says what gets added on
# top of a floor. It has to keep saying it.
lead = cfg["entityLead"].lower()
check(all(w in lead for w in ("owner", "balance sheet", "books")),
      "the businesses band still names what moves the number above the floor "
      f"— {cfg['entityLead']!r}")

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


# Every published line is worded for a client, not for the preparer. The
# generator holds that overlay; this is what stops a newly-published line from
# arriving with the schedule's internal label on it.
published_paths = {p for p, _ in pub["publish"]
                   if p.startswith("per_unit.") and p != "per_unit.schedule_c"}
covered = {p for p in _gen.EXTRA_COPY if p.startswith("per_unit.")}
withheld = {p for p, _ in pub["withhold"]}
check(not (published_paths - covered - withheld),
      "every published extra has client wording in EXTRA_COPY — missing "
      f"{sorted(published_paths - covered - withheld)}")
# Equality, not containment, and BOTH directions are reported. A surplus is as
# wrong as a shortfall: copy for a trigger the schedule has deleted is wording
# for a service the firm has stopped offering, and it will sit on the page
# advertising it. Reporting only the missing side printed "Missing []" on a
# failing check, which says a check failed and refuses to say why.
_hourly_missing = sorted(set(sched["assumed"]) - set(_gen.HOURLY_COPY))
_hourly_stale = sorted(set(_gen.HOURLY_COPY) - set(sched["assumed"]))
check(not _hourly_missing and not _hourly_stale,
      "every hourly trigger has client wording, and no more — the schedule's "
      "own text is a note to the preparer. "
      f"Missing copy: {_hourly_missing}. Copy for triggers the schedule no "
      f"longer has: {_hourly_stale}")


# ── 6 · the firm's positions on the page itself ───────────────────────────

# "just let the prices speak" — 26 Aug 2026. Checked precisely rather than by
# counting tags: the switch between Individuals and Businesses is a control and
# belongs there, so the test is that no PROSE block sits above the prices except
# the one-line lede.
above = page_src.split('class="tiers"')[0].split("<h1")[-1]
check('class="summary"' not in page_src, "the explanatory box is gone")
check(above.count("<p") <= 1,
      f"only the lede sits between the headline and the prices ({above.count('<p')} paragraphs found)")

# "i'm not personally a huge fan of shifting the blame to others."
COMPARATIVE = ("other firms", "other tax", "most tax sites", "most firms",
               "competitor", "elsewhere you", "cheaper than", "big box")
found = [w for w in COMPARATIVE if w in page_src.lower() or w in config_src.lower()]
check(not found, f"the page makes no claim about anyone else's pricing — found {found}")

# Strings rendered through textContent must not carry HTML entities — they
# print literally. Caught exactly that: "you&#39;ll see your own number".
for key in ("includedInEvery", "entityLead"):
    check("&#" not in cfg[key],
          f"{key} has no HTML entities — it renders as text, so they would print raw")


# ── the language a client would actually use ──────────────────────────────
#
# Added after this shipped and was rightly rejected:
#
#   "These are prices, not a quote. You get an estimate in writing with your own
#    lines on it, and the engagement letter governs the work."
#
# The firm's read: "i would never expect a client to understand what an
# engagement letter is inherently. 'governs the work' come on."
#
# The failure was mechanical, not stylistic. The pricing brief says "An estimate
# is not a quote. The engagement letter governs; the estimate accompanies it" —
# and that sentence was written for whoever BUILDS the page, not for a visitor.
# Transcribing a requirement is not writing copy. The requirement says what the
# page must be true about; the copy has to say it in words the reader brought
# with them.
#
# So: the words below are banned from anything a visitor reads. If the concept
# is genuinely needed, say the thing itself — "nothing begins until you've seen
# it and said yes" rather than "the engagement letter governs the work".
CONTRACT_WORDS = [
    "governs", "governed by", "engagement letter", "constitutes",
    "in accordance with", "pursuant", "herein", "thereof", "aforementioned",
    "accompanies", "at our discretion", "in the event that", "utilize",
    "commence", "deemed", "whereupon", "notwithstanding", "shall be",
]

# Only what a visitor reads: no CSS, no scripts, no source comments — a comment
# explaining why not to say "governs" must not itself trip the check.
visible = re.sub(r"<!--.*?-->", " ", page_src, flags=re.S)
visible = re.sub(r"<(script|style)\b.*?</\1>", " ", visible, flags=re.S | re.I)
# Close block elements into sentence boundaries first. Without this a card's
# bullets concatenate into one 30-word pseudo-sentence and the length check
# below fires on markup rather than on prose.
visible = re.sub(r"</(li|p|h[1-6]|div|section|td|th)>", ". ", visible, flags=re.I)
visible = re.sub(r"<[^>]+>", " ", visible)
visible += " " + ". ".join(str(v) for v in _strings(cfg))
visible = visible.lower()

found = [w for w in CONTRACT_WORDS if re.search(rf"\b{re.escape(w)}\b", visible)]
check(not found,
      "no contract-desk language in anything a client reads — found "
      f"{found}. Say the thing itself instead.")

# The register rule, stated by the firm: "public facing and internal are two
# different things ... things should sound way more simple to our clients than
# it does to us."
#
# The schedule's comments, this file, the briefs and the commit messages are all
# written to argue a case, and that is right for them. Client copy is not that,
# and the tell is length: a sentence that needs 30 words is usually one that
# was written to be complete rather than to be read. 28 is generous, and it is
# a floor on effort rather than a style — it only catches the ones that got away.
sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", visible)) if x.strip()]
long_ones = [x for x in sentences if len(x.split()) > 28]
check(not long_ones,
      "no client-facing sentence runs past 28 words — "
      f"{[x[:70] + '...' for x in long_ones]}")


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
              "entities", "entityLead", "hourly", "hourlyApplies"):
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
