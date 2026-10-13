"""The peer roster: which banks are compared, and which one is the bank itself.

``config/peers.json`` holds ``{"banks": [...]}``, each bank with

    cert      the FDIC certificate number, as text ("17534")
    name      the legal name as filed
    short     the label on charts and pickers ("KeyBank")
    group     "self" for the bank itself, "peer" for every other
    regional  true or false: in the "Regionals only" pack or not

:func:`load` refuses a roster rather than guess at one. It raises ValueError
with the reason unless every bank has those five keys of the right kind (a
cert written as the FDIC writes it: ASCII digits, no leading zero), there
is exactly one ``self``, the certificates are unique, the short labels are
unique (a picker cannot tell two "PNC"s apart), and every group is valid.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union

GROUPS = ("self", "peer")
KEYS = ("cert", "name", "short", "group", "regional")


def _is_cert(cert) -> bool:
    """True for a certificate number written exactly as the FDIC's CERT reads
    as text: ASCII digits with no leading zero. "0628" or a fullwidth "６２８"
    would never match a filed row, so that bank would silently get no data,
    and "0628" would slip past the duplicate check beside "628"."""
    if not isinstance(cert, str):
        return False
    cert = cert.strip()
    return cert.isascii() and cert.isdigit() and not cert.startswith("0")


def load(path: Union[str, Path]) -> List[dict]:
    """The roster's banks in file order, each a dict of the five keys."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("%s is not valid JSON: %s" % (path, exc)) from None
    banks = doc.get("banks") if isinstance(doc, dict) else None
    if not isinstance(banks, list) or not banks:
        raise ValueError("%s has no \"banks\" list" % path)

    out = []
    for i, bank in enumerate(banks, 1):
        where = "bank %d in %s" % (i, path)
        if not isinstance(bank, dict):
            raise ValueError("%s is not an object" % where)
        missing = [k for k in KEYS if k not in bank]
        if missing:
            raise ValueError("%s has no %s" % (where, ", ".join(missing)))
        cert = bank["cert"]
        if not _is_cert(cert):
            raise ValueError("%s: cert must be the certificate number as text, "
                             "like \"17534\" (plain digits, no leading zero), "
                             "not %r" % (where, cert))
        for key in ("name", "short"):
            if not isinstance(bank[key], str) or not bank[key].strip():
                raise ValueError("%s: %s must be non-empty text" % (where, key))
        if bank["group"] not in GROUPS:
            raise ValueError("%s (%s): group must be \"self\" or \"peer\", not %r"
                             % (where, bank["short"], bank["group"]))
        if not isinstance(bank["regional"], bool):
            raise ValueError("%s (%s): regional must be true or false, not %r"
                             % (where, bank["short"], bank["regional"]))
        out.append({"cert": cert.strip(), "name": bank["name"].strip(),
                    "short": bank["short"].strip(), "group": bank["group"],
                    "regional": bank["regional"]})

    # Shorts are compared without capitals: the workbooks find a bank by
    # Excel's MATCH, which ignores them, so 'Alpha' and 'alpha' are one bank.
    for key in ("cert", "short"):
        seen = set()
        for bank in out:
            k = bank[key].casefold()
            if k in seen:
                raise ValueError("%s: %s %r appears more than once%s"
                                 % (path, key, bank[key],
                                    " (Excel ignores capitals)" if key == "short" else ""))
            seen.add(k)

    selves = [b["short"] for b in out if b["group"] == "self"]
    if len(selves) != 1:
        raise ValueError("%s: exactly one bank must be group \"self\"; found %d%s"
                         % (path, len(selves),
                            " (%s)" % ", ".join(selves) if selves else ""))
    return out


def peers(roster: List[dict]) -> List[dict]:
    """Every bank except the bank itself, in roster order."""
    return [b for b in roster if b["group"] == "peer"]


def regionals(roster: List[dict]) -> List[dict]:
    """The peers marked regional, in roster order."""
    return [b for b in peers(roster) if b["regional"]]


def self_bank(roster: List[dict]) -> dict:
    """The one bank whose group is "self"."""
    return next(b for b in roster if b["group"] == "self")
