"""Merge the seven desks into one corpus. Run once, then read what it printed.

    `dec-kill`, 8 September 2026 -- the firm: "Kill the desks; one pool."
    And again on 10 September, twice: "I said to delete them. I've said to
    multiple times." / "I do not care. One corpus."

WHAT THIS DOES AND WHAT IT DELIBERATELY DOES NOT. It CONCATENATES RAW MARKDOWN
and rewrites the identifiers that collide. It does NOT re-render the records from
parsed objects, which was the obvious way to write it and is wrong: `record.py`
models the fields it needs and ignores everything else, so a round trip through
the parser would silently drop every `**Why:**` paragraph, every incident note
and every quotation of the firm -- which is most of what those files are FOR.
Losing the reasoning to tidy the data would be the worst trade in this
repository.

THREE THINGS COLLIDE ACROSS SEVEN DESKS, and each is renumbered here:

  SOURCE IDS.   36 source rows share 15 ids -- `S1` names a different
                publication on every desk. Deduplicated to 33 distinct sources
                (title + citation prefix + url), renumbered S1..S33, and every
                reference rewritten: the `Answered from Sn:` keys in SUBJECTS.md
                and the `**Source:** Sn` line inside every extracted passage.
                Measured before writing this: the 3 sources that ARE shared
                agree on tier and storage terms in every case, so the dedupe
                loses nothing.

  POSITION IDS. POS1 appears six times, POS2 six times, POS3 five. Renumbered
                POS1..POSn in desk order. The id is a label; the CITATION is the
                key, and that is what `alongside` and the engine match on.

  CITATIONS.    9 of 785 are held by more than one desk and 6 store DIFFERENT
                TEXT -- every one a truncation of the same passage, the worst
                being `26 CFR 1.274-5T(a)` at 1,466 characters on
                meals-and-entertainment and 125 on vehicle-expense. So a vehicle
                question answered from that citation has been served a twelfth
                of the rule, and nothing could see it because a question only
                ever reached one desk. THE LONGEST TEXT WINS and every drop is
                printed. This is not the merge working around a problem: it is
                the merge FINDING one, and it is the argument for one corpus.

`record.load` already refuses a citation stored twice in `extracted/`
(`record.py:1001-1009`), so a merge that ignored the duplicates would not
silently pick a winner -- it would fail to load at all. That refusal is why this
tool can be trusted to have handled them.

PROBLEMS ARE ALREADY UNIQUE (CB1, VE9, ...) and are concatenated untouched.

    cd desk && python tools/one_corpus.py --dry-run    # print, write nothing
    cd desk && python tools/one_corpus.py              # write corpus/

IT REFUSES TO WRITE IF ANYTHING WOULD BE LOST. Every source, position, problem
and citation present across the seven records is counted before and after, and a
missing one aborts with the count. Behaviour: report the denominator, and a
skipped check is not a passed one.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import record  # noqa: E402

DESKS = HERE / "desks"
CORPUS = HERE / "corpus"

#: A block runs from its `## ` heading to the next one or end of file. The
#: separator `---` that sits between blocks stays attached to the block it
#: follows, which is harmless and keeps the raw text byte-identical.
_BLOCK = re.compile(r"^## .*$", re.M)


def blocks(text: str) -> tuple[str, list[str]]:
    """`(preamble, [block, ...])` -- the file's own prose, then its entries."""
    heads = list(_BLOCK.finditer(text))
    if not heads:
        return text, []
    starts = [m.start() for m in heads] + [len(text)]
    return text[:starts[0]], [text[starts[i]:starts[i + 1]]
                              for i in range(len(heads))]


def desks() -> list[Path]:
    return [d for d in sorted(DESKS.iterdir()) if (d / "SUBJECTS.md").is_file()]


def source_key(s) -> tuple:
    """What makes two source rows the SAME source. Not the id -- the id is a
    position in one desk's list and is exactly what collides."""
    return (s.title.strip(), getattr(s, "citation_prefix", "") or "",
            (s.url or "").strip())


def build_source_map(loaded: dict) -> tuple[dict, list, list]:
    """`{(desk, old_id): new_id}`, the sources in new order, and the dupes."""
    new_id, order, seen, mapping, shared = 0, [], {}, {}, []
    for name, desk in loaded.items():
        for s in desk.sources:
            key = source_key(s)
            if key in seen:
                mapping[(name, s.id)] = seen[key]
                shared.append((s.title, name, s.id, seen[key]))
                continue
            new_id += 1
            label = f"S{new_id}"
            seen[key] = label
            mapping[(name, s.id)] = label
            order.append((label, name, s))
    return mapping, order, shared


def rewrite_source_ids(text: str, name: str, mapping: dict) -> str:
    """Every `Sn` that names a source becomes its corpus id.

    Done in ONE pass over a combined pattern rather than id by id, because
    sequential replacement renumbers its own output: rewriting S1->S9 and then
    S9->S2 turns the first one into S2 as well. Measured the hard way in a
    different repository; here it is simply prevented.
    """
    per_desk = {old: new for (d, old), new in mapping.items() if d == name}
    if not per_desk:
        return text
    pattern = re.compile(r"\b(" + "|".join(sorted(per_desk, key=len,
                                                  reverse=True)) + r")\b")
    return pattern.sub(lambda m: per_desk[m.group(1)], text)


def merge(dry: bool) -> int:
    loaded = {d.name: record.load(d) for d in desks()}
    before = {
        "sources": sum(len(k.sources) for k in loaded.values()),
        "positions": sum(len(k.positions) for k in loaded.values()),
        "problems": sum(len(k.problems) for k in loaded.values()),
        "citations": len({p.citation for k in loaded.values()
                          for p in k.passages}),
    }
    mapping, order, shared = build_source_map(loaded)

    print(f"seven records -> one corpus\n{'=' * 60}")
    print(f"  sources    {before['sources']:>4} rows -> {len(order)} distinct "
          f"({len(shared)} shared by more than one desk)")
    for title, name, old, new in shared:
        print(f"      dedup  {title[:44]:<44} {name}:{old} -> {new}")

    # ---- SOURCES.md -------------------------------------------------------
    src_out = []
    for label, name, s in order:
        raw = (DESKS / name / "SOURCES.md").read_text(encoding="utf-8")
        _, bs = blocks(raw)
        block = next(b for b in bs if b.startswith(f"## {s.id} · "))
        block = block.replace(f"## {s.id} · ", f"## {label} · ", 1)
        src_out.append(rewrite_source_ids(block, name, mapping).rstrip())

    # ---- POSITIONS --------------------------------------------------------
    pos_out, pos_n, renumbered = [], 0, 0
    for name in loaded:
        raw = (DESKS / name / "positions" / "POSITIONS.md").read_text(
            encoding="utf-8")
        for b in blocks(raw)[1]:
            head = re.match(r"^## (POS\d+) · ", b)
            if not head:
                pos_out.append(b.rstrip())
                continue
            pos_n += 1
            label = f"POS{pos_n}"
            if head.group(1) != label:
                renumbered += 1
            pos_out.append(b.replace(f"## {head.group(1)} · ",
                                     f"## {label} · ", 1).rstrip())
    print(f"  positions  {before['positions']:>4} -> {pos_n} "
          f"({renumbered} renumbered; the citation is the key, not the label)")

    # ---- PROBLEMS ---------------------------------------------------------
    prob_out, prob_n = [], 0
    for name in loaded:
        for b in blocks((DESKS / name / "PROBLEMS.md").read_text(
                encoding="utf-8"))[1]:
            prob_out.append(b.rstrip())
            prob_n += 1
    print(f"  problems   {before['problems']:>4} -> {prob_n} (ids already "
          f"unique per desk, untouched)")

    # ---- extracted passages, longest text wins ----------------------------
    best: dict = {}
    dropped = []
    for name in loaded:
        for f in sorted((DESKS / name / "extracted").glob("*.md")):
            raw = f.read_text(encoding="utf-8")
            for b in blocks(raw)[1]:
                citation = re.match(r"^## (.+)$", b, re.M).group(1).strip()
                b = rewrite_source_ids(b, name, mapping).rstrip()
                held = len(quoted(b))
                if citation in best:
                    keep, keep_from, keep_len = best[citation]
                    # IDENTICAL TEXT IS NOT A CONFLICT. Three of the nine
                    # shared citations store byte-identical passages; calling
                    # those "dropped" would pad the finding that matters --
                    # the six where one record holds a TRUNCATION of the rule.
                    if _same_passage(b, keep):
                        continue
                    if held <= keep_len:
                        dropped.append((citation, name, held,
                                        keep_from, keep_len))
                        continue
                    dropped.append((citation, keep_from, keep_len,
                                    name, held))
                best[citation] = (b, name, held)
    print(f"  citations  {before['citations']:>4} distinct -> {len(best)}")
    if dropped:
        print(f"\n  {len(dropped)} CITATION(S) STORED TWICE WITH DIFFERENT "
              f"TEXT -- longest kept, shorter dropped:")
        for citation, lost_from, lost_len, kept_from, kept_len in dropped:
            print(f"      {citation[:46]:<46} dropped {lost_from[:16]:<16} "
                  f"{lost_len:>5}ch  kept {kept_from[:16]:<16} {kept_len:>5}ch")

    # ---- SUBJECTS.md ------------------------------------------------------
    # ONE REGISTRATION, NOT SEVEN, and this is where the desk actually dies.
    # `record.load` refuses a SUBJECTS.md whose heading names something other
    # than its own directory -- "a desk named differently from its directory
    # cannot be reached by the name a refusal gives out". That guard IS the desk
    # concept: it exists so a refusal can say `ask cash-and-bank`. Seven
    # headings cannot survive into one corpus, and renaming all seven to
    # `corpus` would be seven registrations of one name.
    #
    # So the seven blocks collapse into one. WHAT IS KEPT is exactly what
    # `dec-kill` says survives -- which subjects a source answers, and the
    # per-citation NARROWING of that. What is dropped is the desk's name and its
    # one-line subject title, which were only ever there to be routed to.
    #
    # The prose is kept. Each desk's SUBJECTS.md carries the incident that
    # produced its narrowing -- cash-and-bank's is the 5 September service
    # charge served with the timing citation, `checked_subject=True`, real
    # source and wrong paragraph -- and those notes are the reason the
    # narrowings are trusted. They move under `###` sub-headings so they stay
    # inside the one block rather than starting new ones.
    merged: dict = {}
    records: list = []
    notes, judged, unioned = [], set(), []
    for name in loaded:
        raw = (DESKS / name / "SUBJECTS.md").read_text(encoding="utf-8")
        judged.add(loaded[name].judged)
        for b in blocks(raw)[1]:
            b = rewrite_source_ids(b, name, mapping)
            body = b.split("\n", 1)[1] if "\n" in b else ""
            kept, prose = [], []
            for line in body.splitlines():
                if re.match(r"^\*\*Answered (from|by) ", line.strip()):
                    kept.append(line.rstrip())
                elif re.match(r"^\*\*Records:\*\*", line.strip()):
                    # THE FACTS THE CORPUS EXPECTS ON FILE, unioned like the
                    # subject lists. `record.load` refuses a position that needs
                    # a field nothing declares -- "nothing a caller passes could
                    # ever meet it" -- so dropping these would make 20 ratified
                    # positions unservable, which is the loudest possible way to
                    # lose the firm's own answers.
                    records += [x.strip() for x in
                                line.split(":**", 1)[1].split(",") if x.strip()]
                elif re.match(r"^\*\*Judged:\*\*", line.strip()):
                    continue          # one policy, written once below
                else:
                    prose.append(line.rstrip())
            for line in kept:
                head, _, terms = line.partition(":**")
                merged.setdefault(head + ":**", []).append(
                    (name, [x.strip() for x in terms.split(",") if x.strip()]))
            if any(x.strip() for x in prose):
                notes.append(f"### From the {name} record\n"
                             + "\n".join(prose).strip())
    # TWO RECORDS DECLARING THE SAME SOURCE IS NOW ONE LINE, and the terms are
    # UNIONED rather than one file-order winner taking it. The three sources
    # deduped above were each declared by two desks with DIFFERENT subject
    # lists -- `1.162-3` answers "materials and supplies" on one record and
    # "incidental, non-incidental" on the other, and both are true of the same
    # regulation. `record.load` refuses the duplicate outright ("which list wins
    # would be decided by file order"), which is the right refusal and the
    # reason this is done deliberately here rather than discovered later.
    lines = []
    for head, rows in merged.items():
        terms, order = set(), []
        for _, ts in rows:
            for term in ts:
                if term not in terms:
                    terms.add(term)
                    order.append(term)
        lines.append(f"{head} " + ", ".join(order))
        if len(rows) > 1:
            unioned.append((head, [n for n, _ in rows], len(order)))
    if unioned:
        print(f"\n  {len(unioned)} source(s) declared by more than one record "
              f"-- subject lists UNIONED, not overwritten:")
        for head, names, n in unioned:
            key = head.replace("**Answered from ", "").replace(":**", "")
            print(f"      {key:<10} {', '.join(names)} -> {n} subjects")

    if len(judged) != 1:
        print(f"\nREFUSING TO WRITE: the records disagree on `Judged`: "
              f"{sorted(judged)}. One corpus cannot hold two policies.")
        return 1
    kept_records, seen_r = [], set()
    for r in records:
        if r not in seen_r:
            seen_r.add(r)
            kept_records.append(r)
    print(f"  records    {len(kept_records)} fact field(s) kept: "
          f"{', '.join(kept_records)}")
    subj_out = ["## corpus · Everything the firm has admitted as authority",
                "", *lines, "",
                "**Records:** " + ", ".join(kept_records), "",
                f"**Judged:** {judged.pop()}", "",
                "*One policy for one corpus. All seven records declared it "
                "separately and identically; the firm, 8 September 2026, asked "
                "which desks may not serve unjudged and answered* \"The judge "
                "can look at it all I guess?\" *— all seven.*",
                "", "---", "", *notes]
    print(f"\n  subjects   seven registrations -> one; "
          f"{len(lines)} narrowing lines kept, {len(notes)} incident notes kept")

    # BUILT SOMEWHERE ELSE FIRST, LOADED, AND ONLY THEN MOVED INTO PLACE.
    # The check that matters is not "did the blocks add up" -- PROBLEMS.md
    # carries prose sections under `## ` headings that are not problems, and
    # counting those made the first run of this tool refuse to write. It is
    # "does `record.load` read the same inventory out of the corpus that it
    # read out of the seven records". Nothing else proves the merge.
    # STAGED UNDER A DIRECTORY CALLED `corpus`, because `record.load` checks
    # the registration name against the directory basename. Staging as
    # `.corpus-staged` fails that check for a reason that has nothing to do
    # with the merge.
    staging = HERE / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
    staged = staging / "corpus"
    if staged.exists():
        shutil.rmtree(staged)
    (staged / "positions").mkdir(parents=True)
    (staged / "extracted").mkdir()
    _write(staged / "SOURCES.md", _preamble("SOURCES"), src_out)
    _write(staged / "SUBJECTS.md", _preamble("SUBJECTS"), subj_out)
    _write(staged / "PROBLEMS.md", _preamble("PROBLEMS"), prob_out)
    _write(staged / "positions" / "POSITIONS.md", _preamble("POSITIONS"),
           pos_out)
    _write(staged / "extracted" / "authority.md", _preamble("EXTRACTED"),
           [b for b, _, _ in best.values()])

    try:
        after = record.load(staged)
    except record.RecordError as e:
        print(f"\nREFUSING TO WRITE: the merged corpus does not load\n  {e}")
        shutil.rmtree(staging)
        return 1

    lost = _reconcile(loaded, after, mapping)
    print(f"\n{'-' * 60}\nreconciliation, by loading the merged corpus")
    for line in lost["report"]:
        print("  " + line)
    if lost["fatal"]:
        print("\nREFUSING TO WRITE: " + "; ".join(lost["fatal"]))
        shutil.rmtree(staging)
        return 1

    if dry:
        shutil.rmtree(staging)
        print("\n--dry-run: nothing written.")
        return 0

    if CORPUS.exists():
        shutil.rmtree(CORPUS)
    staged.rename(CORPUS)
    shutil.rmtree(staging)
    print(f"\nwritten to {CORPUS}")
    return 0


def quoted(block: str) -> str:
    """The authority text inside a raw passage block, and nothing else.

    THE COMPARISON MUST BE ON THIS AND NOT ON THE BLOCK. The first version of
    this tool picked the longer BLOCK, and a test caught it immediately:
    `26 CFR 1.162-3(c)(1)(i)` was 338 characters of block on one record against
    331 on the other, while the RULE inside them was 238 against 242. The block
    carries `**Source:**`, `**Checked:**`, `**Kind:**` and whatever notes a
    record keeps, so "longer block" and "more of the regulation" are different
    questions — and picking on the wrong one is how a truncation wins a merge
    whose entire purpose is to stop truncations winning.
    """
    return " ".join(l.lstrip("> ").strip() for l in block.splitlines()
                    if l.startswith(">")).strip()


def _same_passage(a: str, b: str) -> bool:
    """Two raw blocks holding the same authority text. `**Source:**` differs
    between records by construction and says nothing about the rule."""
    return quoted(a) == quoted(b)


def _reconcile(loaded: dict, after, mapping: dict) -> dict:
    """Every citation, position and problem that was there before is there now.

    Sources are checked by TITLE rather than by id, because renumbering is the
    whole point and an id comparison would always fail.
    """
    report, fatal = [], []

    was = {p.citation for k in loaded.values() for p in k.passages}
    now = {p.citation for p in after.passages}
    report.append(f"citations   {len(was):>4} before -> {len(now):>4} after")
    if missing := sorted(was - now):
        fatal.append(f"{len(missing)} citations lost, first: {missing[0]!r}")

    was_p = {(q.citation, q.position) for k in loaded.values()
             for q in k.positions}
    now_p = {(q.citation, q.position) for q in after.positions}
    report.append(f"positions   {len(was_p):>4} before -> {len(now_p):>4} after")
    if missing := sorted(was_p - now_p):
        fatal.append(f"{len(missing)} positions lost, first: {missing[0][0]!r}")

    was_b = {b.id for k in loaded.values() for b in k.problems}
    now_b = {b.id for b in after.problems}
    report.append(f"problems    {len(was_b):>4} before -> {len(now_b):>4} after")
    if missing := sorted(was_b - now_b):
        fatal.append(f"{len(missing)} problems lost: {missing}")

    was_s = {s.title.strip() for k in loaded.values() for s in k.sources}
    now_s = {s.title.strip() for s in after.sources}
    report.append(f"sources     {len(was_s):>4} distinct titles before -> "
                  f"{len(now_s):>4} after")
    if missing := sorted(was_s - now_s):
        fatal.append(f"{len(missing)} sources lost: {missing[:2]}")

    # THE PER-CITATION NARROWING, which `dec-kill` names as surviving. It is
    # the one check that still BLOCKS in the engine -- two paragraphs of one
    # publication carrying opposite answers is not a narrow refusal, it is the
    # opposite treatment of the same money -- so losing one here would reopen
    # the 5 September service-charge incident silently.
    was_n = {}
    for k in loaded.values():
        for c, terms in k.answered_by.items():
            was_n.setdefault(c, set()).update(terms)
    now_n = {c: set(ts) for c, ts in after.answered_by.items()}
    report.append(f"narrowings   {len(was_n):>4} before -> {len(now_n):>4} after")
    for c, terms in sorted(was_n.items()):
        if c not in now_n or not terms <= now_n[c]:
            fatal.append(f"per-citation narrowing lost for {c!r}")

    # EVERY PASSAGE MUST STILL NAME A SOURCE THE CORPUS HOLDS. This is the one
    # the renumbering could break silently: a missed `**Source:** Sn` rewrite
    # leaves a passage pointing at whatever publication now carries that id,
    # which is worse than a crash because it still loads.
    ids = {s.id for s in after.sources}
    orphan = sorted({p.citation for p in after.passages
                     if p.source_id not in ids})
    report.append(f"passages naming a source the corpus holds: "
                  f"{len(after.passages) - len(orphan)}/{len(after.passages)}")
    if orphan:
        fatal.append(f"{len(orphan)} passages name a missing source, "
                     f"first: {orphan[0]!r}")
    return {"report": report, "fatal": fatal}


def _write(path: Path, preamble: str, parts: list[str]) -> None:
    path.write_text(preamble + "\n\n" + "\n\n".join(parts) + "\n",
                    encoding="utf-8")


_PREAMBLES = {
    "SOURCES": """# Sources — what the corpus may rely on

One list, for one corpus. Ids are S1..Sn across the whole record: before
10 September 2026 each of seven desks numbered its own sources from S1, so `S1`
named seven different publications and the id said nothing on its own.""",
    "SUBJECTS": """# Subjects — the per-source and per-citation narrowing

**These no longer decide what a question reaches.** `dec-kill` deleted the
word-matching that picked a desk; retrieval is `pool.look`, over the authority's
own text. What is kept here is the half `dec-kill` says survives: which subjects
a source answers, and the per-citation NARROWING of that — the check that stops
one paragraph of a publication being served for a question the paragraph beside
it answers the opposite way.""",
    "PROBLEMS": """# Problems — fact patterns whose answer is already known

Concatenated from the seven records unchanged. Ids were already unique across
them (CB1, VE9, ...) because each was prefixed by hand.""",
    "POSITIONS": """# Positions — the firm's own answers, binding and quoted exactly

Renumbered POS1..POSn across the whole corpus. **The label is not the key** —
the citation is, which is what `alongside` matches on and what the engine checks.""",
    "EXTRACTED": """# The authority, as stored

One file. Where two records held the same citation with different text, the
longest was kept and `tools/one_corpus.py` printed what it dropped.""",
}


def _preamble(which: str) -> str:
    return _PREAMBLES[which]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="print the inventory and write nothing")
    raise SystemExit(merge(p.parse_args().dry_run))
