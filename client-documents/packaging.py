"""What a client actually receives, decided in one place.

The firm, 25 August 2026: *"i like the idea of having it all come out as a
package to send for review/signing, and the estimate is required for the
engagement to make sense"*.

That second clause is the whole design. An engagement letter without its fee
estimate asks somebody to sign for work at a price they have not been shown,
and a firm that sends one and then the other has a window in which the client
has agreed to only half of it. So the pack is ATOMIC: every document in it
renders, or none of them is written.

WHICH DOCUMENTS depends on what is being prepared, and that is derived from
`_return_type` on the record rather than chosen at the call. An individual
signs the tax engagement letter; an entity signs the business one. Neither
list is a fourth thing anyone has to remember.

WHAT IS NOT IN IT: the invoice. An invoice is not something a client signs,
it is something they pay, and it arrives after the work rather than before
it. `--with-invoice` exists for the case where somebody genuinely wants both
in one folder, and it is off by default so nobody sends a bill with a
contract by accident.
"""

from __future__ import annotations

# What each kind of engagement sends out for signature. Keyed on
# `_return_type`, which `intake.compose_record` sets from the federal form.
#
# The estimate and the onboarding letter are in every pack, deliberately: the
# estimate because nothing should be signed without a price, and the
# onboarding letter because it is what tells the client what happens next.
PACKS: dict[str, list[str]] = {
    "individual":  ["tax-letter", "fee-estimate", "onboarding-letter"],
    "s_corp":      ["business-letter", "fee-estimate", "onboarding-letter"],
    "partnership": ["business-letter", "fee-estimate", "onboarding-letter"],
    # SEPARATED 26 August 2026. Until then a C corporation was sent the
    # business letter, whose section 02 is entirely about Schedules K-1 and
    # merges <<ScheduleK1Target>> unconditionally -- a date the interview
    # correctly never asks a C corporation for, because it issues no K-1s. So
    # the pack did not merely say something wrong: it REFUSED, and no 1120
    # client could be sent an engagement letter at all.
    #
    # The firm: "let's go separate - there may be other things we want
    # specific to them anyway."
    "c_corp":      ["ccorp-letter", "fee-estimate", "onboarding-letter"],
}

# Documents that travel with every pack, for the clients they apply to. The
# flag is a field on the record, so nobody decides this per engagement.
#
# THE RECORDS RELEASE BELONGS HERE AND WAS NOT. The firm, 26 August 2026:
# "let's just make an attachment that we send for them to sign by default
# along with the engagement letter." `cli.opening_package` honoured that and
# this module did not, so the two front doors sent different packs -- and the
# onboarding letter INSIDE the pack says, to any client with a predecessor,
# "We have included a short authorization for you to sign." It was not
# included. A pack that promises an enclosure it does not carry is the same
# failure as a pack with a hole in it, arriving by the back door.
CONDITIONAL: dict[str, str] = {"records-release": "PriorFirm"}

# Why each document is in the pack, for the manifest. A folder of PDFs with
# no note is a folder somebody has to reverse-engineer in a year.
PURPOSE = {
    "tax-letter":         "The engagement letter. This is the one that is signed.",
    "ccorp-letter":       "The engagement letter for a C corporation. This is the one that is signed.",
    "business-letter":    "The engagement letter for a partnership or an S corporation. This is the one that is signed.",
    "fee-estimate":       "What the work costs, and what the price assumes. Accompanies the letter; not signed separately.",
    "onboarding-letter":  "What happens next, and what we need from you.",
    "records-release":    "The authorization your previous accountant needs before they release your records. Signed by you and sent to them.",
    "invoice":            "The bill. Not part of what is signed — included because it was asked for.",
}


class PackageError(Exception):
    """The pack cannot be assembled honestly."""


def documents_for(record: dict, *, with_invoice: bool = False) -> list[str]:
    """The documents this engagement's client should receive.

    Raises rather than guessing. A record with no `_return_type` has been
    built by something that skipped `intake.compose_record`, and picking the
    individual pack for it would send an individual engagement letter to a
    corporation.
    """
    kind = record.get("_return_type")
    if not kind:
        raise PackageError(
            "this record does not say what kind of return it is "
            "(`_return_type`), so there is no way to know which engagement "
            "letter belongs in the pack. It was probably built without going "
            "through intake.compose_record."
        )
    if kind not in PACKS:
        raise PackageError(
            f"no signing pack is defined for a {kind!r} engagement. Known: "
            f"{', '.join(sorted(PACKS))}. Add one rather than falling back to "
            f"the individual pack, which would send the wrong letter."
        )
    docs = list(PACKS[kind])
    docs += [doc for doc, flag in CONDITIONAL.items() if record.get(flag)]
    if with_invoice:
        docs.append("invoice")
    return docs


def manifest(record: dict, docs: list[str], written: dict[str, list]) -> dict:
    """What is in the pack, so the folder explains itself."""
    return {
        "EngagementRef": record.get("EngagementRef", ""),
        "Client": record.get("ClientFullName", ""),
        "ReturnType": record.get("_return_type", ""),
        "Period": record.get("PeriodLabel") or record.get("_season", ""),
        "LetterDate": record.get("LetterDate", ""),
        "EstimateTotal": record.get("EstimateTotal", ""),
        "Documents": [
            {"key": d, "purpose": PURPOSE.get(d, ""),
             "files": [p.name for p in written.get(d, [])]}
            for d in docs
        ],
        "Note": (
            "Every document in this pack was rendered in one pass from one "
            "engagement record, so they cannot disagree about the date, the "
            "reference, the address or the price. If any one of them had "
            "failed to render, none of them would have been written."
        ),
    }
