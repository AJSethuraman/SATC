"""Which words actually route, and which questions no desk hears — from real questions.

WHY THIS EXISTS. A desk declares the subjects it fires on, by hand, and a session
building one naturally writes the vocabulary of its own regulation. Measured on
the close's 43 questions: "Where is the line between a tool and a fixed asset?"
routed to NO desk, while the same question as "what is our capitalisation
threshold" routed correctly. The firm's reading, 5 September 2026:

    "having to make words that fire for things like this. But to me, that would
     be obvious. Like, yeah, of course, capitalization has nothing to do with
     fixed asset. So, like, how do we... I don't know. Maybe do a quick kinda
     hits matrix of these are common words that associate with other common
     things."

So this stops guessing and asks the corpus. It reports two things and proposes
nothing: the questions nothing hears, with the words in them no desk claims; and
every declared subject with how many desks it fires and how many real questions
it caught. A term firing four desks is the reason a question consults four
experts; a term catching nothing is vocabulary somebody imagined.

WHAT THIS MAY NOT BECOME. A relevance SCORE, and the distinction is the whole of
why this is safe. Routing wrong costs a round trip -- a desk with nothing to say
refuses. The citation gate being wrong costs a wrong answer, and the firm already
declined a word-overlap gate there on measurement: 4 false refusals in 16 on
`fixed-assets`. Loose is allowed here and nowhere near `_check`.

    python tools/subject_gaps.py [corpus.md ...]
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routing                                             # noqa: E402
from _canon import load_record                             # noqa: E402

HERE = Path(__file__).resolve().parents[1]
DEFAULT = HERE / "docs" / "CLOSE-QUESTIONS-2026-09-05.md"

#: Words that carry no subject and would drown the report. Deliberately short:
#: a long stop list is a second vocabulary to maintain, which is the problem.
STOP = set("""a an the and or but if is are was were be been being of to in on at for
with from by as it its this that these those what which who whom whose how when where
why do does did done can could should would may might must have has had not no nor so
than then there here they them their we us our you your i me my he she his her""".split())


def questions(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    titles = {m.group(1): m.group(2) for m in
              re.finditer(r"^\*\*(Q\d+) · (.+?)\*\*$", text, re.M)}
    why = {m.group(1): m.group(2).split("\n")[0] for m in
           re.finditer(r"^\*\*(Q\d+) · .+?\*\*\n\*Why it matters:\* (.+?)$", text, re.M)}
    return {k: f"{v}. {why.get(k, '')}" for k, v in titles.items()}


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or [DEFAULT]
    regs = routing.registry(HERE / "desks")
    touches = load_record().touches

    asked: dict[str, str] = {}
    for p in paths:
        asked.update(questions(p))
    if not asked:
        sys.exit(f"no questions found in {[str(p) for p in paths]}")

    # ── which questions nothing hears, and what they are made of ─────────────
    claimed = {t for r in regs for t in r.fires_on}
    unheard = []
    for qid, text in sorted(asked.items(), key=lambda kv: int(kv[0][1:])):
        if routing.route(text, regs):
            continue
        words = [w for w in re.findall(r"[a-z][a-z\-']+", text.lower())
                 if w not in STOP and len(w) > 3]
        novel = [w for w, _ in Counter(words).most_common()
                 if not any(touches(w, t) for t in claimed)][:8]
        unheard.append((qid, asked[qid].split(".")[0][:52], novel))

    print(f"{len(asked)} questions · {len(regs)} desks · {len(claimed)} declared subjects\n")
    print(f"HEARD BY NOTHING: {len(unheard)} of {len(asked)}")
    for qid, title, novel in unheard:
        print(f"  {qid:<4} {title}")
        print(f"       no desk claims: {', '.join(novel) or '(nothing distinctive)'}")

    # ── the hits matrix: every subject, how loud and how useful ──────────────
    fires: dict[str, set] = defaultdict(set)
    caught: Counter = Counter()
    for r in regs:
        for term in r.fires_on:
            for text in asked.values():
                if touches(text, term):
                    fires[term].add(r.desk)
                    caught[term] += 1

    noisy = sorted(((len(d), caught[t], t, sorted(d)) for t, d in fires.items()
                    if len(d) > 1), reverse=True)
    print(f"\nTERMS THAT FIRE MORE THAN ONE DESK: {len(noisy)}")
    print("  (each is a question consulting an expert that cannot answer it)")
    for n, hits, term, desks in noisy[:15]:
        print(f"  {n} desks · {hits:>2} questions · {term:<24} {', '.join(desks)}")

    silent = sorted(t for t in claimed if t not in caught)
    print(f"\nDECLARED BUT CAUGHT NOTHING IN THIS CORPUS: {len(silent)} of {len(claimed)}")
    print("  (not wrong -- this is one close. A term silent across many corpora "
          "is vocabulary somebody imagined)")
    print("  " + ", ".join(silent[:24]) + (" ..." if len(silent) > 24 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
