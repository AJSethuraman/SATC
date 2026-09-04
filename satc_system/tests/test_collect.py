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
