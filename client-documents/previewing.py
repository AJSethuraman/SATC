"""Looking at a document is not sending one.

THE FIRM, 2 September 2026, on being told every ad-hoc document would have to
pass the pre-send gate:

    this makes sense but what we need to be able to also like print it or
    something to screen - or a preview. something like it doesn't make sense
    to forcibly have one output

They are right, and the rule as first written conflated two different acts:

* **Looking** -- putting a document on screen, or printing a copy to read at
  your own desk. Nobody receives it. It must not be blocked by a failed check,
  because *a preview of a document that would fail is the most useful preview
  there is*: it is how somebody sees what is wrong before they act on it.
* **Sending** -- producing the artefact a client actually gets. That keeps the
  blocking gate exactly as it is, with the written reason and the log.

WHERE THAT LINE ACTUALLY FALLS, AND WHERE IT CANNOT. The distinction is the
ACT, not the file format, and this module cannot enforce an act. A preview is
served into a browser; a browser can print it, save it, and attach it to an
email. There is no version of "show it on screen" that prevents that.

So the defence is not prevention, it is MARKING: every preview carries the
stamp, in the repeating page header, on every page -- the same mechanism and
the same reason as `cli`'s draft stamp ("page two of an unstamped draft is
byte-identical to page two of the real letter"). A preview that reaches a
client is a preview that reaches them saying, on every sheet, that it is not
the copy that goes to the client. That is the whole of the protection, it is
stated here rather than implied, and if it is not enough the answer is a
different design and not a quieter one.

WHAT A PREVIEW STILL SHOWS. The gate runs. It just cannot stop anything. The
findings are on the page beside the document, so the preparer sees the problem
in the place they are already looking -- which is the point the firm was making.

SENDING ONE DOCUMENT ON ITS OWN, and the one refusal here that is not the
gate's. `packaging` exists because "an engagement letter without its fee
estimate asks somebody to sign for work at a price they have not been shown".
A one-document send is the back door to exactly that, so a document that
belongs in THIS engagement's signing pack may be looked at alone and may not be
sent alone. The rule is derived from `packaging.documents_for`, not listed
again here: a fifth return type added there is covered by this without anybody
remembering to.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import merge
import packaging
import presend


@dataclass
class Look:
    """What one document looks like right now, and what is wrong with it.

    NOTHING HERE IS A DECISION TO SEND. `ready` says the document would render
    strictly -- it is not permission, and `alone` is a separate question with a
    separate answer.
    """
    document: str
    html: str = ""
    # Empty when the document would render for real. Otherwise the merge's own
    # refusal, which names every field that is still blank.
    shortfall: str = ""
    check: presend.Result | None = None
    # Whether this document may be SENT by itself, and why not when it may not.
    alone: bool = False
    why_not_alone: str = ""
    # What is still blank, in the words a preparer knows them by. Descriptive
    # only -- `ready` is the merge's answer, not this list's.
    wanting: list = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.shortfall

    @property
    def blocking(self) -> list:
        return list(self.check.blocking) if self.check else []


def shelf(record: dict) -> list[str]:
    """Every document this engagement's file could produce, in the order of
    the engagement's own life.

    DERIVED FROM WHAT ALREADY DECIDES IT, three registries and no fourth list:
    the signing pack for this kind of return, the bill, and one document per
    lifecycle event. A fifth return type or a sixth event appears here without
    anybody remembering to add it.

    A document that no pack and no event names -- the bookkeeping engagement
    letter is the one, today -- is not on the shelf, because nothing in the
    software says when a client should get it. That is a gap in the pack
    definitions, not something to paper over here.
    """
    import lifecycle
    try:
        pack = packaging.documents_for(record)
    except packaging.PackageError:
        pack = []
    out = list(pack) + ["invoice"]
    for key in sorted(lifecycle.load()):
        doc = lifecycle.event(key).document
        if doc not in out:
            out.append(doc)
    return out


def alone_ok(record: dict, doc: str) -> tuple[bool, str]:
    """May this document be sent on its own? Derived, never listed.

    The pack is the unit for anything a client signs. Re-printing the
    engagement letter means building the pack again -- which needs no
    interview and already works -- not sending the letter by itself.
    """
    try:
        pack = packaging.documents_for(record)
    except packaging.PackageError:
        # We cannot tell what this engagement's pack is, so we cannot tell
        # whether this document belongs to it. Refuse rather than guess: the
        # guess that costs something is the permissive one.
        return False, ("Nothing here says what kind of return this is, so "
                       "there is no way to tell whether this document travels "
                       "with the others. Nothing was sent.")
    if doc in pack:
        return False, ("This goes out with the rest of the signing pack, not "
                       "on its own — nobody should be asked to sign for work "
                       "without the price in front of them. Build the signing "
                       "pack again to get a fresh copy; it needs no interview.")
    return True, ""


def wanting(tokens: dict, labels: dict, shortfall: str) -> list[str]:
    """What this document still has no answer for, named as a person names it.

    NOT THE MERGE'S REFUSAL ITSELF. That message is written for whoever is
    filling a template -- "unresolved fields: <<SignatureDeadline>>" -- and a
    preparer mid-call should never be shown it, which is the whole of
    `plainspoken`'s complaint one surface over. Same facts, their own words.

    THE MERGE STAYS THE AUTHORITY. This does not decide what is required; it
    reads the names out of the refusal and looks each one up. A blank the
    document is happy to leave blank -- an invoice with no credit on it -- is
    not in the refusal and so is not listed here. Listing it would tell a
    preparer that a document which renders perfectly is missing something.
    """
    if not shortfall:
        return []
    asked = _one_question_per_pair()
    out, seen = [], set()
    for kind in ("fields", "lists", "flags"):
        for name in sorted(tokens.get(kind) or ()):
            if name not in shortfall:
                continue
            # TWO FLAGS ARE ONE QUESTION. "Nothing to pay with the extension"
            # and "A payment goes with the extension" listed side by side as
            # two missing things reads as a contradiction; they are one answer
            # nobody has given. `lifecycle` already knows which pairs, and
            # already knows what the question sounds like out loud.
            said = asked.get(name) or labels.get(name) or name
            if said in seen:
                continue
            seen.add(said)
            out.append(said)
    return out


def _one_question_per_pair() -> dict:
    """{flag -> the question it is half of}, for every paired lifecycle flag."""
    import lifecycle
    out = {}
    for key in lifecycle.load():
        for q in lifecycle.event(key).questions:
            for flag in (q.get("pair") or {}).values():
                out[flag] = q.get("question") or flag
    return out


def look(record: dict, doc: str, *, merge_one, stamp, template_dir: Path,
         filename: str, tokens: dict | None = None,
         labels: dict | None = None) -> Look:
    """One document, on screen, with everything the gate would say about it.

    `merge_one(doc, record, draft) -> MergeResult` and
    `stamp(html, labels) -> html` are the caller's, for the same reason
    `sending.build` takes `render`: the template machinery lives in `cli`
    beside the PDF engines, and importing it here would be a cycle.

    Writes nothing outside a temporary directory it removes.
    """
    out = Look(document=doc)
    out.alone, out.why_not_alone = alone_ok(record, doc)

    # WOULD IT GO OUT AS IT STANDS? Asked first and separately, because the
    # answer is the most useful line on a preview and it is not the gate's:
    # the gate reads a rendered document, and this is about one that may not
    # render at all.
    try:
        merge_one(doc, record, False)
    except merge.MergeError as exc:
        out.shortfall = str(exc)
    if tokens is not None:
        out.wanting = wanting(tokens, labels or {}, out.shortfall)

    # AND THEN THE DOCUMENT ITSELF, rendered past whatever is missing. A
    # preview that refuses is a preview of nothing, and the case where it
    # would refuse is the case somebody most needs to see.
    result = merge_one(doc, record, True)
    out.html = stamp(result.html, labels or {})

    staging = Path(tempfile.mkdtemp(prefix="satc-look-"))
    try:
        page = staging / f"{filename}.html"
        # THE UNSTAMPED TEXT IS WHAT THE GATE READS. The stamp is for the
        # person; the checks are about what a client would get, and a check
        # reading our own banner would be checking us.
        page.write_text(result.html, encoding="utf-8")
        for asset in presend.PACK_ASSETS:
            src = Path(template_dir) / asset
            if src.exists():
                shutil.copy2(src, staging / asset)
        book = packaging.manifest(record, [doc], {doc: [page]})
        (staging / "MANIFEST.json").write_text(
            json.dumps(book, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        # `skip_render` because a preview has to come back while somebody is
        # waiting, and opening the document in a second browser costs a minute.
        # The gate reports the skip itself; nothing here hides it.
        out.check = presend.gate(staging, record, rendered={doc: result.html},
                                 skip_render=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return out


def asset(template_dir: Path, name: str) -> Path | None:
    """The stylesheet or the script a preview needs, or None for anything else.

    A preview is served at its own address so a browser can open it, print it
    and scale it like the page it is -- which means the two files every
    template links have to be served beside it. The allow-list is
    `presend`'s, so a preview cannot serve a file a pack would not carry, and
    a name that is not one of them gets nothing rather than whatever happens
    to sit at that path.
    """
    if name not in presend.PACK_ASSETS:
        return None
    found = Path(template_dir) / name
    return found if found.is_file() else None
