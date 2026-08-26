#!/usr/bin/env python3
"""Generate website/pricing-config.js from the fee schedule.

    cd website && python3 build-pricing-config.py

The pricing brief's rule zero is *read the schedule, do not retype it*. A static
site cannot call Python at request time, so it does the next best thing: every
figure, label, note and publish decision on the page is written here by machine
from `client-documents/registry/fee-schedule.yaml`, and `pricing.spec.py`
regenerates the file and fails if the committed copy differs. Retyping a price
is therefore not a thing anyone can do by accident.

What is NOT generated is the short site copy — the one-line "who is this" under
each package, and the bullets on its card. Those are the firm's wording, tuned
on the page rather than in the schedule, and they live in SITE_COPY below. They
carry no figures. The spec asserts SITE_COPY covers exactly the packages the
schedule publishes, so a new or renamed package cannot slip through with no copy.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "client-documents"))

import pricing  # noqa: E402

OUT = HERE / "pricing-config.js"

# ── the firm's page copy, by package id ───────────────────────────────────
#
# `who` is the line under the price. `covers` is the card's bullets, written
# cumulatively ("Everything in Standard") rather than repeating the whole list
# the schedule carries, because four cards that each restate the previous one
# do not fit side by side.
SITE_COPY = {
    "starter": {
        "who": "Just a W&#8209;2.",
        "covers": ["One or two W&#8209;2s", "The standard deduction", "Dependents",
                   "A 1098&#8209;T education credit for yourself"],
    },
    "essentials": {
        "who": "No schedules.",
        "covers": ["Wages, interest and dividends", "The standard deduction"],
    },
    "standard": {
        "who": "You have schedules.",
        "covers": ["Everything in Essentials", "Itemized deductions",
                   "One brokerage statement", "Up to two K&#8209;1s",
                   "A gig Schedule C, standard mileage"],
    },
    # Renamed from "Business" on 26 Aug 2026. It is a 1040 package, and the old
    # name invited an S-corp owner to buy a personal return — so the copy says
    # "you work for yourself", not "you run a business".
    "business": {
        "who": "You work for yourself.",
        "covers": ["Everything in Standard", "One full Schedule C",
                   "Actual expenses, a home office, depreciation, inventory or payroll"],
    },
}

# Extras, in the order they read best on the page. Every one must be in the
# schedule's publish list; the reverse is checked too, so a newly-published line
# cannot go unnoticed.
EXTRA_ORDER = [
    "per_unit.state_return", "per_unit.local_return", "per_unit.rental",
    "per_unit.k1", "per_unit.owner_k1",
    "per_unit.brokerage", "per_unit.brokerage_keyed",
    "per_unit.foreign_account", "per_unit.extension_estimate",
]

# British spellings in the schedule's own wording. The firm is a US LLP filing
# US returns. Fixed here rather than in the schedule, which is not this page's
# to edit.
RESPELL = {"summarised": "summarized", "Cancelled": "Canceled", "cancelled": "canceled"}

NBH = "&#8209;"  # non-breaking hyphen, so "K-1" never wraps


def clean(text: str) -> str:
    for british, american in RESPELL.items():
        text = text.replace(british, american)
    return text.replace("K-1", f"K{NBH}1").replace("W-2", f"W{NBH}2").replace("1098-T", f"1098{NBH}T")


def js(value) -> str:
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(js(v) for v in value) + "]"
    raise TypeError(value)


def build() -> str:
    sched = pricing.load()
    pub = pricing.publication(sched)
    by_path = {path: line for path, line in pub["publish"]}
    froms = {path: line for path, line in pub["from"]}
    rate = sched["basis"]["rate"]

    # ---- packages -------------------------------------------------------
    tiers = sched["base"]["1040"]["tiers"]
    order = [p for p in ("starter", "essentials", "standard", "business")]
    packages = []
    for tid in order:
        t = tiers[tid]
        copy = SITE_COPY[tid]
        packages.append({
            "id": tid, "name": t["label"], "price": t["amount"],
            "who": copy["who"], "covers": [clean(c) for c in copy["covers"]],
        })

    # ---- extras ---------------------------------------------------------
    extras = []
    for path in EXTRA_ORDER:
        line = by_path[path]
        label, detail, amount = line["label"], line.get("detail", ""), line["amount"]

        if path == "per_unit.rental":
            # The form fee covers three; the per-unit amount is each one after.
            detail = f"Covers {line['form_covers']}, then ${line['amount']} each"
            amount = line["form_fee"]
        if path == "per_unit.foreign_account" and line.get("cap_beyond") == "hourly":
            # A78 of the site brief: the cap is SOFT. Saying only "capped at
            # four" is a promise the firm is not making.
            detail = (f"Capped at {line['cap_units']} — past that the time is "
                      f"billed at ${rate} an hour")
        extras.append({"label": clean(label), "detail": clean(detail), "amount": amount})

    # Schedule C is two tiers under one line.
    for tid in ("simple", "standard"):
        t = sched["per_unit"]["schedule_c"]["tiers"][tid]
        extras.append({"label": clean(t["label"]), "detail": clean(t["detail"]),
                       "amount": t["amount"]})

    # ---- the six situations, one price ----------------------------------
    per_form = sched["per_form"]
    situations = [clean(f["label"]) for key, f in per_form["forms"].items()
                  if "amount" not in f and not f.get("when") and f.get("label")]
    situation_price = per_form["amount"]

    # ---- amendments -----------------------------------------------------
    # Three prices, because what decides it is whose work it is. `reprices`
    # means the return's own fee is charged on top.
    amendment = []
    for tid, t in sched["amendment"]["tiers"].items():
        amendment.append({
            "label": clean(t["label"]), "detail": clean(t["detail"]),
            "amount": t["amount"], "reprices": bool(t.get("reprices")),
        })

    # ---- entity returns, from prices with their notes -------------------
    entity_labels = {"base.1065": "Partnership — Form 1065",
                     "base.1120S": "S corporation — Form 1120-S",
                     "base.1120": "C corporation — Form 1120"}
    entities = []
    for path in ("base.1065", "base.1120S", "base.1120"):
        line = froms[path]
        entities.append({
            "label": clean(entity_labels[path]), "amount": line["amount"],
            "notes": [clean(n) for n in line["starting_note"]],
        })

    # ---- hourly ---------------------------------------------------------
    applies = [clean(a["trigger"][0].upper() + a["trigger"][1:])
               for a in sched["assumed"].values()]

    return render(packages, extras, situations, situation_price, amendment,
                  entities, rate, sched)


def render(packages, extras, situations, situation_price, amendment,
           entities, rate, sched) -> str:
    w = max(len(x["label"]) for x in extras)
    lines = [f"""/* SATC — pricing shown on the website.
   ===========================================================================
   GENERATED. Do not edit by hand.

       cd website && python3 build-pricing-config.py

   Every figure, label and note below is written from
   client-documents/registry/fee-schedule.yaml, which is the source of truth.
   pricing.spec.py regenerates this file and fails if the committed copy
   differs, so a price cannot be retyped, stale or invented.

   The short page copy — the line under each price and the card bullets — is
   the firm's wording and lives in SITE_COPY in the generator. It carries no
   figures.

   WITHHELD, and the schedule says why: the farm schedule (taken, never
   advertised — a published price is a solicitation) and the records-sorting
   fee (a floor a preparer sets on sight, not a price).
   =========================================================================== */

window.SATC_PRICING = {{

  /* Load-bearing: without it every per-item price below reads as double
     charging. */
  includedInEvery: 'Every package covers your federal return, plus your first state and first local return.',

  /* The firm's words, 26 August 2026. */
  currentPrices: 'These represent our pricing for the upcoming tax year and are subject to change.',

  /* Cheapest to dearest, which is also the order the engine considers them in.
     Names render from here: one of the four has already been renamed once. */
  packages: ["""]
    for i, p in enumerate(packages):
        lines.append("    {")
        lines.append(f"      id: {js(p['id'])},")
        lines.append(f"      name: {js(p['name'])},")
        lines.append(f"      price: {p['price']},")
        lines.append(f"      who: {js(p['who'])},")
        lines.append(f"      covers: [")
        for j, c in enumerate(p["covers"]):
            lines.append(f"        {js(c)}{',' if j < len(p['covers']) - 1 else ''}")
        lines.append("      ]")
        lines.append("    }" + ("," if i < len(packages) - 1 else ""))
    lines.append("  ],")
    lines.append("")
    lines.append("  /* Charged only past what the package already covers. */")
    lines.append("  extras: [")
    for i, x in enumerate(extras):
        pad = " " * (w - len(x["label"]))
        comma = "," if i < len(extras) - 1 else ""
        lines.append(f"    {{ label: {js(x['label'])},{pad} detail: {js(x['detail'])}, amount: {x['amount']} }}{comma}")
    lines.append("  ],")
    lines.append("")
    lines.append("  /* One price for any of them. All six are things that HAPPENED, so a reader")
    lines.append("     can tell in a second whether one applies. The assumption behind each is on")
    lines.append("     the client's own estimate, attached to a real engagement — not here. */")
    lines.append(f"  situationPrice: {situation_price},")
    lines.append("  situations: [")
    for i, s in enumerate(situations):
        lines.append(f"    {js(s)}{',' if i < len(situations) - 1 else ''}")
    lines.append("  ],")
    lines.append("")
    lines.append("  /* What decides an amendment's price is whose work it is, so there is no")
    lines.append("     single number to print. `reprices` means the return's own fee too. */")
    lines.append("  amendment: [")
    for i, a in enumerate(amendment):
        comma = "," if i < len(amendment) - 1 else ""
        lines.append(f"    {{ label: {js(a['label'])}, detail: {js(a['detail'])}, amount: {a['amount']}, reprices: {js(a['reprices'])} }}{comma}")
    lines.append("  ],")
    lines.append("")
    lines.append("  /* FROM prices, never bare numbers. The 1040 packages are gated on what is")
    lines.append("     on the return, so the price a visitor reads is the price they get. An")
    lines.append("     entity base is a floor — a bare $950 gets read as a total. Each number")
    lines.append("     carries the notes that sit beside it in the schedule. */")
    lines.append("  entities: [")
    for i, e in enumerate(entities):
        lines.append("    {")
        lines.append(f"      label: {js(e['label'])},")
        lines.append(f"      amount: {e['amount']},")
        lines.append("      notes: [")
        for j, n in enumerate(e["notes"]):
            lines.append(f"        {js(n)}{',' if j < len(e['notes']) - 1 else ''}")
        lines.append("      ]")
        lines.append("    }" + ("," if i < len(entities) - 1 else ""))
    lines.append("  ],")
    lines.append("")
    lines.append("  /* Hourly happens INSTEAD of the fixed price, not on top of it. */")
    lines.append(f"  hourly: {{ rate: {rate}, billedIn: {js('the quarter hour')}, "
                 f"minimum: {js(str(sched['basis']['minimum_increment']))} }},")
    lines.append("  hourlyApplies: [")
    applies = [f"{a['label']} — {a['trigger']}" for a in sched["assumed"].values()]
    for i, a in enumerate(applies):
        lines.append(f"    {js(clean(a))}{',' if i < len(applies) - 1 else ''}")
    lines.append("  ]")
    lines.append("};")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            sys.exit("pricing-config.js is out of date — run: python3 build-pricing-config.py")
        print("pricing-config.js matches the schedule")
    else:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.name} from the fee schedule")
