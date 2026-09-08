"""Has the duplication crept back?

The consolidation removed 5,000-odd lines of copy-pasted engine code. Nothing
stops someone copying a module back in next month -- it is the easiest thing in
the world to do, it always works, and it is invisible until the day a fix lands
in one copy and not the other. That is the failure this whole package exists to
remove, so it gets a check rather than a hope.

Three questions, each answered against the repository rather than against a
document that claims things about it:

1. **Is the engine single-sourced?** No file outside ``credit_suite/engine/``
   may carry the contents of an engine module, and a migrated monitor's folder
   may not carry loose Python at all. Content-hashed, so a renamed copy is
   caught too -- renaming is the obvious way to make a copy look like not-a-copy.
2. **Do the tabs match the contract?** Section 2 names them exactly. A monitor
   that grows or loses a tab stops being drivable by the generic Control Center.
3. **Does the CLI match the contract?** Section 4 fixes the flags and the exit
   codes. A runner that spells ``--workbook`` differently is a runner the launcher
   cannot drive.

Every result reports its denominator. A conformance check that examined nothing
looks exactly like one that examined everything, right up until somebody asks.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from credit_suite.parity import repo_root

#: Folders whose monitors are migrated. Anything Python-shaped left in one of
#: these is either a copy of engine code or something nobody is running.
MIGRATED_FOLDERS: Dict[str, str] = {
    "fdic-peer-monitor": "fdic",
    "fred-credit-risk-dashboard": "fred",
}

#: Monitors that have NOT migrated yet. They still carry their own copies, by
#: design -- they move onto the engine in M2. A copy here is reported as
#: PENDING rather than failed on, because failing on known, scheduled work turns
#: the check into noise somebody switches off. It is reported rather than
#: filtered for the opposite reason: a check that silently ignores what it was
#: built to find is worse than no check.
UNMIGRATED_FOLDERS: Dict[str, str] = {
    "bureau-credit-risk-dashboard": "M2",
    "macro-early-warning-dashboard": "M2",
    "cfpb-mortgage-monitor": "M2",
    "edgar-crit-class-tracker": "M2",
}

#: Separate products, deliberately not on this engine. `credit-review-os`
#: carries borrower PII and AES encryption the public-data monitors do not, and
#: the PRD is explicit that it stays separate and may consume patterns, never
#: merge. Its style module is not a copy to be removed.
SEPARATE_PRODUCTS: Dict[str, str] = {
    "credit-review-os": "a separate product (PRD non-goal), not a monitor",
}

#: The one Python file a migrated folder may keep: the generated ASCII bundle,
#: which is a build OUTPUT rather than source, and is deliberately standalone.
GENERATED = re.compile(r"^build_[a-z0-9_]+\.py$")

#: Contract section 2. `Dashboard_<Lane>` and `Raw_<PROVIDER>` are patterns;
#: the rest are exact. `Watchlist_Geo` is FRED's grandfathered spelling.
REQUIRED_TABS = ("_config", "_code_py", "_code_vba", "_readme")
DASHBOARD = re.compile(r"^Dashboard_[A-Za-z0-9_]+$")
RAW = re.compile(r"^Raw_[A-Za-z0-9_]+$")
WATCHLIST = ("Watchlist", "Watchlist_Geo")
OPTIONAL_TABS = ("_provenance", "_mergers")

#: Contract section 4.
REQUIRED_FLAGS = ("--workbook", "--demo", "--asof")


@dataclass(frozen=True)
class Finding:
    """One conformance failure, named well enough to act on."""

    check: str
    subject: str
    detail: str

    def __str__(self) -> str:
        return "%s: %s -- %s" % (self.check, self.subject, self.detail)


@dataclass
class Report:
    findings: List[Finding]
    examined: Dict[str, int]
    pending: List[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def describe(self) -> str:
        counts = ", ".join("%d %s" % (n, what)
                           for what, n in sorted(self.examined.items()))
        lines = ["examined %s" % (counts or "NOTHING")]
        if self.findings:
            lines.append("%d finding(s):" % len(self.findings))
            lines.extend("  - %s" % f for f in self.findings)
        else:
            lines.append("conformance OK (spine)")
        if self.pending:
            lines.append("")
            lines.append("%d copy/copies outstanding by design -- these "
                         "monitors migrate in M2:" % len(self.pending))
            lines.extend("  . %s" % f for f in self.pending)
        return "\n".join(lines)


def _digest(path: Path) -> str:
    """Content hash, newline-normalised.

    A copy checked out with different line endings is still a copy, and on a
    repository that travels between Windows and CI that is the likely shape.
    """
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def engine_modules(root: Path | None = None) -> Dict[str, Path]:
    root = root or repo_root()
    engine = root / "credit-suite" / "src" / "credit_suite" / "engine"
    return {p.name: p for p in sorted(engine.glob("*.py"))}


def _candidate_files(root: Path) -> List[Path]:
    """Every Python file in the repo that is not part of credit-suite itself."""
    skip = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
    out: List[Path] = []
    for path in sorted(root.rglob("*.py")):
        parts = set(path.parts)
        if parts & skip:
            continue
        try:
            path.relative_to(root / "credit-suite")
            continue                      # the engine's own home
        except ValueError:
            pass
        out.append(path)
    return out


def check_single_sourced(root: Path | None = None
                         ) -> tuple[List[Finding], List[Finding], Dict[str, int]]:
    """No copy of an engine module anywhere it should not be.

    Returns ``(findings, pending, examined)``. A copy inside a MIGRATED folder
    is a failure: removing it is what the migration was for. A copy inside a
    monitor that has not migrated yet is pending M2 -- reported and counted, not
    failed on.
    """
    root = root or repo_root()
    modules = engine_modules(root)
    by_digest = {_digest(p): name for name, p in modules.items()}

    findings: List[Finding] = []
    pending: List[Finding] = []
    candidates = _candidate_files(root)
    for path in candidates:
        rel = path.relative_to(root).as_posix()
        folder = rel.split("/")[0]
        if folder in SEPARATE_PRODUCTS:
            continue

        digest = _digest(path)
        if digest in by_digest:
            message = ("byte-identical copy of engine/%s -- delete it and "
                       "import the engine, or the next fix lands in one copy "
                       "and not the other" % by_digest[digest])
            if folder in UNMIGRATED_FOLDERS:
                pending.append(Finding(
                    "single-sourced", rel,
                    "%s (migrates in %s)" % (message,
                                             UNMIGRATED_FOLDERS[folder])))
            else:
                findings.append(Finding("single-sourced", rel, message))
            continue

        # A renamed or lightly-edited copy still shows as the same file NAME in
        # a monitor folder, which is how every copy in this repo actually looked.
        if folder in MIGRATED_FOLDERS and not GENERATED.match(path.name):
            findings.append(Finding(
                "single-sourced", rel,
                "%s is migrated, so it must carry no Python source -- only the "
                "generated build_*.py bundle" % folder))

    return findings, pending, {"python files scanned": len(candidates),
                               "engine modules": len(modules)}


def check_tabs(workbook_tabs: Dict[str, Sequence[str]]
               ) -> tuple[List[Finding], Dict[str, int]]:
    """Contract section 2: the tab taxonomy, exactly."""
    findings: List[Finding] = []
    for monitor, tabs in sorted(workbook_tabs.items()):
        names = list(tabs)
        for required in REQUIRED_TABS:
            if required not in names:
                findings.append(Finding("tabs", monitor,
                                        "missing required tab %r" % required))
        if not any(DASHBOARD.match(t) for t in names):
            findings.append(Finding("tabs", monitor, "no Dashboard_<Lane> tab"))
        if not any(RAW.match(t) for t in names):
            findings.append(Finding("tabs", monitor, "no Raw_<PROVIDER> tab"))
        if not any(t in WATCHLIST for t in names):
            findings.append(Finding(
                "tabs", monitor,
                "no gated lane; expected one of %s" % (WATCHLIST,)))
        for name in names:
            known = (name in REQUIRED_TABS or name in OPTIONAL_TABS
                     or name in WATCHLIST or DASHBOARD.match(name)
                     or RAW.match(name))
            if not known:
                findings.append(Finding(
                    "tabs", monitor,
                    "tab %r is not in the contract's taxonomy; the Control "
                    "Center drives what the contract names, and nothing else"
                    % name))
    return findings, {"monitors": len(workbook_tabs),
                      "tabs": sum(len(t) for t in workbook_tabs.values())}


def check_cli(parsers: Dict[str, object]) -> tuple[List[Finding], Dict[str, int]]:
    """Contract section 4: the flags a launcher relies on."""
    findings: List[Finding] = []
    checked = 0
    for monitor, parser in sorted(parsers.items()):
        options: List[str] = []
        for action in getattr(parser, "_actions", []):
            options.extend(action.option_strings)
        for flag in REQUIRED_FLAGS:
            checked += 1
            if flag not in options:
                findings.append(Finding(
                    "cli", monitor,
                    "runner does not accept %s; control_center.py drives every "
                    "monitor the same way and cannot special-case one" % flag))
        if "-w" not in options:
            findings.append(Finding("cli", monitor, "no -w short form for --workbook"))
    return findings, {"monitors": len(parsers), "flag checks": checked}


def check_exit_codes(runtime_module) -> tuple[List[Finding], Dict[str, int]]:
    """Contract section 4: 0 OK, 1 run error, 2 gate error, 3 missing secret."""
    expected = {"EXIT_OK": 0, "EXIT_RUN_ERROR": 1, "EXIT_GATE_ERROR": 2,
                "EXIT_MISSING_SECRET": 3}
    findings = []
    for name, value in sorted(expected.items()):
        actual = getattr(runtime_module, name, None)
        if actual != value:
            findings.append(Finding("exit-codes", name,
                                    "expected %d, found %r" % (value, actual)))
    return findings, {"exit codes": len(expected)}
