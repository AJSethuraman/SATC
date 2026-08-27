#!/usr/bin/env python3
"""Drive the whole process, for real, across every scenario — and say what broke.

    python exercise.py --out ../out/exercise

THIS IS NOT THE TEST SUITE, and it is not a second one. `pytest` asserts
PROPERTIES: that a total equals its parts, that two documents agree, that a
holed record refuses. It never produces anything anybody looks at, and it
never touches the front doors a preparer actually uses.

This runs the process. Every scenario goes through `intake.finish` and comes
out as real documents on disk, through the same `package`, `invoice` and
`render` paths a preparer drives. Then it reports, per scenario and per
document, what was produced and what refused.

The firm, 27 August 2026: *"when i say scenario test i mean literally it tries
everything, and not just smoke tests or whatever. like you try and produce it
all as you go and debug it ... i will eventually want operating procedures and
stuff so it's integral everything works and can be demonstrated."*

That last word is the point. A procedure nobody has run end to end is a guess
written down. This is what makes one demonstrable: run it, read the output,
and the report is the evidence.

WHAT IT DOES NOT DO. It does not assert. A refusal is not a failure here --
several are correct, and the report says which. Reading the report is the
work; that is deliberate, because the class of bug this project keeps
producing is software saying something is fine when it is not, and only a
person looking at the output catches that.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import cli                       # noqa: E402
import engagements               # noqa: E402
import intake                    # noqa: E402
import invoicing                 # noqa: E402
import merge                     # noqa: E402
import packaging                 # noqa: E402
import presend                   # noqa: E402
import schedules as sched        # noqa: E402
import settings as firm          # noqa: E402


# ── the people ────────────────────────────────────────────────────────────
#
# INVENTED, every one. `CLAUDE.md` is explicit that the leads workbook is real
# prospect data and never leaves the machine; nothing here is read from it.
INDIVIDUAL = {
    # Required since the change questions landed: a first-year client is
    # not asked what changed, because nothing did.
    "returning_client": "no",
    "return_basis": "original", "tax_year": "2026",
    "client_full_name": "Marcus Ellwood", "client_address1": "31 Larchmere Road",
    "client_city": "Solon", "client_state": "OH", "client_zip": "44139",
    "client_email": "mellwood@example.com",
    "joint_return": "no", "taxpayer_name": "Marcus Ellwood",
    "states": ["Ohio"], "localities": ["Solon"],
    "other_income_documents": "no", "has_dependents": "no",
    "additional_forms": [], "count_states": 1, "count_localities": 1,
    "first_deliverable_target": "April 8, 2027",
    "prior_firm": "no", "prior_return_available": "no",
    "red_flags": [], "decision": "yes", "notes": "",
}

ENTITY = {
    # Required since the change questions landed: a first-year client is
    # not asked what changed, because nothing did.
    "returning_client": "no",
    "return_basis": "original", "tax_year": "2026",
    "client_full_name": "Northbank Tooling LLC", "client_address1": "12 Forge Way",
    "client_city": "Solon", "client_state": "OH", "client_zip": "44139",
    "client_email": "office@example.com",
    "entity_structure": "llc", "entity_state": "Ohio",
    "signer_name": "R. Halloway", "signer_title": "Managing Member",
    "states": ["Ohio"], "localities": ["Solon"],
    "other_income_documents": "no", "has_dependents": "no",
    "additional_forms": [], "count_states": 1, "count_localities": 1,
    "first_deliverable_target": "April 8, 2027",
    "prior_firm": "no", "prior_return_available": "no",
    "red_flags": [], "decision": "yes", "notes": "",
}


def individual(**over):
    return {**INDIVIDUAL, "federal_form": "1040", **over}


def entity(form, **over):
    base = {**ENTITY, "federal_form": form, **over}
    if form in ("1120S", "1065"):
        base.setdefault("k1_target", "each owner's personal return")
        base.setdefault("count_owners", 3)
        base.setdefault("owner_returns", "no")
    return base


@dataclass
class Scenario:
    key: str
    what: str            # what a person would call this client
    answers: dict
    expect: str = "engagement"     # or "refused" / "declined"
    note: str = ""


def scenarios() -> list[Scenario]:
    """Every shape the process is supposed to handle, named as a person would.

    Written out rather than generated, because a generated matrix produces
    combinations nobody will ever file and hides the ones that matter in the
    noise. Each of these is a client the firm could actually take on.
    """
    S: list[Scenario] = []
    add = S.append

    # ── the four individual rungs, each at its own gate ──────────────────
    add(Scenario("ind-simple", "W-2 only, standard deduction",
                 individual(return_features=[])))
    add(Scenario("ind-essentials", "Wages, interest and dividends",
                 individual(return_features=["investments"], count_brokerages=1)))
    add(Scenario("ind-standard", "Itemizes, one brokerage, two K-1s",
                 individual(return_features=["itemizing", "investments", "k1"],
                            count_brokerages=1, count_k1s=2)))
    add(Scenario("ind-selfemp", "Runs a business, actual expenses",
                 individual(return_features=["self_employment"],
                            schedule_c_kind="standard", count_businesses=1)))

    # ── the boundaries, which is where prices go wrong ───────────────────
    add(Scenario("ind-rentals-3", "Three rentals — at the form fee",
                 individual(return_features=["rentals"], count_rentals=3)))
    add(Scenario("ind-rentals-4", "Four rentals — one past it",
                 individual(return_features=["rentals"], count_rentals=4)))
    add(Scenario("ind-foreign-4", "Four foreign accounts — at the soft cap",
                 individual(return_features=[], count_foreign_accounts=4)))
    add(Scenario("ind-foreign-5", "Five foreign accounts — past the cap, hourly",
                 individual(return_features=[], count_foreign_accounts=5)))
    add(Scenario("ind-brokerage-2", "Two brokerages — one inside the package",
                 individual(return_features=["investments"], count_brokerages=2)))
    add(Scenario("ind-k1-3", "Three K-1s — one past the allowance",
                 individual(return_features=["k1"], count_k1s=3)))
    add(Scenario("ind-gig", "Gig work, standard mileage",
                 individual(return_features=["self_employment"],
                            schedule_c_kind="simple", count_businesses=1)))
    add(Scenario("ind-farm", "A farm",
                 individual(return_features=["farm"], count_farms=1)))

    # ── the shapes that change the package, not just the price ───────────
    add(Scenario("ind-joint", "Married filing jointly",
                 individual(return_features=["itemizing"], joint_return="yes",
                            taxpayer_name="Marcus Ellwood", spouse_name="Dana Ellwood")))
    add(Scenario("ind-multistate", "Three states, three localities",
                 individual(return_features=[], states=["Ohio", "Michigan", "Indiana"],
                            localities=["Solon", "Ann Arbor", "Gary"],
                            count_states=3, count_localities=3)))
    add(Scenario("ind-prior-firm", "Came from another accountant",
                 individual(return_features=[], prior_firm="yes",
                            prior_firm_name="Vance & Co CPAs",
                            prior_return_available="yes"),
                 note="the records release should be IN the pack"))
    add(Scenario("ind-dependents", "Has dependents",
                 individual(return_features=[], has_dependents="yes")))
    add(Scenario("ind-extension", "Needs an extension with a payment",
                 individual(return_features=[], count_extension_estimates=1)))
    add(Scenario("ind-sorting", "Arrived as a shoebox",
                 individual(return_features=[], count_sorting=1, sorting_amount=175)))

    # ── amendments, all three reasons ────────────────────────────────────
    for why, label in (("our_error", "our mistake"),
                       ("new_information", "a late K-1"),
                       ("other_preparer", "someone else filed it")):
        add(Scenario(f"amend-{why}", f"Amended return — {label}",
                     individual(return_features=[], return_basis="amended",
                                amendment_reason=why)))

    # ── the entities ─────────────────────────────────────────────────────
    add(Scenario("ent-1065", "Partnership, we do the owners too",
                 entity("1065", owner_returns="yes")))
    add(Scenario("ent-1120S", "S corporation, owners elsewhere",
                 entity("1120S", entity_structure="corporation",
                        signer_title="President", owner_returns="no")))
    add(Scenario("ent-1120", "C corporation",
                 entity("1120", entity_structure="corporation",
                        signer_title="President", owner_returns="no"),
                 note="its own letter since 26 Aug; refused entirely before that"))
    add(Scenario("ent-1065-many", "Partnership with seven owners",
                 entity("1065", count_owners=7, owner_returns="yes")))

    # ── the ones that must NOT produce an engagement ─────────────────────
    add(Scenario("refuse-assurance", "Wants an audit",
                 individual(return_features=[], red_flags=["assurance_needed"]),
                 expect="refused", note="work the firm does not take"))
    add(Scenario("declined", "Thinking about it",
                 individual(return_features=[], decision="thinking"),
                 expect="declined", note="no engagement, and nothing written"))

    # ── flagged, but taken ───────────────────────────────────────────────
    add(Scenario("flagged-tight", "Taken, with a tight deadline flagged",
                 individual(return_features=[], red_flags=["deadline_tight"])))
    add(Scenario("flagged-foreign", "Taken, foreign exposure flagged",
                 individual(return_features=[], red_flags=["foreign_exposure"],
                            count_foreign_accounts=2)))
    return S


@dataclass
class Result:
    key: str
    what: str
    note: str
    expect: str
    status: str = ""
    ref: str = ""
    total: str = ""
    lines: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    requests: list = field(default_factory=list)
    compared: list = field(default_factory=list)
    disagreements: list = field(default_factory=list)
    produced: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    surprises: list = field(default_factory=list)
    # NOT a surprise: the software behaved correctly and a
    # HUMAN owes a sentence. A harness that goes red on a
    # [CONFIRM: ] trains people to ignore it.
    blocked: list = field(default_factory=list)


# ── the rest of the client's life ────────────────────────────────────────
#
# THE OPENING PACK IS A THIRD OF THE PROCESS. Everything after it needs facts
# that do not exist when the engagement is created -- a signature deadline, an
# extended deadline, a date the engagement ended -- and a preparer supplies
# them at the moment they become true. An exercise that stops at onboarding
# has demonstrated onboarding, not the process.
#
# These are the values a preparer would type, and they are the ONLY invented
# figures in this file. Every price comes from the schedule.
LATER_FACTS = {
    "delivery-letter": {
        "SignatureDeadline": "April 10, 2027",
        "ReturnsDelivered": [
            {"Return": "Federal Form 1040", "Detail": "Refund of $312"},
            {"Return": "Ohio IT 1040", "Detail": "Balance due of $88"},
        ],
        "ActionList": [
            {"Action": "Sign the federal and Ohio e-file authorizations",
             "Detail": "Both spouses where the return is joint, by April 10, 2027"},
        ],
        "EFiled": True, "PaperFiled": False, "EstimatedPayments": False,
    },
    "extension-notice": {
        "ExtendedDeadline": "October 15, 2027",
        "PaymentDeadline": "April 15, 2027",
        "EstimatedPaymentAmount": "$450.00",
        "PaymentEnclosed": True, "NoPaymentRequired": False,
        "ExtendedReturns": [{"Return": "Federal Form 1040", "Detail": "Extended"}],
        "OutstandingItems": [{"Document": "Your brokerage statements",
                              "Detail": "All accounts, all four quarters"}],
    },
    "disengagement-letter": {
        "EffectiveDate": "June 30, 2027",
        "RecordsAvailableUntil": "September 30, 2027",
        # A PHRASE, NOT A TABLE. The FIELDS spec says so in as many words --
        # "a phrase, not a code, that names precisely what ends" -- and this
        # invented fact handed it a list of rows. `str()` rendered the Python
        # repr straight into the letter: "It covers [{'Item': '2026 federal
        # and Ohio returns', 'Status': 'Complete'}]". Found by opening the
        # letter; merge refuses it outright now.
        "ScopeEnded": "the preparation of your 2026 federal and Ohio "
                      "individual income tax returns",
        "OutstandingBalance": "$0.00",
        "ClientInitiated": True, "FirmInitiated": False,
        "AccountSettled": True, "BalanceOutstanding": False,
        "UpcomingDates": [{"What": "2027 federal return", "When": "April 15, 2028"}],
    },
}

LIFECYCLE = {
    "invoice": "the bill, after the work",
    "delivery-letter": "the returns going back",
    "extension-notice": "an extension, mid-season",
    "disengagement-letter": "the engagement ending",
}


def _unwritten(record: dict) -> list[str]:
    """The [CONFIRM: ] placeholders in this record, as short labels.

    Everything in the request registry prints on a client's letter, so what
    the firm asks a business to send is the firm's sentence to write, not
    mine. The placeholders are what the letter is waiting on.
    """
    import re
    out = []
    # ensure_ascii=False, or an em dash in the firm's own placeholder
    # comes back to them as \u2014 in the thing telling them what to write.
    for text in re.findall(r"\[CONFIRM:([^\]]*)\]",
                           json.dumps(record, ensure_ascii=False)):
        label = " ".join(text.split())[:74]
        if label and label not in out:
            out.append(label)
    return out


def run_one(s: Scenario, store: Path, out: Path) -> Result:
    r = Result(key=s.key, what=s.what, note=s.note, expect=s.expect)
    answers = sched.apply(dict(s.answers))
    try:
        outcome = intake.finish(answers, store=store)
    except Exception as exc:                              # noqa: BLE001
        r.status = "crashed"
        r.surprises.append(f"intake.finish raised {type(exc).__name__}: {exc}")
        return r
    r.status = outcome.status
    if outcome.status != "created":
        if s.expect == "engagement":
            r.surprises.append(f"expected an engagement, got {outcome.status}: "
                               f"{(outcome.reason or '')[:120]}")
        # a refusal must leave nothing behind
        if (store / (outcome.ref or "none")).exists():
            r.surprises.append("a refusal wrote an engagement directory anyway")
        return r
    if s.expect != "engagement":
        r.surprises.append(f"expected {s.expect}, but an engagement was created")

    r.ref = outcome.ref
    record = engagements.load(r.ref, store)
    r.total = str(record.get("EstimateTotal", ""))
    r.lines = [f"{i.get('Service','')} — {i.get('Detail','')} — {i.get('Amount','')}"
               for i in (record.get("LineItems") or [])]
    r.assumptions = [a.get("Text", "") for a in (record.get("Assumptions") or [])]
    r.requests = [q.get("Document", "") for q in (record.get("RequestList") or [])]

    # ── the opening pack, through the real command ───────────────────────
    pack = out / s.key
    rc = cli.main(["package", "--engagement", r.ref, "--store", str(store),
                   "--out", str(pack), "--no-pdf"])
    wanted = packaging.documents_for(record)
    if rc == 0:
        got = sorted(p.name for p in pack.glob("*.html"))
        r.produced += [f"pack/{n}" for n in got]
        if len(got) != len(wanted):
            r.surprises.append(f"pack wrote {len(got)} documents, expected "
                               f"{len(wanted)}: {wanted}")
    else:
        r.refused.append("the opening pack")
        # A [CONFIRM: ] is not a bug. It is the registry saying, out loud, that
        # a sentence a client will read has not been written yet -- and the
        # merge engine refusing rather than sending the placeholder. Counting
        # that as a surprise makes the harness permanently red on a state the
        # software is handling exactly right, and a permanently red harness is
        # one nobody reads.
        waiting = _unwritten(record)
        if waiting:
            r.blocked.append(
                "the opening pack cannot be produced until the firm writes: "
                + "; ".join(waiting))
        else:
            r.surprises.append(
                "the opening pack refused — a client cannot be onboarded")

    # ── DO THE DOCUMENTS AGREE WITH EACH OTHER? ─────────────────────────
    #
    # Producing them is half of it. `consistency.py` joins the pack six ways
    # -- one ref, one date, one scope, one deadline, a total that is the sum
    # of its lines, and nothing billed outside the scope -- and the first run
    # of this harness never asked. It caught a scenario of my own promising a
    # first deliverable five days BEFORE the date the same package told the
    # client to send their papers in.
    try:
        import consistency
        # `cli.build_record` FIRST. Without it the firm's own fields are
        # absent, most documents refuse to render, and `report` compares the
        # one or two that survived -- so the harness said "0 disagreements"
        # while checking almost nothing. A green report that is green because
        # it looked at nothing is worse than a red one.
        full = cli.build_record(record)
        rendered = consistency.render_package(
            full, cli.DOCUMENTS, cli.TEMPLATE_DIR, cli._required_lists(),
            cli._inverse_flags())
        r.compared = sorted(rendered)
        for row in consistency.report(full, rendered):
            if not row.ok:
                r.disagreements.append(f"{row.name}: {row.detail}")
    except Exception as exc:                              # noqa: BLE001
        r.surprises.append(f"consistency raised {type(exc).__name__}: {exc}")

    # ── the rest of the life, each on its own ────────────────────────────
    for doc, why in LIFECYCLE.items():
        if doc == "invoice":
            if cli.main(["invoice", "--engagement", r.ref, "--store", str(store),
                         "--billed", "2026 tax year"]) != 0:
                r.refused.append(f"{doc} ({why})")
                continue
        try:
            merged = {**firm.firm_fields("2026"), **engagements.load(r.ref, store)}
            merged.update(LATER_FACTS.get(doc, {}))
            if doc == "invoice":
                inv = invoicing.find(store, r.ref)
                if inv:
                    merged.update(inv)
            merge.render_file(cli.TEMPLATE_DIR / cli.DOCUMENTS[doc][0], merged)
            r.produced.append(doc)
        except merge.MergeError as exc:
            missing = str(exc).replace("&lt;&lt;", "<<").replace("&gt;&gt;", ">>")
            r.refused.append(f"{doc}: {missing[:90]}")
        except Exception as exc:                          # noqa: BLE001
            r.surprises.append(f"{doc} raised {type(exc).__name__}: {exc}")
    return r


def renders(paths: list[Path]) -> list[dict]:
    """Open each document in a browser and check it actually rendered.

    THE IMPLEMENTATION LIVES IN `presend`, NOT HERE. It used to live in both,
    and the two copies had already drifted: this one still waited on
    `networkidle`, which behind a proxy meant waiting on the Google Fonts CDN
    for about thirteen seconds per document -- for a font FILE that neither
    check needs, since both read the computed family from the pack's own
    stylesheet. Two copies of a gate is two gates, and only one of them gets
    fixed.

    The shape is kept because the harness prints these as `{file, why}`.
    """
    return [{"file": f.document, "why": f.detail} for f in presend.renders(paths)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # DEFAULTS INSIDE client-documents, where `out/` is already gitignored.
    # The first run of this wrote to the REPO ROOT's out/, which is not --
    # rendered client letters, one `git add -A` from being committed. That is
    # the same failure `test_the_template_directory_holds_only_templates`
    # exists to catch, and this harness produces a hundred of them at a time.
    ap.add_argument("--out", default=str(ROOT / "out" / "exercise"),
                    help="where the documents go. Keep it inside an ignored "
                         "directory: everything written here is client-shaped.")
    ap.add_argument("--only", help="run one scenario by key")
    args = ap.parse_args(argv)

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    store = out / "_engagements"
    store.mkdir()

    todo = [s for s in scenarios() if not args.only or s.key == args.only]
    results = []
    for s in todo:
        try:
            results.append(run_one(s, store, out))
        except Exception:                                 # noqa: BLE001
            r = Result(key=s.key, what=s.what, note=s.note, expect=s.expect,
                       status="crashed")
            r.surprises.append(traceback.format_exc().strip().splitlines()[-1])
            results.append(r)

    # ── did any of it actually render? ──────────────────────────────────
    print("\nopening every document in a browser…")
    for r in results:
        pack = out / r.key
        if not pack.exists():
            continue
        broken = renders(sorted(pack.glob("*.html")))
        for b in broken:
            r.surprises.append(f"{b['file']}: {b['why']}")

    (out / "report.json").write_text(
        json.dumps([r.__dict__ for r in results], indent=2), encoding="utf-8")

    made = sum(len(r.produced) for r in results)
    refused = sum(len(r.refused) for r in results)
    surprises = [r for r in results if r.surprises or r.disagreements]
    blocked = [r for r in results if r.blocked and not r.surprises]
    print(f"\n{len(results)} scenarios · {made} documents produced · "
          f"{refused} refusals · {len(surprises)} with something unexpected"
          + (f" · {len(blocked)} waiting on the firm" if blocked else "") + "\n")
    for r in results:
        mark = "!!" if (r.surprises or r.disagreements) else "  "
        cmp = f"{len(r.compared)} cross-checked" if r.compared else ""
        print(f"{mark} {r.key:20} {r.status:10} {r.total:>10}  {cmp:16} {r.what}")
        for x in r.blocked:
            print(f"      WAITING ON THE FIRM: {x}")
        for x in r.surprises:
            print(f"      -> {x}")
        for x in r.disagreements:
            print(f"      DISAGREE: {x}")
        for x in r.refused:
            print(f"      refused: {x}")
    print(f"\nDocuments and report: {out}")
    return 1 if surprises else 0


if __name__ == "__main__":
    raise SystemExit(main())
