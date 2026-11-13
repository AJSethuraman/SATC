"""Which test jobs a change needs.

Read by `.github/workflows/test.yml`. Given the files a pull request changes,
it prints the pytest matrix and the list of other jobs to run, so a PR runs the
suites for the projects it touches plus anything that reads from them -- and
nothing else.

Why this exists: on 12 Nov 2026 a PR that touched only `service-inviter/`, whose
suite runs in about a second, waited well over an hour per push, because every
push queued the whole matrix (client-documents ~8 min, the pocketbook mutation
shards, LibreOffice installs) behind the previous push's.

THE RULE WHEN IN DOUBT IS TO RUN EVERYTHING. A change to the workflow or to this
file, a file at the repository root that nothing here has mapped, a push to
`main`, or a diff that could not be computed -- each selects every job. A
skipped check is not a passed one, so the cost of not knowing is paid in runner
minutes rather than in a check that silently did not happen.

Standard library only: it runs before anything is installed.

    python .github/ci/select_jobs.py --all              # every job
    git diff --name-only A B | python .github/ci/select_jobs.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

# ---------------------------------------------------------------------------
# The pytest matrix. One entry per project, because the repo is one folder per
# project and each has its own stack and its own way of installing.
#
# `reads` lists what the project's tests read from OUTSIDE its own folder. A
# change to any of those runs it too. Each was found by reading the code, not
# guessed; the line that reads it is named beside it so the next person can
# check it is still true.
# ---------------------------------------------------------------------------

PYTEST: List[Dict[str, object]] = [
    {
        "project": "satc_system",
        "install": 'pip install -e ".[dev]"',
        # tests/test_what_a_filed_return_implies.py reads the fee schedule: the
        # join between the two projects is a set of string keys.
        "reads": ["client-documents/registry/"],
    },
    {
        "project": "client-documents",
        # Chromium too: the pipeline tests render real PDFs, and a suite that
        # skips the one step a client actually receives is not testing the
        # pipeline.
        "install": "pip install -r requirements.txt && playwright install --with-deps chromium",
        "reads": [
            "satc-handoff/",                              # cli.py TEMPLATE_DIR, test_registry.py
            "website/intake-config.js",                   # leads.py SITE_CONFIG, test_interview.py
            "docs/OPERATING-PROCEDURES.md",               # procedures.py OUT
            "docs/prd-interview-and-field-registry.md",   # test_registry.py
        ],
    },
    {
        "project": "invoice-generator",
        "install": "pip install -r requirements.txt pytest",
        # tests/test_deploy_gate.py reads render.yaml and the workflows; a
        # change under .github/ already runs everything.
        "reads": ["render.yaml"],
    },
    # canon has no dependencies beyond pytest, deliberately: it is built to be
    # lifted out and installed into projects that share nothing with this one.
    # Its own suite copies the tree into a fresh git repository and runs itself
    # there, which is why `git` matters more here than any package. Where the
    # `claude` CLI is absent -- as on a runner -- the two tests that call the
    # real plugin validator SKIP and say so, rather than passing quietly.
    {
        "project": "canon",
        "install": "pip install pytest",
        "reads": [".claude-plugin/"],                     # tests/test_canon.py, test_voice.py
    },
    # desk depends on canon and, like it, deliberately has no dependency beyond
    # pytest. Its suite is offline by construction -- conftest replaces the
    # socket layer -- so a government website being down never turns this red.
    {
        "project": "desk",
        "install": "pip install pytest",
        "reads": ["canon/", ".claude-plugin/"],           # _canon.py, tests/_layout.py
    },
    # credit-suite had NO CI entry until 4 September 2026, which meant its 240
    # tests, 68 mutations and cell-for-cell parity checks ran only on the one
    # machine that built them. Offline only: every test uses the deterministic
    # demo provider, so there is no network and no FRED key.
    #
    # Its conformance check scans EVERY Python file in the repository for a
    # copy of an engine module. Running it on every .py change anywhere would
    # put this suite back on every PR, which is the thing being fixed; so a copy
    # dropped into an unrelated folder is caught on the push to `main`, where
    # everything runs, rather than on the PR. The folders it names are here.
    {
        "project": "credit-suite",
        "install": 'pip install -e ".[test]"',
        "reads": [
            "fdic-peer-monitor/",                         # parity.py, test_engine_config.py
            "fred-credit-risk-dashboard/",                # parity.py, test_conformance.py
            "bureau-credit-risk-dashboard/",              # conformance.py UNMIGRATED_FOLDERS
            "macro-early-warning-dashboard/",
            "cfpb-mortgage-monitor/",
            "edgar-crit-class-tracker/",
            "control_center.py",                          # conformance.py
            "BACKLOG.md",                                 # tests/test_readme.py
            "TEMPLATE_CONTRACT.md",                       # parity.repo_root() marker
        ],
    },
    # Ember Vault Arena is staged under docs/ for migration to its own
    # repository and is not the practice's software; it runs here so the golden
    # replay (PRD §5.40) is verified on every PR that touches it, with no model
    # call.
    {
        "project": "docs/ember-vault-arena/code",
        "install": "pip install pytest",
        "reads": [],
    },
    # Portfolio Analysis Pack: the suite builds a 40,000-loan synthetic book and
    # reads the workbook back through the `formulas` engine, so every Excel
    # formula is checked against Python.
    {
        "project": "portfolio-analysis-pack",
        "install": 'pip install -e ".[test]"',
        "reads": [],
    },
    # PocketBook: scikit-learn (the `scout` extra) is optional for the analyst
    # and installed here, so the scouting path runs in CI (canon S14:
    # unreachable code is unchecked).
    {
        "project": "pocketbook",
        "install": 'pip install -e ".[test,scout]"',
        "reads": [],
    },
    # Loan Survival: validate.py checks the math against SciPy and statsmodels;
    # gui_check.py drives the real window under xvfb. A SKIP fails in CI.
    {
        "project": "loan-survival",
        "install": "pip install pytest pandas numpy openpyxl scipy statsmodels matplotlib",
        "reads": [],
    },
    # Forever Guild Bot: not practice software. Offline (mocked Blizzard data,
    # no Discord login), so it needs no token and no network.
    {
        "project": "forever-guild-bot",
        "install": "pip install -r requirements.txt pytest",
        "reads": [],
    },
    # Service Inviter: the owner's WoW addon, not practice software. The tests
    # run the real Lua file in Lua 5.1 (lupa) against stubbed game functions.
    {
        "project": "service-inviter",
        "install": "pip install -r requirements.txt",
        "reads": [],
    },
]

# ---------------------------------------------------------------------------
# The jobs outside the matrix. Each key is a job id in test.yml.
# ---------------------------------------------------------------------------

OTHER: Dict[str, List[str]] = {
    # The two mutation checks re-run their project's own suite with bugs put
    # back, so they follow that project and nothing else.
    "mutation": ["portfolio-analysis-pack/"],
    "mutation-pocketbook": ["pocketbook/"],
    "excel-macros": ["excel-macros/"],
    # pricing.spec.py regenerates website/pricing-config.js from
    # client-documents/registry/fee-schedule.yaml, importing client-documents'
    # own modules to do it -- so any change there can move a published price.
    "pricing": ["website/", "client-documents/"],
    # copy.spec.py reads every published page; build-guides.py --check rebuilds
    # the guide pages from docs/guides/.
    "copy": ["website/", "docs/guides/"],
}

# A change here runs every job: the workflow, this selector, anything CI reads.
EVERYTHING = [".github/"]

# Files at the repository root that are known to be read by no test. Any OTHER
# root file runs everything, because an unmapped shared file is exactly where a
# dependency nobody wrote down would hide.
INERT_ROOT_FILES = {
    "README.md", "CLAUDE.md", "PLAN.md", "LOG.md", "PROJECTS.md",
    "SUITE_GUIDE.md", "PRD_TEMPLATE.md", ".gitignore", ".gitkeep",
    "build_suite.py", "make_suite_bundle.py",
}


def _under(path: str, prefix: str) -> bool:
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix


def _mapped_root_files() -> set:
    reads = [p for e in PYTEST for p in e["reads"]]  # type: ignore[union-attr]
    reads += [p for ps in OTHER.values() for p in ps]
    return {p for p in reads if "/" not in p}


def _all_targets() -> List[str]:
    return [str(e["project"]) for e in PYTEST] + list(OTHER)


def select(changed: Iterable[str]) -> Tuple[List[str], str]:
    """Return (targets to run, why). A target is a pytest project or a job id."""
    files = [f.strip() for f in changed if f.strip()]
    for f in files:
        if any(_under(f, p) for p in EVERYTHING):
            return _all_targets(), f"{f} is CI itself"
        if "/" not in f and f not in INERT_ROOT_FILES | _mapped_root_files():
            return _all_targets(), f"{f} is a root file no job is mapped to"

    chosen: List[str] = []
    for entry in PYTEST:
        own = str(entry["project"]) + "/"
        prefixes: Sequence[str] = [own, *entry["reads"]]  # type: ignore[list-item]
        if any(_under(f, p) for f in files for p in prefixes):
            chosen.append(str(entry["project"]))
    for job, prefixes in OTHER.items():
        if any(_under(f, p) for f in files for p in prefixes):
            chosen.append(job)
    return chosen, f"{len(files)} changed file(s)"


def matrix(targets: Sequence[str]) -> Dict[str, list]:
    keep = set(targets)
    return {"include": [{"project": e["project"], "install": e["install"]}
                        for e in PYTEST if e["project"] in keep]}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="select every job")
    args = ap.parse_args(argv)

    if args.all:
        targets, why = _all_targets(), "--all"
    else:
        targets, why = select(sys.stdin.read().splitlines())

    m = matrix(targets)
    out = {
        "pytest_matrix": json.dumps(m, separators=(",", ":")),
        "run_pytest": "true" if m["include"] else "false",
        "run": json.dumps(targets, separators=(",", ":")),
    }
    print(f"why: {why}")
    print(f"selected {len(targets)} of {len(_all_targets())}: "
          + (", ".join(targets) or "nothing"))
    dest = os.environ.get("GITHUB_OUTPUT")
    if dest:
        with open(dest, "a", encoding="utf-8") as fh:
            for k, v in out.items():
                fh.write(f"{k}={v}\n")
    else:
        for k, v in out.items():
            print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
