"""What a FILED return implies about the work — read, never priced.

The firm, 5 September 2026:

    "the final invoice is what really should be made after we do the return and
    can actually compute it… I would expect us to be able to feed a final return
    to our software and have it identify the schedules and stuff that we filled
    out and price the engagement at the end and then it would pretty much need to
    ask if there was hourly work and stuff."

And on 6 September, asked whether to build it: *"Build it next"* — taking the
recommendation to **start with the read**, because the part that carries risk is
deciding what a filed return implies, and that can be built and checked without
anything being billed from it.

So this module reads and reports. **It does not price, and it must not.** The
firm settled ownership on 4 September — *"client-documents owns the engagement;
satc_system holds the return"* — and #267 put the price on the engagement, with
`billing/engagement_price.py` reading it through the ref rather than
recomputing it. A second implementation of the fee ladder here would recreate
the exact defect that seam exists to end: two price lists that disagree, and the
client keeps whichever says the larger number.

WHAT A RETURN CAN AND CANNOT TELL YOU, which is the whole design:

    it CAN     which schedules were actually filled in, and how many of each,
               because the line items are the return's own content
    it CANNOT  how long anything took, whether the records needed sorting,
               whether there were phone calls — none of which leaves a trace on
               a 1040

The second list is why the firm's sentence ends *"and stuff"*: the read produces
a proposal with a hole in it, and the hole is named rather than filled. Unknown
is a third answer.

THE COMPARISON IS THE POINT. Reading the schedules alone tells a preparer what
they already know. Set against what the client was QUOTED — through the same
engagement ref the estimate carries — it answers the question that actually
arises at the end of a job: *did we do what we said we would?* Three rentals on
a return quoted for two is a conversation to have before the invoice, not after.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# What each priced unit looks like on a filed return.
#
# `schedules` are the mart's own schedule codes; `counts_by` says whether the
# unit is one-per-return or one-per-something. Declared as a table rather than
# written as branches so a new priced unit is a row, and so the mapping can be
# read by somebody checking it against the fee schedule.
#
# THE KEYS ARE `client-documents/registry/fee-schedule.yaml`'s `per_unit` keys.
# They are the join, and if one is renamed there this table is where it breaks —
# loudly, in `unmatched_units()`, rather than by quietly evidencing nothing.
@dataclass(frozen=True, slots=True)
class UnitSignature:
    unit: str
    label: str
    schedules: tuple[str, ...]
    per_instance: bool = False
    """True when the return can say HOW MANY -- three rentals, two states -- and
    false when its presence is the whole fact."""

    instance_field: str = "line_code"


SIGNATURES: tuple[UnitSignature, ...] = (
    UnitSignature("schedule_c", "Schedule C — self-employment", ("SCH_C",)),
    UnitSignature("rental", "Schedule E — rental property", ("SCH_E",),
                  per_instance=True),
    UnitSignature("farm", "Schedule F — farm", ("SCH_F",)),
    UnitSignature("brokerage", "Schedule D / brokerage activity", ("SCH_D", "SCH_B")),
    UnitSignature("foreign_account", "Foreign account reporting",
                  ("FBAR", "F8938", "SCH_B_FOREIGN")),
    UnitSignature("k1", "Schedule K-1 received", ("K1",), per_instance=True),
)

#: Units a return CAN evidence but not from its own line items -- they are facts
#: about the SET of returns filed for a client and year, not about the content of
#: one of them. Kept separate because the read for them is a different read, and
#: folding them into `SIGNATURES` would mean pretending a line item exists.
#:
#: `state_return` matters more than the others put together here: most SATC
#: clients file an Ohio return, and a read that could not see it would miss the
#: commonest add-on on the schedule.
JURISDICTION_UNIT = "state_return"

#: Units nothing in this module evidences, with the reason. NOT an oversight
#: list -- a declared boundary, so `unmatched_units` reports a real gap rather
#: than these four every time.
#:
#: `local_return`: the mart's `jurisdiction` does not distinguish a city from a
#: state, so counting one as the other would be a guess wearing a number.
#: `owner_k1`: K-1s ISSUED by a passthrough, which live on that entity's return
#: rather than this one.
DELIBERATELY_NOT_READ: tuple[tuple[str, str], ...] = (
    ("local_return", "the mart records a jurisdiction but not whether it is a "
                     "state or a locality, so counting one as the other would be "
                     "a guess"),
    ("owner_k1", "K-1s ISSUED by a passthrough belong to that entity's return, "
                 "not to this one"),
)

#: What no return can evidence, named so the caller shows the gap rather than
#: producing a total that looks complete. Each is a real fee-schedule line.
CANNOT_BE_READ_FROM_A_RETURN: tuple[tuple[str, str], ...] = (
    ("hourly", "time billed by the hour — a return records the result, never the hours"),
    ("records_sorting", "whether what arrived had to be sorted before it could be worked"),
    ("cleanup", "whether the books had to be reconciled or repaired first"),
    ("extension_estimate", "whether an extension was filed with a payment estimate — "
                           "that happened months before this return existed"),
)


@dataclass(slots=True)
class Evidence:
    """One schedule found on the return, and what proves it."""

    schedule: str
    line_items: int
    instances: int
    """How many distinct things of this kind -- properties, businesses. 1 where
    the return cannot distinguish them."""

    sample: tuple[str, ...] = ()
    """A few line labels, so a person can see WHY this was concluded rather than
    take the count on trust."""


@dataclass(slots=True)
class Implication:
    """A priced unit the return evidences. A PROPOSAL, never a charge."""

    unit: str
    label: str
    quantity: int
    because: str


@dataclass(slots=True)
class ReturnReading:
    """Everything the read concluded, with its denominators."""

    return_key: str
    filed: bool
    filing_status_line: str
    line_items_read: int
    schedules_seen: tuple[str, ...]
    evidence: list[Evidence] = field(default_factory=list)
    implies: list[Implication] = field(default_factory=list)
    must_ask: list[tuple[str, str]] = field(default_factory=list)
    quoted_ref: str = ""
    quoted_lines: tuple[tuple[str, str], ...] = ()
    quoted_total: str = ""
    quote_problem: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def read_nothing(self) -> bool:
        """A return with no line items concluded nothing, and must say so.

        S2: "no work evidenced" and "nothing was examined" are the same sentence
        otherwise, and only one of them means the job was simple.
        """
        return self.line_items_read == 0

    @property
    def is_complete_enough_to_bill(self) -> bool:
        """Always False, and deliberately so.

        There is no reading of a return that finishes an invoice: `must_ask` is
        never empty, because a return cannot record hours. This property exists
        to be read by a caller that thinks otherwise, and to make the answer a
        stated one rather than an omission.
        """
        return False


def read_return(store, return_key: str, *, engagement_ref: str = "") -> ReturnReading:
    """What this return evidences, and what still has to be asked.

    Never raises on a missing or half-built return: a reading that says "this
    return has nothing on it" is more useful than a traceback, and this runs on
    whatever the preparer has in front of them.
    """
    from satc.models.filing import status_line_for

    mart = store.load_mart()
    items = [li for li in mart.line_items if li.return_key == return_key]
    filings = store.load_filings(return_key)
    status_line = status_line_for(filings)

    by_schedule: dict[str, list] = {}
    for li in items:
        by_schedule.setdefault(li.schedule, []).append(li)

    reading = ReturnReading(
        return_key=return_key,
        filed=any(getattr(f, "transmitted_at", None) for f in filings),
        filing_status_line=status_line,
        line_items_read=len(items),
        schedules_seen=tuple(sorted(by_schedule)),
        must_ask=list(CANNOT_BE_READ_FROM_A_RETURN),
    )

    if reading.read_nothing:
        reading.notes.append(
            "No line items on this return, so nothing was evidenced — which is "
            "not the same as a simple return. Post the confirmed figures first, "
            "or check the return key.")
        return reading

    # NOT FILED IS A FINDING, NOT A REFUSAL. A preparer reviewing what a return
    # implies before transmitting is doing the right thing; the reading simply
    # has to say which it is, so a proposal built from a draft is never mistaken
    # for one built from a filed return.
    if not reading.filed:
        reading.notes.append(
            f"This return has not been transmitted ({status_line}). What follows "
            f"describes the return as it stands, and it can still change.")

    for sig in SIGNATURES:
        found = [li for s in sig.schedules for li in by_schedule.get(s, [])]
        if not found:
            continue
        instances = (len({li.line_code.split("_")[0] for li in found})
                     if sig.per_instance else 1)
        sample = tuple(li.label for li in found[:3] if li.label)
        reading.evidence.append(Evidence(
            schedule="/".join(sig.schedules), line_items=len(found),
            instances=instances, sample=sample))
        reading.implies.append(Implication(
            unit=sig.unit, label=sig.label, quantity=instances,
            because=(f"{len(found)} line item(s) on "
                     f"{', '.join(sorted({li.schedule for li in found}))}"
                     + (f", distinguishing {instances}" if sig.per_instance else ""))))

    _read_the_other_jurisdictions(store, mart, reading)
    if engagement_ref:
        _attach_the_quote(reading, engagement_ref)
    return reading


def _read_the_other_jurisdictions(store, mart, reading: ReturnReading) -> None:
    """State returns, read from the SET of returns rather than from line items.

    A state return is its own `ReturnRecord` with a different `jurisdiction`, so
    it leaves no trace inside the federal return's line items. Missing it would
    have been the most expensive omission in the read: most SATC clients file an
    Ohio return, and it is the commonest priced add-on on the schedule.

    Counted from returns that CARRY CONTENT. A jurisdiction row with no line
    items is a return somebody created and did not fill in, and billing for it
    would be charging for a shell.
    """
    this = next((r for r in mart.returns if r.return_key == reading.return_key), None)
    if this is None:
        return
    with_content = {li.return_key for li in mart.line_items}
    others = [r for r in mart.returns
              if r.client_id == this.client_id and r.tax_year == this.tax_year
              and r.jurisdiction != this.jurisdiction
              and r.jurisdiction.upper() != "US"
              and r.return_key in with_content]
    if not others:
        return
    where = ", ".join(sorted({r.jurisdiction for r in others}))
    reading.implies.append(Implication(
        unit=JURISDICTION_UNIT, label="State return",
        quantity=len({r.jurisdiction for r in others}),
        because=f"a separate return with line items exists for {where}"))


def _attach_the_quote(reading: ReturnReading, ref: str) -> None:
    """What the client was quoted, read through the ref -- never recomputed.

    `engagement_price` is a READER by design: the figure a client holds is the
    one on their estimate, and re-deriving it here would be a second rendering
    of the same money. So this attaches what the estimate SAYS and leaves the
    comparison to a person, which is also the honest division of labour --
    matching a quoted line to a schedule is a judgement, not a lookup.
    """
    from satc.billing.engagement_price import price_for_ref

    quoted = price_for_ref(ref)
    reading.quoted_ref = ref
    if not getattr(quoted, "is_priced", False):
        reading.quote_problem = getattr(quoted, "reason", "no quote could be read")
        return
    reading.quoted_lines = quoted.lines
    reading.quoted_total = quoted.total


def unmatched_units(fee_schedule_units) -> list[str]:
    """Priced units this module has no signature for.

    The join between the two projects is a set of string keys, and a key
    renamed in `fee-schedule.yaml` would otherwise make this module quietly stop
    evidencing that unit -- the failure being silence rather than an error. A
    caller can ask, and a test does.
    """
    known = ({s.unit for s in SIGNATURES}
             | {k for k, _ in CANNOT_BE_READ_FROM_A_RETURN}
             | {k for k, _ in DELIBERATELY_NOT_READ}
             | {JURISDICTION_UNIT})
    return sorted(set(fee_schedule_units) - known)
