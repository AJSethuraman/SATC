"""Nothing sensitive may live in `canon`. Checked, with its denominator.

WHY THIS RUNS BEFORE THE BULK IMPORT AND NOT AFTER. `canon` is designed to be
installed into every project the firm builds, which makes it the most portable
thing they own -- and the worst possible home for anything that has to stay put.
A guard that arrives after the corpus does is guarding something already inside.

IT REPORTS WHAT IT SCANNED. A clean result from a check that examined nothing is
worse than a dirty one, so the count of files and bytes is part of the output
rather than an implication of it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Shapes that must never appear. Each is deliberately broad: a false positive
# costs one line of review, a false negative costs a client's data.
FORBIDDEN = [
    ("a taxpayer identifier", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("an employer identifier", re.compile(r"\b\d{2}-\d{7}\b")),
    ("a telephone number", re.compile(r"\b\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")),
    ("a payment credential", re.compile(r"\bsq0(?!idp-|idb-)[a-z]{3}-[\w-]{8,}|\bEAAA[\w-]{10,}")),
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("an access token assignment", re.compile(r"(?i)\b(token|secret|password)\s*[:=]\s*['\"]?[\w-]{16,}")),
]

# The firm's own published addresses are not client data. Anything else is,
# until somebody says otherwise -- which is the right way round.
OURS = re.compile(r"@satcllp\.com\b")
EMAIL = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


# THE ONE EXCLUSION, NAMED RATHER THAN ASSUMED. `tests/` plants a fake taxpayer
# number and a fake key on purpose -- a guard that has never caught anything is
# a guard tested on the case it cannot fail -- so scanning it flags the fixtures
# every time and the check becomes noise nobody reads.
#
# THE HOLE THIS OPENS IS REAL AND IS WRITTEN DOWN: anything genuinely sensitive
# hidden under `tests/` would not be seen. That is why the exclusion is a single
# named directory rather than a pattern, and why `test_canon.py` asserts it is
# the ONLY one -- a second exclusion cannot be added quietly.
EXCLUDED = ("tests",)


def scan(root: Path = HERE) -> tuple[list[str], int, int]:
    """(findings, files examined, bytes examined)."""
    bad: list[str] = []
    files = seen_bytes = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name == Path(__file__).name:
            continue
        if any(part in EXCLUDED for part in path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files += 1
        seen_bytes += len(text)
        rel = path.relative_to(root)
        for what, rx in FORBIDDEN:
            for hit in rx.findall(text):
                # NEVER PRINT THE VALUE. A check that reports a secret in order
                # to complain about it has published it into a terminal, a log,
                # and whatever screenshot goes into a ticket.
                bad.append(f"{rel}: {what}")
                break
        for address in EMAIL.findall(text):
            if not OURS.search(address):
                bad.append(f"{rel}: an email address that is not the firm's own")
                break
    return bad, files, seen_bytes


def main() -> int:
    bad, files, size = scan()
    print(f"canon — {files} file(s), {size:,} characters examined")
    if not bad:
        print("Nothing that must not be here. No client data, no credentials.")
        return 0
    print(f"\n{len(bad)} thing(s) that must not be in this repository:\n")
    for line in bad:
        print(f"  {line}")
    print("\nThe value itself is deliberately not printed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
