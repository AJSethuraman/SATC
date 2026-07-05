"""Encryption-at-rest for engagement workbooks (AES-256-GCM).

A real engagement workbook holds a client bank's confidential borrower data;
it must never sit on disk readable. Mirrors ``satc_system``'s vault approach
(``satc/persistence/crypto.py``): the AES-GCM data encryption is identical on
every platform; only the *key sealing* is OS-specific.

Key management (256-bit key, generated once, stored in the key dir):
  * **Windows (the owner's platform):** the key file is sealed with DPAPI
    (``CryptProtectData``) so only the same Windows user account can unseal
    it; copying workbook + key elsewhere does not decrypt.
  * **Other platforms / no pywin32:** raw key in a ``0600`` file — a
    documented weaker fallback relying on file permissions + full-disk
    encryption.

Encrypted files are ``CROSENC1 | nonce(12) | AES-GCM(ciphertext+tag)``. The
repo itself stores only synthetic demo artifacts — encryption gates real-
engagement use, not the demo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"CROSENC1"
_KEY_FILE = "credit_review.key"


def default_key_dir() -> Path:
    return Path.home() / ".credit-review"


# -- key sealing (satc_system pattern) --------------------------------------
def _seal(key: bytes) -> bytes:
    if sys.platform == "win32":
        try:
            import win32crypt  # from pywin32 (bundled on Windows)

            sealed = win32crypt.CryptProtectData(
                key, "Credit Review OS key", None, None, None, 0)
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
    return blob


def _restrict(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # best effort (Windows relies on the DPAPI seal + NTFS ACLs)


def load_or_create_key(key_dir: Path | None = None) -> bytes:
    key_dir = Path(key_dir) if key_dir else default_key_dir()
    key_dir.mkdir(parents=True, exist_ok=True)
    key_path = key_dir / _KEY_FILE
    if key_path.exists():
        return _unseal(key_path.read_bytes())
    key = AESGCM.generate_key(bit_length=256)
    key_path.write_bytes(_seal(key))
    _restrict(key_path)
    return key


# -- whole-file encryption ---------------------------------------------------
def is_encrypted(data: bytes) -> bool:
    return data.startswith(MAGIC)


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    if is_encrypted(data):
        return data  # idempotent — never double-encrypt
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, None)


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    if not is_encrypted(blob):
        return blob  # already plaintext (the synthetic demo path)
    body = blob[len(MAGIC):]
    nonce, ct = body[:12], body[12:]
    return AESGCM(key).decrypt(nonce, ct, None)
