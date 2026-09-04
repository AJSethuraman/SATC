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

THE REPOSITORY IS THE ONE YOU ARE STANDING IN, not the one this file sits in.
The first version derived it from the script's own location, which is correct
in a checkout and wrong everywhere else: installed as a plugin this file lives
in a versioned cache directory that is not a git repository at all, and the
skill documents running it from exactly there. It is the same mistake as a
session reading the record from whatever copy it happened to find, made again
by the person who had just fixed that -- which is the argument for an
adversarial pass in one sentence.

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

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# THE ONLY PATH THAT CROSSES. Hardcoded rather than an argument, because an
# argument is a thing somebody can widen in a hurry -- and the first time it is
# widened is the time nobody checks what came with it.
FINDINGS = "canon/findings/test_findings.py"

# WHERE THE FETCHED BRANCH IS PUT. Its own namespace, under `refs/`, so
# resolving it cannot be ambiguous and nothing of the operator's is touched.
# `git fetch origin <branch>` alone writes only FETCH_HEAD -- the plain name
# then resolves to nothing in a fresh clone, which is precisely the workflow
# this script exists for, and the first version rejected every delivery made
# that way.
STAGING_REF = "refs/canon-intake/incoming"

# pytest's own exit codes. 0 all passed, 1 some failed, 5 nothing collected --
# all three are results. 2, 3, 4 and anything else mean it did not get far
# enough to have a result, and must not read as one.
RAN = {0, 1, 5}

_SUMMARY = re.compile(r"^=*\s*(?:\d+\s+\w+(?:,\s*)?)+.*?(?:in\s[\d.]+s).*$", re.M)


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
    landed_at: Path
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


def repo_root(start: Path | None = None) -> Path:
    """The repository you are standing in.

    Deliberately not derived from this file's location: installed as a plugin
    it lives in a cache directory that is not a repository, and the skill
    documents running it from there.
    """
    start = start or Path.cwd()
    out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise IntakeError(
            f"{start} is not inside a git repository. Run this from the checkout "
            f"whose code you are testing — the findings are about that code, and "
            f"they land beside it.")
    return Path(out.stdout.strip())


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(root), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise IntakeError(f"git said no — {out.stderr.strip()[:300]}")
    return out.stdout


def resolve(root: Path, branch: str) -> str:
    """Get the branch into a ref this script owns, and return that ref.

    Tries the remote first because that is where a far side pushes, then a
    local branch of the same name. What raises is the branch failing to
    resolve either way -- named as that, rather than as a git command, because
    "you are offline" and "nobody pushed that" are different problems.
    """
    name = branch.removeprefix("origin/")
    for spec in (f"+refs/heads/{name}:{STAGING_REF}",
                 f"+refs/remotes/origin/{name}:{STAGING_REF}"):
        try:
            _git(root, "fetch", "origin", spec, "--quiet")
            return STAGING_REF
        except IntakeError:
            continue
    try:                                   # no remote, or already local
        _git(root, "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}")
        return branch
    except IntakeError as exc:
        raise IntakeError(
            f"no branch named {branch}, here or on origin. Check the name the "
            f"far side actually pushed to — a pass delivered to a branch nobody "
            f"reads has not been delivered.") from exc


def what_else_it_touched(root: Path, ref: str, base: str) -> tuple[str, ...]:
    """Every path the branch changed except the one that crosses.

    Reported, never acted on. This is the visibility half; the prevention half
    is that nothing here is ever read.
    """
    changed = _git(root, "diff", "--name-only", f"{base}...{ref}").split()
    return tuple(p for p in changed if p != FINDINGS)


def _tally(out: str, word: str) -> int:
    """Count from pytest's SUMMARY LINE, not from everywhere it printed.

    Searching the whole capture meant a failing test whose assertion message
    happened to contain "99 passed" was counted as ninety-nine passing tests.
    The summary is the one line pytest writes as its answer; the rest is
    working.
    """
    summary = _SUMMARY.findall(out)
    line = summary[-1] if summary else ""
    m = re.search(rf"(\d+) {word}", line)
    return int(m.group(1)) if m else 0


def take(branch: str, base: str = "origin/main", root: Path | None = None) -> Result:
    """Check out the one path, run it, and report what it proved."""
    root = root or repo_root()
    ref = resolve(root, branch)
    ignored = what_else_it_touched(root, ref, base)

    lands_at = root / FINDINGS
    lands_at.parent.mkdir(parents=True, exist_ok=True)
    try:
        blob = _git(root, "show", f"{ref}:{FINDINGS}")
    except IntakeError as exc:
        raise IntakeError(
            f"{branch} carries no {FINDINGS}. An adversarial pass that wrote its "
            f"findings somewhere else has not delivered them: the file is the "
            f"deliverable, and nothing else on the branch is read.\n  {exc}") from exc
    # `git show` RATHER THAN `git checkout <ref> -- <path>`. Checkout with a
    # pathspec updates the index as well as the working tree, so the supposedly
    # ephemeral, gitignored findings file was left STAGED and would have gone
    # into the operator's next commit without anybody adding it. Writing the
    # blob straight out cannot stage anything, which makes that impossible
    # rather than merely unlikely.
    lands_at.write_text(blob, encoding="utf-8")

    ran = subprocess.run([sys.executable, "-m", "pytest", "-q", str(lands_at),
                          "--no-header", "-rN"],
                         cwd=lands_at.parent.parent, capture_output=True, text=True)
    out = ran.stdout + ran.stderr
    if ran.returncode not in RAN:
        # A RUNNER THAT NEVER RAN MUST NOT REPORT A RESULT. With the return
        # code ignored, a missing pytest produced no summary, every count read
        # zero, and the script said the file held no tests -- which reads as a
        # clean pass over an empty delivery. It is neither.
        raise IntakeError(
            f"pytest exited {ran.returncode} without producing a result, so "
            f"nothing was examined. This is not an empty finding set — it is no "
            f"run at all. Check pytest is installed in this environment.\n\n"
            f"{out.strip()[-1500:]}")

    return Result(branch=branch, findings=_tally(out, "failed"),
                  not_findings=_tally(out, "passed"), errors=_tally(out, "error"),
                  ignored=ignored, landed_at=lands_at, output=out)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    if len(sys.argv) < 2:
        print("usage: python intake.py <branch>   e.g. codex/canon-adversarial\n"
              "Run it from inside the checkout whose code is being tested.")
        raise SystemExit(2)
    try:
        result = take(sys.argv[1])
    except IntakeError as exc:
        print(f"Nothing taken.\n\n{exc}")
        raise SystemExit(1)
    print(result.say())
    print(f"\nThe file is now at {result.landed_at} and is NOT collected by "
          f"`pytest tests`.\nRead each red one, decide whether it is right, and "
          f"only then change the code.\nA finding is a claim about what SHOULD "
          f"happen — being red proves it differs from\nwhat does happen, not that "
          f"it is correct to want it.")
