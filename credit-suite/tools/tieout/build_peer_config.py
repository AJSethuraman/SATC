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
OUT = CS / "config"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import series_seed as SEED         # noqa: E402


def legal_name(cert, newest=True):
    """The institution name off the front page of one of that bank's filings.

    The FFIEC facsimile prints `Institution Name` and then the legal name on
    its own line. Reading the first capitalised run instead picks up the cover
    page's `Board of Governors of the Federal Reserve System` -- which is what
    my first version did, and it flagged Bank of New York Mellon as a mismatch
    when the filing plainly says BANK OF NEW YORK MELLON,THE.

    ``newest`` picks which end of the ten years to read. Both matter: the
    newest says whether the certificate is the bank we print today, the oldest
    whether it was the same institution when the window opens.

    Sorted CHRONOLOGICALLY, which these filenames are not. They are
    `filing-<cert>-MMDDYYYY.pdf`, so a plain sort orders by month first and
    "the latest filing" was whichever December sorted last -- 31 December 2025
    rather than the 30 June 2026 filing that is actually the newest. Every
    identity in `config/peers.json` had been checked against the wrong end of
    a six-month gap.
    """
    def when(path):
        d = path.stem.rsplit("-", 1)[1]          # MMDDYYYY
        return d[4:], d[:2], d[2:4]

    pdfs = sorted((SB / "banks").glob("filing-%s-*.pdf" % cert), key=when)
    if not pdfs:
        return None, None
    chosen = pdfs[-1] if newest else pdfs[0]
    doc = pymupdf.open(chosen)
    text = doc[0].get_text()
    doc.close()
    m = re.search(r"Institution Name\s*\n\s*(.+)", text)
    return (m.group(1).strip() if m else None), chosen.name


def matches(ours, theirs):
    """Same bank, allowing for `NA` against `NATIONAL ASSOCIATION` and commas."""
    if not theirs:
        return False
    a = re.sub(r"[^a-z]", "", ours.lower())
    b = re.sub(r"[^a-z]", "", theirs.lower())
    return a[:9] in b or b[:9] in a


entries, unverified, renamed = [], [], []
for slot, cert, name, group, active in SEED.PEERS:
    legal, filing = legal_name(str(cert))
    oldest, oldest_filing = legal_name(str(cert), newest=False)
    ok = matches(name, legal)
    # Same certificate, different name at the start of the window. Cosmetic
    # for a charter conversion; not cosmetic when the institution absorbed
    # another one and kept the certificate, which is the Truist case.
    same_throughout = bool(oldest) and matches(legal or "", oldest)
    entries.append({"slot": slot, "cert": str(cert), "name": name,
                    "group": group, "active": active == "TRUE",
                    "legal_name_on_filing": legal,
                    "checked_against": filing,
                    "identity_verified": bool(ok),
                    "legal_name_at_window_start": oldest,
                    "window_start_filing": oldest_filing,
                    "same_name_throughout": same_throughout})
    if not ok:
        unverified.append((name, cert, legal))
    if oldest and not same_throughout:
        renamed.append((name, str(cert), oldest, legal))
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
    "_over_time": "`same_name_throughout` is false where the institution "
                  "behind the certificate carried a different name on the "
                  "oldest filing in the window. A certificate is stable and "
                  "the bank behind it is not. One of the two is a rename that "
                  "changed nothing about the institution: ZB, National "
                  "Association became Zions Bancorporation, N.A. The other is "
                  "not cosmetic at all -- everything before December 2019 "
                  "under the label 'Truist Bank' is Branch Banking and Trust, "
                  "which is half the bank that carries the name afterwards. "
                  "See not-comparable-periods.csv for the size of that step "
                  "and of every other one.",
    "generated": "2026-09-07",
    "slots_built": 40,
    "banks": entries,
}
(OUT / "peers.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")

print("\n%d banks, %d slots built, %d free"
      % (len(entries), doc["slots_built"], doc["slots_built"] - len(entries)))
print("identity verified against the filing's own front page: %d of %d"
      % (sum(1 for e in entries if e["identity_verified"]), len(entries)))
print("same name on the oldest and the newest filing: %d of %d"
      % (sum(1 for e in entries if e["same_name_throughout"]), len(entries)))
for nm, cert, was, now in renamed:
    print("   %-7s %-38s -> %s" % (cert, was, now))
if unverified:
    print("\nNOT VERIFIED -- do not run these until the certificate is confirmed:")
    for name, cert, legal in unverified:
        print("   %-26s cert %-7s filing says %r" % (name, cert, legal))
print("\nwrote %s" % (OUT / "peers.json"))
