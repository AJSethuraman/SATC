"""Adopting a repository that predates canon: read it, propose, never assert.

WHAT ADOPTION IS. Pointing canon at a codebase it has never seen and asking two
things of it. What rules does this repository's own history already prove? And
what is this project, in four lines, so a session arriving cold knows where it
is?

WHY THE PROOF HAS TO BE A REPO WITH NO TENETS. Adopting SATC would prove
nothing: SATC's tenets were written by hand, from incidents somebody remembered.
A repository that has never been mined is the only honest test of whether the
reading works, and that is what this was run against.

THE CARD IS THIN ON PURPOSE, AND THE THINNESS IS ENFORCED. What the project is,
what it is for, its stack, where it lives, which convictions apply. NEVER what
the code currently does -- no file inventory, no test count, no status, no
"currently". Those are true on the day they are written and quietly false a
week later, and a card nobody trusts is worse than no card, because it is
consulted anyway. Bassy reads the repo when it needs to know the state; the card
exists so it knows what it is reading.

Enforced twice, because one of them is not enough:
  - `Card` is a fixed set of fields, so it cannot GROW an inventory; and
  - every text field is checked for drift-shaped content, because a free-text
    line can carry "1,249 tests passing" through any structure you like.

TWO TIERS AGAIN, and for the same reason as the miner. A commit that changed a
test file AND a source file together is a mistake somebody thought worth
pinning -- that is a fact about the commit, not a judgement. A commit whose
subject carries a fix-word is a GUESS about relevance. They are counted apart
and labelled, always.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from record import Conviction, RecordError, Evidence, touches

# Fix-shaped words in a subject line. A guess, labelled as one everywhere.
FIX_WORDS: tuple[str, ...] = (
    "fix", "fixes", "fixed", "bug", "broken", "wrong", "silently", "actually",
    "never", "regression", "revert", "correct", "corrects", "corrected",
    "stale", "leak", "crash", "refuse", "refuses",
)

_TEST_PATH = re.compile(r"(^|/)(tests?|spec)(/|$)|(^|/)test_[^/]*\.py$|_test\.[a-z]+$|\.spec\.[a-z]+$")

# What must never appear on an identity card. Each of these is a fact that is
# true the day it is written and quietly false a week later.
DRIFT = [
    ("a count of things in the repo",
     re.compile(r"\b\d[\d,]*\s+(tests?|files?|lines?|commits?|modules?|"
                r"functions?|classes|endpoints?|screens?|documents?)\b", re.I)),
    ("a pass/fail status",
     re.compile(r"\b(passing|failing|green|red|broken|works|working|"
                r"all tests|coverage)\b", re.I)),
    ("a statement about right now",
     re.compile(r"\b(currently|at present|as of|right now|so far|to date|"
                r"today|this week|latest)\b", re.I)),
    ("a work-in-progress marker",
     re.compile(r"\b(TODO|FIXME|WIP|in progress|half[- ]done|not yet built)\b", re.I)),
    ("a file inventory", re.compile(r"(?:^|\s)[\w/-]+\.(?:py|js|ts|md|ya?ml|html)\b")),
    ("a version number", re.compile(r"\bv?\d+\.\d+\.\d+\b")),
]


@dataclass(frozen=True)
class Commit:
    sha: str
    when: str
    subject: str
    paths: tuple[str, ...]

    @property
    def pinned(self) -> bool:
        """Changed a test AND something else: a mistake somebody pinned.

        A fact about the commit, not a judgement about it. This is the tier
        that needs no guessing.
        """
        tests = [p for p in self.paths if _TEST_PATH.search(p)]
        return bool(tests) and len(tests) < len(self.paths)

    @property
    def fix_words(self) -> tuple[str, ...]:
        return tuple(w for w in FIX_WORDS if touches(self.subject, w))


@dataclass(frozen=True)
class Reading:
    """What was read, and -- just as important -- what was not.

    `unread` is not an error list. It is the part of the denominator that keeps
    the rest of the report honest: a repository whose history is one squashed
    commit yields almost nothing, and the report has to say that rather than
    presenting its thin findings as a thorough look.
    """
    project: str
    commits: tuple[Commit, ...]
    reachable: int
    docs: tuple[str, ...]
    unread: tuple[str, ...]
    first: str
    last: str

    @property
    def pinned_share(self) -> float:
        return (sum(1 for c in self.commits if c.pinned) / len(self.commits)
                if self.commits else 0.0)

    def say(self) -> str:
        pinned = sum(1 for c in self.commits if c.pinned)
        lines = [f"{self.project} — {len(self.commits)} of {self.reachable} "
                 f"commit(s) read, {self.first} to {self.last}",
                 f"  {pinned} changed a test and something else in the same commit",
                 f"  {len(self.docs)} document(s) read"]
        # WHEN THE SIGNAL IS NOT A SIGNAL, SAY SO. The first repository this
        # was run against was built test-first, so 14 of 17 commits touched a
        # test and a source file together -- which is the normal case there,
        # not evidence of a pinned mistake. A tool that flags four-fifths of
        # everything has told the reader nothing, and it must not present that
        # as a finding (S4).
        if self.pinned_share > 0.5:
            lines.append(
                f"\n  Note: {pinned / len(self.commits):.0%} of commits here "
                f"changed a test alongside source. This project appears to be "
                f"built test-first, which means that signal is its normal case "
                f"rather than a finding. Read the list as history, not as a "
                f"shortlist.")
        lines.append("\nNOT examined, and it matters which:")
        for what in self.unread:
            lines.append(f"  - {what}")
        return "\n".join(lines)


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RecordError(f"{repo}: git said no — {out.stderr.strip()[:200]}")
    return out.stdout


def read_repo(repo: Path, *, limit: int = 400, within: str = "") -> Reading:
    """Read a repository's history and its documents. Reads nothing else.

    `within` narrows to a subdirectory, which is how a monorepo folder is
    adopted as its own project -- the nine analytics projects live that way.
    """
    repo = Path(repo).resolve()
    scope = [within] if within else []
    # THE PROJECT IS NAMED FROM THE GIT ROOT, NOT FROM THE PATH HANDED IN.
    # It was `repo.name`, so pointing the adopter at any subdirectory of a
    # repository named the project after that subdirectory -- `vendor`, in the
    # first install into a host repo, for a project called `unrelated-project`.
    # Nothing was wrong enough to fail; the card would simply have carried the
    # wrong name forever.
    root = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
    # THE RECORD SEPARATOR GOES FIRST, NOT LAST. Written last, git emits it
    # before the `--name-only` file list, so every chunk after the first
    # carried the previous commit's paths and the split blew up on the first
    # real repository it was pointed at. Leading, each chunk is exactly one
    # commit: header line, blank line, its own paths.
    raw = _git(repo, "log", f"-{limit}", "--date=short",
               "--pretty=format:%x1e%H%x1f%ad%x1f%s", "--name-only",
               *(["--", *scope] if scope else []))

    commits: list[Commit] = []
    for chunk in raw.split("\x1e"):
        if not chunk.strip():
            continue
        head, _, body = chunk.strip().partition("\n")
        sha, when, subject = head.split("\x1f", 2)
        commits.append(Commit(sha=sha[:9], when=when, subject=subject,
                              paths=tuple(p for p in body.splitlines() if p.strip())))

    where = root / within if within else root
    docs = tuple(sorted(p.name for p in where.glob("*.md"))) if where.is_dir() else ()

    # HOW MUCH HISTORY EXISTS versus how much this branch can see. The first
    # real repository this was pointed at reported one commit, honestly -- and
    # nineteen were reachable from other refs, because the project had arrived
    # as a squashed merge. A denominator of one, silently, would have made a
    # thorough-looking report out of a single line.
    everywhere = len([l for l in _git(
        repo, "log", "--all", "--oneline", *(["--", *scope] if scope else [])
    ).splitlines() if l.strip()])

    unread = [
        "the code itself — adoption reads history and documents, never behaviour",
        "anything not in git: untracked files, ignored files, local data",
        f"commits beyond the most recent {limit}" if len(commits) >= limit
        else "nothing was truncated by the commit limit",
        "documents below the top level of the project",
        "whether any test in this repository actually passes",
    ]
    if everywhere > len(commits):
        unread.insert(0, f"{everywhere - len(commits)} commit(s) reachable only "
                         f"from other branches — this history is squashed or "
                         f"this branch is behind, and the reading is that much "
                         f"thinner than it looks")
    stamps = sorted(c.when for c in commits) or ["—", "—"]
    return Reading(project=within or root.name, commits=tuple(commits),
                   reachable=everywhere, docs=docs, unread=tuple(unread),
                   first=stamps[0], last=stamps[-1])


@dataclass(frozen=True)
class CandidateTenet:
    """A rule this repository's own history might already prove. NOT A TENET.

    It carries the commit it came from so the reader can go and look. A
    candidate with no citation is an opinion, and this module has none.
    """
    rule: str
    commit: Commit
    certain: bool

    def as_evidence(self, project: str) -> Evidence:
        return Evidence(project=project, when=self.commit.when,
                        citation=f"commit {self.commit.sha} — {self.commit.subject}",
                        detail=self.rule)


def candidate_tenets(reading: Reading) -> tuple[list[CandidateTenet], list[CandidateTenet]]:
    """(pinned, guessed). Never one list, for the same reason as the miner.

    THE RULE TEXT IS THE COMMIT'S OWN SUBJECT, not a generalisation of it.
    Generalising is the step that turns "this repo fixed a thing" into "this
    repo proves a law", and that step belongs to a person -- it is exactly
    where a plausible, wrong tenet would enter the record and never leave.
    """
    pinned, guessed = [], []
    for c in reading.commits:
        if c.pinned:
            pinned.append(CandidateTenet(rule=c.subject, commit=c, certain=True))
        elif c.fix_words:
            guessed.append(CandidateTenet(rule=c.subject, commit=c, certain=False))
    return pinned, guessed


@dataclass(frozen=True)
class Card:
    """A project's identity card. Fixed fields, so it cannot grow an inventory.

    Every field answers a question that stays true between commits. There is
    deliberately no field for status, no field for structure, and no field for
    what the code does -- not because they are uninteresting but because they
    are the ones that rot.
    """
    project: str
    what_it_is: str
    what_it_is_for: str
    stack: str
    where_it_lives: str
    convictions: tuple[str, ...] = ()

    TEXT = ("what_it_is", "what_it_is_for", "stack", "where_it_lives")

    def __post_init__(self) -> None:
        for name in self.TEXT:
            value = getattr(self, name)
            if not value.strip():
                raise RecordError(f"{self.project}: the card's {name} is empty. "
                                  f"A card with a blank line on it teaches "
                                  f"whoever reads it that the card is optional.")
            for what, rx in DRIFT:
                if rx.search(value):
                    raise RecordError(
                        f"{self.project}: the card's {name} carries {what}. "
                        f"A card states what the project IS, never what the "
                        f"code currently does — that is true today and quietly "
                        f"false next week, and the card gets consulted anyway.")

    def render(self) -> str:
        applies = ", ".join(self.convictions) if self.convictions else "none recorded"
        return (f"## {self.project}\n\n"
                f"**What it is:** {self.what_it_is}\n\n"
                f"**What it is for:** {self.what_it_is_for}\n\n"
                f"**Stack:** {self.stack}\n\n"
                f"**Where it lives:** {self.where_it_lives}\n\n"
                f"**Convictions that apply:** {applies}\n")


def convictions_for(convictions: list[Conviction], card_text: str) -> tuple[str, ...]:
    """Which held convictions bear on this project, by the one matching rule."""
    return tuple(c.id for c in convictions if c.held
                 and any(touches(card_text, t) for t in c.fires_on))


def report(reading: Reading, pinned: list[CandidateTenet],
           guessed: list[CandidateTenet]) -> str:
    lines = [reading.say(), ""]
    lines.append(f"— {len(pinned)} commit(s) changed a test and something else "
                 f"together. That is a mistake somebody thought worth pinning; "
                 f"no judgement in this list.")
    for cand in pinned:
        lines.append(f"\n  {cand.commit.when}  {cand.commit.sha}  {cand.rule}")
    lines.append(f"\n\n— {len(guessed)} commit(s) whose subject carries a "
                 f"fix-word. THIS HALF IS A GUESS about relevance.")
    for cand in guessed:
        lines.append(f"\n  {cand.commit.when}  {cand.commit.sha}  "
                     f"[{', '.join(cand.commit.fix_words)}]  {cand.rule}")
    lines.append("\n\nNone of the above is a tenet. Each is a commit worth "
                 "reading; a rule is what a person writes after reading it, "
                 "and it needs the firm's yes like anything else.")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    import sys

    if len(sys.argv) < 2:
        print("usage: python adopt.py <repo> [subdirectory]")
        raise SystemExit(2)
    reading = read_repo(Path(sys.argv[1]),
                        within=sys.argv[2] if len(sys.argv) > 2 else "")
    print(report(reading, *candidate_tenets(reading)))
