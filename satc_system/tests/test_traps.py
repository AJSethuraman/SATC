"""The nightly trap drill — docs/AUTONOMY-CHARTER.md section 7.

Two families of test here, and the brief asks for both by name:

* Each trap fires when its defect is present and stays quiet when it is not
  — the MUTATION TABLE (principle 12). Every trap is broken on purpose, the
  drill is proved to catch it, and the break is undone within the same test
  (pytest's ``monkeypatch`` fixture undoes it regardless; each test also
  re-runs the drill afterward to prove it is quiet again, rather than taking
  the fixture's word for it).
* A trap that CANNOT run counts as a miss, never a skip — checked at every
  level a "cannot run" can happen: an individual check raising, the whole
  synthetic practice failing to build, and the config itself being
  unreadable.
"""

from __future__ import annotations

import ast
import itertools
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from satc import cli
from satc.autonomy import traps
from satc.autonomy.traps import DrillResult, TrapResult, run_drill

TODAY = date(2026, 4, 15)

ALL_KEYS = (
    "zero_line_invoice",
    "stale_chase_date",
    "cross_client_merge",
    "duplicate_payment",
    "stale_cheque_matches_future_invoice",
)


def _by_key(result: DrillResult) -> dict[str, TrapResult]:
    return {t.key: t for t in result.traps}


# --- baseline: quiet against the real, unmutated engine ----------------------


def test_the_drill_runs_and_every_trap_is_quiet_against_the_real_engine():
    result = run_drill(today=TODAY)
    assert result.ran is True
    assert result.today == TODAY
    assert {t.key for t in result.traps} == set(ALL_KEYS)
    assert result.misses == ()
    assert result.demotions == ()
    assert all(t.passed for t in result.traps)
    # Every row carries an auditable one-line reason regardless of outcome —
    # principle 13, the same rule a queue row is held to.
    assert all(t.why.strip() for t in result.traps)


def test_config_and_check_registry_declare_the_same_keys():
    """The two halves that make a trap real must never drift apart quietly."""
    declared = {d["key"] for d in traps._load_declared_traps(None)}
    assert declared == set(traps._CHECKS.keys()) == set(ALL_KEYS)


# --- mutation table: break each rule on purpose, confirm the miss, restore --


def test_mutation_zero_line_invoice(monkeypatch):
    from satc.billing.invoice import Invoice

    def bypassed_issue(self, *, on, due_in_days=30):
        # The exact shape of the shipped defect: the guard simply isn't there.
        self.issued_on = on
        self.due_on = on + timedelta(days=due_in_days)
        return self

    with monkeypatch.context() as m:
        m.setattr(Invoice, "issue", bypassed_issue)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["zero_line_invoice"].passed is False
    assert broken.misses == ("zero_line_invoice",)
    assert broken.demotions == ("billing.invoice_issue",)
    # Every OTHER trap held — one broken rule demotes its own capability only.
    assert all(t.passed for t in broken.traps if t.key != "zero_line_invoice")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_stale_chase_date(monkeypatch):
    import satc.actions.propose as propose_mod

    real_chase = propose_mod.chase_outstanding

    def frozen_clock_chase(requested, *, client_id, tax_year, today, stale_after_days=3):
        # The exact shape of the shipped defect: the day count is computed
        # against a fixed date instead of the one it was actually asked about.
        return real_chase(requested, client_id=client_id, tax_year=tax_year,
                          today=date(2000, 1, 1), stale_after_days=stale_after_days)

    with monkeypatch.context() as m:
        m.setattr(propose_mod, "chase_outstanding", frozen_clock_chase)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["stale_chase_date"].passed is False
    assert broken.misses == ("stale_chase_date",)
    assert broken.demotions == ("documents.chase",)
    assert all(t.passed for t in broken.traps if t.key != "stale_chase_date")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_stale_chase_date_wrong_but_plausible_count(monkeypatch):
    """The reviewer's exact break: the day count is computed against a
    SHIFTED clock, not a frozen one, so it produces a wrong but perfectly
    plausible-looking number ("45 days ago" instead of 20) rather than the
    huge nonsense number the frozen-clock mutation above produces. The old
    assertion (`"20" not in observed`) passed anyway, because the sentence
    also names the tax year ("...for 2026...") and "2026" contains the
    digits "20" — the trap was checking for a substring that is present on
    every run, never the actual day count.
    """
    import satc.actions.propose as propose_mod

    real_chase = propose_mod.chase_outstanding

    def shifted_clock_chase(requested, *, client_id, tax_year, today, stale_after_days=3):
        return real_chase(requested, client_id=client_id, tax_year=tax_year,
                          today=today + timedelta(days=25), stale_after_days=stale_after_days)

    with monkeypatch.context() as m:
        m.setattr(propose_mod, "chase_outstanding", shifted_clock_chase)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["stale_chase_date"].passed is False
    assert broken.misses == ("stale_chase_date",)
    assert broken.demotions == ("documents.chase",)
    assert all(t.passed for t in broken.traps if t.key != "stale_chase_date")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_cross_client_merge(monkeypatch):
    import sys

    import satc.comms  # noqa: F401 - ensures satc.comms.render is in sys.modules

    # NOT `import satc.comms.render as render_mod`: satc/comms/__init__.py does
    # `from satc.comms.render import render`, which rebinds the ATTRIBUTE
    # `satc.comms.render` on the package object to the function itself — so an
    # attribute-chasing import here would silently patch the function, not the
    # module. Pulling the real submodule straight from ``sys.modules`` (keyed
    # by its full dotted name, which import machinery always populates
    # correctly) sidesteps that shadowing.
    render_mod = sys.modules["satc.comms.render"]
    real_render = render_mod.render
    leak_cache: dict[str, str] = {}

    def leaky_render(template, values, *, library=None):
        # The exact shape of the shipped defect: a value filled for one
        # client survives, through shared mutable state, into the next
        # client's render.
        merged = {**leak_cache, **values}
        leak_cache.update({k: v for k, v in values.items() if v})
        return real_render(template, merged, library=library)

    with monkeypatch.context() as m:
        m.setattr(render_mod, "render", leaky_render)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["cross_client_merge"].passed is False
    assert broken.misses == ("cross_client_merge",)
    assert broken.demotions == ("comms.render",)
    assert all(t.passed for t in broken.traps if t.key != "cross_client_merge")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_duplicate_payment(monkeypatch):
    import satc.billing.payment as payment_mod

    real_payment_id = payment_mod.payment_id
    counter = itertools.count()

    def unstable_payment_id(**kwargs):
        # The exact shape of the shipped defect: an id that depends on WHEN
        # it was computed rather than only on what the payment IS — the
        # payment-hash collision's mirror image (principle 8).
        return f"{real_payment_id(**kwargs)}-{next(counter)}"

    with monkeypatch.context() as m:
        m.setattr(payment_mod, "payment_id", unstable_payment_id)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["duplicate_payment"].passed is False
    assert broken.misses == ("duplicate_payment",)
    assert broken.demotions == ("payments.dedupe",)
    assert all(t.passed for t in broken.traps if t.key != "duplicate_payment")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_duplicate_payment_negative_only_control(monkeypatch):
    """The reviewer's first break: `merge()` replaced with a stub that always
    returns an EMPTY ledger. The old check only asserted `if added: fail` —
    it could not tell "correctly deduplicated" from "recorded nothing at
    all", so a merge() that throws every payment away in silence still
    passed.
    """
    import satc.billing.payment as payment_mod

    def merge_that_records_nothing(existing, arriving):
        return [], []

    with monkeypatch.context() as m:
        m.setattr(payment_mod, "merge", merge_that_records_nothing)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["duplicate_payment"].passed is False
    assert broken.misses == ("duplicate_payment",)
    assert broken.demotions == ("payments.dedupe",)
    assert all(t.passed for t in broken.traps if t.key != "duplicate_payment")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_duplicate_payment_hash_ignores_amount(monkeypatch):
    """The reviewer's second break: `payment_id` computed with `amount`
    zeroed out. The old check never exercised two genuinely different
    payments at all, so a $450 cheque and a $4,500 cheque from the same
    client on the same day, colliding into ONE row and silently dropping
    the second, passed clean. This is the payment-hash collision
    configs/autonomy/traps.yaml names for this key, from the direction that
    loses revenue rather than the direction that double-counts it.
    """
    import satc.billing.payment as payment_mod

    real_payment_id = payment_mod.payment_id

    def amount_blind_payment_id(*, amount, **kwargs):
        return real_payment_id(amount=Decimal("0"), **kwargs)

    with monkeypatch.context() as m:
        m.setattr(payment_mod, "payment_id", amount_blind_payment_id)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["duplicate_payment"].passed is False
    assert broken.misses == ("duplicate_payment",)
    assert broken.demotions == ("payments.dedupe",)
    assert all(t.passed for t in broken.traps if t.key != "duplicate_payment")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


def test_mutation_stale_cheque_matches_future_invoice(monkeypatch):
    import satc.billing.payment as payment_mod

    real_open_for = payment_mod._open_for

    def undated_open_for(client_id, invoices, payments, *, arrived_on=None):
        # The exact shape of the shipped defect: the arrival date is dropped
        # on the floor, so an invoice issued decades later is still "open".
        return real_open_for(client_id, invoices, payments, arrived_on=None)

    with monkeypatch.context() as m:
        m.setattr(payment_mod, "_open_for", undated_open_for)
        broken = run_drill(today=TODAY)

    assert _by_key(broken)["stale_cheque_matches_future_invoice"].passed is False
    assert broken.misses == ("stale_cheque_matches_future_invoice",)
    assert broken.demotions == ("payments.reconcile",)
    assert all(t.passed for t in broken.traps
               if t.key != "stale_cheque_matches_future_invoice")

    restored = run_drill(today=TODAY)
    assert restored.misses == ()


# --- tripwires fail toward the click: "cannot run" is a miss, never a skip --


def test_a_check_that_raises_is_a_miss_not_a_skip(monkeypatch):
    def boom(practice):
        raise RuntimeError("Ollama unreachable")

    with monkeypatch.context() as m:
        m.setattr(traps, "_CHECKS", {**traps._CHECKS, "zero_line_invoice": boom})
        result = run_drill(today=TODAY)

    assert result.ran is True
    row = _by_key(result)["zero_line_invoice"]
    assert row.passed is False
    assert "Ollama unreachable" in row.observed
    assert "zero_line_invoice" in result.misses
    assert "billing.invoice_issue" in result.demotions
    # A check that couldn't run must not silently vanish from the report —
    # the other four still ran and are unaffected.
    assert len(result.traps) == 5


def test_the_whole_practice_failing_to_build_misses_every_trap(monkeypatch):
    def broken(today):
        raise RuntimeError("cannot construct synthetic clients")

    with monkeypatch.context() as m:
        m.setattr(traps, "_build_synthetic_practice", broken)
        result = run_drill(today=TODAY)

    assert result.ran is True
    assert set(result.misses) == set(ALL_KEYS)
    assert set(result.demotions) == {
        "billing.invoice_issue", "documents.chase", "comms.render",
        "payments.dedupe", "payments.reconcile",
    }
    assert len(result.traps) == 5
    assert all(not t.passed for t in result.traps)


def test_a_missing_traps_config_is_a_miss_not_a_skip(tmp_path):
    empty_root = tmp_path / "configs"
    (empty_root / "autonomy").mkdir(parents=True)
    # No traps.yaml written at all — the drill has nothing telling it what to check.

    result = run_drill(today=TODAY, config_root=empty_root)

    assert result.ran is True
    assert result.misses == ("_config",)
    assert result.demotions == ("autonomy.drill",)
    assert len(result.traps) == 1
    assert "could not load" in result.traps[0].observed


def test_an_unparsable_traps_config_is_a_miss_not_a_skip(tmp_path):
    root = tmp_path / "configs"
    (root / "autonomy").mkdir(parents=True)
    (root / "autonomy" / "traps.yaml").write_text("traps: [this is not: a: valid: mapping", encoding="utf-8")

    result = run_drill(today=TODAY, config_root=root)

    assert result.ran is True
    assert result.misses == ("_config",)
    assert result.demotions == ("autonomy.drill",)


def test_a_trap_declared_with_no_check_function_is_a_miss(tmp_path):
    root = tmp_path / "configs"
    (root / "autonomy").mkdir(parents=True)
    (root / "autonomy" / "traps.yaml").write_text(
        "traps:\n"
        "  - key: zero_line_invoice\n"
        "    capability: billing.invoice_issue\n"
        "    summary: a real one\n"
        "  - key: not_a_real_check\n"
        "    capability: something.imaginary\n"
        "    summary: declared but never implemented\n",
        encoding="utf-8")

    result = run_drill(today=TODAY, config_root=root)

    assert result.ran is True
    by_key = _by_key(result)
    assert by_key["zero_line_invoice"].passed is True
    assert by_key["not_a_real_check"].passed is False
    assert "no check function is registered" in by_key["not_a_real_check"].observed
    assert "not_a_real_check" in result.misses
    assert "something.imaginary" in result.demotions
    # The real trap next to it is unaffected — one bad declaration demotes
    # only the capability it named.
    assert "billing.invoice_issue" not in result.demotions


# --- the drill touches no real client record ----------------------------------


def test_the_drill_never_imports_persistence():
    """Parsed, not grepped — so the module stays free to talk ABOUT the store
    in its own docstrings without this test getting confused by prose.
    """
    tree = ast.parse(Path(traps.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("satc.persistence"), alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith("satc.persistence"), mod
            assert not mod.startswith("satc.app.state"), mod


def test_synthetic_ids_are_unmistakably_synthetic():
    practice = traps._build_synthetic_practice(TODAY)
    ids = [
        practice.zero_line_invoice.client_id,
        practice.zero_line_invoice.invoice_id,
        practice.chase_client_id,
        practice.duplicate_payment.client_id,
        practice.distinct_payment_low.client_id,
        practice.distinct_payment_high.client_id,
        practice.predating_invoice.client_id,
        practice.predating_invoice.invoice_id,
        practice.predating_payment.client_id,
    ]
    assert all(cid.startswith("SATC-DRILL-") for cid in ids), ids


def test_running_the_drill_leaves_no_file_behind(tmp_path, monkeypatch):
    """The drill writes nothing to disk, real practice or otherwise."""
    monkeypatch.chdir(tmp_path)
    run_drill(today=TODAY)
    run_drill(today=TODAY)
    assert list(tmp_path.iterdir()) == []


# --- the CLI ------------------------------------------------------------------


def test_cli_drill_exits_zero_when_everything_passes(capsys):
    rc = cli.main(["drill"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in out
    for key in ALL_KEYS:
        assert key in out


def test_cli_drill_exits_nonzero_on_a_miss(monkeypatch, capsys):
    def fake_run_drill(*, today, config_root=None):
        return DrillResult(
            ran=True, today=today,
            traps=(TrapResult(key="zero_line_invoice", capability="billing.invoice_issue",
                              expected="e", observed="o", passed=False, why="w"),),
            misses=("zero_line_invoice",), demotions=("billing.invoice_issue",))

    monkeypatch.setattr("satc.autonomy.traps.run_drill", fake_run_drill)
    rc = cli.main(["drill"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "MISS" in out
    assert "billing.invoice_issue" in out


# --- Finding 3: the precondition gate must not survive a reset --------------
#
# This module owns satc.autonomy.traps, not satc.app.autonomy_views,
# satc.persistence.store, or satc.cli — but tests/test_traps.py is the only
# test file this slice is permitted to touch, so the coverage for those three
# files' precondition seam lives here rather than nowhere.
#
# THE BUG: autonomy_views.py used to write autonomy_preconditions.json next
# to the store's own database files instead of inside them. `satc reset`
# unlinks only the database files, so a freshly reset practice — zero
# clients, zero approvals — still showed "all three autonomy preconditions
# confirmed and current": the one gate meant to hold a wiped practice back
# was the one thing a wipe could not touch. Verified durable by an Opus
# reviewer against the real drill.
#
# THE FIX: preconditions now live in a table inside satc_mart.db (deleted by
# `satc reset` the same as everything else), and a legacy JSON file left over
# from the earlier design is imported into the store exactly once and then
# renamed out of the way — and `satc reset` also removes the legacy file and
# its renamed markers, so an UN-migrated copy cannot resurrect old
# confirmations after a reset either.


def _autonomy_state(tmp_path, monkeypatch):
    """A fresh AppState pointed at an isolated data directory, wired into
    satc.app.autonomy_views exactly the way the real app is (that module
    binds `STATE` at import time via `from satc.app.state import STATE`, so
    the module-level name has to be patched directly for a substitute store
    to actually be seen)."""
    import satc.app.autonomy_views as autonomy_views_mod
    from satc.app.state import AppState

    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    state = AppState()
    monkeypatch.setattr(autonomy_views_mod, "STATE", state)
    return autonomy_views_mod, state


def test_a_store_built_before_the_preconditions_table_existed_still_opens_and_saves(tmp_path):
    """``CREATE TABLE IF NOT EXISTS`` is the whole migration for a brand-new
    table (same reasoning ``approvals`` got, per store.py's own DDL comment)
    — but that is only true if it actually runs against a database that
    predates the table. Simulate exactly that: an older mart.db with no
    ``autonomy_preconditions`` table in it at all, the same technique
    tests/test_store.py uses for its own legacy-schema coverage."""
    import sqlite3

    from satc.autonomy.preconditions import PreconditionRecord
    from satc.persistence.store import SATCStore

    legacy = sqlite3.connect(tmp_path / "satc_mart.db")
    legacy.execute("CREATE TABLE app_meta (k TEXT PRIMARY KEY, v TEXT)")
    legacy.commit()
    legacy.close()

    with SATCStore(tmp_path) as store:
        assert store.load_preconditions() == []
        store.save_preconditions([PreconditionRecord(
            key="mfa", confirmed_on=TODAY, confirmed_by="owner")])
        assert [r.key for r in store.load_preconditions()] == ["mfa"]


def test_a_recorded_precondition_survives_an_ordinary_reload(tmp_path, monkeypatch):
    from satc.autonomy.preconditions import record_precondition
    from satc.models.actor import Actor

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    record = record_precondition(actor=Actor.owner(), key="mfa", confirmed_on=TODAY)
    assert autonomy_views._record_precondition(record) is True
    assert [r.key for r in autonomy_views.load_preconditions()] == ["mfa"]
    # Pinned to the STORE directly, not just to whatever load_preconditions()
    # happens to read back — a JSON file beside the store could satisfy the
    # line above on its own and still be the exact bug this slice fixes.
    assert [r.key for r in state.store.load_preconditions()] == ["mfa"]
    state.store.close()


def test_the_precondition_gate_does_not_survive_a_reset(tmp_path, monkeypatch):
    """Confirm all three, reset the store, and confirm the gate reads as
    fully missing again — not still "confirmed and current" on a practice
    that was just wiped to zero clients and zero approvals."""
    from satc.autonomy.preconditions import ALL_PRECONDITIONS, gate_status, record_precondition
    from satc.models.actor import Actor

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    actor = Actor.owner()
    for key in ALL_PRECONDITIONS:
        autonomy_views._record_precondition(
            record_precondition(actor=actor, key=key, confirmed_on=TODAY))

    before = gate_status(autonomy_views.load_preconditions(), cadence_days=90, today=TODAY)
    assert before.holds is True
    state.store.close()          # release the sqlite handle before unlinking it

    rc = cli.main(["reset", "--dir", str(tmp_path), "--yes"])
    assert rc == 0

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    after = gate_status(autonomy_views.load_preconditions(), cadence_days=90, today=TODAY)
    assert after.holds is False
    assert set(after.missing) == set(ALL_PRECONDITIONS)
    state.store.close()


def test_mutation_a_reset_that_only_deletes_the_databases_lets_the_gate_survive(
        tmp_path, monkeypatch):
    """The exact shape of the shipped defect, reproduced on purpose: unlink
    ONLY satc_vault.db and satc_mart.db (the original `satc reset`) against a
    legacy JSON ledger that was never migrated in, and confirm the gate comes
    back holding — resurrected, on a practice that was supposed to be wiped.
    Then run the REAL, fixed `satc reset` over the identical setup and
    confirm it does not."""
    import json

    from satc.autonomy.preconditions import ALL_PRECONDITIONS, gate_status

    legacy_path = tmp_path / "autonomy_preconditions.json"

    def _seed_legacy_confirmations():
        legacy_path.write_text(json.dumps([
            {"key": k, "confirmed_on": TODAY.isoformat(), "confirmed_by": "owner", "note": ""}
            for k in ALL_PRECONDITIONS
        ]), encoding="utf-8")

    # -- reproduce the bug: the ORIGINAL reset, database files only ----------
    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    _seed_legacy_confirmations()
    state.store.close()

    for name in ("satc_vault.db", "satc_mart.db"):
        (tmp_path / name).unlink(missing_ok=True)
    assert legacy_path.exists(), "the original reset never touched this file"

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    resurrected = gate_status(autonomy_views.load_preconditions(), cadence_days=90, today=TODAY)
    assert resurrected.holds is True, (
        "this IS the defect: a reset practice reading as fully cleared for "
        "autonomy is exactly what charter section 3 forbids"
    )
    state.store.close()

    # -- confirm the fix: the REAL `satc reset` over the identical setup ----
    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    _seed_legacy_confirmations()   # a fresh, un-migrated legacy file again
    state.store.close()

    rc = cli.main(["reset", "--dir", str(tmp_path), "--yes"])
    assert rc == 0
    assert not legacy_path.exists()

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    fixed = gate_status(autonomy_views.load_preconditions(), cadence_days=90, today=TODAY)
    assert fixed.holds is False
    assert set(fixed.missing) == set(ALL_PRECONDITIONS)
    state.store.close()


def test_a_pre_store_json_ledger_is_imported_once_then_renamed(tmp_path, monkeypatch):
    """The migration off the old JSON-beside-the-store design: a legacy file
    is read into the store once, then renamed so it can never be re-read —
    otherwise a reset followed by a reload would import it right back
    (see the mutation test above)."""
    import json

    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    legacy_path = tmp_path / "autonomy_preconditions.json"
    legacy_path.write_text(json.dumps([
        {"key": "mfa", "confirmed_on": TODAY.isoformat(), "confirmed_by": "owner", "note": ""},
    ]), encoding="utf-8")

    loaded = autonomy_views.load_preconditions()
    assert [r.key for r in loaded] == ["mfa"]
    assert not legacy_path.exists()
    assert legacy_path.with_suffix(".json.imported").exists()

    # Reloading again must not double the row, and must not need the file —
    # it is already gone.
    loaded_again = autonomy_views.load_preconditions()
    assert [r.key for r in loaded_again] == ["mfa"]
    state.store.close()


def test_an_unreadable_pre_store_json_ledger_is_named_not_trusted_or_dropped(
        tmp_path, monkeypatch):
    """Neither half of principle 5's "refuse rather than default": an
    unparsable legacy file is not silently imported as zero facts (that
    would be trusting a coin flip), and it is not silently deleted either
    (that would drop evidence the owner might need to look at) — it is
    renamed to say what is wrong with it."""
    autonomy_views, state = _autonomy_state(tmp_path, monkeypatch)
    legacy_path = tmp_path / "autonomy_preconditions.json"
    legacy_path.write_text("{not json", encoding="utf-8")

    loaded = autonomy_views.load_preconditions()
    assert loaded == []
    assert not legacy_path.exists()
    assert legacy_path.with_suffix(".json.unreadable").exists()
    state.store.close()


def test_reset_also_clears_the_legacy_json_ledger_and_its_renamed_markers(tmp_path):
    """A reset has to remove every copy of the gate, including a legacy file
    that was already imported (`.json.imported`) or found unreadable
    (`.json.unreadable`) on some earlier run — leaving either behind is
    harmless to THIS reset (neither is read again by its original name) but
    is still a stray copy of PII-adjacent practice state in a directory a
    reset is supposed to have emptied."""
    names = ("satc_vault.db", "satc_mart.db", "autonomy_preconditions.json",
            "autonomy_preconditions.json.imported", "autonomy_preconditions.json.unreadable")
    for name in names:
        (tmp_path / name).write_bytes(b"x")

    rc = cli.main(["reset", "--dir", str(tmp_path), "--yes"])
    assert rc == 0
    for name in names:
        assert not (tmp_path / name).exists(), name
