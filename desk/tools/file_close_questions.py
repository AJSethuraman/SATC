"""File a close's questions into the queue — and refuse the ones that do not belong there.

WHAT THIS IS FOR. An agent closing a real set of books stopped, and wrote down 43
things it needed to know. `unsupported.from_question` is the front door for
exactly that. This walks a triaged corpus through it.

THE INTERESTING PART IS WHAT IT WILL NOT FILE. `from_question` accepts two
reasons, and they are the two a question can honestly be in: authority is missing,
or a fact is. Measured on the 43, that is 22 of them. The other 21 resolve by
requesting a document, by the firm deciding once, by fixing a bug, or by nobody
doing anything at all — and there is no queue for any of those.

So this tool REPORTS the 21 rather than finding somewhere to put them. Filing a
document request under `authority_absent` would make the queue say the record is
missing authority it is not missing, and the thing that actually resolves it —
someone asking for a statement — would never be raised. A queue that accepts
everything stops meaning anything, which is the same argument as the closed reason
set it is enforcing.

    python tools/file_close_questions.py [--write]

Without `--write` it reports and touches nothing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unsupported                                          # noqa: E402

HERE = Path(__file__).resolve().parents[1]
CORPUS = HERE / "docs" / "CLOSE-QUESTIONS-2026-09-05.md"
TRIAGE = HERE / "docs" / "CLOSE-QUESTIONS-TRIAGE.md"
QUEUE = HERE / "unfiled" / "CLOSE-2026-09-05.md"

#: The kinds the queue holds, and the reason each files under. Written as a
#: mapping rather than an if/else because the point of the exercise is that the
#: remaining kinds have NO entry here -- a missing key is the finding, and a
#: default would hide it.
#:
#: C WAS NOT HERE UNTIL 5 SEPTEMBER 2026. Eight questions resolved by requesting
#: a document nobody had asked for, and the queue had no reason for it, so this
#: tool named their owner and refused to file them. The firm answered the docket
#: -- "wire it up properly", and "but not direct to client - things would be
#: wired to go to me as the last resort right now" -- and `document_not_requested`
#: is that, with the constraint in it: the request is raised to the PREPARER.
FILES_AS = {"A": "authority_absent", "B": "facts_not_established",
            "C": "document_not_requested"}

#: What resolves the kinds this queue cannot hold. Named so the report says who
#: has to move, rather than leaving 21 questions described only as "not filed".
OWNED_BY = {
    "D": "one decision from the firm, ratified once",
    "E": "a defect in the software, not a question",
    "F": "nobody: it changes nothing",
}


def triaged() -> list[tuple[int, str, str]]:
    """(number, title, primary kind) from the triage table."""
    out = []
    for line in TRIAGE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\*\*([A-F])\*\*\s*\|", line)
        if m:
            out.append((int(m.group(1)), m.group(2), m.group(3)))
    return out


def reasoning() -> dict[int, str]:
    """Each question's `Why it matters`, which is the working the queue keeps.

    A question filed without it is a line of text somebody has to re-derive the
    importance of, and the reasoning is the best evidence of what is missing --
    which is the whole argument for keeping refusals rather than counting them.
    """
    text = CORPUS.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\*\*Q(\d+) · .+?\*\*\n\*Why it matters:\* (.+?)$",
                         text, re.M | re.S):
        out[int(m.group(1))] = " ".join(m.group(2).split("\n")[0].split())
    return out


def main(argv: list[str]) -> int:
    write = "--write" in argv
    rows, why = triaged(), reasoning()
    if not rows:
        sys.exit("no triaged questions found; has the table moved?")

    existing = (unsupported.parse(QUEUE.read_text(encoding="utf-8"))
                if QUEUE.exists() else [])
    filed, refused = [], []

    for number, title, kind in rows:
        if kind not in FILES_AS:
            refused.append((number, title, kind))
            continue
        entry = unsupported.from_question(
            f"Q{number}: {title}",
            why=why.get(number, ""),
            model="the agent closing the books, 5 September 2026",
            because=FILES_AS[kind],
            existing=existing,
        )
        filed.append((number, kind, entry))
        if write:
            unsupported.append(QUEUE, entry)
            existing = unsupported.parse(QUEUE.read_text(encoding="utf-8"))

    print(f"{len(rows)} triaged · {len(filed)} filed · {len(refused)} have no queue\n")
    for kind, reason in sorted(FILES_AS.items()):
        n = sum(1 for _, k, _ in filed if k == kind)
        print(f"  filed as {reason:<24} {n}")
    print()
    for kind, owner in sorted(OWNED_BY.items()):
        rows_ = [r for r in refused if r[2] == kind]
        if not rows_:
            continue
        print(f"  NOT FILED ({len(rows_)}) — {owner}")
        for number, title, _ in rows_:
            print(f"      Q{number}: {title}")
    print()
    print(f"{'wrote' if write else 'would write'} {QUEUE.relative_to(HERE)}")
    if not write:
        print("(nothing was written; pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
