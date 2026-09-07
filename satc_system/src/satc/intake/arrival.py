"""How a batch of documents arrived — asked once, in words a preparer uses.

D26, and the firm's answer of 6 September 2026: **"Ask once per folder."**

`run_intake` reads a folder, classifies each file and closes the matching
request. Until now it wrote nothing to the arrivals register, so the register
26 CFR §1.6695-2(b)(4)(i)(C) requires — *"a record of how and when the
information was obtained… including the identity of any person furnishing the
information"* — had never held a real row in the product's whole history. The
Documents screen prints that citation under the table.

THE PART THE CODE CANNOT ANSWER. Three of the four fields intake can fill
honestly: WHEN (now), WHOSE (the client it was pointed at), WHAT (the classified
type). **HOW it got there, it cannot.** A client emailed it, the preparer pulled
it off a payroll portal, it is last year's carry-forward, somebody handed over a
thumb drive — the file on disk is identical in every case, and that is precisely
the question the regulation asks. Guessing is what this codebase refuses to do.

So it is asked, once, for the batch. One dropdown, one click, and the ordinary
case — a client sends a folder of documents — produces a complete record.

WHY THE OPTIONS ARE PROSE AND NOT THE ENUM. `obtained_how` is a closed list of
five machine values (`furnished_by_client`, `furnished_by_third_party`,
`downloaded_by_preparer`, `prior_year_carryforward`, `unknown`). Putting those on
a screen would be S35 exactly — writing for the person who built it. A preparer
knows whether the client emailed them; they do not know which of five literals
that is. The table below is the translation, and it carries the CHANNEL too,
because "the client emailed them" answers both questions at once and the
regulation asks for both.

WHY `unknown` IS THE DEFAULT AND NOT THE COMMONEST ANSWER. Skipping the dropdown
has to produce an honest gap, not a plausible-looking record. A run nobody
described writes `unknown`, the row flags itself `provenance incomplete`, and
the screen says so — which is the whole difference between a compliance record
and something that merely looks like one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Arrival:
    """One answer to "how did these arrive", and what it records."""

    key: str
    label: str
    """What the preparer reads. Their words, not the enum's."""

    obtained_how: str
    channel: str
    """Empty where the answer genuinely does not settle it — a third party
    sending something says who, not by what means."""

    furnished_by_client: bool = False
    """Whether the CLIENT is the person furnishing it, so `furnished_by` can be
    filled with their name rather than left blank."""

    @property
    def is_complete(self) -> bool:
        """Whether this answer alone yields a complete §1.6695-2 record.

        `furnished_by` still has to be resolvable, which it is for the client and
        is not for an unnamed third party — so this is necessary, not sufficient,
        and the row's own `has_known_provenance` remains the authority.
        """
        return self.obtained_how != "unknown" and bool(self.channel)


#: Order matters: this is the order of the dropdown, and the first entry is the
#: default. `not_recorded` leads because a default that asserts something is how
#: a register fills up with answers nobody gave.
ARRIVALS: tuple[Arrival, ...] = (
    Arrival("not_recorded", "Not recorded — I would rather leave it blank",
            "unknown", ""),
    Arrival("client_email", "The client emailed them",
            "furnished_by_client", "email", furnished_by_client=True),
    Arrival("client_portal", "The client uploaded them to the portal",
            "furnished_by_client", "portal", furnished_by_client=True),
    Arrival("client_paper", "The client handed them over or posted them",
            "furnished_by_client", "paper", furnished_by_client=True),
    Arrival("preparer_download", "I downloaded them from a payroll or bank portal",
            "downloaded_by_preparer", "portal"),
    Arrival("third_party", "A third party sent them (employer, broker, prior accountant)",
            "furnished_by_third_party", ""),
    Arrival("carryforward", "Carried forward from last year's file",
            "prior_year_carryforward", "prior year file"),
)

_BY_KEY = {a.key: a for a in ARRIVALS}

DEFAULT = ARRIVALS[0]


def resolve(key: str | None) -> Arrival:
    """The answer for `key`, or the honest default.

    An unrecognised key resolves to `not_recorded` rather than raising. A typo in
    a form post must not lose a whole intake run, and the cost of the fallback is
    a row that says it does not know — which is true.
    """
    return _BY_KEY.get((key or "").strip(), DEFAULT)


def choices() -> list[tuple[str, str]]:
    """`(key, label)` pairs for a form, in the order they should be offered."""
    return [(a.key, a.label) for a in ARRIVALS]
