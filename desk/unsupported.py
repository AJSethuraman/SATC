"""Refused, but kept — the queue that turns a refusal into a work item.

A refusal is a FINDING, and throwing away the reasoning behind it destroys the
finding. The engine refuses to *serve* an uncited answer; it does not delete it.

WHY THIS EXISTS AT ALL. An answer the desk could not support is usually telling
you one of two useful things: that real authority exists and was never loaded, or
that the rules permit a choice and nobody has taken one. From outside those look
identical, and only the reasoning tells them apart. Without this queue the desk's
failures are a number that goes down for reasons nobody can inspect.

THREE RESOLUTIONS, NONE AUTOMATIC, ALL BY PULL REQUEST:

  real authority never loaded  -> promote to a SOURCE
  a defensible call the rules do not settle -> promote to a POSITION, in the
                                               firm's own words
  an invention                 -> leave it. its visibility IS the finding.

**Retained is not accepted.** An entry here is never returned to a caller and
never counted as correct. That boundary is the whole reason keeping it is safe,
and `test_unsupported.py` asserts it rather than trusting this paragraph.

This is `canon-mine`'s discipline applied to answers instead of convictions:
propose, never write.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from record import RecordError, _blocks, _date, _field, _inline

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)


@dataclass(frozen=True)
class Unsupported:
    """One answer the engine would not serve, kept with its reasoning."""
    id: str
    question: str
    concluded: str
    believed_authority: str
    failed_because: str
    recorded: str
    model: str = ""
    working: str = ""

    def render(self) -> str:
        """The exact text stored. Written so a person can read the diff."""
        lines = [
            f"## {self.id} · {self.question}",
            "",
            f"**Failed because:** {self.failed_because} · **Recorded:** {self.recorded}",
            "",
            f"**Concluded:** {self.concluded}",
            "",
            f"**Believed authority:** {self.believed_authority or '(none offered)'}",
        ]
        if self.model:
            lines += ["", f"**Model:** {self.model}"]
        if self.working:
            lines += ["", f"**Working:** {self.working}"]
        return "\n".join(lines) + "\n"


def parse(text: str) -> list[Unsupported]:
    out = []
    for head, block in _blocks(text, _HEAD):
        uid, question = head.group(1), head.group(2).strip()
        where = f"unsupported {uid}"
        out.append(Unsupported(
            id=uid,
            question=question,
            failed_because=_inline(block, "Failed because", where),
            recorded=_date(_inline(block, "Recorded", where), "recorded", where),
            concluded=_field(block, "Concluded", where),
            believed_authority=_field(block, "Believed authority", where),
            model=_field(block, "Model", where, required=False),
            working=_field(block, "Working", where, required=False),
        ))
    return out


PREAMBLE = """# Unsupported — answers the engine would not serve, kept with their reasoning

**Retained is not accepted.** Nothing here was returned to a caller and nothing
here is counted as correct. It is kept because a refusal is a finding, and the
reasoning behind it is the best evidence of what this desk's record is missing.

Three resolutions, none automatic, all by pull request:

| What the reasoning shows | Resolution |
|---|---|
| Real authority that was never loaded | promote to a **source** |
| A defensible call the rules do not settle | promote to a **position**, in the firm's words |
| An invention | leave it. Its visibility *is* the finding |

A queue that only grows is a desk nobody is feeding.

---

"""


def append(path: Path, entry: Unsupported) -> Path:
    """Add one entry. Creates the file with its preamble if absent.

    Idempotent on id: re-recording the same refusal returns without duplicating
    it, because a queue that grows a new row every retry stops being readable
    and the count stops meaning anything.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(PREAMBLE, encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if any(u.id == entry.id for u in parse(text)):
        return path
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + sep + entry.render() + "\n---\n\n", encoding="utf-8")
    return path


def next_id(existing: list[Unsupported]) -> str:
    """Ids are never reused. A gap with no explanation invites being filled."""
    used = {int(m.group(1)) for u in existing
            if (m := re.fullmatch(r"U(\d+)", u.id))}
    return f"U{max(used, default=0) + 1}"


def from_refusal(question: str, answer, result, *, model: str = "",
                 existing: list[Unsupported] | None = None,
                 today: str | None = None) -> Unsupported:
    """Build the entry the engine keeps when it refuses to serve an answer."""
    existing = existing or []
    return Unsupported(
        id=next_id(existing),
        question=question,
        concluded=answer.position or "(no position offered)",
        believed_authority=answer.citation,
        failed_because=result.reason or "no_citation",
        recorded=today or date.today().isoformat(),
        model=model,
        working=answer.working,
    )
