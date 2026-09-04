"""The join that lets a collected document close the request it satisfies.

The collector files documents correctly and cannot mark anything Received,
because the two halves of the system name an engagement differently:

  * `client-documents` -- and every letter, estimate and invoice a client ever
    sees -- uses an ``EngagementRef``, "2026-0001".
  * `satc_system` -- where the requests and the tasks live -- keys on
    ``client_id``, "SATC-001000".

Nothing joined them, so `collect` had no way to resolve an arriving folder to
a client. The firm chose to add the field rather than rename either side (31
Aug 2026: "ADD THE FIELD"), which is the right way round: the ref is what a
client sees on their paperwork, and putting an internal id on a folder you
share with them would be leaking a detail for the software's convenience.

Ported from the pre-schema-port version (`git show
parked/satc-system-pre-schema-port:satc_system/tests/test_engagement_ref.py`),
which asserted the same four things against ``IntakeEngagement``. That type
is gone -- ``IntakeEngagement`` became ``Job`` in the work.py port, and the
CONTRACT (fee, letter status, and now the ref) is ``Engagement``, keyed on
``(client_id, tax_year)`` rather than a generated engagement id. The ref
belongs there: it names a client's paperwork for a year, the same thing the
contract is for.
"""

from __future__ import annotations

from satc.models.work import Engagement


def _eng(**kw):
    base = dict(client_id="SATC-001000", tax_year=2026)
    base.update(kw)
    return Engagement(**base)


def test_an_engagement_can_carry_the_ref_a_client_sees():
    e = _eng(engagement_ref="2026-0001")
    assert e.engagement_ref == "2026-0001"


def test_the_ref_is_optional_so_old_engagements_still_load():
    assert _eng().engagement_ref == ""


# -- the store ----------------------------------------------------------------

def test_the_ref_survives_a_save_and_load(tmp_path):
    from satc.models.mart import DataMart
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_mart(DataMart(engagements=[_eng(engagement_ref="2026-0001")]))
    back = store.load_mart().engagements
    assert [e.engagement_ref for e in back] == ["2026-0001"]


def test_a_database_made_before_the_column_existed_still_opens(tmp_path):
    """The migration, asserted rather than assumed.

    ``CREATE TABLE IF NOT EXISTS`` never alters an existing table, so a store
    seeded by an older build has no ``engagement_ref`` column. Opening it must
    add the column, not raise -- and a row written before the column existed
    must still load, reading back blank rather than failing.
    """
    import sqlite3

    from satc.models.mart import DataMart
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_mart(DataMart(engagements=[_eng()]))

    # Put the schema back the way an older build left it.
    db = sqlite3.connect(tmp_path / "satc_mart.db")
    db.execute("ALTER TABLE engagements DROP COLUMN engagement_ref")
    db.commit()
    db.close()

    reopened = SATCStore(tmp_path)          # must migrate, not explode
    cols = {r["name"] for r in
            reopened.mart.execute("PRAGMA table_info(engagements)")}
    assert "engagement_ref" in cols
    assert reopened.load_mart().engagements[0].engagement_ref == ""


# -- the lookup ---------------------------------------------------------------

def test_a_ref_resolves_to_the_client_it_belongs_to(tmp_path):
    from satc.models.mart import DataMart
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_mart(DataMart(engagements=[
        _eng(client_id="SATC-001000", engagement_ref="2026-0001"),
        _eng(client_id="SATC-002000", engagement_ref="2026-0002"),
    ]))
    assert store.client_for_ref("2026-0001") == "SATC-001000"
    assert store.client_for_ref("2026-0002") == "SATC-002000"


def test_an_unknown_ref_resolves_to_nothing_rather_than_a_guess(tmp_path):
    from satc.models.mart import DataMart
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_mart(DataMart(engagements=[_eng(engagement_ref="2026-0001")]))
    assert store.client_for_ref("2026-9999") is None


def test_a_blank_ref_never_matches_the_engagements_that_have_none(tmp_path):
    """The trap: most engagements will carry "" for a while. A lookup on "" must
    not return the first of them, or an unplaced drop folder would silently
    reconcile against whoever happened to be saved first."""
    from satc.models.mart import DataMart
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_mart(DataMart(engagements=[
        _eng(client_id="SATC-001000"),
        _eng(client_id="SATC-002000", tax_year=2025),
    ]))
    assert store.client_for_ref("") is None
