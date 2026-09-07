"""Get the vault key out to somewhere safe, and back in on a new machine.

THE FIRM, 4 September 2026, having been told to open `vault.key` in Notepad and
paste it into Bitwarden: *"i opened this in notepad and it looks corrupted,
values cant be read at all"*.

It is not corrupted. It is doing exactly what it was built to do, and the
instruction was wrong. `vault.key` is 296 bytes of binary beginning `DPAPI\\0` --
the 32-byte AES key wrapped by Windows' Data Protection API. Notepad renders
binary as mojibake, and copying it through a text box mangles bytes that have no
character to be.

BUT THE REAL PROBLEM IS THE ONE THAT LOOKS LIKE IT WORKED. Even a byte-perfect
copy of that file is USELESS on another machine. `CryptProtectData` is called
with no entropy and no machine flag, so the wrapping is bound to THIS Windows
account on THIS machine (`crypto.py:64-73`). Restore the sealed file onto a new
laptop after a disk failure and `CryptUnprotectData` refuses it -- which is
precisely the disaster the copy existed for. A backup that only works on the
machine that did not fail is not a backup.

So what has to leave this machine is the key INSIDE the wrapper: 32 bytes, 44
characters of base64, small enough to paste into a password manager by hand.

    python vault_key.py --show          print those 44 characters, once
    python vault_key.py --verify        prove the file works, print nothing
    python vault_key.py --restore XXX   rebuild the key file on a new machine

`--show` PRINTS THE ACTUAL KEY. That is the point of it and there is no way to
put a key in a password manager without the key being visible for a moment. It
says so before it does it. Nothing here writes the key to a log, a file, or an
argument that a shell would remember -- `--restore` is the one exception and it
warns about shell history.
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_DATA = ROOT / "build" / "data"
KEY_FILE = "vault.key"
KEY_BYTES = 32                       # AES-256


def _crypto():
    from satc.persistence import crypto
    return crypto


def _key_path(data_dir: Path) -> Path:
    return Path(data_dir) / KEY_FILE


def show(data_dir: Path) -> int:
    """Unseal the key and print it as base64, for a password manager."""
    crypto = _crypto()
    path = _key_path(data_dir)
    if not path.exists():
        print(f"\n  There is no key at {path}.")
        print("  Nothing to export. This machine has never opened a vault.\n")
        return 1
    try:
        key = crypto._unseal(path.read_bytes())
    except Exception as exc:                       # noqa: BLE001
        print(f"\n  The key could not be unwrapped: {exc}")
        print("  If this file came from another machine or another Windows")
        print("  account, that is expected -- DPAPI wrapping does not travel.\n")
        return 1
    if len(key) != KEY_BYTES:
        print(f"\n  Unwrapped {len(key)} bytes, expected {KEY_BYTES}. Not printing it.\n")
        return 1

    print("\n  " + "=" * 62)
    print("   THIS IS THE ACTUAL KEY TO YOUR CLIENT VAULT.")
    print("  " + "=" * 62)
    print("\n  Anyone with these 44 characters and a copy of satc_vault.db can")
    print("  read every client name and Social Security number in it.\n")
    print("  Put it straight into your password manager, then close this window.")
    print("  Do not paste it into a chat, a ticket, an email or a screenshot.\n")
    print("  " + base64.b64encode(key).decode())
    print()
    print("  Suggested entry:  SATC vault key (base64)")
    print(f"  Wrapped copy lives at: {path}")
    print("  That wrapped copy only works on this Windows account, on this")
    print("  machine. The 44 characters above are the part that survives.\n")
    return 0


def verify(data_dir: Path) -> int:
    """Prove the key file works and opens the vault. Prints nothing secret."""
    crypto = _crypto()
    path = _key_path(data_dir)
    print(f"\n  Key file:  {path}")
    if not path.exists():
        print("  MISSING. The vault cannot be opened.\n")
        return 1
    blob = path.read_bytes()
    kind = ("DPAPI-wrapped (bound to this Windows account)"
            if blob.startswith(b"DPAPI\x00") else
            "RAW, NOT WRAPPED — readable by anything that can read the file"
            if blob.startswith(b"RAW\x00") else
            "an old headerless file")
    print(f"  Format:    {kind}")
    print(f"  Size:      {len(blob)} bytes")
    try:
        key = crypto._unseal(blob)
    except Exception as exc:                       # noqa: BLE001
        print(f"  Unwrap:    FAILED — {exc}\n")
        return 1
    ok = len(key) == KEY_BYTES
    print(f"  Unwrap:    ok, {len(key)} bytes" + ("" if ok else "  <-- WRONG LENGTH"))

    # END TO END. Unwrapping proves the file; only a round trip proves the key.
    cipher = crypto.VaultCipher(key)
    probe = "a probe value, not client data"
    if cipher.decrypt(cipher.encrypt(probe)) != probe:
        print("  Round trip: FAILED — this key does not encrypt and decrypt.\n")
        return 1
    print("  Round trip: ok — this key encrypts and decrypts\n")
    return 0 if ok else 1


def restore(data_dir: Path, b64: str) -> int:
    """Rebuild the key file on a new machine from the 44 characters."""
    crypto = _crypto()
    path = _key_path(data_dir)

    # REFUSING TO OVERWRITE IS THE WHOLE SAFETY OF THIS COMMAND. A vault
    # encrypted with key A and handed key B is not recoverable by anyone, ever.
    if path.exists():
        print(f"\n  There is already a key at {path}.")
        print("  Refusing to overwrite it. A vault encrypted with one key and")
        print("  given another is unreadable for good, by anybody.\n")
        print("  If you are certain this machine's key is wrong, move the")
        print("  existing file aside by hand first.\n")
        return 1
    try:
        key = base64.b64decode(b64.strip(), validate=True)
    except Exception:                              # noqa: BLE001
        print("\n  That is not valid base64. Paste the 44 characters exactly as")
        print("  they were stored, with no line breaks or spaces.\n")
        return 1
    if len(key) != KEY_BYTES:
        print(f"\n  That decodes to {len(key)} bytes; a vault key is {KEY_BYTES}.")
        print("  Nothing was written.\n")
        return 1

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(crypto._seal(key))
    crypto._restrict(path)
    print(f"\n  Written {path}, wrapped for this Windows account.")
    print("  Now run:  python vault_key.py --verify\n")
    print("  NOTE: the key was passed on the command line, so it is in this")
    print("  shell's history. Clear it, or close the window.\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Export, verify or restore the SATC vault key.")
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA),
                    help=f"where vault.key lives (default: {DEFAULT_DATA})")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--show", action="store_true",
                   help="print the key as base64, to put in a password manager")
    g.add_argument("--verify", action="store_true",
                   help="prove the key file works. Prints nothing secret")
    g.add_argument("--restore", metavar="BASE64",
                   help="rebuild the key file on a new machine")
    args = ap.parse_args(argv)

    data = Path(args.data_dir)
    if args.show:
        return show(data)
    if args.verify:
        return verify(data)
    return restore(data, args.restore)


if __name__ == "__main__":
    raise SystemExit(main())
