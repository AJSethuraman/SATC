"""An engagement's facts, read off a file the firm keeps — never off a guess.

THE GAP THIS FILLS, measured on 7 September 2026 rather than assumed. Three
desks declare a fact they need on file: `trade`, `taxpayer`,
`capitalization_rule`. `engine.serve()` will take all three. **Nothing produced
them.** The only thing carrying facts anywhere in this plugin was a worked
example's own `On file` line, which is a test fixture — so five of the close's
eighteen questions refused with `context_not_on_file` against a file that did
not exist. A desk cannot be piloted through a real close until an engagement has
somewhere to be written down.

THE FILE DOES NOT LIVE HERE, AND `load` REFUSES TO READ ONE THAT DOES. `desk` is
a plugin: it has to lift out whole, it holds no client data, and it is a git
repository that gets pushed. An engagement file inside it is a client's affairs
in a public checkout, one `git add -A` away. So the path is the caller's, it is
refused if it resolves inside this plugin, and what ships here is the reader and
its fixtures.

WHAT IS REFUSED, AND WHY EACH REFUSAL IS A REFUSAL RATHER THAN A DEFAULT:

* **A fact no desk declares.** Checked against every desk's own `Records:` line,
  which is data. A typo becomes an error at read time instead of a fact nothing
  ever meets — the same guarantee `Context.facts` already gives one desk,
  extended to the file that fills it.
* **A fact with no value.** `**Value:**` missing is not "unknown"; it is a
  half-written record. A desk asking for it and a file half-answering it are
  different states and only one of them is honest.
* **A fact nobody recorded.** Every fact names who wrote it and the day. This is
  `DESIGN-PRINCIPLES.md`'s *facts are recorded, not inferred* made checkable:
  the difference between a fact and a guess is that somebody put their name on
  it, and a file that cannot say who is a file of guesses.
* **Anything shaped like identity.** A value matching an SSN or an EIN is
  refused, loudly, whatever field it was written under. The vault holds those.
  This cannot be the only guard — a legal name is not a shape — which is why the
  fact names are a closed set the desks declare, and no desk declares a name.

WHAT IS NOT REFUSED, deliberately: `none`. A file saying there is no client-level
rule is the third state `Context.standing_rule` exists for, and losing it here
would collapse "somebody checked and the answer was no" back into "nobody
asked".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import record

HERE = Path(__file__).resolve().parent


class EngagementError(Exception):
    """The file could not be read as an engagement. Never half-read."""


#: An engagement's own reference, and the only thing about it this file holds.
#: Letters, digits, dashes and underscores: a reference, not a person. It is
#: printed in refusals and it is the caller's to keep meaningless.
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")

_HEAD = re.compile(r"^## (.+)$", re.M)

#: THE TWO SHAPES A NUMBER CAN HAVE THAT MEAN IT IS SOMEBODY'S IDENTITY.
#: A social security number and an employer identification number, with or
#: without their separators. Nine digits in a row is caught by both.
_TIN = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),      # 123-45-6789
    re.compile(r"\b\d{2}-\d{7}\b"),            # 12-3456789
    re.compile(r"\b\d{9}\b"),                  # either, unseparated
)


@dataclass(frozen=True)
class Fact:
    """One recorded fact, and the person who recorded it."""
    name: str
    value: str
    by: str
    on: str
    #: Where it came from, in the recorder's own words. Optional: some facts
    #: come from a form and the form is the answer.
    source: str = ""


@dataclass(frozen=True)
class Engagement:
    """One engagement's file, read. Carries no identity — see the module note."""
    ref: str
    path: str
    facts: tuple = field(default_factory=tuple)

    def context(self) -> record.Context:
        """What `ask.consult` and `engine.serve` take. Values only, because
        that is all a desk is allowed to see: a desk answers from authority and
        from what the file records, never from who recorded it."""
        return record.Context(facts={f.name: f.value for f in self.facts})

    def by_name(self, name: str) -> Fact | None:
        for f in self.facts:
            if f.name == name:
                return f
        return None


def declared(desks: Path | None = None) -> dict:
    """`{fact name: [desks that record it]}` — read off the desks, never listed.

    A vocabulary typed here would be a second copy of something the desks
    already declare, and the copy is what goes stale. `record.py` refuses to
    hold one for exactly this reason: every desk shares that layer, so a fact
    vocabulary in it makes all of them speak accounting.
    """
    root = Path(desks) if desks else HERE / "desks"
    out: dict = {}
    for d in sorted(root.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        for name in record.load(d).records:
            out.setdefault(name, []).append(d.name)
    return out


def _identity(value: str) -> str:
    for pattern in _TIN:
        if pattern.search(value):
            return pattern.pattern
    return ""


def _one(name: str, block: str, where: str, known: dict) -> Fact:
    name = name.strip().lower()
    if name not in known:
        raise EngagementError(
            f"{where}: no desk records a fact called {name!r}. The desks record "
            f"{', '.join(sorted(known)) or '(nothing)'}. A fact no desk asks "
            f"for is one nothing will ever meet, so this is a typo caught here "
            f"rather than a silence discovered in front of a client."
        )
    try:
        value = record._field(block, "Value", where)
        by = record._field(block, "Recorded by", where)
        on = record._date(record._field(block, "Recorded on", where),
                          "Recorded on", where)
    except record.RecordError as exc:
        raise EngagementError(
            f"{exc}. A fact with no value, nobody's name on it or no day is not "
            f"a recorded fact — and 'recorded, not inferred' is the whole "
            f"difference between this file and a guess."
        ) from exc

    shape = _identity(value)
    if shape:
        raise EngagementError(
            f"{where}: the value matches {shape}, which is the shape of a "
            f"taxpayer identification number. Identity lives in the encrypted "
            f"vault and never in this file, which is read by desks and printed "
            f"into refusals. Record the category, not the taxpayer."
        )
    return Fact(name=name, value=value, by=by, on=on,
                source=record._field(block, "From", where, required=False))


def parse(text: str, path: str = "engagement", known: dict | None = None) -> Engagement:
    known = declared() if known is None else known
    head = re.search(r"^#\s+Engagement\s+·\s+(\S+)\s*$", text, re.M)
    if not head:
        raise EngagementError(
            f"{path}: the first line must be '# Engagement · <ref>'. The "
            f"reference is how a refusal says which engagement it is about."
        )
    ref = head.group(1)
    if not _REF.match(ref):
        raise EngagementError(
            f"{path}: {ref!r} is not a reference — letters, digits, dots, "
            f"dashes and underscores, 2 to 64 of them. It is printed in "
            f"refusals, so it is the firm's to keep meaningless."
        )

    facts, seen = [], set()
    for h, block in record._blocks(text, _HEAD):
        f = _one(h.group(1), block, f"{path}, fact {h.group(1).strip()}", known)
        if f.name in seen:
            raise EngagementError(
                f"{path}: {f.name!r} is recorded twice. Two answers to one "
                f"question is not a record; one of them is wrong and the file "
                f"does not say which."
            )
        seen.add(f.name)
        facts.append(f)

    if not facts:
        raise EngagementError(
            f"{path}: no facts. An engagement file recording nothing is "
            f"indistinguishable from no file at all, and the desks would "
            f"refuse identically — but this one looks answered."
        )
    return Engagement(ref=ref, path=path, facts=tuple(facts))


def load(path: Path, known: dict | None = None) -> Engagement:
    """Read one engagement's file. The path is the caller's and must be outside
    this plugin — see the module note."""
    # `~` IS EXPANDED HERE AND NOT BY THE CALLER. `Path.resolve` does not do it
    # -- `Path("~/x").resolve()` is the working directory with a literal `~` in
    # it -- so a caller pasting the documented example gets "no engagement file
    # at /somewhere/~/engagements/...", which reads as a missing file rather
    # than as the tilde it actually is.
    path = Path(path).expanduser().resolve()
    if path.is_relative_to(HERE):
        raise EngagementError(
            f"{path} is inside the desk plugin. An engagement's facts are "
            f"client data and this directory is a checkout that gets pushed; "
            f"keep the file where the firm keeps its files and pass the path."
        )
    if not path.is_file():
        raise EngagementError(f"no engagement file at {path}")
    return parse(path.read_text(encoding="utf-8"), str(path), known)


def gaps(eng: Engagement | None, known: dict | None = None) -> dict:
    """`{fact: [desks]}` for every declared fact this file does not record.

    THE HALF THAT MATTERS. A file listing what it holds leaves a reader to
    assume the rest were not needed; `ask.brief` already prints the gaps by name
    for one desk, and this is the same answer for a whole engagement, before
    anybody asks a question. Passing `None` is a real question with a real
    answer — everything is missing — rather than an error.
    """
    known = declared() if known is None else known
    have = {f.name for f in (eng.facts if eng else ())}
    return {name: list(desks) for name, desks in sorted(known.items())
            if name not in have}
