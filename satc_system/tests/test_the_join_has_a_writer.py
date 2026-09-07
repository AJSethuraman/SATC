"""The engagement ref can be recorded, and the row it lives on now exists.

**THE JOIN THE WHOLE PRACTICE DEPENDS ON HAD NO WRITER.** A client sees
`2026-0001` on every letter, estimate and invoice that `client-documents`
produces; this system keys on `SATC-001000`, which a client is never shown.
`Engagement.engagement_ref` exists to hold the first so the second can be found
from it — added on the firm's instruction, 31 August 2026, verbatim *"ADD THE
FIELD"*.

The column migrates, saves, loads, and `SATCStore.client_for_ref` reads it.
`collect` sent the preparer to set it. **Nothing set it**, and its only writers
were `tests/test_engagement_ref.py`.

**AND IT WAS WORSE THAN A MISSING SETTER.** Reading it properly on 4 September
2026: every use of `mart.engagements` in `src/` was a READ — `rate_plan_for`,
the comms screen, the intake fan-out, the workbook, the dashboard totals. The
only writers were `fixtures/synthetic.py` and the store's own loader. **An
`Engagement` existed for the four demo clients and for nobody else.** So the
field had no row to sit on: the rate plan agreed, the fee, invoiced, paid and
the ref were all unreachable for a real client.

The firm settled the ownership question the same evening: *"client-documents
owns the engagement; satc_system holds the return."* So the ref is recorded
here, not allocated here.
"""

from __future__ import annotations

import pytest

from satc.models.work import Engagement, Job, engagement_for, rate_plan_for


# ── the producer that did not exist ──────────────────────────────────────────

def test_a_lookup_does_not_quietly_manufacture_a_row():
    """`create=False` is the default for a reason. Most callers are asking a
    question, and a client nobody has engaged must keep reading as silence."""
    rows: list = []
    assert engagement_for(rows, client_id="SATC-009000", tax_year=2025) is None
    assert rows == [], "a plain lookup appended a row"


def test_asking_for_one_creates_exactly_one():
    rows: list = []
    made = engagement_for(rows, client_id="SATC-009000", tax_year=2025,
                          create=True)
    assert made is not None and rows == [made]
    assert made.client_id == "SATC-009000" and made.tax_year == 2025


def test_creating_twice_returns_the_same_row():
    """Idempotent by the primary key, so re-running the engagement generator
    is a re-run and not a duplicate."""
    rows: list = []
    a = engagement_for(rows, client_id="SATC-009000", tax_year=2025, create=True)
    b = engagement_for(rows, client_id="SATC-009000", tax_year=2025, create=True)
    assert a is b and len(rows) == 1


def test_a_new_row_agrees_to_nothing():
    """It says "there is a contract for this year" and must not also say a rate
    was agreed, a fee was settled, or a letter went out. `rate_plan_key`'s own
    note explains why blank rather than "standard"."""
    rows: list = []
    made = engagement_for(rows, client_id="SATC-009000", tax_year=2025, create=True)
    assert made.rate_plan_key == "" and made.rate_plan_basis == ""
    assert made.engagement_ref == ""
    assert made.fee_amount is None
    assert made.invoiced is False and made.paid is False


def test_creating_rows_did_not_change_what_the_rate_plan_says():
    """THE REGRESSION THIS CHANGE COULD EASILY HAVE CAUSED.

    `rate_plan_for` distinguishes a plan somebody agreed from the practice
    default. If it had keyed on *whether an engagement row exists*, then making
    the product create rows would have turned every unpriced client into one
    that looks priced. It keys on whether a plan was AGREED, so it does not —
    asserted here so a later refactor cannot quietly change that.
    """
    empty: list = []
    before = rate_plan_for(empty, client_id="SATC-009000", tax_year=2025)
    engagement_for(empty, client_id="SATC-009000", tax_year=2025, create=True)
    after = rate_plan_for(empty, client_id="SATC-009000", tax_year=2025)
    assert before.source == after.source == "practice_default"
    assert after.basis == ""


# ── recording a ref through the screen ───────────────────────────────────────

@pytest.fixture
def app_and_job():
    """A real app, and a job made through the door the product actually uses.

    The seeded demo store has clients and no jobs, so the job is created with
    `create_engagement_from_intake` -- which is also the call this change made
    into the producer of the contract row, so the fixture exercises it rather
    than reaching around it.
    """
    from satc.app.server import create_app
    from satc.app.state import STATE
    from satc.intake.service import create_engagement_from_intake

    STATE.reload()
    app = create_app()
    # INDIVIDUAL only. `personal_1040_core` refuses a client recorded as an
    # S corporation or a partnership, and it is right to -- whether an entity
    # is an S corporation is assigned by the IRS in writing, not settled by
    # whichever workflow happened to be picked. A freshly seeded store holds
    # exactly one individual, so the second is created here rather than hoped
    # for: a fixture that depends on how much demo data happens to be present
    # is a fixture that passes alone and fails in a full run.
    #
    # INVENTED NAME, and no SSN. Nothing here resembles a real client.
    from satc.intake.service import create_person_client
    create_person_client(STATE.store, first_name="Walkthrough",
                         last_name="Fixture")
    STATE.reload()
    clients = [c.client_id for c in STATE.mart.public_clients
               if getattr(c, "entity_type", "") == "INDIVIDUAL"][:2]
    assert len(clients) == 2, f"need two individual clients, got {clients}"

    made = []
    for cid in clients:
        plan = create_engagement_from_intake(
            STATE.store, client_id=cid, workflow_key="personal_1040_core",
            tax_year=2025, answers={})
        made.append(plan.job)
    STATE.reload()
    return app, made[0], made[1]


def test_recording_a_ref_makes_the_drop_folder_resolvable(app_and_job):
    """END TO END, AND THIS IS THE WHOLE POINT.

    Before: `client_for_ref` cannot resolve the ref, so `collect` files the
    documents and marks nothing Received. After one form post: it resolves to
    this client.
    """
    app, job, other = app_and_job
    from satc.app.state import STATE

    assert STATE.store.client_for_ref("2026-0001") is None, (
        "the ref resolved before anything recorded it")

    resp = app.test_client().post(f"/engagements/{job.job_id}/ref",
                                  data={"engagement_ref": "2026-0001"})
    assert resp.status_code in (302, 303), resp.status_code

    assert STATE.store.client_for_ref("2026-0001") == job.client_id, (
        "the ref was accepted but a drop folder named for it still resolves to "
        "nobody — which is the exact failure this whole field exists to fix")


def test_it_survives_a_reload_because_it_reached_the_database(app_and_job):
    """In-memory is not recorded. The store is re-read from disk."""
    app, job, other = app_and_job
    from satc.app.state import STATE
    app.test_client().post(f"/engagements/{job.job_id}/ref",
                           data={"engagement_ref": "2026-0002"})
    STATE.reload()
    assert STATE.store.client_for_ref("2026-0002") == job.client_id


def test_a_ref_in_the_wrong_shape_is_refused_and_says_the_shape(app_and_job):
    app, job, other = app_and_job
    from satc.app.state import STATE
    resp = app.test_client().post(f"/engagements/{job.job_id}/ref",
                                  data={"engagement_ref": "26-1"})
    assert resp.status_code == 400
    body = resp.get_data(as_text=True)
    assert "YYYY-NNNN" in body, "the refusal did not say what the format is"
    assert STATE.store.client_for_ref("26-1") is None


def test_a_ref_already_belonging_to_someone_else_is_refused(app_and_job):
    """THE ONE THAT MATTERS MOST, because the alternative failure is silent.

    `client_for_ref` uses SELECT DISTINCT and returns None when a ref names
    more than one client — correctly, since picking one arbitrarily would close
    the WRONG client's document request. But at collection time that refusal is
    indistinguishable from "nobody ever set the ref". Caught at the keyboard it
    costs a sentence.
    """
    app, job, other = app_and_job
    from satc.app.state import STATE
    assert other.client_id != job.client_id

    app.test_client().post(f"/engagements/{other.job_id}/ref",
                           data={"engagement_ref": "2026-0003"})
    resp = app.test_client().post(f"/engagements/{job.job_id}/ref",
                                  data={"engagement_ref": "2026-0003"})
    assert resp.status_code == 400
    assert "already belongs" in resp.get_data(as_text=True)
    assert STATE.store.client_for_ref("2026-0003") == other.client_id, (
        "the duplicate was refused but the original stopped resolving — which "
        "would be worse than allowing it")


def test_the_same_client_may_correct_its_own_ref(app_and_job):
    """The duplicate guard must not stop somebody fixing a typo on the
    engagement that already holds it."""
    app, job, other = app_and_job
    from satc.app.state import STATE
    c = app.test_client()
    c.post(f"/engagements/{job.job_id}/ref", data={"engagement_ref": "2026-0004"})
    resp = c.post(f"/engagements/{job.job_id}/ref",
                  data={"engagement_ref": "2026-0004"})
    assert resp.status_code in (302, 303)
    assert STATE.store.client_for_ref("2026-0004") == job.client_id


def test_clearing_it_is_allowed_and_means_nothing_resolves(app_and_job):
    app, job, other = app_and_job
    from satc.app.state import STATE
    c = app.test_client()
    c.post(f"/engagements/{job.job_id}/ref", data={"engagement_ref": "2026-0005"})
    c.post(f"/engagements/{job.job_id}/ref", data={"engagement_ref": ""})
    assert STATE.store.client_for_ref("2026-0005") is None


# ── the screen actually offers it ────────────────────────────────────────────

def test_the_engagement_screen_renders_the_box(app_and_job):
    """A route with no control on any page is a route nobody can reach. That
    was the whole defect: the field existed and no screen offered it."""
    app, job, other = app_and_job
    body = app.test_client().get(f"/engagements/{job.job_id}").get_data(as_text=True)
    assert f"/engagements/{job.job_id}/ref" in body, (
        "no form on the engagement screen posts to the ref endpoint")
    assert 'name="engagement_ref"' in body


def test_the_screen_says_plainly_when_nothing_is_set(app_and_job):
    """Silence has to read as silence. A blank box with no words beside it
    looks like a field somebody forgot, not a fact about this client."""
    app, job, other = app_and_job
    body = app.test_client().get(f"/engagements/{job.job_id}").get_data(as_text=True)
    assert "Not set" in body


# ── check the checker ────────────────────────────────────────────────────────

def test_nothing_in_src_created_an_engagement_before_this(app_and_job):
    """MUTATION, of a sort — asserting the state of the world this fixes.

    The claim is that `create_engagement_from_intake` is now the producer. If a
    second producer appears, the invariant "one contract row per client-year,
    created where the contract is made" quietly stops holding, and two rows for
    one client would make `client_for_ref` ambiguous — the very thing the
    duplicate guard above exists to prevent.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "satc"
    makers = []
    for path in root.rglob("*.py"):
        if path.name in {"synthetic.py", "store.py", "work.py"}:
            continue                       # fixtures, the loader, the definition
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if "Engagement(" in line and "engagement_for" not in line:
                makers.append(f"{path.relative_to(root)}:{i}: {line.strip()}")
    assert not makers, (
        "these construct an Engagement directly instead of going through "
        "engagement_for(), which is how a client ends up with two contract "
        "rows for one year:\n  " + "\n  ".join(makers))
