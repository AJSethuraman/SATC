"""Fill in the two Square facts without opening a YAML file or a web console.

THE FIRM, 4 September 2026: *"i can get the location and prod IDs if that's
what we need - i want it to be simple for me to update these figures."*

Two things stand between a working invoice and a paid one, and neither is code:

  1. `square.location_id` in `registry/payments.yaml` -- WHICH of the firm's
     Square locations the money belongs to.
  2. A Square access token, which is deliberately never written down here.

Both were "go and find it, then edit a file". That produced the exact mistake it
was always going to: on 2 September the firm sent an APPLICATION id
(`sq0idp-...`) instead of a LOCATION id (`L...`), because Square's console shows
them side by side and nothing said which was wanted. `live_check` already
answers half of it -- given a token it asks Square and prints the locations
rather than sending anyone hunting. This is the other half: it writes the answer
down.

WHY A SURGICAL TEXT EDIT AND NOT `yaml.safe_dump`. `payments.yaml` is mostly
comments -- which processor was chosen and against what numbers, why the token
is not in the file, why there are two location ids. Round-tripping it through
PyYAML produces a valid file with every one of those decisions deleted. So this
finds the one line a key names and replaces the value on it, exactly as
`registry_editor.py` does for prices, and holds the same safety property:

    set_location(key, current_value)  leaves the file BYTE-IDENTICAL

A writer that cannot rewrite a value as itself is reformatting something, and
the thing it reformats will be a comment.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry" / "payments.yaml"

# A Square location id. Short, uppercase alphanumerics -- and NOT an application
# id, which is the mistake this module exists to make impossible.
LOCATION = re.compile(r"^L[A-Z0-9]{5,30}$")
APPLICATION = re.compile(r"^(sandbox-)?sq0id[bp]-", re.I)

KEYS = ("location_id", "sandbox_location_id")


class SetupError(RuntimeError):
    """Something that would put the wrong identifier in the registry."""


def looks_wrong(value: str) -> str:
    """Why this cannot be a location id, or "" if it can be.

    Checked BEFORE Square is asked, because the answer Square gives for an
    application id is a 401 -- which reads like a bad token, and a person who
    has just pasted a token will believe it.
    """
    v = (value or "").strip()
    if not v:
        return "nothing was entered."
    if APPLICATION.match(v):
        return (f"{v!r} is an APPLICATION id, not a location id. They sit side "
                f"by side in Square's console and name different things: the "
                f"application is the integration, the location is the business "
                f"the money belongs to. A location id looks like LM2T2W21MZ5CY.")
    if not LOCATION.match(v):
        return (f"{v!r} does not look like a Square location id, which starts "
                f"with L and is capital letters and digits only.")
    return ""


def _line_of(text: str, key: str) -> int:
    """The index of the line holding `key`, inside the `square:` block.

    Anchored to the block on purpose: a bare search for `location_id:` also
    matches the words in a comment, and this file has several.
    """
    if key not in KEYS:
        raise SetupError(f"{key!r} is not a location key; expected one of {KEYS}.")
    lines = text.splitlines()
    inside = False
    for i, line in enumerate(lines):
        if re.match(r"^square:\s*$", line):
            inside = True
            continue
        if inside and line and not line[0].isspace():
            break                      # a new top-level key ends the block
        if inside and re.match(rf"^\s+{re.escape(key)}\s*:", line):
            return i
    raise SetupError(
        f"square.{key} is not in {REGISTRY.name}. It was not added by hand, so "
        f"this will not add it either -- a key this writes and nothing reads is "
        f"worse than a missing one.")


def set_location(key: str, value: str, *, text: str | None = None) -> str:
    """The registry text with `square.<key>` set to `value`. Does not save.

    Refuses an identifier that cannot be a location id. `processor()` builds
    from this file, so a wrong value here reaches Square as a real request
    against a location that is not the firm's.
    """
    why = looks_wrong(value)
    if why:
        raise SetupError(why)
    src = text if text is not None else REGISTRY.read_text(encoding="utf-8")
    i = _line_of(src, key)
    lines = src.splitlines(keepends=True)
    line = lines[i]
    end = "\n" if line.endswith("\n") else ""
    indent = re.match(r"^(\s*)", line).group(1)
    lines[i] = f'{indent}{key}: "{value.strip()}"{end}'
    return "".join(lines)


def save_location(key: str, value: str) -> Path:
    """Write it. Returns the path written.

    `newline=""` IS LOAD-BEARING ON WINDOWS. Text mode translates every `\\n` to
    `\\r\\n`, so an ordinary `write_text` here rewrites the line ending of all
    ~100 lines while changing one value -- the whole file, to anyone reading a
    diff without `core.autocrlf`, and the byte-identical property this module
    promises quietly stops being true on disk while still being true in memory.

    Caught by `git status` reporting the file modified after a run that had
    restored it to its original contents.
    """
    REGISTRY.write_text(set_location(key, value), encoding="utf-8", newline="")
    return REGISTRY


# ── the token ────────────────────────────────────────────────────────────────
#
# STILL NOT IN THE REPOSITORY, and that reasoning has not changed: a token in
# the repository is a token in every clone, every backup and every screenshot.
#
# What changes is that "set an environment variable in the shell that runs this"
# is a real obstacle for the one person who has to do it -- and an obstacle in
# front of a security control is how the control gets worked around. The
# likeliest workaround is the worst one: pasting the token into a file.
#
# So: an OPTIONAL file OUTSIDE the repository, in the user's own profile, sealed
# with DPAPI so no other Windows account on this machine can read it. That is
# the same protection `satc_system` gives the vault key. The environment
# variable still wins where it is set, so nothing that works today stops.

TOKEN_FILE = Path.home() / ".satc" / "square-token"


def _dpapi(data: bytes, *, unprotect: bool = False) -> bytes | None:
    """DPAPI seal or unseal. None where that is not available or refused.

    None rather than an exception so the caller decides -- and `remember_token`
    REFUSES rather than falling back to writing the token in the clear.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = BLOB()
        crypt = ctypes.windll.crypt32
        fn = crypt.CryptUnprotectData if unprotect else crypt.CryptProtectData
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0,
                  ctypes.byref(blob_out)):
            return None
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    except Exception:            # noqa: BLE001 -- absent, refused, same answer
        return None


def remember_token(token: str) -> Path:
    """Seal a token into the user's profile. REFUSES if it cannot seal it."""
    raw = (token or "").strip().encode("utf-8")
    if not raw:
        raise SetupError("no token was given, so nothing was stored.")
    sealed = _dpapi(raw)
    if sealed is None:
        raise SetupError(
            "this token could not be sealed on this machine, so it has NOT been "
            "written anywhere. Storing a live payment token in the clear is "
            "worse than typing it again -- set $SATC_SQUARE_TOKEN in your shell "
            "instead.")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_bytes(sealed)
    try:
        os.chmod(TOKEN_FILE, 0o600)      # a no-op on Windows; the ACL does it
    except OSError:
        pass
    return TOKEN_FILE


def stored_token() -> str:
    """The remembered token, or "" if there is none this account can read."""
    try:
        sealed = TOKEN_FILE.read_bytes()
    except OSError:
        return ""
    raw = _dpapi(sealed, unprotect=True)
    return raw.decode("utf-8").strip() if raw else ""


def forget_token() -> bool:
    """Delete the remembered token. True if there was one to delete."""
    try:
        TOKEN_FILE.unlink()
        return True
    except OSError:
        return False
