"""Ask the desks the close's real questions — the ones with no answer key.

WHAT THIS IS NOT. `scoreboard.py` scores PROBLEMS: fact patterns whose answer is
already known because it was read off the authority. That measures a brain
against a key, and it is the right way to compare two brains.

THIS HAS NO KEY, AND THAT IS THE POINT. The 43 questions came out of a real close
that could not finish. Nobody knows the answers; that is why they were asked. So
nothing here can grade anything. What it produces is what a desk WOULD hand back
in production — the answer, the citation, the tier, and whether the engine would
serve it at all — laid out so the firm can say whether they agree.

    the desk proposes; the firm disposes; and until the firm has looked,
    a green scoreboard says nothing about whether a client would be
    correctly advised.

WHAT AN ANSWERER MAY SEE, and why it is not everything in the directory:

  SOURCES.md      yes — it must know what it is allowed to rely on
  extracted/      yes — the authority itself
  positions/      RATIFIED ONLY — the firm's word is real authority. A PROPOSED
                  position is an agent's suggestion nobody has said yes to, and
                  showing it would let one agent's guess become the next one's
                  premise, which is the whole failure `positions/` exists to stop
  PROBLEMS.md     NEVER — it is the answer key, and this exercise has no key

    python tools/ask_the_desks.py            # write one brief per question
    python tools/ask_the_desks.py --serve answers.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine                                              # noqa: E402
import record                                              # noqa: E402
import routing                                             # noqa: E402

HERE = Path(__file__).resolve().parents[1]
CORPUS = HERE / "docs" / "CLOSE-QUESTIONS-2026-09-05.md"
TRIAGE = HERE / "docs" / "CLOSE-QUESTIONS-TRIAGE.md"
BRIEFS = HERE / "runs" / "asked-2026-09-05"


def kind_a() -> list[tuple[int, str, str]]:
    """(number, title, why) for the questions a desk is supposed to answer."""
    text = CORPUS.read_text(encoding="utf-8")
    titles = {int(m.group(1)): m.group(2) for m in
              re.finditer(r"^\*\*Q(\d+) · (.+?)\*\*$", text, re.M)}
    why = {int(m.group(1)): m.group(2).split("\n")[0] for m in
           re.finditer(r"^\*\*Q(\d+) · .+?\*\*\n\*Why it matters:\* (.+?)$", text, re.M)}
    a = [int(m.group(1)) for m in
         re.finditer(r"^\|\s*(\d+)\s*\|[^|]*\|\s*\*\*A\*\*\s*\|",
                     TRIAGE.read_text(encoding="utf-8"), re.M)]
    return [(n, titles[n], why.get(n, "")) for n in sorted(a)]


def brief(number: int, title: str, why: str, desk: record.Desk) -> str:
    """Everything an answerer may see, and nothing else."""
    ratified = [q for q in desk.positions if not q.proposed]
    out = [
        f"# Q{number} — {title}",
        "",
        f"**Why the close raised it:** {why}",
        "",
        f"You are the **{desk.name}** desk. Answer ONLY from the authority below.",
        "",
        "## What you must return",
        "",
        "```json",
        '{"position": "<your conclusion, one short line>",',
        ' "citation": "<one citation, copied EXACTLY from a heading below>",',
        ' "working": "<why that paragraph settles it>"}',
        "```",
        "",
        "Or, if nothing below settles it:",
        "",
        "```json",
        '{"escalated": true, "reason": "<one of: authority_absent, '
        'authority_permits_choice, facts_not_established>", "working": "<what is missing>"}',
        "```",
        "",
        "**`facts_not_established`** is the right answer when the rule is clear and",
        "what you do not know is a fact about the client — what was bought, which",
        "entity, which period. It is not a failure; it is the answer that says who",
        "has to be asked.",
        "",
        "**Never cite a paragraph that is not printed below.** The engine verifies",
        "the citation against this desk's record and refuses anything else,",
        "however real it is.",
        "",
        "## Sources this desk may rely on",
        "",
    ]
    for s in desk.sources:
        out.append(f"- **{s.id}** · {s.title} · tier **{s.tier}**")
    if ratified:
        out += ["", "## Positions the firm has already taken (their words, and binding)", ""]
        for q in ratified:
            out += [f"### {q.citation}", "", f"> {q.position}", ""]
    out += ["", "## The authority", ""]
    for p in desk.passages:
        out += [f"### {p.citation}", "", f"> {p.text}", ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--serve":
        return serve_answers(Path(argv[1]))

    regs = routing.registry(HERE / "desks")
    BRIEFS.mkdir(parents=True, exist_ok=True)
    index = []
    for number, title, why in kind_a():
        hits = routing.route(f"{title}. {why}", regs)
        if not hits:
            print(f"Q{number:<3} NO DESK — not asked")
            index.append({"q": number, "title": title, "desk": None})
            continue
        for r in hits:
            desk = record.load(HERE / "desks" / r.desk)
            path = BRIEFS / f"Q{number}-{r.desk}.md"
            path.write_text(brief(number, title, why, desk), encoding="utf-8")
            index.append({"q": number, "title": title, "desk": r.desk,
                          "brief": str(path.relative_to(HERE))})
            print(f"Q{number:<3} -> {r.desk:<32} {len(desk.passages):>3} passages")
    (BRIEFS / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\n{len(index)} brief(s) -> {BRIEFS.relative_to(HERE)}")
    return 0


def serve_answers(path: Path) -> int:
    """Put each answer through the production path and report what it did.

    NOTHING HERE IS A SCORE. `serve()` says whether an answer may leave the desk
    at all -- that its citation resolves, that it binds or carries the firm's
    word, and that its source is declared to answer this subject. Whether the
    CONCLUSION is right is the firm's to say, and this prints it for them to say
    it about.
    """
    answers = json.loads(path.read_text(encoding="utf-8"))
    served = refused = 0
    rows = []
    for a in answers:
        desk = record.load(HERE / "desks" / a["desk"])
        question = a["question"]
        if a.get("escalated"):
            ans = engine.Answer(position="", citation="", escalated=True,
                                reason=a["reason"])
        else:
            ans = engine.Answer(position=a["position"], citation=a["citation"])
        out = engine.serve(ans, desk, question=question)
        ok = not isinstance(out, engine.Refusal)
        served, refused = served + ok, refused + (not ok)
        rows.append({
            "q": a["q"], "desk": a["desk"], "question": question,
            "served": ok,
            "position": out.position if ok else a.get("position", ""),
            "citation": out.citation if ok else a.get("citation", ""),
            "tier": out.tier if ok else "",
            "checked_subject": out.checked_subject if ok else None,
            "reason": "" if ok else out.reason,
            "detail": "" if ok else out.detail,
            "working": a.get("working", ""),
        })
    out_path = BRIEFS / "served.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{len(rows)} answers · {served} the engine would serve · "
          f"{refused} it would refuse")
    print("\nNOT A SCORE. Whether a served conclusion is RIGHT is the firm's to "
          "say; this only reports what would have left the desk.\n")
    for r in rows:
        mark = "SERVED " if r["served"] else "REFUSED"
        print(f"  {mark} Q{r['q']:<3} {r['desk']:<32} "
              f"{r['position'] or r['reason']}")
    print(f"\n-> {out_path.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
