"""The collector resolving a drop folder's ref to the client it belongs to.

Filing already worked with no store at all -- a folder named "2026-0001" gets
its documents filed under that ref regardless. What did not exist was the
other half: knowing that "2026-0001" IS a client, so an arriving document can
close the request it satisfies rather than just sit filed. See
docs/DEFECT-REGISTER.md S3 and satc.models.work.Engagement.engagement_ref.

These tests cover only the store-resolution seam `collect` added -- the
folder-reading and splitting behaviour is unchanged and untested here.
"""

from __future__ import annotations

import pymupdf
import pytest

from satc.collect import Drop, SyncedFolder, collect
from satc.models.evidence import RequestedItem


def _form(path, lines: list[str]):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 16
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


W2 = ["Form W-2  Wage and Tax Statement", "2026",
      "Employer: Buckeye Manufacturing LLC",
      "1 Wages, tips, other compensation  64,500.00"]


@pytest.fixture
def drop_root(tmp_path):
    root = tmp_path / "Client Uploads"
    _form(root / "2026-0001 — Maplewood" / "IMG_4471.pdf", W2)
    return root


class FakeStore:
    """The two methods `collect` needs off a store, with no SQLite involved --
    same shape as the FakeStore in test_document_year.py."""

    def __init__(self, *, refs: dict[str, str], requested: list[RequestedItem]):
        self._refs = refs
        self._requested = requested
        self.saved: list[RequestedItem] = []

    def client_for_ref(self, ref: str) -> str | None:
        return self._refs.get(ref) if ref else None

    def load_mart(self):
        class _Mart:
            pass
        m = _Mart()
        m.requested_items = self._requested
        return m

    def save_requested_items(self, items) -> None:
        self.saved.extend(items)

    def load_jobs(self):
        return []

    def save_task(self, task) -> None:
        pass


# -- resolving the ref ---------------------------------------------------------

def test_with_no_store_the_drop_is_filed_but_not_resolved(drop_root, tmp_path):
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True)
    dr = rep.drops[0]
    assert dr.client_id == ""
    assert dr.arrivals, "filing still happens with no store"


def test_a_ref_the_store_does_not_know_is_reported_not_guessed(drop_root, tmp_path):
    store = FakeStore(refs={}, requested=[])
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True,
                  store=store)
    dr = rep.drops[0]
    assert dr.client_id == ""
    assert "engagement_ref" in dr.unresolved


def test_a_known_ref_resolves_to_its_client(drop_root, tmp_path):
    store = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[])
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True,
                  store=store)
    dr = rep.drops[0]
    assert dr.client_id == "SATC-001000"
    assert not dr.unresolved


# -- closing the request ---------------------------------------------------------

def test_a_resolved_arrival_closes_the_request_it_satisfies(drop_root, tmp_path):
    req = RequestedItem(request_id="R1", client_id="SATC-001000", tax_year=2026,
                        doc_type="W-2", request_text="Upload your W-2s")
    store = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[req])

    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True,
                  store=store)

    arrival = rep.drops[0].arrivals[0]
    assert arrival.satisfied == "W-2"
    assert [i.request_id for i in store.saved] == ["R1"]
    assert req.status == "satisfied"


def test_a_preview_resolves_the_client_but_closes_nothing(drop_root, tmp_path):
    """apply=False previews. Filing writes nothing on a preview, and neither
    should the client's open request -- a preview is not a decision."""
    req = RequestedItem(request_id="R1", client_id="SATC-001000", tax_year=2026,
                        doc_type="W-2", request_text="Upload your W-2s")
    store = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[req])

    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=False,
                  store=store)

    assert rep.drops[0].client_id == "SATC-001000"
    assert rep.drops[0].arrivals[0].satisfied == ""
    assert store.saved == []
    assert req.status == "outstanding"


def test_a_client_with_no_matching_request_files_but_closes_nothing(drop_root, tmp_path):
    store = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[])
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True,
                  store=store)
    arrival = rep.drops[0].arrivals[0]
    assert arrival.satisfied == ""
    assert store.saved == []


# -- the model guard --------------------------------------------------------

def test_a_model_classified_arrival_does_not_close_a_request_on_its_own(tmp_path):
    """Only the vision rung asks a model, and a model may not close a client's
    request on its own -- see Classification.is_model_classified and
    reconcile_received's model guard, which state.py already respects by
    deriving Actor.model("vision") for a vision verdict. collect() must derive
    the same actor rather than let reconcile_received default to INTAKE,
    which would bypass the guard for every vision-classified arrival."""
    from satc.ingest.classify import Classification
    from satc.models.evidence import RequestedItem

    root = tmp_path / "Client Uploads"
    (root / "2026-0001 — Maplewood").mkdir(parents=True)
    (root / "2026-0001 — Maplewood" / "scan.jpg").write_bytes(b"not a real image")

    vision_verdict = Classification(label="W-2", key="w2", code="W2",
                                    confidence="MEDIUM", method="vision",
                                    tax_year=2026)

    class VisionClassifier:
        def classify_path(self, path):
            return vision_verdict

    req = RequestedItem(request_id="R1", client_id="SATC-001000", tax_year=2026,
                        doc_type="W-2", request_text="Upload your W-2s")
    store = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[req])

    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True,
                  store=store, classifier=VisionClassifier())

    arrival = rep.drops[0].arrivals[0]
    assert arrival.satisfied == "", "a model verdict closed a request on its own"
    assert store.saved == []
    assert req.status == "outstanding"


# -- retrying a reconciliation the ledger once skipped -----------------------

def test_a_document_filed_before_its_ref_resolved_still_closes_once_it_does(
        drop_root, tmp_path):
    """The ledger records that a file was FILED, not that its request was ever
    closed. An unresolved ref at filing time means no reconciliation was even
    attempted -- and the digest still enters the ledger, because filing does
    not depend on resolution. A later run, once the firm sets engagement_ref,
    must not skip that file as 'already seen' and leave the request stuck
    outstanding forever."""
    lib = tmp_path / "lib"
    req = RequestedItem(request_id="R1", client_id="SATC-001000", tax_year=2026,
                        doc_type="W-2", request_text="Upload your W-2s")

    unresolved = FakeStore(refs={}, requested=[req])
    first = collect(SyncedFolder(drop_root), library=lib, apply=True, store=unresolved)
    assert first.drops[0].arrivals[0].satisfied == ""
    assert req.status == "outstanding"

    resolved = FakeStore(refs={"2026-0001": "SATC-001000"}, requested=[req])
    second = collect(SyncedFolder(drop_root), library=lib, apply=True, store=resolved)
    assert second.drops[0].arrivals[0].satisfied == "W-2"
    assert req.status == "satisfied"
