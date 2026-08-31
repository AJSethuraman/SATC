"""The join that lets a collected document close the request it satisfies.

The collector files documents correctly and cannot mark anything Received,
because the two halves of the system name an engagement differently:

  * `client-documents` — and every letter, estimate and invoice a client
    ever sees — uses `EngagementRef`, "2026-0001".
  * `satc_system` — where the requests and the tasks live — keys on a
    `client_id`, "SATC-001000".

Nothing joined them, so `reconcile_received` had nothing to look up. The firm
chose to add the field rather than rename the folders (31 Aug 2026: "ADD THE
FIELD"), which is the right way round: the ref is what a client sees on their
paperwork, and putting an internal id on a folder you share with them would be
leaking a detail for the software's convenience.
"""

from __future__ import annotations

import pytest

from satc.models.intake import IntakeEngagement


def _eng(**kw):
    base = dict(engagement_id="ENG-1", client_id="C1", workflow_key="1040")
    base.update(kw)
    return IntakeEngagement(**base)


def test_an_engagement_can_carry_the_ref_a_client_sees():
    e = _eng(engagement_ref="2026-0001")
    assert e.engagement_ref == "2026-0001"


def test_the_ref_is_optional_so_old_engagements_still_load():
    assert _eng().engagement_ref == ""


# -- the store ----------------------------------------------------------------

def test_the_ref_survives_a_save_and_load(tmp_path):
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_intake_engagement(_eng(engagement_ref="2026-0001"))
    back = store.load_intake_engagements()
    assert [e.engagement_ref for e in back] == ["2026-0001"]


def test_a_database_made_before_the_column_existed_still_opens(tmp_path):
    """The migration, asserted rather than assumed.

    CREATE TABLE IF NOT EXISTS never alters an existing table, so a store seeded
    by an older build has no engagement_ref column. Opening it must add the
    column, not raise.
    """
    import sqlite3

    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_intake_engagement(_eng())

    # Put the schema back the way an older build left it.
    db = sqlite3.connect(tmp_path / "satc_mart.db")
    db.execute("ALTER TABLE intake_engagements DROP COLUMN engagement_ref")
    db.commit()
    db.close()

    reopened = SATCStore(tmp_path)          # must migrate, not explode
    cols = {r["name"] for r in
            reopened.mart.execute("PRAGMA table_info(intake_engagements)")}
    assert "engagement_ref" in cols
    assert reopened.load_intake_engagements()[0].engagement_ref == ""


# -- the lookup ---------------------------------------------------------------

def test_a_ref_resolves_to_the_client_it_belongs_to(tmp_path):
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_intake_engagement(_eng(engagement_id="E1", client_id="C1",
                                      engagement_ref="2026-0001"))
    store.save_intake_engagement(_eng(engagement_id="E2", client_id="C2",
                                      engagement_ref="2026-0002"))
    assert store.client_for_ref("2026-0001") == "C1"
    assert store.client_for_ref("2026-0002") == "C2"


def test_an_unknown_ref_resolves_to_nothing_rather_than_a_guess(tmp_path):
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_intake_engagement(_eng(engagement_ref="2026-0001"))
    assert store.client_for_ref("2026-9999") is None


def test_a_blank_ref_never_matches_the_engagements_that_have_none(tmp_path):
    """The trap: most engagements will carry "" for a while. A lookup on "" must
    not return the first of them, or an unplaced drop folder would silently
    reconcile against whoever happened to be saved first."""
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    store.save_intake_engagement(_eng(engagement_id="E1", client_id="C1"))
    store.save_intake_engagement(_eng(engagement_id="E2", client_id="C2"))
    assert store.client_for_ref("") is None
