"""Write the peer group into the repository, where a temp folder cannot lose it.

The peer group is defined in `series_seed.PEERS` -- slot, certificate, name,
group, active. But the DERIVED index that eleven tie-out tools actually read
lived at `scratchpad/banks/index.json`, in a Windows temp folder: not backed up,
and exactly the sort of thing a housekeeping command removes. Nothing would be
lost permanently, since it regenerates, but nobody would know it had gone until
a tool failed.

The firm's answer, 7 September 2026: move it into the repo. Same argument that
moved the 132 exhibits onto the Forge -- a thing you depend on should not live
somewhere a cleanup can delete.

So `config/peers.json` is generated from the seed and committed. A competitor
swap then shows up as a readable diff of certificates and names rather than as a
binary that changed.

**Each certificate is checked against the filing's own front page**, which
carries the institution's legal name. That check exists because everything else
in this project proves the FDIC agrees with the filing FOR A GIVEN CERTIFICATE,
and proves nothing about whether that certificate is the bank whose name we
print. A wrong certificate ties perfectly against itself. The seed's own comment
says nine of the twelve are "illustrative from public sources and must be
re-verified before a live run", and until now none had been.
"""
import json
import pathlib
import re
import sys

import pymupdf

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = CS / "config"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import series_seed as SEED         # noqa: E402


def legal_name(cert):
    """The institution name off the front page of that bank's latest filing.

    The FFIEC facsimile prints `Institution Name` and then the legal name on
    its own line. Reading the first capitalised run instead picks up the cover
    page's `Board of Governors of the Federal Reserve System` -- which is what
    my first version did, and it flagged Bank of New York Mellon as a mismatch
    when the filing plainly says BANK OF NEW YORK MELLON,THE.
    """
    pdfs = sorted((SB / "banks").glob("filing-%s-*.pdf" % cert))
    if not pdfs:
        return None, None
    doc = pymupdf.open(pdfs[-1])
    text = doc[0].get_text()
    doc.close()
    m = re.search(r"Institution Name\s*\n\s*(.+)", text)
    return (m.group(1).strip() if m else None), pdfs[-1].name


def matches(ours, theirs):
    """Same bank, allowing for `NA` against `NATIONAL ASSOCIATION` and commas."""
    if not theirs:
        return False
    a = re.sub(r"[^a-z]", "", ours.lower())
    b = re.sub(r"[^a-z]", "", theirs.lower())
    return a[:9] in b or b[:9] in a


entries, unverified = [], []
for slot, cert, name, group, active in SEED.PEERS:
    legal, filing = legal_name(str(cert))
    ok = matches(name, legal)
    entries.append({"slot": slot, "cert": str(cert), "name": name,
                    "group": group, "active": active == "TRUE",
                    "legal_name_on_filing": legal,
                    "checked_against": filing,
                    "identity_verified": bool(ok)})
    if not ok:
        unverified.append((name, cert, legal))
    print("  slot %2d  %-7s %-26s %-44s %s"
          % (slot, cert, name[:26], (legal or "NO FILING ON DISK")[:44],
             "" if ok else "<-- NOT THIS BANK?"))

doc = {
    "_what": "The peer group. Generated from series_seed.PEERS by "
             "tools/tieout/build_peer_config.py -- edit the seed, not this.",
    "_identity": "`identity_verified` means the certificate's own filed Call "
                 "Report names this bank on its front page. Everything else in "
                 "this project proves the FDIC agrees with a filing for a given "
                 "certificate; only this proves the certificate is the bank we "
                 "print beside it.",
    "generated": "2026-09-07",
    "slots_built": 40,
    "banks": entries,
}
(OUT / "peers.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")

print("\n%d banks, %d slots built, %d free"
      % (len(entries), doc["slots_built"], doc["slots_built"] - len(entries)))
print("identity verified against the filing's own front page: %d of %d"
      % (sum(1 for e in entries if e["identity_verified"]), len(entries)))
if unverified:
    print("\nNOT VERIFIED -- do not run these until the certificate is confirmed:")
    for name, cert, legal in unverified:
        print("   %-26s cert %-7s filing says %r" % (name, cert, legal))
print("\nwrote %s" % (OUT / "peers.json"))
