"""Building a signing pack: the decisions, with no front door attached.

**One engine, two front doors**, for the same reason `intake.py` exists. Every
rule below used to live inside `cli.cmd_package` -- the terminal's own code
path -- interleaved with the `print()` calls that reported it. Anything driving
the pipeline any other way would have got none of it:

* the pre-send gate would not have run, so a pack that does not survive being
  opened could be written and sent,
* `--force` would have had no counterpart, so an override would go unlogged,
  and an override with no record is just a quieter way to send a pack that did
  not pass,
* a merge failure in one document would still have written the others, and a
  pack with a hole in it is worse than no pack at all -- the client signs what
  arrived and the rest turns up later saying something different,
* the output directory would not have been checked, so a complete pack from a
  DIFFERENT engagement could sit in it looking current.

`build()` returns a `Pack` -- a decision and a set of facts, not a printed
message. The CLI renders it as text, a web view renders it as a page, a test
asserts on it. Neither door can write a pack without going through the gate,
because writing it is inside this function and nowhere else.

RENDERING IS PASSED IN. The template machinery lives in `cli` alongside the
PDF engines and the draft stamp, and importing it here would be a cycle. What
this module owns is the ORDER and the REFUSALS: what is rendered where, what
is checked before anything is written, and what happens when a check fails.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import engagements
import merge
import notes as notes_mod
import packaging
import presend


@dataclass
class Pack:
    """What building a pack decided.

    `status` is the machine-readable answer and the only thing a caller should
    branch on:

    * `written`       -- everything rendered, the gate passed (or was
                         deliberately overridden and logged), the pack is in
                         `outdir`
    * `not-ours`      -- `outdir` holds somebody else's files; nothing touched
    * `refused-merge` -- one or more documents would not render; nothing written
    * `refused-gate`  -- the gate blocked and nothing overrode it
    * `no-reason`     -- an override was asked for without a reason for it
    * `not-logged`    -- the override could not be recorded, so it did not
                         happen; the log is the only thing that makes an
                         override different from no gate at all

    Every status but `written` means NOTHING WAS WRITTEN, and they are kept
    distinct because they are five different things to whoever reads them.
    """
    status: str
    outdir: Path
    documents: list[str] = field(default_factory=list)
    written: dict[str, list[Path]] = field(default_factory=dict)
    # (document, why) for each one that refused to render.
    refused: list[tuple[str, str]] = field(default_factory=list)
    check: presend.Result | None = None
    # The advisory half, only when it was asked for. Never stops anything.
    readings: list = field(default_factory=list)
    manifest: dict | None = None
    manifest_json: str = ""
    # The ref of a pack this code wrote into `outdir` before, if any. On a
    # refusal it is the warning: that pack is still there and is not this one.
    stale: str = ""
    # Where the override went, when one was recorded.
    override: str = ""
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "written"


def previous_pack(outdir: Path) -> str | None:
    """The engagement ref of a pack this code wrote here before, or None.

    None means either an empty/absent directory or one we do not recognise --
    the caller tells those apart, because they need different answers.
    """
    book = outdir / "MANIFEST.json"
    if not book.is_file():
        return None
    try:
        return json.loads(book.read_text(encoding="utf-8")).get(
            "EngagementRef") or "an earlier engagement"
    except (OSError, ValueError):
        return "an earlier engagement"


@dataclass
class GateOutcome:
    """What the gate said about a staged set of documents, and what to do."""

    status: str = "passed"      # passed | refused-gate | no-reason | not-logged
    check: object = None
    override: str = ""
    detail: str = ""

    @property
    def may_write(self) -> bool:
        return self.status == "passed"


def gate_staged(staging: Path, record: dict, *, rendered: dict[str, str],
                documents: list[str], written: dict[str, list],
                ref: str = "", store: Path | None = None,
                command: str = "render", force: bool = False,
                reason: str = "", skip_render: bool = False,
                whole_pack: bool = True,
                attach: "list[str] | None" = None) -> GateOutcome:
    """Run the pre-send gate over documents staged but not yet delivered.

    **THE SECOND FRONT DOOR HAD NO GATE AT ALL.** `presend.gate` had exactly two
    callers -- `build` below and `previewing.preview` -- and neither was on the
    path `cli.py event` takes. So the delivery letter, the organizer cover, the
    extension notice, the disengagement letter and the invoice via `render`
    reached clients unchecked. `docs/WHERE-THINGS-STAND.md` called it "the
    biggest hole still open"; `CLAUDE.md` and `docs/REPO-INVENTORY.md`
    meanwhile both asserted that *every* document a client receives passes a
    blocking gate, which was the more dangerous half -- a gap invites a look and
    a false claim forecloses one.

    Extracted rather than duplicated. `build` had the whole discipline already
    -- manifest before gate, blocking refusal, an override that must carry a
    reason and must be logged or it does not happen -- and a second copy of that
    in `cli` would be two implementations of one policy, drifting apart from the
    day it was written.

    THE MANIFEST GOES IN FIRST, for the reason `build` states: a rendered
    document is named for the client, so nothing about the file says which
    template it came from, and `compliance_floor` and `pointer_test` refuse
    without it.

    AN OVERRIDE THAT CANNOT BE LOGGED IS REFUSED. Forcing past a gate with no
    trace is the thing this design exists to prevent, so a run with no
    engagement ref -- a one-off render from a record file -- cannot be forced at
    all, and says so rather than silently allowing it.
    """
    book = packaging.manifest(record, documents, written, attach)
    (staging / "MANIFEST.json").write_text(
        json.dumps(book, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    check = presend.gate(staging, record, rendered=rendered,
                         skip_render=skip_render, whole_pack=whole_pack)
    out = GateOutcome(check=check)
    if not check.blocking:
        return out
    if not force:
        out.status = "refused-gate"
        return out

    why = (reason or "").strip()
    if not why:
        out.status = "no-reason"
        return out
    if not ref or store is None:
        out.status = "not-logged"
        out.detail = ("there is no engagement to record the override against -- "
                      "a forced send with no trace is exactly what the log "
                      "exists to prevent. Render from --engagement, not a "
                      "record file, if this has to go out.")
        return out

    entry = {
        "at": _dt.datetime.now(_dt.timezone.utc)
              .replace(microsecond=0).isoformat(),
        "command": command,
        "reason": why,
        "failed": [{"check": f.check, "document": f.document,
                    "detail": f.detail} for f in check.blocking],
    }
    try:
        out.override = str(engagements.record_override(ref, entry, store))
    except Exception as exc:                                # noqa: BLE001
        out.status = "not-logged"
        out.detail = str(exc)
    return out


def build(record: dict, outdir: Path, *, render, ref: str, store: Path,
          template_dir: Path, documents: list[str], want_pdf: bool = True,
          attach=None, skip_render: bool = False, readings: bool = False,
          force: bool = False, reason: str = "") -> Pack:
    """Render, gate, and only then write. ATOMIC is the point.

    Everything is rendered into a temporary directory and checked there, and
    `outdir` is only touched once every document has succeeded and the gate has
    passed. That is why a refusal costs nothing and leaves no half-pack behind.

    `render(doc, record, into, draft, want_pdf) -> (result, files)` is the
    caller's -- see the module docstring.
    """
    outdir = Path(outdir)
    # WHOSE DIRECTORY IS THIS? Found by testing the refusal path: a run that
    # refuses leaves whatever was already in `outdir` untouched, so a complete
    # pack from a DIFFERENT engagement sits there looking current, and the
    # person who reads "No pack written" and then opens the folder finds one.
    # That is the failure this exists to prevent, arriving by the back door.
    #
    # So the pack owns its directory. A folder we wrote before (it has our
    # MANIFEST) is replaced wholesale. A folder with anything else in it is
    # somebody's, and we do not touch it.
    stale = previous_pack(outdir)
    if stale is None and outdir.exists() and any(outdir.iterdir()):
        return Pack(status="not-ours", outdir=outdir, documents=documents)

    staging = Path(tempfile.mkdtemp(prefix="satc-pack-"))
    written: dict[str, list[Path]] = {}
    refused: list[tuple[str, str]] = []
    try:
        rendered: dict[str, str] = {}
        for doc in documents:
            try:
                result, files = render(doc, record, staging, False, want_pdf)
                written[doc] = files
                rendered[doc] = result.html
            except merge.MergeError as exc:
                refused.append((doc, str(exc)))

        if refused:
            return Pack(status="refused-merge", outdir=outdir,
                        documents=documents, written=written, refused=refused,
                        stale=stale or "")

        # THE HTML IS NOT SELF-CONTAINED. Every template links `satc-doc.css`
        # and `doc-page.js` by relative path, so a pack folder holding only
        # HTML opens as UNSTYLED PLAIN TEXT -- the whole document, no masthead,
        # no rules, no layout. Found by the firm, opening one: "these html
        # files are plain text?"
        #
        # They go into STAGING, before the gate -- a gate that inspects a pack
        # the assets have not reached yet would fail every time for the wrong
        # reason.
        for asset in presend.PACK_ASSETS:
            src = template_dir / asset
            if src.exists():
                shutil.copy2(src, staging / asset)

        # THE MANIFEST GOES IN BEFORE THE GATE, NOT AFTER, and until that was
        # true two of the eight blocking checks had never examined anything on
        # a real send. A rendered document is named for the client, so nothing
        # about the file on disk says which template it came from; the manifest
        # is the only thing that knows, and both `compliance_floor` and
        # `pointer_test` refuse without it.
        book = packaging.manifest(record, documents, written, attach)
        manifest_json = json.dumps(book, indent=2, ensure_ascii=False) + "\n"
        (staging / "MANIFEST.json").write_text(manifest_json, encoding="utf-8")

        # THE GATE. The firm's choice, 27 August 2026: blocking, with a logged
        # override. Nothing has been written to `outdir` yet.
        check = presend.gate(staging, record, rendered=rendered,
                             skip_render=skip_render)
        # THE ADVISORY HALF, AND IT IS OPT-IN. Exact tenets block, judgement
        # ones advise. An advisory printed beside a blocking failure every
        # single time is an advisory people learn to scroll past, and they take
        # the eight real gates with them.
        read = notes_mod.review(staging) if readings else []

        out = Pack(status="written", outdir=outdir, documents=documents,
                   written=written, check=check, readings=read, manifest=book,
                   manifest_json=manifest_json, stale=stale or "")

        if check.blocking and not force:
            out.status = "refused-gate"
            return out

        if check.blocking and force:
            why = (reason or "").strip()
            if not why:
                out.status = "no-reason"
                return out
            entry = {
                "at": _dt.datetime.now(_dt.timezone.utc)
                      .replace(microsecond=0).isoformat(),
                "command": "package",
                "reason": why,
                "failed": [{"check": f.check, "document": f.document,
                            "detail": f.detail} for f in check.blocking],
            }
            try:
                out.override = str(engagements.record_override(ref, entry,
                                                               store))
            except Exception as exc:                        # noqa: BLE001
                # Refuse rather than send unlogged. The override IS the record;
                # forcing past a gate with no trace is the thing this design
                # exists to prevent.
                out.status = "not-logged"
                out.detail = str(exc)
                return out

        # Replace, do not merge. An entity pack written over an individual one
        # would leave two engagement letters in the folder, and whoever sends
        # it picks the wrong one.
        if stale is not None and outdir.exists():
            for old_file in outdir.iterdir():
                if old_file.is_file():
                    old_file.unlink()
        outdir.mkdir(parents=True, exist_ok=True)
        moved: dict[str, list[Path]] = {}
        for doc, files in written.items():
            moved[doc] = [Path(shutil.copy2(f, outdir / f.name)) for f in files]
        for asset in presend.PACK_ASSETS:
            staged = staging / asset
            if staged.exists():
                shutil.copy2(staged, outdir / asset)
        out.written = moved
        # The SAME manifest the gate read, byte for byte. Rebuilding it here
        # from `moved` would be a second construction of a thing that must
        # agree with the first -- and the one the client gets would be the one
        # nothing checked.
        (outdir / "MANIFEST.json").write_text(manifest_json, encoding="utf-8")
        return out
    finally:
        shutil.rmtree(staging, ignore_errors=True)
