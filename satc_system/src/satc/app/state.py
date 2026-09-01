"""Application state for the SATC prototype — backed by the SQLite store.

The durable data (clients, returns, documents, statuses, line items,
carryforwards, engagements) lives in the SQLite store and survives restarts. The
staging gate is a per-session working area, re-derived from the documents on
hand. This is the vault-side UI, so it may resolve client_id -> name from the
vault for display; everything it persists to the mart is de-identified.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from satc.config import load_extraction_map
from satc.fixtures import synthetic_documents
from satc.ids import return_key
from satc.ingest import (
    MAPPING_1040,
    MapExtractor,
    StagingGate,
    load_classifier,
    split_to_dir,
)
from satc.ingest.readers import (
    OllamaVisionReader,
    PdfFormReader,
    TesseractOcrReader,
    TextAnchorReader,
    VisionDocumentReader,
)
from satc.models.mart import DataMart, DocumentRecord, ReturnRecord
from satc.persistence import SATCStore
from satc.settings import cloud_vision_enabled

# Status flow for a document in the repository.
DOC_FLOW = ["Requested", "Received", "Sent", "Signed", "N/A"]

# Friendly names for the reader backends (shown in intake notes).
_READER_LABELS = {
    "PdfFormReader": "fillable form fields (free)",
    "TextAnchorReader": "text layer (free)",
}


# How much text a PDF must carry before we call its text layer usable. A page of
# a real form runs to hundreds of characters; a stray watermark or a scanner's
# empty /Contents can leave a handful. Set low on purpose -- the point is to tell
# "nothing to read" from "something to read", not to judge quality.
TEXT_LAYER_MIN = 40


def _skipped_note(pages: list[int]) -> str:
    """What to say when the page rule left pages out. Empty when it did not."""
    if not pages:
        return ""
    which = ", ".join(str(p) for p in pages)
    return (f"read from the form's own pages; page{'s' if len(pages) > 1 else ''} "
            f"{which} looked like the instructions and {'were' if len(pages) > 1 else 'was'} "
            f"not read. ")


def text_layer_chars(fpath) -> int:
    """How much real text this PDF carries -- asked of the FILE, not of a reader.

    THE DISTINCTION THIS EXISTS TO MAKE. "This document has no text to read" and
    "our reader could not read this document's text" are different facts, and the
    reader ladder used to conflate them: its only question at each rung was
    whether that rung returned any fields. So a software-printed W-2 with a
    perfectly good text layer, whose labels our anchors were never written for,
    fell through to OCR exactly as a photograph would. OCR then rasterised a
    document that already had text and read it worse -- and the note it produced
    looked exactly like a success, so the parser bug stayed invisible.

    The firm, 30 August 2026: *"it was not smart enough for some reason even
    though I suggested it to use PDF scanning over OCR when applicable."* It was
    applicable. Nothing in the ladder could tell.

    Never raises. A truncated download, a OneDrive placeholder with no bytes, or
    a file that is not a PDF at all is "no text" -- the ladder's job is to keep
    going and say what it saw, not to fall over on a bad file.
    """
    from pathlib import Path

    path = Path(fpath)
    if path.suffix.lower() != ".pdf":
        return 0
    try:
        import pymupdf

        with pymupdf.open(str(path)) as doc:
            if doc.page_count == 0:
                return 0
            # EVERY PAGE, not page one. This asked `doc[0]` alone, and page 1 of
            # a real IRS document is routinely a notice -- so a SCANNED W-2
            # whose eleven form pages carry no text at all still answered 1754
            # characters, because the notice ahead of them had a text layer.
            # The ladder then took the text rung, matched nothing, and blamed
            # OUR ANCHORS for a document that is a pure image; and because that
            # blame sets `unread`, both model rungs were skipped -- on the one
            # document class they exist for.
            #
            # Summing is the right shape as well as the safe one: the question
            # is "is there text in this document to read", and the ladder that
            # reads it now reads the form's pages, not page one.
            return sum(len(page.get_text().strip()) for page in doc)
    except Exception:       # noqa: BLE001 -- an unreadable file has no text layer
        return 0


@dataclass
class AppState:
    store: SATCStore = field(default_factory=lambda: SATCStore(os.environ.get("SATC_DATA_DIR")))
    mart: DataMart = field(default_factory=DataMart)
    names: dict[str, str] = field(default_factory=dict)
    gate: StagingGate = field(default_factory=StagingGate)
    intake_summary: dict = field(default_factory=dict)
    posted_summary: dict = field(default_factory=dict)
    # Absolute paths of the files read in the last intake — the allow-list the
    # /source route serves from, so Staging can show a value next to its document.
    intake_sources: set = field(default_factory=set)
    # The client/year the current intake is for — set when reading a client's folder,
    # so Staging → Post targets the right return (defaults to the demo client).
    intake_context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.store.seed_if_empty()           # first run: populate from synthetic fixtures
        # Layer the practice's in-app questionnaire edits over the built-in workflows.
        from satc.intake.workflows import set_override_provider
        set_override_provider(self.store.load_workflow_override)
        self.reload()
        # Seed the working staging gate with the sample documents ONLY while the
        # built-in sample data is present, so a cleared practice never shows phantom
        # "reads" it never actually performed. Real intake replaces this gate.
        if self.has_sample_data():
            for doc in synthetic_documents():
                cfg = load_extraction_map(doc["doc_key"])
                self.gate.add(MapExtractor(cfg).extract(
                    document_id=doc["document_id"], client_id="SATC-001000",
                    tax_year=2024, labeled_fields=doc["labeled"]))

    def reload(self) -> None:
        self.mart = self.store.load_mart()
        self.names = self.store.names()

    # -- display helpers --------------------------------------------------
    def name(self, client_id: str) -> str:
        return self.names.get(client_id, client_id)

    def public_client(self, client_id: str):
        """The de-identified projection for a client (or ``None``)."""
        return next((c for c in self.mart.public_clients if c.client_id == client_id), None)

    def client_email(self, client_id: str) -> str:
        """A client's contact email (from the vault) for pre-filling drafts."""
        return self.store.client_email(client_id)

    def filing_status(self, client_id: str) -> str:
        pc = self.public_client(client_id)
        return getattr(pc, "filing_status", "") if pc else ""

    def set_filing_status(self, client_id: str, filing_status: str) -> None:
        self.store.set_filing_status(client_id, filing_status)
        self.reload()

    # -- new vs returning client (drives the branched interview) ----------
    def is_returning(self, client_id: str) -> bool:
        """A client we've worked with before — prior engagement OR a return on file."""
        if any(e.client_id == client_id for e in self.store.load_intake_engagements()):
            return True
        return any(r.client_id == client_id for r in self.mart.returns)

    def prior_engagement(self, client_id: str, workflow_key: str = ""):
        """Most recent prior engagement for a client — preferring the same workflow.

        Used to pre-fill a returning client's interview with last year's answers.
        """
        engs = [e for e in self.store.load_intake_engagements() if e.client_id == client_id]
        if workflow_key:
            same = [e for e in engs if e.workflow_key == workflow_key]
            if same:
                return same[-1]
        return engs[-1] if engs else None

    def documents(self) -> list[DocumentRecord]:
        return self.mart.documents

    def outstanding(self) -> list[DocumentRecord]:
        return [d for d in self.mart.documents if d.status == "Requested"]

    def returns(self):
        return self.mart.returns

    def clients(self) -> list[str]:
        seen: list[str] = []
        for r in self.mart.returns:
            if r.client_id not in seen:
                seen.append(r.client_id)
        return seen

    # -- mutations (write through to the store) ---------------------------
    def set_document_status(self, document_id: str, status: str) -> None:
        if status not in DOC_FLOW:
            return
        self.store.set_document_status(document_id, status)   # durable
        for d in self.mart.documents:                          # keep view in sync
            if d.document_id == document_id:
                d.status = status

    def confirm_field(self, field_id: str) -> None:
        self.gate.confirm(field_id, by="preparer (UI)")

    def reject_field(self, field_id: str) -> None:
        self.gate.reject(field_id, by="preparer (UI)")

    def unconfirm_field(self, field_id: str) -> None:
        self.gate.unconfirm(field_id)

    def delete_field(self, field_id: str) -> None:
        self.gate.delete_field(field_id)

    def edit_field(self, field_id: str, raw_value: str) -> None:
        """Hand-correct a staged value (parses money the same conservative way reads do)."""
        from satc.ingest.extractors.base import parse_money
        amount, _conf, _note = parse_money(raw_value)   # None if it isn't a clean number
        self.gate.edit(field_id, value_text=raw_value.strip(), value_amount=amount)

    def auto_confirm(self) -> int:
        return self.gate.auto_confirm_high(by="auto (UI)")

    # -- sample data (the built-in demo) ----------------------------------
    def _sample_client_ids(self) -> set[str]:
        from satc.fixtures import synthetic_identities
        return {rec.client_id for rec in synthetic_identities()}

    def has_sample_data(self) -> bool:
        """Whether the built-in sample clients are still present (un-cleared)."""
        sample = self._sample_client_ids()
        return any(pc.client_id in sample for pc in self.mart.public_clients)

    def clear_sample_data(self) -> int:
        """Remove every built-in sample client (and the seeded demo staging gate)."""
        from satc.ingest import StagingGate
        present = [pc.client_id for pc in self.mart.public_clients
                   if pc.client_id in self._sample_client_ids()]
        for cid in present:
            self.store.delete_client(cid)
        self.gate = StagingGate()
        self.intake_summary = {}
        self.reload()
        return len(present)

    def delete_client(self, client_id: str) -> None:
        """Discard a client everywhere (vault + mart + any staged fields)."""
        self.store.delete_client(client_id)
        self.gate.documents = [d for d in self.gate.documents if d.client_id != client_id]
        self.reload()

    # -- intake: actually read the files in a folder ----------------------
    def run_intake(self, folder: str, *, client_id: str = "SATC-001000",
                   tax_year: int = 2024) -> dict:
        """Read every file in ``folder`` and stage the values. Returns a summary.

        Each file is classified by *content* — not its name — so a W-2 named
        ``scan001.pdf`` is still recognized. A combined multi-form PDF is split into
        its parts first, and each document is read by the cheapest sufficient
        backend: fillable form fields, then the free text layer, then vision.
        """
        import os
        import tempfile

        from satc.intake import matching, reconcile_received
        from satc.intake.service import outstanding_parts

        # L8: if an intake root is configured, refuse folders outside it so an
        # agent-supplied path can't reach arbitrary directories. No-op when unset.
        root = os.environ.get("SATC_INTAKE_ROOT")
        if root:
            root_p, folder_p = Path(root).resolve(), Path(folder).resolve()
            if root_p != folder_p and root_p not in folder_p.parents:
                raise ValueError(f"intake folder {folder} is outside SATC_INTAKE_ROOT ({root})")

        self.intake_context = {"client_id": client_id, "tax_year": tax_year}
        self.gate = StagingGate()          # fresh working area for this intake
        self.intake_sources = set()        # allow-list of source files for /source
        files_read = 0
        fields_staged = 0
        reconciled = 0
        notes: list[str] = []
        allow_cloud = cloud_vision_enabled()   # OFF unless the practice opts in
        classifier = load_classifier(has_key=allow_cloud)
        base = Path(folder)
        # Read the folder recursively so a sorted, by-type tree (W-2/…, 1099-INT/…)
        # reads just like a flat folder. Skip a nested _SATC_Sorted copy (avoids
        # reading both an original and its sorted duplicate) and hidden files.
        files = []
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                rel = p.relative_to(base).parts
                if p.is_file() and "_SATC_Sorted" not in rel and not any(s.startswith(".") for s in rel):
                    files.append(p)

        with tempfile.TemporaryDirectory() as tmp:
            for path in files:
                parts = split_to_dir(path, tmp, classifier) if path.suffix.lower() == ".pdf" else []
                if parts:
                    notes.append(f"{path.name}: combined PDF — split into {len(parts)} documents.")
                    docs = [(c, fp, f"{path.name} ▸ part {i} · {c.label}")
                            for i, (c, fp) in enumerate(parts, start=1)]
                else:
                    c = classifier.classify_path(path)
                    docs = [(c, path, path.name)]

                for c, fpath, doc_id in docs:
                    how = f"detected by {c.method}" if c.classified else "could not identify"
                    # A multi-form page closes nothing on its own -- see
                    # matching.is_multi. It is filed and flagged; which requests
                    # it actually satisfies is the preparer's call.
                    if c.may_close_a_request:   # close the loop: does this satisfy an open request?
                        matched = reconcile_received(self.store, client_id=client_id,
                                                     doc_type=c.label, doc_year=c.tax_year)
                        if matched is not None:
                            reconciled += 1
                            # A BUNDLE THAT IS NOT YET COMPLETE SAYS SO. Saying
                            # "marked Received" for a request still waiting on
                            # two forms is the packet reading complete while a
                            # named form is missing -- exactly the failure this
                            # was fixed for, moved into the note.
                            waiting = outstanding_parts(matched)
                            if waiting:
                                notes.append(
                                    f"{doc_id} → ✓ part of your request "
                                    f"“{matched.doc_type}” — still waiting on "
                                    f"{matching.names(waiting)}.")
                            else:
                                notes.append(
                                    f"{doc_id} → ✓ satisfies your request "
                                    f"“{matched.doc_type}” — marked Received.")
                    if not c.extractable:
                        what = c.label if c.classified else "unrecognized document"
                        notes.append(f"{doc_id} → {what} ({how}): filed, not extracted.")
                        continue
                    cfg = load_extraction_map(c.key)
                    result, problem = self._read_document(fpath, cfg, allow_cloud)
                    if result is None:
                        notes.append(f"{doc_id} → {c.label} ({how}): {problem}")
                        continue
                    staged = MapExtractor(cfg).extract(
                        document_id=doc_id, client_id=client_id, tax_year=tax_year,
                        labeled_fields=result.labeled_fields,
                        confidences=result.confidence_map(),
                        # WHERE EACH FIGURE CAME FROM. The workpaper cited every
                        # value as `Doc <id>` with no page, so $200,000 lifted
                        # off an instructions page looked exactly like a figure
                        # read off the form. See ReadResult.pages.
                        pages=result.pages)
                    staged.source_path = str(path)        # retain the file for compare-to-source
                    if parts:
                        staged.source_note = doc_id        # which part of the combined PDF
                    self.gate.add(staged)
                    self.intake_sources.add(str(path))
                    files_read += 1
                    fields_staged += len(staged.fields)
                    via = _READER_LABELS.get(result.backend, result.backend)
                    notes.append(f"{doc_id} → {c.label} ({how}): staged "
                                 f"{len(staged.fields)} fields via {via}.")

        self.gate.auto_confirm_high(by="auto (intake)")
        if reconciled:
            self.reload()              # refresh documents view with the new Received statuses
        self.intake_summary = {"folder": folder, "files_read": files_read,
                               "fields_staged": fields_staged, "reconciled": reconciled,
                               "notes": notes}
        return self.intake_summary

    @staticmethod
    def _read_document(fpath: Path, cfg: dict, allow_cloud: bool):
        """Read one document via the local-first reader ladder.

        Order: fillable form fields → text layer → local OCR (Tesseract) → local
        vision (Ollama) → cloud vision (opt-in only). Everything before the last
        rung runs entirely on the machine.

        The text-layer rung is entered on a fact about the FILE (does it carry
        text at all -- see :func:`text_layer_chars`), never on whether the rung
        before it happened to return fields. That is the whole point: a document
        we could read but failed to parse must not look like a document there was
        nothing to read.

        DETERMINISTIC FIRST, in both senses the firm meant. The rungs run in
        order of how reproducible they are, and the two MODEL rungs are skipped
        entirely when the document was readable and our own parser is what failed
        -- see the note beside them. Separately, nothing a model produces can
        auto-confirm, whatever it says about itself: see
        ``ReadResult.confidence_map``.

        Returns ``(ReadResult|None, problem)``. ``problem`` is NOT only an error:
        it also carries a diagnostic on an otherwise successful read, so a note
        can say the answer came from OCR *because our anchors missed*, rather
        than reporting a plain success.
        """
        from satc.settings import ocr_enabled, ollama_enabled

        unread = ""    # set when WE failed on a document that was readable
        try:
            if fpath.suffix.lower() == ".pdf":
                result = PdfFormReader(cfg).read(str(fpath))      # 1) fillable form fields (local)
                if result.labeled_fields:
                    return result, ""
                chars = text_layer_chars(fpath)
                if chars >= TEXT_LAYER_MIN:
                    anchors = TextAnchorReader(cfg)
                    result = anchors.read(str(fpath))                 # 2) text layer (local)
                    if result.labeled_fields:
                        # A DROPPED PAGE IS NEVER SILENT. The page rule reads the
                        # form's own pages and skips the IRS's instructions about
                        # it; on the documents clients actually send there is
                        # usually nothing to skip. When there is, the note says
                        # which pages, so nobody has to take the rule on trust.
                        return result, _skipped_note(anchors.skipped_pages)
                    # THE DOCUMENT WAS READABLE AND WE FAILED ON IT. Falling
                    # straight to OCR here is what hid this from the firm for a
                    # season: OCR rasterises text that was already there, reads
                    # it worse, and reports a success. We still go on -- a text
                    # layer can be genuine rubbish, and refusing outright would
                    # lose documents OCR does handle -- but the note now says
                    # which of the two happened, so a parser gap is visible as a
                    # parser gap instead of passing for an ordinary scan.
                    unread = (f"text layer present ({chars} characters) but no "
                              f"field labels matched — our anchors, not the "
                              f"document. ")
            if ocr_enabled():                                     # 3) local OCR (Tesseract)
                result = TesseractOcrReader(cfg).read(str(fpath))
                if result.labeled_fields:
                    return result, unread
            # THE MODEL RUNGS ARE GATED ON `unread`, and this is the second half
            # of "deterministic first". When the document HAD text and our
            # anchors missed it, the failure is ours and it is fixable -- one
            # label in an extraction map. Asking a vision model to judge it
            # instead buries that gap under an answer nobody can reproduce, and
            # the gap stays for every client sending the same form.
            #
            # Tesseract above is still allowed there: it is deterministic and may
            # lay the page out differently to the text layer. A model is not.
            if not unread:
                if ollama_enabled():                              # 4) local vision (Ollama)
                    result = OllamaVisionReader(cfg).read(str(fpath))
                    if result.labeled_fields:
                        return result, unread
                if allow_cloud:                                   # 5) cloud vision (opt-in only)
                    return VisionDocumentReader(cfg).read(str(fpath)), unread
            if unread:
                return None, unread + "Add the label to this form's extraction map."
            return None, "scan with no text layer — enable local OCR (Tesseract) or key it in manually."
        except Exception as exc:        # noqa: BLE001 - surface, don't crash
            return None, f"could not read ({exc})."

    # -- sort + re-label a folder (non-destructive preview/apply) ----------
    def sort_folder(self, folder: str, *, apply: bool = False, client_id: str = "",
                    tax_year: str = "", dest: str = ""):
        """Classify and (optionally) copy a folder's files into a clean tree.

        When ``client_id`` + ``tax_year`` are given, the clean copies land in that
        client's year folder in the document library — which is then a
        ready-to-read Intake folder (``plan.dest``).
        """
        from satc.ingest import sort_folder as _sort
        from satc.ingest.client_library import client_year_folder
        allow_cloud = cloud_vision_enabled()   # OFF unless opted in; a key alone is not enough
        target = dest or None
        if not target and client_id and tax_year:
            target = str(client_year_folder(client_id, tax_year, self.name(client_id)))
        return _sort(folder, target, apply=apply, classifier=load_classifier(has_key=allow_cloud))

    def client_choices(self) -> list[tuple[str, str]]:
        """(client_id, display name) for every known client — for pickers."""
        ids = {pc.client_id for pc in self.mart.public_clients} | set(self.names)
        return sorted(((cid, self.name(cid)) for cid in ids), key=lambda x: x[1])

    # -- the last hop: post confirmed intake onto the return + data mart ---
    def post_confirmed(self, *, client_id: str | None = None, tax_year: int | None = None,
                       return_type: str = "1040", jurisdiction: str = "US") -> dict:
        """Write the gate's CONFIRMED values onto the client's return as line items.

        Only confirmed fields flow (the gate already enforces that), projected onto
        1040 line ids with aggregation (every W-2 box 1 summed into wages, etc.).
        The return is created if it doesn't exist; re-posting is idempotent.
        """
        client_id = client_id or self.intake_context.get("client_id") or "SATC-001000"
        tax_year = tax_year or self.intake_context.get("tax_year") or 2024
        rk = return_key(client_id, tax_year, return_type, jurisdiction)
        ret = next((r for r in self.mart.returns if r.return_key == rk), None)
        if ret is None:
            ret = ReturnRecord(return_key=rk, client_id=client_id, tax_year=tax_year,
                               return_type=return_type, jurisdiction=jurisdiction, status="In prep")
            self.mart.returns.append(ret)

        items = self.gate.to_line_items(rk, MAPPING_1040)
        # Idempotent re-post: an intake line that is no longer produced this run
        # must not linger. Drop ALL prior intake-sourced (SOURCE_DOC) lines for
        # this return — from memory and the store — then add the current set.
        # Non-intake lines (Drake output, carryforwards, preparer entries) on the
        # same return are left untouched.
        self.mart.line_items = [
            li for li in self.mart.line_items
            if not (li.return_key == rk and li.provenance is not None
                    and li.provenance.source_kind == "SOURCE_DOC")]
        self.mart.line_items.extend(items)

        self.store.delete_intake_line_items(rk)
        self.store.save_mart(self.mart)
        self.reload()
        self.posted_summary = {"return_key": rk, "client_id": client_id, "posted": len(items),
                               "lines": [(li.label, float(li.amount) if li.amount is not None
                                          else li.text_value) for li in items]}
        return self.posted_summary

    # -- client intake & engagement workflows -----------------------------
    def intake_engagements(self) -> list:
        """All generated engagements (workflow instances), newest first."""
        return list(reversed(self.store.load_intake_engagements()))

    def engagement(self, engagement_id: str):
        return next((e for e in self.store.load_intake_engagements()
                     if e.engagement_id == engagement_id), None)

    def relationships(self) -> list:
        return self.store.load_relationships()

    def create_person_client(self, **kw) -> str:
        from satc.intake import create_person_client
        cid = create_person_client(self.store, **kw)
        self.reload()
        return cid

    def create_business_client(self, **kw) -> str:
        from satc.intake import create_business_client
        cid = create_business_client(self.store, **kw)
        self.reload()
        return cid

    def add_relationship(self, **kw):
        from satc.intake import add_relationship
        return add_relationship(self.store, **kw)

    def create_engagement(self, **kw):
        from satc.intake import create_engagement
        eng = create_engagement(self.store, **kw)
        self.reload()
        return eng

    def set_task_completed(self, task_id: str, completed: bool = True) -> None:
        """Mark an engagement task done/undone (durable)."""
        for eng in self.store.load_intake_engagements():
            for task in eng.tasks:
                if task.task_id == task_id:
                    task.completed = completed
                    self.store.save_task(task)
                    return

    def workflow_catalog(self) -> dict[str, list]:
        """Workflows offered per client type, for the intake screens."""
        from satc.intake.workflows import workflows_for_client_type
        return {ct: workflows_for_client_type(ct) for ct in ("person", "business")}

    # -- bulk client import (CSV / spreadsheet / Drake export) ------------
    def preview_client_import(self, *, csv_text: str | None = None, rows: list[dict] | None = None):
        """Parse a roster into previewed clients (new / duplicate / review)."""
        from satc.intake.service import preview_import
        return preview_import(self.store, csv_text=csv_text, rows=rows)

    def commit_client_import(self, parsed, *, include_duplicates: bool = False) -> list[str]:
        from satc.intake.service import commit_import
        ids = commit_import(self.store, parsed, include_duplicates=include_duplicates)
        self.reload()
        return ids

    def add_client_smart(self, **fields):
        """Smart single-add: detect person/business + normalize, then create."""
        from satc.intake import importer
        from satc.intake.service import commit_import
        parsed = importer.parse_one(**fields)
        ids = commit_import(self.store, [parsed], include_duplicates=True)
        self.reload()
        return (ids[0] if ids else None), parsed

    # -- questionnaire customization --------------------------------------
    def all_workflows(self) -> list:
        from satc.intake.workflows import list_workflows
        return list_workflows()

    def base_workflow(self, key: str):
        """The built-in workflow WITHOUT overrides (for showing originals in the editor)."""
        from satc.intake import workflows as wf
        provider, wf._OVERRIDE_PROVIDER = wf._OVERRIDE_PROVIDER, None
        try:
            return wf.load_workflow(key)
        finally:
            wf._OVERRIDE_PROVIDER = provider

    def workflow_override(self, key: str) -> dict:
        return self.store.load_workflow_override(key) or {}

    def save_workflow_override(self, key: str, data: dict) -> None:
        self.store.save_workflow_override(key, data)

    # -- dashboard rollups ------------------------------------------------
    def pipeline_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.mart.returns:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    def fees_total(self) -> float:
        return float(sum((e.fee_amount or 0) for e in self.mart.engagements))

    def fees_unpaid(self) -> float:
        return float(sum((e.fee_amount or 0) for e in self.mart.engagements if not e.paid))


STATE = AppState()
