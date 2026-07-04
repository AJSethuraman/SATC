"""The identity vault is encrypted at rest — SSNs/names are never plaintext on disk,
but reads round-trip transparently and legacy plaintext is migrated on open."""

from __future__ import annotations

from satc.models.identity import IdentityRecord, VaultAddress, VaultContact
from satc.persistence.store import SATCStore


def _client():
    return IdentityRecord(
        client_id="C-1", entity_type="INDIVIDUAL",
        legal_name="Zelda Quibblesworth", tin="400-55-9999",
        addresses=[VaultAddress(line1="123 Secret Ln", city="Athens", state="OH", zip="45701")],
        contacts=[VaultContact(name="Zelda Quibblesworth", email="zq@example.com",
                               phone="555-0100", role="Taxpayer")],
    )


def test_pii_is_ciphertext_on_disk_but_reads_round_trip(tmp_path):
    store = SATCStore(directory=tmp_path)
    store.upsert_identity(_client())

    raw = (tmp_path / "satc_vault.db").read_bytes()
    for secret in (b"400-55-9999", b"Quibblesworth", b"123 Secret Ln", b"zq@example.com"):
        assert secret not in raw, f"{secret!r} is plaintext on disk"

    assert store.names()["C-1"] == "Zelda Quibblesworth"
    assert store.client_email("C-1") == "zq@example.com"


def test_migration_encrypts_legacy_plaintext_and_vacuums(tmp_path):
    # Simulate a pre-encryption store: write plaintext straight into the table.
    store = SATCStore(directory=tmp_path)
    store.vault.execute("INSERT OR REPLACE INTO identities VALUES (?,?,?,?)",
                        ("C-OLD", "INDIVIDUAL", "Legacy Plainname", "111-22-3333"))
    store.vault.commit()
    store.vault.close()

    store2 = SATCStore(directory=tmp_path)  # re-open -> migrate + VACUUM
    raw = (tmp_path / "satc_vault.db").read_bytes()
    assert b"111-22-3333" not in raw
    assert b"Legacy Plainname" not in raw
    assert store2.names()["C-OLD"] == "Legacy Plainname"


def test_empty_email_stays_empty_and_selectable(tmp_path):
    store = SATCStore(directory=tmp_path)
    store.upsert_identity(IdentityRecord(
        client_id="C-2", entity_type="INDIVIDUAL", legal_name="No Email", tin="",
        contacts=[VaultContact(name="No Email", email="", phone="", role="Taxpayer")]))
    assert store.client_email("C-2") == ""


def test_cipher_is_idempotent_no_double_encrypt(tmp_path):
    from satc.persistence.crypto import open_cipher
    c = open_cipher(tmp_path)
    once = c.encrypt("hello")
    assert c.encrypt(once) == once            # already-encrypted passes through
    assert c.decrypt(once) == "hello"
    assert c.decrypt("legacy plaintext") == "legacy plaintext"  # tolerant of un-migrated
