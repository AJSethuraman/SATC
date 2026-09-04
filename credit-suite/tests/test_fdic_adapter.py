"""The FDIC adapter and metric registry must produce identical numbers.

This is the parity precondition. The workbook's values come from the demo
provider through the metric registry, so if either moves by a float, the golden
diff lights up and the migration is not parity-preserving. Better to catch it
here, where the failure names a field and a quarter, than in a 22,836-cell diff.
"""

from __future__ import annotations

from datetime import date

import pytest

from credit_suite.engine.config import EntityRow
from credit_suite.engine.metrics import metric_value
from credit_suite.engine.provider import make_field_spec
from credit_suite.sources.fdic import adapter, fields
from credit_suite.sources.fdic.spec import FDIC

from test_engine_config import _load_legacy, legacy  # noqa: F401

ASOF = date(2026, 3, 31)
#: The seeded peer set, plus keys chosen to hit the demo profile's special
#: cases: the null-BRO bank (s % 17 == 3), null-auto (s % 19 == 9) and
#: null-DEPUNINS (s % 23 == 7) branches.
CERTS = ["628", "3511", "3510", "7213", "6548", "6384", "9846", "4297",
         "17534", "639", "33124", "32992", "1", "2", "3", "17", "19", "23"]


def entity(slot, key):
    return EntityRow(slot=slot, key=key, name="Bank %s" % key, group="peer",
                     active=True, key_prefix="cert")


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------

@legacy
def test_the_registry_holds_exactly_the_legacy_metrics():
    old = _load_legacy()
    assert set(fields.REGISTRY) == set(old.METRICS)
    assert len(fields.REGISTRY) == 53
    for name in sorted(fields.REGISTRY):
        got_fields, got_fn = fields.REGISTRY[name]
        want_fields, want_fn = old.METRICS[name]
        assert set(got_fields) == set(want_fields), name
        assert (got_fn is None) == (want_fn is None), name


@legacy
def test_every_metric_computes_the_same_value_as_the_legacy_registry():
    """Over real demo fields, for every bank and every metric -- not a sample."""
    old = _load_legacy()
    demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    demo.prime(CERTS, ASOF)
    checked = 0
    for cert in CERTS:
        quarters = demo._profile(cert)
        for _period, values in quarters:
            for name in sorted(fields.REGISTRY):
                assert metric_value(fields.REGISTRY, name, values) == \
                    old.metric_value(name, values), (cert, name)
                checked += 1
    assert checked == len(CERTS) * 16 * 53


@legacy
def test_the_field_table_is_unchanged():
    old = _load_legacy()
    assert fields.RAW_FIELDS == old.RAW_FIELDS
    assert fields.PCT_FIELDS == old.PCT_FIELDS
    assert fields.FIELD_UNITS == old.FIELD_UNITS
    assert fields.PACK_RATIOS == old.PACK_RATIOS
    assert fields.LOANBOOK_CLASS == old.LOANBOOK_CLASS


def test_the_field_table_is_the_size_the_pack_declares():
    assert len(fields.RAW_FIELDS) == 68
    assert len(set(fields.RAW_FIELDS)) == 68, "a duplicated field shifts columns"
    assert len(fields.RAW_FIELDS) + 2 < fields.MAX_REQUEST_FIELDS


def test_units_are_assigned_to_every_field_and_only_two_kinds_exist():
    """Trap F4: mixing $ thousands with percents is what units exist to stop."""
    assert set(fields.FIELD_UNITS) == set(fields.RAW_FIELDS)
    assert set(fields.FIELD_UNITS.values()) == {"USD_thousands", "pct"}
    assert fields.FIELD_UNITS["ASSET"] == "USD_thousands"
    assert fields.FIELD_UNITS["NCLNLSR"] == "pct"


# --------------------------------------------------------------------------
# the demo provider
# --------------------------------------------------------------------------

@legacy
def test_the_demo_provider_returns_identical_rows_to_the_legacy_one():
    """Every bank x every field x every quarter. The parity linchpin."""
    old = _load_legacy()
    new_demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    old_demo = old.FdicDemoProvider(asof=ASOF, raw_slots=16)
    new_demo.prime(CERTS, ASOF)
    old_demo.prime(CERTS, ASOF)

    checked = 0
    for slot, cert in enumerate(CERTS, start=1):
        new_row = entity(slot, cert)
        old_row = old.PeerRow(slot=slot, cert=cert, name="Bank %s" % cert,
                              group="peer", active=True)
        for fname in fields.RAW_FIELDS:
            got = new_demo.fetch_series(
                make_field_spec(new_row, fname, fields.FIELD_UNITS))
            want = old_demo.fetch_series(old.make_field_spec(old_row, fname))
            assert len(got) == len(want), (cert, fname)
            for g, w in zip(got, want):
                assert (g.id, g.period, g.value, g.geo_segment, g.source_class,
                        g.units) == (w.id, w.period, w.value, w.geo_segment,
                                     w.source_class, w.units), (cert, fname)
            checked += 1
    assert checked == len(CERTS) * 68


def test_the_demo_provider_is_deterministic_for_a_fixed_asof():
    a = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    b = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    a.prime(CERTS, ASOF)
    b.prime(CERTS, ASOF)
    assert a._profile("628") == b._profile("628")


def test_the_same_bank_yields_the_same_history_in_any_slot():
    """So a [PEERS] swap visibly moves data between slots rather than
    regenerating it -- which is what makes a swap reviewable."""
    demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    demo.prime(CERTS, ASOF)
    first = demo.fetch_series(make_field_spec(entity(1, "628"), "ASSET",
                                             fields.FIELD_UNITS))
    ninth = demo.fetch_series(make_field_spec(entity(9, "628"), "ASSET",
                                             fields.FIELD_UNITS))
    assert [r.value for r in first] == [r.value for r in ninth]
    assert first[0].id == "s01_ASSET" and ninth[0].id == "s09_ASSET"


def test_the_demo_provider_needs_no_key_and_no_network():
    """Every test in the suite depends on this being true."""
    demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    demo.prime(["628"], ASOF)
    rows = demo.fetch_series(make_field_spec(entity(1, "628"), "ASSET",
                                             fields.FIELD_UNITS))
    assert rows and rows[0].value is not None
    assert "demo" in (demo.vintage or "").lower()


def test_the_demo_data_carries_nulls_that_never_read_as_zero():
    """Trap F3 rehearsed in the demo set: some banks genuinely have no BRO, no
    auto book, or no DEPUNINS, and those must arrive as None."""
    demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    demo.prime(CERTS, ASOF)
    seen_null = False
    for cert in CERTS:
        for _period, values in demo._profile(cert):
            if any(v is None for v in values.values()):
                seen_null = True
    assert seen_null, "no null anywhere -- the F3 path is never exercised"


def test_a_null_never_arrives_in_the_newest_two_quarters():
    """The headline formulas read the newest quarter, so an injected null there
    would blank a dashboard for a reason that is an artefact of the demo."""
    demo = adapter.FdicDemoProvider(asof=ASOF, raw_slots=16)
    demo.prime(CERTS, ASOF)
    for cert in CERTS:
        quarters = demo._profile(cert)          # oldest-first
        newest = quarters[-1][1]
        populated = [v for v in newest.values() if v is not None]
        assert len(populated) > 40, \
            "%s: newest quarter is mostly blank (%d populated)" % (cert,
                                                                   len(populated))


# --------------------------------------------------------------------------
# provider selection
# --------------------------------------------------------------------------

def test_demo_mode_is_honoured_from_the_flag_and_from_config():
    from credit_suite.engine.config import Config
    cfg = Config(spec=FDIC, settings={"demo_mode": "FALSE", "raw_slots": "16"})
    assert isinstance(adapter.make_provider(cfg, True, ASOF),
                      adapter.FdicDemoProvider)
    cfg_demo = Config(spec=FDIC, settings={"demo_mode": "TRUE", "raw_slots": "16"})
    assert isinstance(adapter.make_provider(cfg_demo, False, ASOF),
                      adapter.FdicDemoProvider)


def test_the_live_provider_is_keyless():
    """FDIC BankFind needs no key, so there is no secret to fail fast on -- and
    nothing that could leak into a workbook or a bundle."""
    from credit_suite.engine.config import Config
    from credit_suite.engine.provider import resolve_secret
    cfg = Config(spec=FDIC, settings={"demo_mode": "FALSE", "raw_slots": "16"})
    live = adapter.make_provider(cfg, False, ASOF)
    assert isinstance(live, adapter.FdicProvider)
    assert resolve_secret(cfg) is None
