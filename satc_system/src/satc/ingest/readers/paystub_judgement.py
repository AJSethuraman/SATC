"""When a local model may be asked about a paystub, and what its answer IS.

THE FIRM, 31 August 2026:

    "Another piece to the ocr is the fallback to ollama for judgmental
     processing. I really want it deterministic first though"

    "same care in diligence of control setting"

"Deterministic first" is not a preference about ordering. It is a boundary, and
a boundary needs three things written down: WHEN the model may be reached, WHAT
it is allowed to be asked, and WHAT ITS ANSWER IS when it comes back. This
module is all three, and `tests/test_paystub_columns.py` fails if any of them
gives way.

1 · WHEN. Only after :class:`PaystubColumnReader` has said, in writing, that it
    cannot tell. Not "returned nothing" — SAID SO, with a reason code. The
    difference matters: a reader that crashed, or whose labels drifted, also
    returns nothing, and firing a model at that hides a fixable parser gap under
    an answer nobody can reproduce. `test_the_ladder_reaches_no_model_while_a_
    deterministic_rung_can_still_read` already makes this argument for the
    document ladder; this is the same argument one document down.

2 · WHAT. Only the fields it said it could not tell, and only for the reasons in
    :data:`ASKABLE`. A CONTRADICTION IS NEVER ASKABLE. When two pages give
    different year-to-date figures, or the printed schedule fights the printed
    dates, the fact that the stub disagrees with itself IS the finding — it is
    what the preparer has to take back to the client. A model handed that will
    resolve it, fluently, and the finding is gone. So a model is asked to read
    what is printed, never to decide which of two printed things is true.

3 · WHAT ITS ANSWER IS. Not a figure. A :class:`Claim` — the model's reading,
    the page it read, and why it was asked at all. A claim is not in
    `labeled_fields` and cannot get there by accident: :func:`with_claims` is
    the only path, it refuses to overwrite anything the deterministic reader
    answered, and everything it merges arrives flagged for review on a result
    that has stopped calling itself deterministic. `ReadResult.confidence_map`
    then puts every one of them at LOW, and `auto_confirm_high` never sees them.

WHAT NONE OF THIS BUYS. A model that reads a column heading wrong produces a
claim that is wrong, marked as a claim. The control here is not that the answer
is right — it is that the answer never stops looking like an answer from a
model. That distinction is the whole of `docs/SOFTWARE-TENETS.md` S31, and it is
the only thing a boundary can honestly promise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.paystub_columns import PaystubRead

# The reasons a person would reasonably hand to somebody else to look at.
ASKABLE: frozenset[str] = frozenset({
    "no_columns",       # the stub never named its columns — read the page and judge
    "not_found",        # nothing carries the label we know — it may be worded oddly
    "column_unclear",   # a figure sits between two columns
})

# The reasons that are findings, not gaps. Written out so the next person sees
# the argument rather than the set.
NEVER_ASKABLE: dict[str, str] = {
    "rows_disagree": "the stub states this figure twice, differently — a person must choose",
    "pages_disagree": "two pages of the stub disagree — a person must choose",
    "ytd_below_period": "the stub's own figures contradict each other",
    "frequency_conflict": "the printed schedule and the printed dates disagree",
    "frequency_unknown": "no schedule is printed anywhere; there is nothing to read",
}


class ModelBoundary(RuntimeError):
    """Raised when something tries to reach a model outside the boundary."""


@dataclass(frozen=True, slots=True)
class Claim:
    """A model's reading. Never a value; always a claim, with why it was asked."""

    label: str
    value: str
    page: int
    asked_because: str
    source: str

    def as_note(self) -> str:
        """What a preparer is shown beside the box, in their words not ours."""
        return (f"Read off page {self.page} by the model on this machine, because "
                f"{self.asked_because} Check it against the stub before using it.")


def askable(read: PaystubRead) -> dict[str, str]:
    """``{label: why}`` for the fields a model may be asked about — and no others."""
    out: dict[str, str] = {}
    for fig in read.figures.values():
        if fig.read or fig.reason_code not in ASKABLE:
            continue
        out[fig.label] = fig.problem
    return out


def ask(read: PaystubRead, *, page: int, source: str,
        transport: Callable[[list[str]], dict[str, str]]) -> list[Claim]:
    """Ask a local model about the fields the deterministic reader gave up on.

    ``transport`` takes the list of labels being asked about and returns
    ``{label: printed text}``. It is injected so the boundary is testable with
    no Ollama, no model and no network — and so the test can assert the exact
    set of labels that crossed it.
    """
    wanted = askable(read)
    if not wanted:
        raise ModelBoundary(
            "Nothing to ask a model about: every figure was either read or "
            "refused for a reason a person has to settle.")
    answers = transport(sorted(wanted))
    claims: list[Claim] = []
    for label, why in sorted(wanted.items()):
        value = answers.get(label)
        if value is None or str(value).strip() == "":
            continue
        claims.append(Claim(label=label, value=str(value).strip(), page=page,
                            asked_because=why, source=source))
    return claims


def with_claims(read: PaystubRead, claims: list[Claim]) -> ReadResult:
    """Merge claims into a read result — as claims, and only as claims."""
    result = read.to_read_result()
    if not claims:
        return result
    for claim in claims:
        if claim.label in result.labeled_fields:
            raise ModelBoundary(
                f"A model's answer would have overwritten a figure this software "
                f"read off the stub itself ({claim.label}).")
        result.labeled_fields[claim.label] = claim.value
        result.uncertain_labels.add(claim.label)
        result.pages[claim.label] = claim.page
    # THE READ AS A WHOLE STOPS BEING DETERMINISTIC. Not the field — the read.
    # `ReadResult.deterministic` is a property of the READER, and the reader
    # that produced this output now includes a model. Marking only the claim
    # would leave a result that calls itself reproducible and is not.
    result.deterministic = False
    result.backend = f"{result.backend}+{claims[0].source}"
    return result


def ollama_transport(page_image_b64: str, *, model: str, host: str,
                     http: Callable[[dict], dict] | None = None
                     ) -> Callable[[list[str]], dict[str, str]]:
    """A transport backed by the local Ollama vision model.

    Deliberately thin, and deliberately not a reader: it answers the question
    `ask` poses and has no way to reach a record. `readers/ollama.py` is the
    document-ladder rung and keys on an extraction map's field paths; a paystub
    has no such map, so the prompt is built from the labels being asked about
    and nothing else.
    """
    import json

    def _call(labels: list[str]) -> dict[str, str]:
        prompt = (
            "This is one page of a payroll pay stub. For each item below, return "
            "the EXACT printed figure from the page, or null if it is not printed "
            "there. Do not calculate, do not infer, do not convert. Return only a "
            "JSON object keyed by the item text.\n"
            + "\n".join(f"- {label}" for label in labels))
        payload = {"model": model, "stream": False, "format": "json",
                   "messages": [{"role": "user", "content": prompt,
                                 "images": [page_image_b64]}]}
        if http is not None:
            data = http(payload)
        else:                                    # pragma: no cover - live Ollama
            import urllib.request
            req = urllib.request.Request(
                host.rstrip("/") + "/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, TypeError):
            return {}
        return {k: v for k, v in (parsed or {}).items()
                if k in labels and v is not None}

    return _call
