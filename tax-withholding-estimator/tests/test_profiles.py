"""Tests for profile storage (uses TWE_PROFILE_DIR to stay in a temp dir)."""

from __future__ import annotations

import importlib

import pytest

from twe.paystub import FieldRule, Profile


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("TWE_PROFILE_DIR", str(tmp_path))
    import twe.profiles as profiles
    importlib.reload(profiles)
    return profiles


def _profile(name: str) -> Profile:
    return Profile(
        name=name,
        pay_frequency="biweekly",
        rules=[FieldRule(field="gross_pay_per_period", kind="currency",
                         region=[0.4, 0.1, 0.5, 0.13], label_text="Gross Pay")],
        match_keywords=["Acme"],
    )


def test_save_and_load_roundtrip(store):
    saved = _profile("Acme Biweekly")
    store.save_profile(saved)
    loaded = store.load_profile("Acme Biweekly")
    assert loaded is not None
    assert loaded.name == "Acme Biweekly"
    assert loaded.pay_frequency == "biweekly"
    assert loaded.rules[0].field == "gross_pay_per_period"
    assert loaded.rules[0].label_text == "Gross Pay"
    assert loaded.match_keywords == ["Acme"]


def test_list_profiles(store):
    store.save_profile(_profile("Beta Corp"))
    store.save_profile(_profile("Acme Inc"))
    names = [p.name for p in store.list_profiles()]
    assert names == ["Acme Inc", "Beta Corp"]  # sorted by name


def test_delete_profile(store):
    store.save_profile(_profile("Temp"))
    assert store.delete_profile("Temp") is True
    assert store.load_profile("Temp") is None
    assert store.delete_profile("Temp") is False


def test_empty_name_rejected(store):
    with pytest.raises(ValueError):
        store.save_profile(_profile("   "))


def test_load_missing_returns_none(store):
    assert store.load_profile("nope") is None
