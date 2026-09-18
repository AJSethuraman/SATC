from __future__ import annotations

"""Deals (PRD §5.19–21): recorded, never enforced.

A deal rides in the action's ``deal`` slot, one per character per round. An
offer names one living character in the offerer's room (it is spoken, so it
has to be heard) and one of three terms:

  truce       rounds 1–6: neither attacks the other, from the round it is
              struck through ``rounds`` rounds
  share_item  an item id and a round: the offerer hands the item to the other
              by the end of that round
  escort      a room id and a round: both stand in that room at the end of
              some round no later than that one

An offer becomes ``offer_made`` with an id; an ``accept`` naming an open offer
made to the acceptor, the round after it was made or later, becomes
``deal_struck``; an offer not accepted by the end of the next round lapses as
``offer_lapsed``. An offer or accept the referee cannot record is ``deal_lost``
with the reason, no penalty, the way a whisper to an empty room is lost.

A break is mechanical and judged at the end of each round against that round's
committed events: an attack on a truce partner inside the term, a share not
handed over by its round, an escort not kept by its round. Each is a public
``deal_broken`` naming who broke what, in every digest. Nothing is prevented,
nothing is scored. A death ends a standing deal without a break. A deal whose
term runs out unbroken is ``kept`` in the ledger and leaves the digest; the
record has no kept event, so the audience reads a kept deal from its silence.

The ledger lives in ``state["deals"]`` and is part of the state hash, so a
replay carries every promise. Every function here is pure on ``state`` and
returns what happened; the engine writes the events.
"""

from typing import Any, Mapping, Sequence

from . import items

DEALS_VERSION = "ember-vault-deals-0.1"

DEAL_KINDS: tuple[str, ...] = ("offer", "accept")
DEAL_TYPES: tuple[str, ...] = ("truce", "share_item", "escort")
TRUCE_ROUNDS_MIN = 1
TRUCE_ROUNDS_MAX = 6
OFFER_OPEN_FOR_ROUNDS = 1  # not accepted by the end of the NEXT round: lapsed
BREAKS_IN_DIGEST = 8

# The events that are an attack on a named body (the declared target).
ATTACK_EVENTS: frozenset[str] = frozenset({"attack_hit", "attack_miss"})


def new_ledger() -> dict[str, Any]:
    return {"offers": {}, "struck": {}}


def offer_id(round_no: int, from_id: str) -> str:
    return f"offer-r{round_no}-{from_id}"


def terms_of(deal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rounds": deal.get("rounds"),
        "item": deal.get("item"),
        "destination": deal.get("destination"),
        "by_round": deal.get("by_round"),
    }


def describe_terms(state: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    """One clause, for the referee's line: what was promised."""
    terms = record["terms"]
    kind = record["type"]
    if kind == "truce":
        n = int(terms["rounds"] or 0)
        return f"a truce of {n} round{'s' if n != 1 else ''}"
    if kind == "share_item":
        return f"the {items.item_name(terms['item'])} handed over by round {terms['by_round']}"
    room = state["rooms"].get(terms["destination"] or "", {}).get("name", terms["destination"])
    return f"an escort to {room} by round {terms['by_round']}"


# ---------------------------------------------------------------------------
# recording
# ---------------------------------------------------------------------------


def record_offer(
    state: dict[str, Any], round_no: int, from_id: str, deal: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Record an offer. Returns (offer, None) or (None, why it is lost)."""
    agents = state["agents"]
    me = agents[from_id]
    to_id = deal.get("to")
    other = agents.get(to_id or "")
    if other is None or to_id == from_id:
        return None, "no such character to offer it to"
    if other["status"] != "active":
        return None, "the other party is out of the match"
    if other["room"] != me["room"]:
        return None, "the other party is not in the room to hear it"
    kind = deal.get("type")
    by_round = deal.get("by_round")
    if kind == "share_item" and not items.is_known_item(deal.get("item")):
        return None, "no such item"
    if kind == "escort" and deal.get("destination") not in state["rooms"]:
        return None, "no such room"
    if kind in ("share_item", "escort"):
        if not isinstance(by_round, int) or by_round <= round_no:
            return None, "by_round has to be a later round"
        if by_round > int(state.get("max_rounds", by_round)):
            return None, "by_round is after the last round"
    oid = offer_id(round_no, from_id)
    if oid in state["deals"]["offers"]:
        return None, "one offer per round"
    offer = {
        "id": oid,
        "from": from_id,
        "to": to_id,
        "type": kind,
        "terms": terms_of(deal),
        "made_round": round_no,
        "lapses_after_round": round_no + OFFER_OPEN_FOR_ROUNDS,
        "status": "open",
    }
    state["deals"]["offers"][oid] = offer
    return offer, None


def record_accept(
    state: dict[str, Any], round_no: int, by_id: str, oid: str | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Strike a deal from an open offer. Returns (deal, None) or (None, why)."""
    offer = state["deals"]["offers"].get(oid or "")
    if offer is None:
        return None, "no such offer"
    if offer["to"] != by_id:
        return None, "that offer was not made to you"
    if offer["status"] != "open":
        return None, f"that offer is {offer['status']}"
    if offer["made_round"] >= round_no:
        return None, "an offer is answered the round after it is made"
    if state["agents"][offer["from"]]["status"] != "active":
        return None, "the offerer is out of the match"
    offer["status"] = "struck"
    terms = offer["terms"]
    if offer["type"] == "truce":
        term_end = round_no + int(terms["rounds"]) - 1
    else:
        term_end = int(terms["by_round"])
    deal = {
        "id": offer["id"],
        "from": offer["from"],
        "to": offer["to"],
        "parties": [offer["from"], offer["to"]],
        "type": offer["type"],
        "terms": dict(terms),
        "struck_round": round_no,
        "term_end": term_end,
        "status": "standing",
        "broken_by": [],
        "broken_round": None,
        "how": None,
    }
    state["deals"]["struck"][offer["id"]] = deal
    return deal, None


def lapse_offers(state: dict[str, Any], round_no: int) -> list[dict[str, Any]]:
    lapsed = []
    for oid in sorted(state["deals"]["offers"]):
        offer = state["deals"]["offers"][oid]
        if offer["status"] == "open" and offer["lapses_after_round"] <= round_no:
            offer["status"] = "lapsed"
            lapsed.append(offer)
    return lapsed


# ---------------------------------------------------------------------------
# settlement, end of round
# ---------------------------------------------------------------------------


def _item_id(payload: Mapping[str, Any]) -> str | None:
    item = payload.get("item")
    if isinstance(item, Mapping):
        return item.get("id")
    return item if isinstance(item, str) else None


def settle(
    state: dict[str, Any], round_no: int, round_events: Sequence[Mapping[str, Any]]
) -> dict[str, list[Any]]:
    """Judge every standing deal against this round's committed events.

    Returns ``{"broken": [(deal, breaker_id)], "kept": [deal], "void": [deal]}``.
    Breaks are judged before deaths, so a truce partner killed inside the term
    is a break and not a void.
    """
    agents = state["agents"]
    out: dict[str, list[Any]] = {"broken": [], "kept": [], "void": []}
    for did in sorted(state["deals"]["struck"]):
        deal = state["deals"]["struck"][did]
        if deal["status"] != "standing":
            continue
        a, b = deal["parties"]
        kind, terms = deal["type"], deal["terms"]
        breakers: list[str] = []
        how = None
        kept = False
        if kind == "truce":
            if deal["struck_round"] <= round_no <= deal["term_end"]:
                for ev in round_events:
                    if ev.get("event_type") in ATTACK_EVENTS and {ev.get("actor_id"), ev.get("target_id")} == {a, b}:
                        breakers, how = [str(ev.get("actor_id"))], "attacked a truce partner inside the truce"
                        break
            if not breakers and round_no >= deal["term_end"]:
                kept = True
        elif kind == "share_item":
            handed = any(
                ev.get("event_type") == "item_given"
                and ev.get("actor_id") == deal["from"]
                and ev.get("target_id") == deal["to"]
                and _item_id(ev.get("payload") or {}) == terms["item"]
                for ev in round_events
            )
            if handed:
                kept = True
            elif round_no >= deal["term_end"]:
                breakers, how = [deal["from"]], f"never handed over the {items.item_name(terms['item'])}"
        elif kind == "escort":
            there = [p for p in deal["parties"] if agents[p]["status"] == "active" and agents[p]["room"] == terms["destination"]]
            if len(there) == 2:
                kept = True
            elif round_no >= deal["term_end"]:
                breakers = [p for p in deal["parties"] if p not in there and agents[p]["status"] == "active"]
                how = "did not arrive together by the round promised"
        if breakers:
            deal["status"] = "broken"
            deal["broken_by"] = sorted(breakers)
            deal["broken_round"] = round_no
            deal["how"] = how
            for breaker in sorted(breakers):
                out["broken"].append((deal, breaker))
            continue
        if agents[a]["status"] != "active" or agents[b]["status"] != "active":
            deal["status"] = "void"
            out["void"].append(deal)
            continue
        if kept:
            deal["status"] = "kept"
            out["kept"].append(deal)
    return out


# ---------------------------------------------------------------------------
# the digest block
# ---------------------------------------------------------------------------


def public_breaks(state: Mapping[str, Any], limit: int = BREAKS_IN_DIGEST) -> list[dict[str, Any]]:
    ledger = state.get("deals") or new_ledger()
    broken = [d for d in ledger["struck"].values() if d["status"] == "broken"]
    broken.sort(key=lambda d: (d["broken_round"], d["id"]))
    return [
        {
            "id": d["id"],
            "type": d["type"],
            "terms": dict(d["terms"]),
            "broken_by": list(d["broken_by"]),
            "against": [p for p in d["parties"] if p not in d["broken_by"]],
            "round": d["broken_round"],
            "how": d["how"],
        }
        for d in broken[-limit:]
    ]


def digest(state: Mapping[str, Any], agent_id: str) -> dict[str, Any]:
    """Fixed shape, flat size (PRD §5.21–22): the character's open offers
    either way, its standing deals, every public break, and who it could
    offer to this round."""
    ledger = state.get("deals") or new_ledger()
    me = state["agents"][agent_id]
    offers = [
        {
            "id": o["id"],
            "from": o["from"],
            "to": o["to"],
            "type": o["type"],
            "terms": dict(o["terms"]),
            "made_round": o["made_round"],
            "lapses_after_round": o["lapses_after_round"],
            "yours": o["from"] == agent_id,
        }
        for _, o in sorted(ledger["offers"].items())
        if o["status"] == "open" and agent_id in (o["from"], o["to"])
    ]
    standing = [
        {
            "id": d["id"],
            "with": d["to"] if d["from"] == agent_id else d["from"],
            "you_are": "offerer" if d["from"] == agent_id else "acceptor",
            "type": d["type"],
            "terms": dict(d["terms"]),
            "struck_round": d["struck_round"],
            "term_end": d["term_end"],
        }
        for _, d in sorted(ledger["struck"].items())
        if d["status"] == "standing" and agent_id in d["parties"]
    ]
    can_offer_to = sorted(
        other_id
        for other_id, other in state["agents"].items()
        if other_id != agent_id and other["status"] == "active" and other["room"] == me["room"]
    )
    return {
        "version": DEALS_VERSION,
        "offers": offers,
        "standing": standing,
        "breaks": public_breaks(state),
        "can_offer_to": can_offer_to,
        "policy": {
            "enforced": False,
            "one_per_round": True,
            "offer_lapses_after_rounds": OFFER_OPEN_FOR_ROUNDS,
            "truce_rounds": [TRUCE_ROUNDS_MIN, TRUCE_ROUNDS_MAX],
            "types": list(DEAL_TYPES),
        },
    }
