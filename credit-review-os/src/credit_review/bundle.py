"""ASCII-bundle build-on-target (the repo's transmission format, contract §11).

Binary files do not survive a bank's email/DLP boundary; plain text does. So
the workbook is never transmitted — it is **built where it will live**:
``make_bundle`` emits a single **pure-ASCII** python script embedding the
builder package and the engagement's configs (gzip+base64). On the target
machine, ``python build_credit_review.py`` writes the engagement workbook
locally and prints its SHA-256 — byte-identical to a build here, because the
builder is deterministic.

Target requirements: Python 3.10+ with ``openpyxl`` and ``PyYAML`` only (the
re-ingest and crypto layers are deliberately not bundled — they run on the
reviewer's own machine, not the bank's).
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

import yaml

from credit_review.config import Engagement

PACKAGE_DIR = Path(__file__).parent

# Only what the build path needs. crypto/cli/ingest/bundle stay home — no
# cryptography or formulas dependency lands on the target.
_BUNDLED_MODULES = (
    "__init__.py", "config.py", "config_sheet.py", "cover.py", "findings.py",
    "ingest.py", "keybank_style.py", "linesheet.py", "master.py", "mart.py",
    "methodology.py", "workbook.py",
)

_RUNNER = '''\
#!/usr/bin/env python3
# Credit Review OS -- build-on-target bundle (pure ASCII; see _readme tab).
# Run:  python {script_name}
# Needs: Python 3.10+, openpyxl, PyYAML  (pip install openpyxl PyYAML)
import base64, gzip, hashlib, os, sys

FILES = {files_literal}

def main():
    root = os.path.join(os.getcwd(), "credit_review_bundle_src")
    for relpath, blob in FILES.items():
        dest = os.path.join(root, *relpath.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(gzip.decompress(base64.b64decode(blob)))
    sys.path.insert(0, root)

    from credit_review.config import load_engagement, load_loans, load_program
    from credit_review.workbook import build_engagement_workbook, workbook_bytes

    program = load_program(os.path.join(root, "credit_review", "programs",
                                        {program_name!r}))
    engagement = load_engagement(os.path.join(root, "engagement",
                                              {engagement_name!r}))
    loans = load_loans(engagement.loans_path)
    data = workbook_bytes(build_engagement_workbook(program, engagement, loans))
    out = {output_name!r}
    with open(out, "wb") as fh:
        fh.write(data)
    print("wrote %s  (%d loans)" % (out, len(loans)))
    print("sha256 %s" % hashlib.sha256(data).hexdigest())

if __name__ == "__main__":
    main()
'''


def _pack(data: bytes) -> str:
    return base64.b64encode(gzip.compress(data, mtime=0)).decode("ascii")


def make_bundle(program_path: Path, engagement: Engagement,
                engagement_path: Path, script_name: str) -> str:
    """Return the pure-ASCII self-building script as text."""
    files: dict[str, str] = {}
    for name in _BUNDLED_MODULES:
        files[f"credit_review/{name}"] = _pack((PACKAGE_DIR / name).read_bytes())
    files[f"credit_review/programs/{program_path.name}"] = \
        _pack(program_path.read_bytes())

    # The overlay travels with its loan fixture beside it; re-point the loans
    # reference at the basename so the extracted pair stays linked.
    overlay = yaml.safe_load(engagement_path.read_text(encoding="utf-8"))
    overlay["loans"] = engagement.loans_path.name
    files[f"engagement/{engagement_path.name}"] = \
        _pack(yaml.safe_dump(overlay, sort_keys=False).encode("utf-8"))
    files[f"engagement/{engagement.loans_path.name}"] = \
        _pack(engagement.loans_path.read_bytes())

    files_literal = "{\n" + "".join(
        f"    {relpath!r}:\n    {blob!r},\n" for relpath, blob in sorted(files.items())
    ) + "}"
    script = _RUNNER.format(
        script_name=script_name,
        files_literal=files_literal,
        program_name=program_path.name,
        engagement_name=engagement_path.name,
        output_name=f"{engagement.engagement_id}.xlsx",
    )
    script.encode("ascii")   # the whole point — refuse to emit anything binary
    return script
