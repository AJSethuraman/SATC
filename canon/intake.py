"""Take the findings off an adversarial branch, and nothing else.

WHY THIS IS A SCRIPT AND NOT AN INSTRUCTION. The safety property of an
adversarial pass is that only one file crosses over. Written down as a step
somebody performs -- "remember to extract just the test file" -- that property
lasts exactly as long as somebody remembers it on a busy day. Written here, the
script cannot take anything else, because there is no code in it that would.
That is behaviour 4: prevent, don't detect.

WHAT CROSSES, AND WHAT DOES NOT. One path. Whatever else the branch carries --
scratch harnesses, fixtures, an edited `record.py`, a half-finished refactor --
is never read and never lands. That is what makes the far side free to write
whatever code it needs: the branch is a sandbox, not a contribution.

THE FINDINGS DO NOT JOIN THE SUITE. They land in `findings/`, which `pytest
tests` does not collect, and this script runs them on purpose. A red test in
`tests/` would turn the suite red and every later run would report a failure
that is a finding rather than a regression -- and after the second day nobody
reads either. A finding is red BY DESIGN; the suite is red only when something
broke.

A RED TEST IS A FINDING. A GREEN ONE IS NOT. That is the whole triage, and it
needs no judgement about the far side's reasoning: the test either reproduces
against this code or it does not.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent

# THE ONLY PATH THAT CROSSES. Hardcoded rather than an argument, because an
# argument is a thing somebody can widen in a hurry -- and the first time it is
# widened is the time nobody checks what came with it.
FINDINGS = "canon/findings/test_findings.py"
LANDS_AT = HERE / "findings" / "test_findings.py"


class IntakeError(RuntimeError):
    """The branch could not be read as an adversarial pass."""


@dataclass(frozen=True)
class Result:
    """What was taken, what it proved, and what was ignored."""
    branch: str
    findings: int          # red: reproduce against this code
    not_findings: int      # green: the behaviour is already correct
    errors: int            # neither: the test itself is broken
    ignored: tuple[str, ...]
    output: str

    @property
    def examined(self) -> int:
        return self.findings + self.not_findings + self.errors

    def say(self) -> str:
        lines = [f"{self.branch} — {self.examined} test(s) taken from {FINDINGS}"]
        if not self.examined:
            # A COUNT OF ZERO IS SAID IN WORDS. "0 findings" reads as a clean
            # bill of health; "the file held no tests" is a different fact, and
            # only one of them means what a reader takes it to mean (S2).
            lines.append("  The file held no tests at all. Nothing was examined,"
                         " which is not the same as nothing being wrong.")
        else:
            lines.append(f"  {self.findings} reproduce against this code — these are the findings")
            lines.append(f"  {self.not_findings} pass, so the behaviour they assert is already correct")
            if self.errors:
                lines.append(f"  {self.errors} could not run — the test itself is broken, "
                             f"which is neither a finding nor a clean result")

        lines.append("\nNOT taken, and deliberately not read:")
        if self.ignored:
            for path in self.ignored:
                lines.append(f"  - {path}")
            lines.append("  Nothing above crossed over. It is listed because what a"
                         "\n    branch did outside its lane says whether to trust it"
                         "\n    with a bigger job, not because it is dangerous.")
        else:
            lines.append("  - nothing; the branch touched only the findings file")
        return "\n".join(lines)


def _git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(HERE.parent), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise IntakeError(f"git said no — {out.stderr.strip()[:300]}")
    return out.stdout


def what_else_it_touched(branch: str, base: str = "origin/main") -> tuple[str, ...]:
    """Every path the branch changed except the one that crosses.

    Reported, never acted on. This is the visibility half; the prevention half
    is that nothing here is ever checked out.
    """
    changed = _git("diff", "--name-only", f"{base}...{branch}").split()
    return tuple(p for p in changed if p != FINDINGS)


def take(branch: str, base: str = "origin/main") -> Result:
    """Check out the one path, run it, and report what it proved."""
    # FETCHING IS BEST EFFORT, AND RESOLVING THE BRANCH IS NOT. A fetch that
    # fails is not the same problem as a branch that does not exist: the first
    # happens on a laptop with no network, or for a branch already local, and
    # blocking on it turns "you are offline" into "the pass delivered nothing".
    # The check that matters is whether the ref resolves, so that is the one
    # that raises, and it names the branch rather than the git command.
    try:
        _git("fetch", "origin", branch.removeprefix("origin/"), "--quiet")
    except IntakeError:
        pass
    try:
        _git("rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}")
    except IntakeError as exc:
        raise IntakeError(
            f"no branch named {branch}, here or on origin. Check the name the "
            f"far side actually pushed to — a pass delivered to a branch nobody "
            f"reads has not been delivered.") from exc

    ignored = what_else_it_touched(branch, base)

    LANDS_AT.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git("checkout", branch, "--", FINDINGS)
    except IntakeError as exc:
        raise IntakeError(
            f"{branch} carries no {FINDINGS}. An adversarial pass that wrote its "
            f"findings somewhere else has not delivered them: the file is the "
            f"deliverable, and nothing else on the branch is read.\n  {exc}") from exc

    ran = subprocess.run([sys.executable, "-m", "pytest", "-q", str(LANDS_AT),
                          "--no-header", "-rN"],
                         cwd=HERE, capture_output=True, text=True)
    out = ran.stdout + ran.stderr

    # PARSED FROM PYTEST'S OWN SUMMARY rather than counted by hand. A second
    # tally beside the one the runner already produces is a second thing that
    # can disagree with it, and nothing would be comparing them (S31).
    def count(word: str) -> int:
        import re
        m = re.search(rf"(\d+) {word}", out)
        return int(m.group(1)) if m else 0

    return Result(branch=branch, findings=count("failed"),
                  not_findings=count("passed"), errors=count("error"),
                  ignored=ignored, output=out)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    if len(sys.argv) < 2:
        print("usage: python intake.py <branch>   e.g. codex/canon-adversarial")
        raise SystemExit(2)
    try:
        result = take(sys.argv[1])
    except IntakeError as exc:
        print(f"Nothing taken.\n\n{exc}")
        raise SystemExit(1)
    print(result.say())
    print(f"\nThe file is now at {LANDS_AT.relative_to(HERE)} and is NOT collected "
          f"by `pytest tests`.\nRead each red one, decide whether it is right, and "
          f"only then change the code.\nA finding is a claim about what SHOULD "
          f"happen — being red proves it differs from\nwhat does happen, not that "
          f"it is correct to want it.")
