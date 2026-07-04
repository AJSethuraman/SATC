"""At-rest encryption for the vault's client PII (AES-256-GCM).

The identity vault holds the crown-jewel data — legal names, SSNs/EINs, home
addresses, contact info. This module keeps those fields as ciphertext on disk so
a copied/synced/backed-up ``satc_vault.db`` yields nothing readable. Encrypted
values are stored as ``enc:v1:<base64(nonce|ciphertext+tag)>``.

Key management (256-bit data key, generated once, stored in the data dir):
  * **Windows (the target platform):** the key file is sealed with **DPAPI**
    (``CryptProtectData``), so only the same Windows user account can unseal it.
    Copying the vault + key to another machine/user does NOT decrypt it, and the
    user never types a passphrase. Requires ``pywin32`` (bundled on Windows).
  * **Other platforms / no pywin32:** the key is stored raw in a ``0600`` file.
    This is a documented weaker fallback that relies on full-disk encryption and
    file permissions — it is not equivalent to the DPAPI seal.

The AES-GCM data encryption is identical on every platform (and unit-tested);
only the *key sealing* is OS-specific.
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_PREFIX = "enc:v1:"
_KEY_FILE = "vault.key"


class VaultCipher:
    """AES-256-GCM field encryption. Empty strings stay empty (so ``!=''`` SQL
    filters keep working); legacy plaintext is passed through on decrypt so an
    un-migrated value never crashes a read."""

    def __init__(self, key: bytes) -> None:
        self._aes = AESGCM(key)

    def is_encrypted(self, value: str | None) -> bool:
        return bool(value) and isinstance(value, str) and value.startswith(_PREFIX)

    def encrypt(self, plaintext: str | None) -> str | None:
        if plaintext is None or plaintext == "":
            return plaintext
        if self.is_encrypted(plaintext):
            return plaintext  # idempotent — never double-encrypt
        nonce = os.urandom(12)
        blob = nonce + self._aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return _PREFIX + base64.b64encode(blob).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if not self.is_encrypted(value):
            return value  # empty, None, or legacy plaintext
        raw = base64.b64decode(value[len(_PREFIX):])
        nonce, ct = raw[:12], raw[12:]
        return self._aes.decrypt(nonce, ct, None).decode("utf-8")


# --------------------------------------------------------------------------
# Key sealing
# --------------------------------------------------------------------------

def _seal(key: bytes) -> bytes:
    if sys.platform == "win32":
        try:
            import win32crypt  # from pywin32 (bundled on Windows)

            sealed = win32crypt.CryptProtectData(key, "SATC vault key", None, None, None, 0)
            return b"DPAPI\x00" + sealed
        except Exception:
            pass  # fall through to raw storage if DPAPI is unavailable
    return b"RAW\x00" + key


def _unseal(blob: bytes) -> bytes:
    if blob.startswith(b"DPAPI\x00"):
        import win32crypt

        return win32crypt.CryptUnprotectData(blob[6:], None, None, None, 0)[1]
    if blob.startswith(b"RAW\x00"):
        return blob[4:]
    return blob  # very old raw-key file with no header


def _restrict(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # best effort (e.g. Windows without POSIX perms — NTFS ACLs handle it)


def load_or_create_key(data_dir: Path) -> bytes:
    """Return the vault data key, creating + sealing it on first run."""
    key_path = Path(data_dir) / _KEY_FILE
    if key_path.exists():
        return _unseal(key_path.read_bytes())
    key = AESGCM.generate_key(bit_length=256)
    key_path.write_bytes(_seal(key))
    _restrict(key_path)
    return key


def open_cipher(data_dir: Path) -> VaultCipher:
    return VaultCipher(load_or_create_key(Path(data_dir)))
