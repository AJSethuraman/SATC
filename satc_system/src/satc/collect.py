"""Collecting what a client uploaded: from their folder to the pipeline.

Everything downstream of this module already worked -- split a combined scan,
classify each document by reading it, file it by client and year, match it to the
request it satisfies, mark that Received, stage the figures behind the
confirmation gate, draft the "still waiting on" email. What did not exist was the
first two links: getting the bytes from the firm's SharePoint upload folder onto
this machine, and knowing when they landed.

THE SOURCE IS BEHIND A SEAM, and the seam is the point.

Today the source is :class:`SyncedFolder` -- an ordinary directory that OneDrive
keeps in step with a SharePoint library. No app registration, no admin consent,
no client secret to store beside the one we just spent a week keeping out of the
repository. The entire integration is a path.

The alternative was the Microsoft Graph API, and it was rejected on evidence
rather than taste: `graph.microsoft.com` answers 403 on CONNECT from the build
environment, so a Graph adapter could be written here and never once run. Shipping
software nobody has watched work is the failure this practice's tenets exist to
stop. If the firm ever needs a headless pickup with the machine switched off,
Graph becomes a second class implementing the same two methods -- a file, not a
rewrite.

WHAT THIS MODULE PROMISES

* It never moves or deletes what the client uploaded. The copy they sent is the
  evidence of what they sent, as against what we decided it was.
* A file whose bytes are not on the disk is refused by name and NOT recorded as
  done, so it is collected on a later run once OneDrive has hydrated it.
* Running it twice collects nothing the second time. Idempotency is by content
  hash, kept in the firm's own library folder -- never written into the client's.
* A folder it cannot place is reported, never skipped. Silently ignoring a drop
  folder loses documents, which is the whole failure this replaces.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from satc.ingest.classify import (Classification, DocumentClassifier,
                                  load_classifier)
from satc.ingest.split import split_to_dir
from satc.models.actor import Actor

# The engagement ref every client document carries -- YYYY-NNNN, from
# client-documents/README.md. Naming the drop folder for it is what lets an
# arriving file already know whose it is.
REF = re.compile(r"\b(\d{4}-\d{4})\b")

# Where the firm's own bookkeeping for a collection lives. In OUR library folder,
# never in the client's upload folder: writing into a folder the client can see
# is both a surprise to them and a file we would then have to keep correct.
LEDGER = ".satc-collected.json"


@dataclass(frozen=True)
class Drop:
    """One client's upload folder, as found."""

    path: Path
    ref: str                      # "2026-0001", or "" when the name carries none
    label: str                    # the human remainder: "Maplewood"
    files: tuple[Path, ...] = ()

    @property
    def placed(self) -> bool:
        return bool(self.ref)


class Source(Protocol):
    """Where drop folders come from. Two methods, so a second one is a file."""

    def describe(self) -> str: ...
    def drops(self) -> list[Drop]: ...


class SyncedFolder:
    """Drop folders as an ordinary directory -- what OneDrive gives you.

    One subfolder per engagement, named for its ref so the software never has to
    guess whose a document is: ``2026-0001 — Maplewood``. The ref is read from
    anywhere in the name, so the firm can write it however reads best to them.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def describe(self) -> str:
        return f"synced folder {self.root}"

    def drops(self) -> list[Drop]:
        if not self.root.is_dir():
            return []
        out: list[Drop] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            files = tuple(sorted(p for p in child.iterdir()
                                 if p.is_file() and not p.name.startswith(".")))
            if not files:
                continue          # an empty folder is not an arrival
            m = REF.search(child.name)
            ref = m.group(1) if m else ""
            label = child.name.replace(ref, "").strip(" -–—_")
            out.append(Drop(path=child, ref=ref, label=label, files=files))
        return out


@dataclass
class Arrival:
    """One document that came in and where it went."""

    name: str                     # the file the client uploaded
    label: str                    # what we decided it is
    confidence: str
    method: str
    tax_year: int | None
    filed_to: str = ""            # relative to the library root, "" on preview
    note: str = ""
    satisfied: str = ""           # the request this closed, "" if none
    # Whether this verdict was good enough to CLOSE a request rather than just
    # to file the document. Carried from the classification so the rule stays
    # in one place -- see Classification.may_close_a_request.
    may_close: bool = False


@dataclass
class DropReport:
    drop: Drop
    client_id: str = ""           # resolved from the folder's ref, "" if unknown
    arrivals: list[Arrival] = field(default_factory=list)
    not_downloaded: list[str] = field(default_factory=list)
    unresolved: str = ""          # why this folder could not be placed


@dataclass
class Report:
    source: str
    drops: list[DropReport] = field(default_factory=list)
    applied: bool = False

    @property
    def collected(self) -> int:
        return sum(len(d.arrivals) for d in self.drops)

    @property
    def refused(self) -> int:
        return sum(len(d.not_downloaded) for d in self.drops)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ledger(folder: Path) -> set[str]:
    path = folder / LEDGER
    if not path.exists():
        return set()
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()              # a corrupt ledger re-collects; it never loses
    return set(got.get("digests", []))


def _remember(folder: Path, digests: set[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / LEDGER).write_text(
        json.dumps({"digests": sorted(digests)}, indent=2) + "\n", encoding="utf-8")


def _unique(folder: Path, name: str) -> Path:
    target = folder / name
    if not target.exists():
        return target
    stem, dot, ext = name.rpartition(".")
    n = 2
    while target.exists():
        target = folder / (f"{stem} ({n}).{ext}" if dot else f"{name} ({n})")
        n += 1
    return target


def collect(source: Source, *, library: str | Path, apply: bool = False,
            classifier: DocumentClassifier | None = None, store=None) -> Report:
    """Walk the source's drop folders and file what has arrived.

    ``apply=False`` previews: it reads and classifies but writes nothing, so the
    firm can see what a run would do before it does it -- the same shape as
    ``satc sort``.

    Refusals do NOT enter the ledger. A file with no bytes on the disk has not
    been collected, and recording it as done would mean the real document, once
    OneDrive hydrates it, is never picked up.

    ``store`` is OPTIONAL and closing the loop depends on it. Given one, a
    folder's ref is resolved to a client (``SATCStore.client_for_ref``) and
    each document good enough to trust is marked against the request it
    satisfies. Without one -- or when the ref is not in the store -- documents
    are still filed and the report says plainly that nothing was closed.
    Filing is useful on its own; guessing which client a document belongs to
    never is.
    """
    classifier = classifier or load_classifier()
    lib = Path(library)
    report = Report(source=source.describe(), applied=apply)

    for drop in source.drops():
        dr = DropReport(drop=drop)
        report.drops.append(dr)
        if store is not None and drop.ref:
            dr.client_id = store.client_for_ref(drop.ref) or ""
            if not dr.client_id:
                dr.unresolved = (
                    f"no engagement in the store carries the ref {drop.ref!r} -- "
                    f"the documents are filed, but nothing was marked Received. "
                    f"Set `engagement_ref` on that engagement and run this again.")
        if not drop.placed:
            dr.unresolved = (
                f"no engagement ref in the folder name {drop.path.name!r} -- name it "
                f"for the engagement (e.g. '2026-0001 — Maplewood') so an arriving "
                f"document knows whose it is")

        # Documents land under the ref when there is one; otherwise in a holding
        # folder of their own, still filed and still visible, never discarded.
        dest_root = lib / (drop.ref or "_unplaced")
        seen = _ledger(dest_root) if apply else set()
        fresh: set[str] = set()

        for path in drop.files:
            c = classifier.classify_path(path)
            if c.method == "not downloaded":
                dr.not_downloaded.append(path.name)
                continue          # deliberately NOT remembered -- see the docstring
            digest = _digest(path)
            # A digest already in the ledger is not re-copied -- but it may
            # still need to be RECONCILED. The ledger records that a file was
            # FILED, not that its request was ever closed: an unresolved ref
            # at filing time meant no reconciliation was even attempted, and
            # skipping the file here on every later run would leave it filed
            # but stuck outstanding, even after the firm sets engagement_ref.
            already_filed = digest in seen or digest in fresh
            if not already_filed:
                fresh.add(digest)
            for arrival in _file_one(path, c, dest_root, lib, classifier,
                                     apply and not already_filed):
                # CLOSE THE LOOP, and only when we are sure whose it is AND sure
                # enough what it is. Gating on `may_close` matters: a LOW verdict
                # off the file's name is good enough to FILE but not to tell a
                # client their request is satisfied -- see
                # Classification.may_close_a_request, the one place that rule
                # is written.
                if apply and store is not None and dr.client_id and arrival.may_close:
                    from satc.intake.service import reconcile_received
                    # THE ACTOR IS DERIVED FROM WHICH RUNG CLASSIFIED IT, same
                    # as state.py's equivalent path. Only the vision rung asks
                    # a model, and a model may not close a client's request on
                    # its own -- leaving classified_by at its INTAKE default
                    # here would bypass reconcile_received's own guard for
                    # every vision-classified arrival.
                    classified_by = (Actor.model("vision")
                                     if arrival.method == "vision"
                                     else Actor.system(f"classifier:{arrival.method}"))
                    matched = reconcile_received(
                        store, client_id=dr.client_id, doc_type=arrival.label,
                        doc_year=arrival.tax_year, classified_by=classified_by)
                    if matched is not None:
                        arrival.satisfied = matched.doc_type
                if not already_filed or arrival.satisfied:
                    dr.arrivals.append(arrival)

        if apply and fresh:
            _remember(dest_root, seen | fresh)

    return report


def _file_one(path: Path, c: Classification, dest_root: Path, lib: Path,
              classifier: DocumentClassifier, apply: bool) -> list[Arrival]:
    """One uploaded file -> one arrival per document inside it.

    A client's single upload is often several documents: a scanned stack of a
    W-2 then two 1099s. Splitting here rather than downstream means the register
    counts documents, which is what a request is about, rather than files, which
    is an accident of how the client used their scanner.
    """
    # The splitter writes each part out before we can file it, and those parts
    # are WORKING FILES, not documents. Writing them under the library left a
    # stray folder of duplicates beside the real ones -- found by running this,
    # not by reading it -- so they go to a scratch directory that is removed
    # whatever happens next.
    with tempfile.TemporaryDirectory(prefix="satc-collect-") as scratch:
        # Splitting runs on a PREVIEW TOO, into the same scratch directory that
        # is thrown away either way. It was once gated on `apply`, so a combined
        # upload previewed as one document and filed as two -- and the preview is
        # the thing the firm decides on. Splitting reads the file; it does not
        # write anything the caller keeps.
        parts: list[tuple[Classification, Path]] = []
        if path.suffix.lower() == ".pdf":
            try:
                parts = split_to_dir(path, Path(scratch), classifier)
            except Exception:     # noqa: BLE001 - a bad PDF is still a document
                parts = []
        if not parts:
            parts = [(c, path)]

        out: list[Arrival] = []
        for part_c, src in parts:
            filed = ""
            if apply:
                folder = dest_root / _safe(part_c.label)
                folder.mkdir(parents=True, exist_ok=True)
                target = _unique(folder, f"{_safe(part_c.label)}{src.suffix}")
                shutil.copy2(src, target)
                filed = str(target.relative_to(lib))
            out.append(Arrival(
                name=path.name, label=part_c.label, confidence=part_c.confidence,
                method=part_c.method, tax_year=part_c.tax_year, filed_to=filed,
                may_close=part_c.may_close_a_request,
                note="from a combined upload" if len(parts) > 1 else "",
            ))
        return out


def _safe(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", str(text)).strip() or "Unnamed"
