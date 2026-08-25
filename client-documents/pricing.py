"""Interview counts + fee schedule -> the estimate's line items and total.

The seam the pipeline was missing. The interview collected `count_states`,
`count_k1s` and the rest and nothing turned them into money, so `LineItems` and
`EstimateTotal` stayed unfilled and the fee estimate could not render.

**An unpriced item does not become zero.** Every amount in `fee-schedule.yaml`
is a `[CONFIRM:` until the firm sets it, and a `[CONFIRM:` is carried through to
the line and to the total rather than skipped or defaulted. The estimate then
refuses to render, which is the correct outcome: quoting a client $0 for a
service is worse than quoting nothing at all.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

import money as m

ROOT = Path(__file__).resolve().parent
SCHEDULE = ROOT / "registry" / "fee-schedule.yaml"


class PricingError(RuntimeError):
    pass


def load(path: Path | str = SCHEDULE) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def is_open(value) -> bool:
    """Is this an amount nobody has set?"""
    return isinstance(value, str) and "[CONFIRM:" in value


def open_amounts(schedule: dict | None = None) -> list[tuple[str, str]]:
    """Every unset amount, as (path, question). What `doctor` reports."""
    s = schedule if schedule is not None else load()
    found: list[tuple[str, str]] = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif is_open(node):
            q = node.split("[CONFIRM:", 1)[1].rsplit("]", 1)[0].strip()
            found.append((path, q))

    walk(s, "")
    return found


# Every phrase the estimate assembles, and the slots each one is allowed to
# fill. The schedule holds the words; this holds the contract, because a slot
# is the one part of a phrase a human editing the wording must not invent.
_SLOTS = {
    "includes": {"detail", "list"},        "includes_only": {"list"},
    "with_allowance": {"detail", "branch"},
    "base_covers_one": set(),
    "after_first": {"detail"},             "after_first_only": set(),
    "after_n": {"detail", "n"},            "after_n_only": {"n"},
    "capped": {"detail", "n"},             "capped_only": {"n"},
    "multiplier": {"detail", "n", "each"}, "multiplier_only": {"n", "each"},
    "assumption": {"label", "assumes", "where", "trigger", "consequence"},
    "inside_base": set(), "outside_base": set(),
    "beyond_hourly": {"rate"},
    "beyond_priced": {"each", "amount"},
}


def say(schedule: dict, key: str, **slots) -> str:
    """One phrase from the schedule, with its slots filled.

    The words are the firm's -- "templates should be easily customizable to
    the degree possible, in the sense that i can easily manually update how
    they read", 25 August 2026 -- so they live in the registry and this only
    fills the holes.

    A phrase that names a slot nothing supplies raises rather than printing
    an empty one or a literal `{brace}` on a client's estimate. That is the
    whole safety of moving prose into data: the failure is loud, at render,
    with the phrase named.
    """
    text = (schedule.get("phrases") or {}).get(key)
    if text is None:
        # The WORDING is the firm's and there is one copy of it, in the
        # registry. A schedule that does not carry its own falls back to that
        # rather than to English hidden in this file -- a sample schedule, a
        # test fixture and a future second schedule should all say the same
        # thing to a client, and only one file should have to be edited to
        # change what that is. A schedule MAY override any phrase; omitting
        # them all is the normal case.
        text = _registry_phrases().get(key)
    if text is None:
        raise PricingError(
            f"the fee schedule has no phrase {key!r}, so there is no wording "
            f"for something the estimate needs to say. Add it under "
            f"`phrases:` rather than letting the line render blank."
        )
    try:
        return text.format(**slots)
    except (KeyError, IndexError) as exc:
        raise PricingError(
            f"the phrase {key!r} uses {exc} , which is not one of its slots "
            f"({sorted(_SLOTS.get(key, slots)) or 'none'}). Keep the slots "
            f"that are already in a phrase and do not add new ones -- a slot "
            f"is a hole the software fills, and it can only fill the ones it "
            f"knows about."
        ) from None


@lru_cache(maxsize=1)
def _registry_phrases() -> dict:
    try:
        return (load().get("phrases") or {})
    except Exception:
        return {}


def _line(service: str, detail: str, amount, code: str) -> dict:
    return {"Service": service, "Detail": detail,
            "Amount": m.money(amount, code), "_raw": amount}


def _capped(unit: dict, count: int) -> tuple[int, object]:
    """How many units are actually charged, and whether a cap did the work.

    Returns `(billed, capped)`. `capped` is False when no cap applied, True
    when one did, and a `[CONFIRM:` string when the schedule says a line IS
    capped without saying where -- which is not the same as uncapped, and must
    not quietly price as though it were.

    The firm asked for this on 25 August 2026 against `foreign_account`, and
    the reason is worth keeping: the price was set from their own practice
    with one client -- "i have been doing this stuff with a client for awhile
    and just charge per account - NOTHING HUGE THOUGH" -- and then written by
    me as a line that runs to infinity. One FBAR can list a dozen accounts.
    The keying is real work and it does scale, but not linearly: the second
    account at the same bank is a row, not a filing.

    Every other line on this sheet has either an allowance or a package around
    it. A cap is what those are, for a line that has neither.
    """
    cap = unit.get("cap_units")
    if cap is None:
        return count, False
    if is_open(cap):
        # One unit cannot be over any cap worth setting, so the open value
        # cannot change that client's price and is not worth refusing over.
        return count, (cap if count > 1 else False)
    if count > cap:
        return int(cap), True
    return count, False


def _resolve_tier(unit: dict, answers: dict) -> dict:
    """A tiered item, reduced to the flat one its answer selects.

    Returns the unit unchanged when it has no tiers, so every caller downstream
    sees one shape. An unanswered `tier_from` is NOT a default: which tier the
    client is in changes the price, and picking the cheapest to keep the
    estimate rendering would quote a business return at a gig-worker fee. It
    carries the question instead, and the `[CONFIRM:` stops the render -- the
    same way an unpriced line does.
    """
    tiers = unit.get("tiers")
    if not tiers:
        return unit
    key = unit.get("tier_from")
    if not key:
        raise PricingError(
            f"{unit.get('label', 'an item')!r} has tiers but no `tier_from`, so "
            f"nothing says which one applies. Name the interview answer."
        )
    chosen = answers.get(key)
    if chosen is None or chosen == "":
        return {**unit, "label": unit.get("label", key),
                "detail": "", "amount":
                f"[CONFIRM: the interview did not answer {key!r}, so the tier "
                f"is unknown. One of: {', '.join(sorted(tiers))}.]"}
    if chosen not in tiers:
        raise PricingError(
            f"{key} = {chosen!r} is not a tier of {unit.get('count_from')!r}. "
            f"Known tiers: {', '.join(sorted(tiers))}."
        )
    tier = tiers[chosen]
    for field in ("label", "detail", "amount"):
        if field not in tier:
            raise PricingError(
                f"tier {chosen!r} is missing {field!r}. A tier supplies the "
                f"whole line, so a missing field would print blank."
            )
    return {**unit, **tier}


# ── deriving the package ──────────────────────────────────────────────────

_GATE_OPS = ("schedules_none", "schedules_any", "schedules_none_of",
             "answer_is", "any_of")


def _schedules(answers: dict) -> set:
    raw = answers.get("federal_schedules") or []
    if isinstance(raw, str):
        raw = [s.strip() for s in raw.split(",") if s.strip()]
    return set(raw)


def _gate_holds(gate, answers: dict, where: str) -> bool:
    """Does one gate hold for this client? Every operator in it must.

    Gates key on what is ON the return, never on how many of something there
    is. A count can be blank when the thing exists -- a client ticks the
    rentals schedule and leaves the number for later -- and a gate that reads
    that as zero sends a landlord to the cheapest package.
    """
    if not isinstance(gate, dict):
        raise PricingError(
            f"{where}: a gate must be a mapping of conditions, got "
            f"{type(gate).__name__}. An unreadable gate cannot be allowed to "
            f"quietly never match."
        )
    unknown = set(gate) - set(_GATE_OPS)
    if unknown:
        raise PricingError(
            f"{where}: unknown gate condition(s) {sorted(unknown)}. Known: "
            f"{sorted(_GATE_OPS)}. A misspelled condition would never hold, "
            f"and a package that can never be selected is invisible."
        )
    have = _schedules(answers)
    for op, val in gate.items():
        if op == "schedules_none":
            if bool(val) != (not have):
                return False
        elif op == "schedules_any":
            if not (have & set(val)):
                return False
        elif op == "schedules_none_of":
            if have & set(val):
                return False
        elif op == "answer_is":
            for q, expected in val.items():
                if answers.get(q) != expected:
                    return False
        elif op == "any_of":
            if not any(_gate_holds(sub, answers, f"{where}.any_of")
                       for sub in val):
                return False
    return True


def _unit_price(schedule: dict, count_from: str, answers: dict | None = None):
    """What one of a counted thing costs to THIS client, or None.

    None means "cannot be compared": either nothing prices it, the price is
    still open, or it is tiered and the interview has not said which tier.
    A tiered unit is read directly rather than through `_resolve_tier`, which
    raises when the tier question is unanswered -- correct when a line is
    being priced, wrong here, where the caller only wants to know whether a
    comparison is possible at all.
    """
    answers = answers or {}
    for unit in (schedule.get("per_unit") or {}).values():
        if unit.get("count_from") != count_from:
            continue
        amount = unit.get("amount")
        if unit.get("tiers"):
            chosen = answers.get(unit.get("tier_from"))
            tier = (unit["tiers"] or {}).get(chosen)
            amount = tier.get("amount") if isinstance(tier, dict) else None
        return None if amount is None or is_open(amount) else amount
    return None


def _allowance(key: str, tiers: dict, answers: dict,
               schedule: dict | None = None, where: str = "") -> dict:
    """How many of each counted thing this package already covers.

    Three shapes, in the order they are applied.

    `allows` is flat and always applies.

    `allows_when` is flat but conditional -- a gate, then the counts it
    releases. Property & Business needs it: the package includes a GIG
    Schedule C (it inherits one from Standard) but not a full one, and
    "which kind" is an answer, not a count. Written as a plain flat allowance
    instead, a full-Schedule-C client would get their C free AND the rentals,
    which is exactly the "not both" the sheet rules out.

    `allows_one_of` is the either/or -- three rentals OR one full Schedule C
    -- and the branch worth most to the CLIENT is the one applied, because a
    client must never lose money to an ambiguity in our own schedule.

    Branches are compared in money, and the comparison is on what is LEFT
    after the flat allowances above. Scoring the raw counts double-counts
    anything already included and hands the client the wrong branch: a
    landlord with a side gig has their gig C covered flat, so the
    full-Schedule-C branch is worth nothing more to them -- but scored raw it
    is worth $65, beats a $45 rental, and they pay for a rental the package
    was meant to include.

    Money is the right comparator and the one that fails quietly: a branch
    whose price is not set yet scores zero, which is indistinguishable from a
    branch worth nothing, so the choice silently falls to file order. That is
    not a hypothetical -- with both prices open, a client with one full
    Schedule C and no rentals had the RENTALS branch applied and their
    Schedule C billed on top of a package that said it covered it. So when a
    branch the client actually uses has no price, no choice is made and the
    allowance carries the question instead. A branch the client has no units
    left in cannot change the answer and is not grounds to refuse.
    """
    tier = tiers[key]

    # Flat allowances inherit down the `includes:` chain, broadest first, so
    # "Everything in Standard" is one fact rather than two -- a sentence in
    # `covers:` and a copy of Standard's numbers that has to be kept in step
    # with it by hand. The either/or does NOT inherit: it is the thing that
    # makes a package that package, and a lower rung's choice is not on offer
    # at a higher one.
    flat: list[dict] = []
    conditional: list[tuple[str, dict]] = []
    for name in reversed(_chain(key, tiers, where)):
        rung = tiers[name]
        flat.append(rung.get("allows") or {})
        conditional.extend((name, spec) for spec in (rung.get("allows_when") or []))

    out: dict = {}
    for allows in flat:
        for k, allowed in allows.items():
            out[k] = max(out.get(k, 0), allowed)

    for i, (owner, spec) in enumerate(conditional):
        if not isinstance(spec, dict):
            raise PricingError(
                f"{where}.allows_when[{i}] ({owner}) is not a mapping, so there is no "
                f"way to read what it releases or when."
            )
        gate = spec.get("when")
        if gate is None:
            raise PricingError(
                f"{where}.allows_when[{i}] ({owner}) has no `when`, so it is a flat "
                f"allowance wearing a conditional one's clothes. Move it to "
                f"`allows` or give it a gate."
            )
        if is_open(gate) or not _gate_holds(gate, answers,
                                            f"{where}.allows_when[{i}]"):
            continue
        for key, allowed in spec.items():
            if key == "when":
                continue
            out[key] = max(out.get(key, 0), allowed)

    branches = tier.get("allows_one_of") or []
    if not branches:
        return out

    s = schedule or {}

    def residual(key: str) -> int:
        """What the client still has after the flat allowances above."""
        return max(0, _count(answers.get(key), key) - int(out.get(key, 0) or 0))

    targets = {k for b in branches for k in b if k != "label"}
    blocked = [k for k in sorted(targets)
               if residual(k) > 0 and _unit_price(s, k, answers) is None]
    if blocked:
        out["_open"] = (
            "[CONFIRM: this package covers one of several things and the "
            "cheaper choice cannot be worked out while "
            + ", ".join(blocked) + " has no price. Set it, or the client is "
            "charged by whichever option happens to be written first.]"
        )
        return out

    def saving(branch: dict) -> float:
        return sum(
            min(residual(k), n) * (_unit_price(s, k, answers) or 0)
            for k, n in branch.items() if k != "label")

    best = max(branches, key=saving)
    if saving(best) <= 0:
        # Every branch is worth nothing to this client -- they have none of
        # the things on offer, or already had them. Applying one anyway is
        # harmless arithmetic and a misleading sentence: the estimate would
        # print "with up to three rentals" to somebody who owns none.
        return out
    for target, allowed in best.items():
        if target == "label":
            continue
        out[target] = max(out.get(target, 0), allowed)
    out["_branch"] = best.get("label", "")
    return out


def _chain(key: str, tiers: dict, where: str) -> list[str]:
    """This package, then the one it includes, then that one's, ... .

    `includes:` names the rung below and is followed rather than printed. It
    has to be data: "Everything in Standard" is a true sentence on a public
    price page, where a reader can see Standard, and a meaningless one on an
    estimate, where the client sees only the package they bought. One chain
    serves both, and serves the allowances too -- so a package cannot say it
    includes everything in the one below and quietly allow less.
    """
    chain: list[str] = []
    at = key
    while at:
        if at in chain:
            raise PricingError(
                f"{where}: the packages {' -> '.join(chain + [at])} include "
                f"each other in a loop, so what one covers cannot be worked out."
            )
        if at not in tiers:
            raise PricingError(
                f"{where}.{chain[-1] if chain else key} includes {at!r}, "
                f"which is not a package on this ladder."
            )
        chain.append(at)
        at = (tiers[at] or {}).get("includes")
    return chain


def covers(key: str, tiers: dict, where: str) -> list[str]:
    """Every line a package covers, broadest rung first."""
    out: list[str] = []
    for name in reversed(_chain(key, tiers, where)):
        for line in (tiers.get(name) or {}).get("covers") or []:
            if line not in out:
                out.append(line)
    return out


def derive_tier(unit: dict, answers: dict, where: str) -> tuple:
    """(key, tier) for the first tier whose gate holds -- or (None, None).

    Read top to bottom, FIRST match wins, because the tiers are written most
    specific first. Last-match-wins was the original rule and it is wrong at
    the cheap end: Starter is the most restrictive gate and the least
    expensive package, so a Starter client also satisfies Essentials, and
    taking the later (dearer) match quotes them 200 instead of 100.
    Specificity is what decides, so specificity is what the file is ordered by.
    """
    for key, tier in (unit.get("tiers") or {}).items():
        gate = tier.get("gate")
        if gate is None:
            raise PricingError(
                f"{where}.{key} has no gate, so nothing can ever select it."
            )
        if is_open(gate):
            # An undecided gate never matches. It is reported by `doctor`
            # rather than guessed at, which is the whole point of [CONFIRM:].
            continue
        if _gate_holds(gate, answers, f"{where}.{key}"):
            return key, tier
    return None, None


def _gate_sentence(key: str, tier: dict) -> str:
    """What the estimate prints under the package name.

    The point is that a wrong pick is visible on the page before the document
    reaches a client, so this says what selected the package rather than
    restating its price.
    """
    return tier.get("detail", "") or key


def _count(value, key: str) -> int:
    """An answer read as a number of things, or nothing at all.

    Absence is fine -- an unanswered count is zero, and a question the
    interview never reached because of a `showIf` is absent by design. What is
    not fine is a value that LOOKS countable and is not:

    * `True` is `int()`-able to 1, so a yes/no wired to a count question would
      bill for exactly one of whatever it counted, silently.
    * `2.7` truncated to 2. Nobody has 2.7 K-1s, so the answer is wrong rather
      than imprecise, and rounding it hides that it was ever wrong.

    Both were real behaviours of this function. Neither raised.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0
    if isinstance(value, bool):
        raise PricingError(
            f"{key} answered {value!r}, which is not a count. A yes/no cannot "
            f"say how many, and treating it as one would bill for exactly one."
        )
    if isinstance(value, float) and value != int(value):
        raise PricingError(
            f"{key} answered {value!r}, which is not a count. Rounding it "
            f"would hide that the answer was wrong rather than imprecise."
        )
    try:
        return int(value)
    except (TypeError, ValueError):
        # Free text where a number belongs is treated as absence, not as an
        # error: the interview coerces its own types, and a stray string here
        # means the count was never really asked.
        return 0


def _forms_on(answers: dict, schedule: dict) -> list[tuple[str, dict]]:
    """The per-form situations this client ticked, in the SCHEDULE's order.

    Schedule order, not tick order, so two clients with the same forms get the
    same estimate -- which matters the first time two of them compare notes.

    A ticked value the schedule does not name is an error rather than a silent
    skip: it means the interview offers a situation nobody priced, and the
    client would be told $0 for something that costs.
    """
    block = schedule.get("per_form") or {}
    forms = block.get("forms") or {}
    if not forms:
        return []
    key = block.get("select_from")
    if not key:
        raise PricingError(
            "per_form names forms but no `select_from`, so nothing can ever "
            "select one and the whole block is dead weight."
        )
    picked = answers.get(key) or []
    if isinstance(picked, str):
        picked = [p.strip() for p in picked.split(",") if p.strip()]
    unknown = [p for p in picked if p not in forms]
    if unknown:
        raise PricingError(
            f"the interview offers {sorted(unknown)} under {key!r} and the fee "
            f"schedule prices none of them. Either price them or stop asking: "
            f"a situation the client ticks and the estimate ignores is billed "
            f"at nothing."
        )
    return [(value, spec) for value, spec in forms.items() if value in picked]


def line_items(answers: dict, schedule: dict | None = None) -> list[dict]:
    """The estimate's `LineItems`, in the order they read on the page.

    `answers` is the interview's raw answers, not a composed record: pricing is
    driven by what was counted, and the counts never become merge fields.
    """
    s = schedule if schedule is not None else load()
    code = s.get("currency", "USD")
    base_covers = s.get("base_covers")
    items: list[dict] = []

    form = answers.get("federal_form")
    if not form:
        # Not a soft skip. Guarding the base with `if form:` and pricing the
        # per-unit lines anyway produced an estimate for the ADD-ONS ALONE --
        # a confident total with no return in it. An unknown form already
        # refuses; a missing one is the same failure with less to go on.
        raise PricingError(
            "the record names no federal form, so there is no base fee to "
            "quote. An estimate for the add-ons alone is not an estimate."
        )
    base = (s.get("base") or {}).get(form)
    if base is None:
        raise PricingError(
            f"the fee schedule has no base fee for federal form {form!r}. "
            f"Add it rather than letting the estimate quote without one."
        )

    allowance: dict = {}
    tiers = base.get("tiers") if isinstance(base, dict) else None
    if tiers:
        key, tier = derive_tier(base, answers, f"base.{form}")
        if tier is None:
            # Every gate was either undecided or unmet. Quoting the cheapest
            # tier here would be the single most expensive guess in the file.
            raise PricingError(
                f"no package gate matched this client, so there is no price "
                f"to quote for form {form!r}. Either a gate is wrong or this "
                f"is a client the ladder does not describe; both are worth "
                f"knowing before an estimate goes out."
            )
        for field in ("label", "amount"):
            if field not in tier:
                raise PricingError(
                    f"base.{form}.{key} is missing {field!r}, so the package "
                    f"line cannot be written."
                )
        label = tier["label"]
        detail = _gate_sentence(key, tier)
        base = tier["amount"]
        allowance = _allowance(key, tiers, answers, s, f"base.{form}.{key}")
        if allowance.get("_open"):
            # The package price itself is knowable; which of its options the
            # client got is not. Carry the question on the line so it reaches
            # the total and the estimate refuses rather than guessing.
            base = allowance["_open"]
        elif allowance.get("_branch"):
            detail = say(s, "with_allowance", detail=detail,
                         branch=allowance["_branch"])
        # What the package covers, printed. Without this the estimate names a
        # package and a price and says nothing about what is inside it, which
        # is how a client reads a $500 line as "everything" and how a $200
        # line reads as too much. The list is the sentence the price needs.
        included = covers(key, tiers, f"base.{form}")
        if included:
            joined = "; ".join(included)
            detail = (say(s, "includes", detail=detail, list=joined) if detail
                      else say(s, "includes_only", list=joined))
    else:
        label = {"1040": "Federal Form 1040", "1120S": "Federal Form 1120-S",
                 "1065": "Federal Form 1065", "1120": "Federal Form 1120"}.get(form, form)
        detail = ""
        if base_covers == "one_included":
            detail = say(s, "base_covers_one")
        elif is_open(base_covers):
            # The structure itself is undecided, so the line cannot honestly
            # describe what it covers. Carry the question, not a guess.
            detail = base_covers
    items.append(_line(label, detail, base, code))

    # Per-unit lines. When the base includes the first state and locality, the
    # first of each is already paid for and only the rest are charged.
    for _, unit in (s.get("per_unit") or {}).items():
        raw = _count(answers.get(unit["count_from"]), unit["count_from"])
        count = raw
        if base_covers == "one_included" and unit["count_from"] in (
                "count_states", "count_localities"):
            count = max(0, count - 1)
        # What the package already swallowed. Composes with the first state
        # and locality above rather than replacing it, and never goes below
        # zero -- a package covering more than the client has is not a credit.
        count = max(0, count - int(allowance.get(unit["count_from"], 0) or 0))
        if count <= 0:
            continue

        unit = _resolve_tier(unit, answers)
        amount = unit["amount"]
        billed, capped = _capped(unit, count)
        total = amount if is_open(amount) else amount * billed
        if is_open(capped):
            # The cap exists as a decision and not yet as a number, and this
            # client has enough units for the difference to show. Carry the
            # question to the line rather than quoting them the uncapped
            # total, which is the answer the firm has already rejected.
            total = capped
        detail = unit.get("detail", "")
        if capped is True:
            detail = (say(s, "capped", detail=detail, n=unit["cap_units"])
                      if detail else say(s, "capped_only", n=unit["cap_units"]))
        # Say that the first ones were free. A client who is told their
        # package includes a state return and then sees a "State return"
        # line on the same page reasonably concludes they were charged for
        # it; the line has to carry the word "after" or the covers list
        # above it looks like a lie.
        free = raw - count
        if free == 1:
            detail = (say(s, "after_first", detail=detail) if detail
                      else say(s, "after_first_only"))
        elif free > 1:
            detail = (say(s, "after_n", detail=detail, n=free) if detail
                      else say(s, "after_n_only", n=free))
        if billed > 1:
            each = amount if is_open(amount) else m.money(amount, code)
            detail = (say(s, "multiplier", detail=detail, n=billed, each=each)
                      if detail else say(s, "multiplier_only", n=billed, each=each))
        items.append(_line(unit["label"], detail, total, code))

    # One price per named form. Ticked from a multi-select, priced flat, and
    # written in the schedule's own order rather than the order the client
    # happened to tick them -- two clients with the same forms get the same
    # estimate, which matters the first time two of them compare.
    for value, spec in _forms_on(answers, s):
        if spec.get("priced_by"):
            # Priced by a counted line instead, which has already run. A form
            # that fired here as well would bill the first one twice.
            continue
        amount = (s.get("per_form") or {}).get("amount")
        if amount is None:
            raise PricingError(
                "per_form names forms but no amount, so a ticked form has no "
                "price. One amount is the whole point of the block."
            )
        label = spec.get("label")
        if not label:
            raise PricingError(
                f"per_form.forms.{value} has no label, so the line cannot be "
                f"written. A $50 line reading '{value}' is not an estimate."
            )
        items.append(_line(label, spec.get("detail", ""), amount, code))

    # Nothing here for `assumed:` items. They carry no price, so they produce
    # no line: an estimate lists what is being charged for, and a line reading
    # "Records cleanup -- included" or "-- hourly" is a term of business
    # wearing a line item's clothes. Terms belong in `assumptions()` below,
    # which puts them in the estimate's own assumptions block in words.

    return items


def assumptions(answers: dict, schedule: dict | None = None) -> list[str]:
    """The sentences the estimate must carry, given what the fee assumes.

    One per `assumed:` item, always -- not only when something looks unusual.
    An assumption a client is told about only after it fails is not an
    assumption, it is a surprise, and the whole point of stating the boundary
    is that it is stated before the work rather than after.
    """
    s = pricing_schedule(schedule)
    rate = (s.get("basis") or {}).get("rate")
    out = [_assumption(spec, rate, schedule=s, check_beyond=True)
           for _, spec in (s.get("assumed") or {}).items()]

    # And one per form the client actually ticked. The per-form rule IS its
    # assumption -- hold it and pay the flat price, break it and the meter
    # runs -- so a $50 line without its sentence is half a price. Only the
    # ticked ones: an assumption about a form nobody is filing is noise, and
    # noise is how a client learns to skip this block.
    for _, spec in _forms_on(answers, s):
        if spec.get("assumes"):
            out.append(_assumption(spec, rate, schedule=s))
    return out


def _assumption(spec: dict, rate, *, schedule: dict | None = None,
                check_beyond: bool = False) -> str:
    """One boundary, in words a client reads before the work rather than after.

    The label leads rather than acting as the subject, or every sentence says
    its own noun twice: "Brokerage activity assumes your brokerage activity
    arrives as...".

    `check_beyond` only applies to the `assumed:` block. A per-form assumption
    has no `beyond:` to check because the answer is not a choice there: the
    per-form rule IS "hold the assumption, pay the flat price; break it, the
    meter runs", so the consequence is the rule rather than a per-item setting.
    """
    label = (spec.get("label") or "").strip()
    assumes = (spec.get("assumes") or "").strip()
    trigger = (spec.get("trigger") or "").strip()
    if not (label and assumes and trigger):
        raise PricingError(
            f"the assumed item {label or '(unnamed)'} is missing its "
            f"label, assumption or trigger. Without all three there is no "
            f"honest sentence to print, and a boundary nobody stated is "
            f"not a boundary."
        )
    s = schedule or {}
    where = say(s, "inside_base" if spec.get("inside_base") else "outside_base")

    beyond = spec.get("beyond", "hourly")
    if check_beyond and beyond not in _BEYOND:
        raise PricingError(
            f"{label} says work beyond the assumption is {beyond!r}. "
            f"Supported: {sorted(_BEYOND)}. The firm ruled out re-quoting "
            f"deliberately, and a consequence nobody recognises would print "
            f"as an hourly one."
        )

    if beyond == "priced":
        consequence = _priced_consequence(label, spec, s)
    else:
        rate_txt = f" at ${rate:,.0f} an hour" if isinstance(rate, (int, float)) else ""
        consequence = say(s, "beyond_hourly", rate=rate_txt)

    return say(s, "assumption", label=label, assumes=assumes, where=where,
               trigger=trigger, consequence=consequence)


# What can happen past an assumption. Deliberately short, and every entry is a
# decision the firm made rather than a shape the code allows.
#
#   hourly  the fixed price stops applying and the meter runs
#   priced  the overrun has a NAMED PRICE, already on this sheet, told to the
#           client up front and confirmed with them at the moment we find it
#
# `requote` is absent on purpose: it stops the job and opens a negotiation the
# firm did not want. A test refuses it, and refusing it is the point.
_BEYOND = {"hourly", "priced"}


def _priced_consequence(label: str, spec: dict, schedule: dict) -> str:
    """The sentence for a boundary whose consequence is a price, not a rate.

    The firm, 25 August 2026, when asked whether this was worth having:

        "this should be more like - we will tell you it's going to be $95 more
         and we agree now that we know?"

    That is a third thing, and the best of the three. Hourly tells a client a
    rate and leaves them unable to work out the total. A re-quote stops the
    job. This tells them the NUMBER before the work, and confirms it with them
    at the moment it is found -- so nothing lands on the invoice unannounced
    and nothing has to be renegotiated.

    The price is read from the per-unit line that charges it rather than typed
    here, because two places holding the same number is how an estimate ends
    up promising $95 while the invoice bills $110.
    """
    key = spec.get("beyond_price_from")
    if not key:
        raise PricingError(
            f"{label} says the consequence is a price but does not say which "
            f"line prices it. Name it in `beyond_price_from`, or the sentence "
            f"has to invent a number."
        )
    unit = (schedule.get("per_unit") or {}).get(key)
    if not isinstance(unit, dict):
        raise PricingError(
            f"{label} points `beyond_price_from` at {key!r}, which is not a "
            f"per-unit line. A boundary that names a price nothing charges is "
            f"a promise the invoice cannot keep."
        )
    amount = unit.get("amount")
    if amount is None or is_open(amount):
        raise PricingError(
            f"{label} prices its overrun from per_unit.{key}, which has no "
            f"amount set. Set it before promising a client a number."
        )
    return say(schedule, "beyond_priced",
               each=unit.get("per_each") or "that one",
               amount=m.money(amount, schedule.get("currency", "USD")))


def pricing_schedule(schedule: dict | None) -> dict:
    return load() if schedule is None else schedule


def estimate_total(items: list[dict], schedule: dict | None = None) -> str:
    """The sum, formatted — or the reason it cannot be summed.

    Never typed, per the registry: computed from the lines. If any line is
    unpriced the total is a `[CONFIRM:` naming how many, because a total that
    silently omits an unpriced line is a quote the firm cannot stand behind.
    """
    s = schedule if schedule is not None else load()
    code = s.get("currency", "USD")

    unpriced = [i for i in items if is_open(i["_raw"])]
    if unpriced:
        # Name the line AND carry its own reason. "No price" was true when
        # every open value was a missing amount; a line can now be open
        # because its CAP is unset, which is a different question with a
        # different answer, and a total that flattens the two sends whoever
        # reads it to the wrong part of the file.
        why = "; ".join(f"{i['Service']} — {i['_raw']}" for i in unpriced)
        return (f"[CONFIRM: {len(unpriced)} line(s) cannot be priced from "
                f"fee-schedule.yaml. {why}]")
    return m.money(sum(i["_raw"] for i in items), code)


def price(answers: dict, schedule: dict | None = None) -> dict:
    """`LineItems`, `EstimateTotal` and `Assumptions`, ready to merge.

    Assumptions ride with the price rather than being fetched separately,
    because they are part of the price: they say what it covers and what it
    stops covering. Split them and the estimate can be built without them --
    which is exactly what happened the first time this was wired, and the
    template's [[EACH Assumptions]] block collapsed to nothing without the
    render so much as warning about it.
    """
    items = line_items(answers, schedule)
    total = estimate_total(items, schedule)
    return {
        "LineItems": [{k: v for k, v in i.items() if not k.startswith("_")}
                      for i in items],
        "EstimateTotal": total,
        "Assumptions": [{"Text": t} for t in assumptions(answers, schedule)],
    }
