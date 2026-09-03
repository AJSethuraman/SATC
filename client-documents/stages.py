"""Where an engagement has got to, as seven things the software can prove.

THE DESIGN ASKED FOR NINE AND THE SOFTWARE KNOWS SEVEN. Claude Design's app
set (`satc-handoff/06-APP/`) drew a nine-step bar reading "4 of 9" -- and two
of its nine are not facts this system holds apart:

  * *interviewed* and *priced* happen in the same instant. `intake.finish`
    prices before the store is touched and writes the record and the answers
    together, so nothing is ever one and not the other.
  * *filed* and *closed* are one artifact. `cli.py close` writes
    `closeout.json` and that is the only record either way; nothing anywhere
    records "we transmitted this return" as its own act.

A bar reading "4 of 9" against seven knowable states is §0 of
`docs/SOFTWARE-TENETS.md` with a progress bar on it -- something reporting
more than it did. So this module derives the seven, and each one names the
file on disk that proves it.

AND THERE IS NO RUNNING COUNT, which is the firm's own decision, 3 September
2026. The steps are not a sequence. `signing._unsettled` says so in its own
comment -- *"blocking on an invoice that does not exist would stop every
engagement that bills after filing, which is most of them"* -- while every
engagement letter promises the opposite for the ones that are billed first:
*"we will not e-file a return before the invoice for it is settled."* Both are
true of different clients, so "4 of 7" would count backwards for whichever
kind it was not drawn for. Seven marks, each lit when it happens, and no arrow
of time drawn over the top of them.

UNKNOWN IS NOT UNREACHED. `signed` is the one step that needs more than a file
test -- it reads the signature lines out of the templates -- and if the
templates cannot be read the honest answer is that we do not know, not that
nobody has signed. `Step.reached` is `None` for that, and the screen draws it
differently. A gate that quietly treats "we cannot tell" as "no" is the same
failure as one that treats it as "yes" (S5).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import engagements

# The seven, in the order a file usually moves -- which is the order they are
# LISTED in and not a claim that they happen in it. See the module docstring.
STEPS: list[tuple[str, str]] = [
    ("sitting", "sitting done"),
    ("packed", "pack built"),
    ("sent", "sent"),
    ("signed", "signed"),
    ("billed", "billed"),
    ("paid", "paid"),
    ("closed", "closed"),
]

# What on disk proves each one. Kept beside the derivation so a reader can
# check the claim without reading the code, and so `cli.py`/`web.py` can print
# it when somebody asks why a mark is not lit.
PROOF: dict[str, str] = {
    "sitting": "the answers saved with the record",
    "packed": "a pack this software wrote, in the engagement's own folder",
    "sent": "somebody wrote down that the pack went out",
    "signed": "every signature the pack asks for has been recorded",
    "billed": "an invoice has been raised",
    "paid": "every invoice raised is recorded as settled",
    "closed": "the close-out answers, from the filed return",
}


@dataclass(frozen=True)
class Step:
    key: str
    name: str
    # True, False, or None for "cannot tell" -- which is a third answer, not a
    # shy way of saying no.
    reached: bool | None
    why: str = ""


def _dir(store: Path, ref: str) -> Path:
    return engagements._dir(Path(store), ref)


def _signed(ref: str, store: Path, template_dir: Path | None) -> bool | None:
    """Every signature the pack asks for, recorded.

    `Standing.complete` is False on an empty census on purpose -- a pack that
    asks for no signature is a broken census, not a completed one -- and that
    distinction is why this delegates rather than counting rows itself (S3:
    two halves of one tool must make the same call).
    """
    import packaging
    import signing

    try:
        record = engagements.load(ref, store)
        docs = packaging.documents_for(record)
        if template_dir is None:
            import cli
            template_dir = cli.TEMPLATE_DIR
        where = signing.standing(ref, record, docs, Path(template_dir),
                                 store=store)
    except Exception:                                          # noqa: BLE001
        return None
    return where.complete


def _paid(store: Path, ref: str) -> bool:
    """Every bill raised is settled. A file with no bill is not paid."""
    import invoicing

    raised = invoicing.issued_for(store, ref)
    return bool(raised) and all(b.get("SettledOn") for b in raised)


def _billed(store: Path, ref: str) -> bool:
    import invoicing

    return bool(invoicing.issued_for(store, ref))


def reached(ref: str, store: Path, *,
            template_dir: Path | None = None) -> list[Step]:
    """The seven, each with its answer. Never raises on a broken engagement.

    A step whose evidence cannot be read comes back False rather than blowing
    up the list it is drawn in: a stage bar is not a control, and a screen
    that 500s because one invoice file is malformed is worse than a screen
    with one mark missing. The one place that genuinely cannot tell -- the
    signature census -- says so with `None` instead.
    """
    store = Path(store)
    here = _dir(store, ref)

    def safe(fn, default=False):
        try:
            return fn()
        except Exception:                                      # noqa: BLE001
            return default

    import signing

    answers = {
        "sitting": (here / "interview.json").is_file(),
        "packed": (here / "pack" / "MANIFEST.json").is_file(),
        "sent": bool(safe(lambda: signing.sent_on(ref, store), "")),
        "signed": _signed(ref, store, template_dir),
        "billed": safe(lambda: _billed(store, ref)),
        "paid": safe(lambda: _paid(store, ref)),
        "closed": (here / "closeout.json").is_file(),
    }
    return [Step(key=key, name=name, reached=answers[key], why=PROOF[key])
            for key, name in STEPS]


def lit(steps: list[Step]) -> list[Step]:
    return [s for s in steps if s.reached is True]


def unknown(steps: list[Step]) -> list[Step]:
    return [s for s in steps if s.reached is None]
