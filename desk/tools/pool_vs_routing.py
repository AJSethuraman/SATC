"""The evidence `dec-order` asked for: does the pool beat the word list?

    `dec-order`, 9 September 2026 -- "Build the pool beside the desks; switch on
    evidence." So `dec-kill` is a decided destination and not an immediate
    demolition. The word-matching stays alive until the pool answers the same
    questions at least as well.

This prints that comparison and nothing else. It makes no claim: it runs both
mechanisms over the same questions and shows what each returned, so the switch
is decided on a measurement in the same way the kill was.

    cd desk && python tools/pool_vs_routing.py

EVERY QUESTION HERE WAS ACTUALLY ASKED. None is invented for this file, and that
is deliberate -- the last time a test in this repository was built from imagined
phrasings, the vocabulary was widened by nineteen words to satisfy sentences
nobody had ever typed and six plain bookkeeping questions started being answered
out of tax law. Each case below carries where it came from.

WHERE THE ONE CASE WITH A KNOWN RIGHT ANSWER COMES FROM. Forge-Occam's close on
9 September asked what is required before a payment with a vendor and no item is
a deductible business expense. Two desks escalated; `personal-or-business`
escalated `authority_absent` after two independent judges refused two different
citations, and reported that the authority it wanted was Pub. 583's
recordkeeping guidance, sitting on `cash-and-bank`. That is the target below.
There is exactly ONE such case, which is a thin denominator and is stated rather
than padded.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pool  # noqa: E402
import routing  # noqa: E402


DESKS = Path(__file__).resolve().parent.parent / "desks"

#: The authority Occam's desk said it needed, and the five phrasings they tried.
#: A hit is the pool placing this citation prefix anywhere in its top three.
TARGET = 'IRS Pub. 583'

SUBSTANTIATION = [
    # All five reported verbatim in Forge-Occam's field report, 9 Sep 2026.
    "what supporting documents does the client have to keep?",
    "what supporting documents must be kept?",
    "recordkeeping for business expenses",
    "what receipts do we need to keep?",
    "what records must be kept for a business expense?",
    # The two that worked for them, kept so a regression shows up here too.
    "supporting documents for a bank statement charge",
    "what kinds of records to keep for a bank account?",
]

#: The working vernacular, as measured on 10 September against `routing`.
#: Fifteen questions somebody types during a close. No known-right answer for
#: most of them -- what is being compared is whether ANYTHING is returned, and
#: silence from both mechanisms is a COVERAGE result, not a retrieval one.
WORKING = [
    "what records are required for a charge with only a vendor name?",
    "charge on the bank statement with no receipt or invoice - what records are required?",
    "we do not know what was bought - can we deduct it?",
    "the client took cash out of the ATM and we do not know what for",
    "is a payment to a credit card we have no statement for a business cost?",
    "unlabelled deposits into the business account - are they all revenue?",
    "the owner paid the company card from a personal account, what is that?",
    "a cheque with no payee on the feed - how do we book it?",
    "hand tools bought for the trade - deducted or capitalized?",
    "beer at a taproom with a customer - is it deductible?",
    "mileage or actual expenses for the van?",
    "cash back on the business card - income?",
    "what supporting documents does the client have to keep?",
    "the statement cycle closes on the 2nd, what is the opening balance at 1 January?",
    "groceries on the business card - business or personal?",
]

#: From `dec-kill` itself. The question that killed the word list, and the desk
#: it wrongly reached. Recorded so the pool's answer on it is visible -- NOT as
#: a pass/fail, because nothing in the corpus settles whether an unidentified
#: deposit is revenue. That is the hole `dec-coverage` is about.
THE_KILLING_QUESTION = "are unidentified deposits gross receipts?"


def _rule(title):
    print(f"\n{title}\n{'=' * len(title)}")


def main() -> int:
    held = pool.assemble(DESKS)
    known = pool.stats(held)
    registry = routing.registry(DESKS)

    print(f"pool: {len(held)} citations from {len(registry)} records "
          f"({sum(1 for h in held if h.text)} with stored text)")

    _rule("1 · The one case with a known right answer: Pub. 583 on records to keep")
    print(f"   {'phrasing':<58} {'word list':<28} pool top 3")
    routed_hits = pool_hits = 0
    for question in SUBSTANTIATION:
        desks = sorted(r.desk for r in routing.route(question, registry))
        found = pool.look(question, held, limit=3, known=known)
        got = [f.held.citation for f in found]
        # The word list can only ever name a DESK, so its hit is whether the desk
        # holding Pub. 583 was reached at all.
        routed = "cash-and-bank" in desks
        pooled = any(c.startswith(TARGET) for c in got)
        routed_hits += routed
        pool_hits += pooled
        where = ", ".join(desks) if desks else "-- nothing --"
        rank = next((i + 1 for i, c in enumerate(got)
                     if c.startswith(TARGET)), None)
        print(f"   {question[:56]:<58} {where[:26]:<28} "
              f"{'#' + str(rank) if rank else '-- not in top 3 --'}")
    print(f"\n   word list reached the holding desk: {routed_hits}/{len(SUBSTANTIATION)}")
    print(f"   pool placed the authority in top 3: {pool_hits}/{len(SUBSTANTIATION)}")

    _rule("2 · Does anything come back at all, on the working vernacular")
    silent_routing = silent_pool = 0
    for question in WORKING:
        desks = routing.route(question, registry)
        found = pool.look(question, held, limit=3, known=known)
        silent_routing += not desks
        silent_pool += not found
        top = found[0].held.citation if found else "-- nothing --"
        print(f"   {len(desks)} desk(s) | {top[:48]:<50} {question[:44]}")
    print(f"\n   word list returned nothing: {silent_routing}/{len(WORKING)}")
    print(f"   pool returned nothing:      {silent_pool}/{len(WORKING)}")
    print("   NOTE: returning something is not the same as returning the right "
          "thing.\n         Only section 1 has a known right answer.")

    _rule("3 · The question that killed the word list (dec-kill)")
    desks = sorted(r.desk for r in routing.route(THE_KILLING_QUESTION, registry))
    print(f"   {THE_KILLING_QUESTION!r}")
    print(f"   word list -> {', '.join(desks) if desks else '-- nothing --'}")
    print("   pool ->")
    for f in pool.look(THE_KILLING_QUESTION, held, limit=3, known=known):
        print(f"      {f.score:6.2f}  {f.held.citation[:56]:<56} [{f.held.read_from}]")
    print("   NEITHER IS RIGHT. Nothing on file settles whether an unidentified\n"
          "   deposit is revenue; that is a coverage hole, not a retrieval one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
