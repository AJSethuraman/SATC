"""The vault key has to survive the machine it was made on.

THE FIRM, 4 September 2026, told to open `vault.key` in Notepad and paste it
into a password manager: *"i opened this in notepad and it looks corrupted,
values cant be read at all"*.

It was not corrupted. `vault.key` is 296 bytes beginning `DPAPI\\0` — the 32-byte
AES key wrapped by Windows' Data Protection API — and Notepad renders binary as
mojibake. The instruction was wrong, not the file.

THE INSTRUCTION WAS ALSO WRONG IN A WAY THAT WOULD HAVE LOOKED LIKE IT WORKED.
`_seal` calls `CryptProtectData` with no entropy and no machine flag, so the
wrapping is bound to one Windows account on one machine. A byte-perfect copy of
the sealed file restored onto a replacement laptop cannot be unwrapped — which
is the exact disaster the copy was made for. The backup would have sat in
Bitwarden looking like insurance and been worth nothing on the only day it
mattered.

So what leaves the machine is the key inside the wrapper: 32 bytes, 44
characters of base64. These tests hold that the round trip works and that the
one irreversible mistake is refused.
"""

from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "vault_key", ROOT / "scripts" / "vault_key.py")
vault_key = importlib.util.module_from_spec(_spec)
sys.modules["vault_key"] = vault_key
_spec.loader.exec_module(vault_key)

from satc.persistence import crypto  # noqa: E402


def _make(dir_: Path) -> bytes:
    dir_.mkdir(parents=True, exist_ok=True)
    return crypto.load_or_create_key(dir_)


def _shown(capsys) -> str:
    """The 44 characters `--show` printed."""
    out = capsys.readouterr().out
    for line in out.splitlines():
        s = line.strip()
        if len(s) == 44 and s.endswith("="):
            return s
    raise AssertionError("no key line in:\n" + out)


# -- the round trip that is the whole point -----------------------------------

def test_a_key_survives_being_carried_to_another_machine(tmp_path, capsys):
    """THE DISASTER THIS EXISTS FOR. Disk dies; a new machine gets the 44
    characters out of the password manager and the old vault opens."""
    here, elsewhere = tmp_path / "old", tmp_path / "new"
    original = _make(here)

    assert vault_key.show(here) == 0
    exported = _shown(capsys)

    assert vault_key.restore(elsewhere, exported) == 0
    assert crypto.load_or_create_key(elsewhere) == original

    # Not just equal bytes -- data written before the move must read after it.
    before = crypto.VaultCipher(original).encrypt("Jane Q Client")
    after = crypto.VaultCipher(crypto.load_or_create_key(elsewhere))
    assert after.decrypt(before) == "Jane Q Client"


def test_what_is_exported_is_the_key_itself_not_the_wrapper(tmp_path, capsys):
    """The sealed file is ~296 bytes and machine-bound; the key is 32 bytes and
    portable. Exporting the wrapper is the mistake that looks like it worked."""
    here = tmp_path / "d"
    key = _make(here)
    assert vault_key.show(here) == 0
    assert base64.b64decode(_shown(capsys)) == key
    assert len(key) == 32
    assert len((here / "vault.key").read_bytes()) > 32


# -- the mistake that cannot be undone ----------------------------------------

def test_it_refuses_to_overwrite_an_existing_key(tmp_path, capsys):
    """A vault encrypted with one key and handed another is unreadable for
    good, by anybody. This is the only truly irreversible action here."""
    here = tmp_path / "d"
    original = _make(here)
    other = base64.b64encode(b"z" * 32).decode()

    assert vault_key.restore(here, other) == 1
    assert "Refusing to overwrite" in capsys.readouterr().out
    assert crypto.load_or_create_key(here) == original, "the key was replaced"


@pytest.mark.parametrize("junk", ["", "not base64!!", "c2hvcnQ=",
                                  base64.b64encode(b"x" * 31).decode(),
                                  base64.b64encode(b"x" * 33).decode()])
def test_a_key_that_is_not_a_key_is_refused_and_writes_nothing(tmp_path, junk):
    here = tmp_path / "d"
    here.mkdir()
    assert vault_key.restore(here, junk) == 1
    assert not (here / "vault.key").exists()


def test_a_key_of_exactly_the_right_length_is_accepted(tmp_path):
    """The length check must not be so keen it rejects real keys."""
    here = tmp_path / "d"
    assert vault_key.restore(here, base64.b64encode(b"k" * 32).decode()) == 0
    assert crypto.load_or_create_key(here) == b"k" * 32


# -- verify says what is true, and never says the key ------------------------

def test_verify_proves_the_key_without_printing_it(tmp_path, capsys):
    here = tmp_path / "d"
    key = _make(here)
    assert vault_key.verify(here) == 0
    out = capsys.readouterr().out
    assert "Round trip: ok" in out
    assert base64.b64encode(key).decode() not in out, "verify leaked the key"
    assert key.hex() not in out


def test_verify_reports_a_missing_key_rather_than_crashing(tmp_path, capsys):
    here = tmp_path / "empty"
    here.mkdir()
    assert vault_key.verify(here) == 1
    assert "MISSING" in capsys.readouterr().out


def test_verify_says_out_loud_when_a_key_is_not_wrapped(tmp_path, capsys):
    """`_seal` falls back to RAW when DPAPI is unavailable, silently. A key
    sitting unwrapped on disk is a different security posture and the check
    that looks at it should say so rather than reporting a cheerful ok."""
    here = tmp_path / "d"
    here.mkdir()
    (here / "vault.key").write_bytes(b"RAW\x00" + b"k" * 32)
    assert vault_key.verify(here) == 0
    assert "NOT WRAPPED" in capsys.readouterr().out


# -- nothing is exported that does not exist ---------------------------------

def test_show_on_a_machine_with_no_vault_says_so(tmp_path, capsys):
    here = tmp_path / "empty"
    here.mkdir()
    assert vault_key.show(here) == 1
    assert "no key" in capsys.readouterr().out.lower()
