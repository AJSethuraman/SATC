"""Build the cash-and-bank-reconciliation desk from two public sources.

THE SUBJECT IS AN ACCOUNTING CONVENTION AND THE SOURCES HERE ARE TAX SOURCES.
That is stated first because getting it backwards is the mistake this desk was
built out of. Whether an outstanding check is a reconciling item or an entry in
the books is bookkeeping, not tax: the books record the transaction when it
happened and the bank records it when it processed it, so the difference is
timing and timing is explained rather than booked. It holds on cash basis too --
cash basis governs WHEN income and expense are recognised, not whether a check
that was written was written.

The two sources below are what can be REACHED, not what governs. § 1.446-1
defers to the trade's practice; Publication 583 illustrates the treatment in a
worked example without ruling on it. The literature that governs is FASB ASC,
which is human_only, and every other accounting-side source is refused by this
environment's network policy. So the convention itself lives in `positions/` in
the firm's own words -- which is exactly the case the two-store design was built
for, and the reason this subject was worth picking.

WHY A SECOND EXTRACTOR AND NOT `extract_ecfr.py`. That one refuses this section,
correctly: `outline()` raises "no assignment of levels is consistent with the
sequence" on § 1.446-1, because the section uses LOWER-CASE LETTERS at a fourth
level (`(e)(2)(ii)(d)`) where the CFR alphabet cycle expects upper-case ones. The
refusal is the tool working. This one does less and says so.

WHAT IT STORES, AND WHAT IT REFUSES TO. A paragraph is stored only when its
citation follows from the labels the paragraphs themselves print, under the
ordinary cycle (letter, then arabic, then lower roman) and no deeper. Everything
below that is COUNTED AND LEFT OUT rather than guessed at -- a stored citation
that might be the wrong paragraph is worse than none, which is the rule
`extract_ecfr.outline()` already applies to the same problem one level up.

THE WORKED RECONCILIATION IS NOT AUTHORITY. Publication 583 ends with a worked
bank reconciliation, and that example is where this desk's answers are read from.
Storing it as authority would put the answer key in the corpus -- measured on the
fixed-assets desk on 4 September 2026, where 21 problems and 21 stored passages
made citing an assignment puzzle and the citation number unreadable (#244).
`guards.authority_is_more_than_the_answer_key` now fails the build on that shape;
this module keeps the example out in the first place.

IT TAKES LOCAL FILES AND NEVER FETCHES. Same discipline as `extract_ecfr.py`: the
network belongs to a person running two commands they can read, not to a build.

    curl -sS --compressed -o 446.xml \\
      "https://www.ecfr.gov/api/versioner/v1/full/<DATE>/title-26.xml?part=1&section=1.446-1"
    curl -sSL --compressed -o p583.html "https://www.irs.gov/publications/p583"

    python tools/build_cash_desk.py 446.xml p583.html <repo-root> <branch> <YYYY-MM-DD>

The eCFR endpoint REQUIRES compression -- without `--compressed` it answers 406
with "This endpoint requires response compression", which reads like a bad URL.
"""
from __future__ import annotations

import html as _html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factory                                            # noqa: E402

#: The label alphabets, only as deep as this section can be read unambiguously.
#: A fourth level exists in § 1.446-1 and is deliberately not reached.
LOWER = tuple("abcdefghijklmnopqrstuvwxyz")
ARABIC = tuple(str(n) for n in range(1, 60))
ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
         "xi", "xii", "xiii", "xiv", "xv")
LEVELS = (LOWER, ARABIC, ROMAN)

_LEAD = re.compile(r"^((?:\([a-zA-Z0-9]{1,4}\)\s*)+)")
_LABEL = re.compile(r"\(([a-zA-Z0-9]{1,4})\)")

#: A run-in heading opens two levels in one element: "(a) General rule. (1) …"
#: and "(c) Permissible methods—(1) In general." are both one paragraph carrying
#: two labels. Read only the first here; the second is picked up as the next
#: element's own label would be, and the element is cited at its outer path.
_RUNIN = re.compile(r"^\(([a-z])\)\s+[^.—]{1,90}[.—]\s*\((\d+)\)")


def cfr_paragraphs(xml_path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """`(kept, excluded)` — every paragraph this reader can place, and the rest.

    The hierarchy is implied by the sequence and by nothing else: each element
    prints one label and its depth follows from what came before. So the reader
    walks the section in order, keeping a stack, and places an element only where
    exactly one depth in the ordinary cycle admits its label as the successor of
    what is already there. Where none does -- which is where this section drops
    into lower-case letters again -- the element is named in `excluded`.
    """
    root = ET.parse(xml_path).getroot()
    elements = [" ".join("".join(p.itertext()).split())
                for p in root.iter() if p.tag in ("P", "PSPACE")]

    kept: list[tuple[str, str]] = []
    excluded: list[str] = []
    stack: list[str] = []

    def place(label: str) -> int | None:
        """The one depth that admits this label here, or None. Never a guess."""
        for depth, alphabet in enumerate(LEVELS):
            if label not in alphabet:
                continue
            if depth < len(stack):
                at = stack[depth]                     # it continues that level
                if at in alphabet and alphabet.index(label) == alphabet.index(at) + 1:
                    return depth
            elif depth == len(stack) and label == alphabet[0]:
                return depth                          # it opens the next level
        return None

    for text in elements:
        # A RUN-IN HEADING OPENS TWO LEVELS IN ONE ELEMENT, and missing that
        # silently costs every child of the outer one. "(a) General rule. (1)
        # Section 446(a) provides…" is paragraphs (a) AND (a)(1); read as (a)
        # alone, the (2) that follows continues a level that was never opened,
        # so (a)(2), (a)(3) and (a)(4) were all dropped -- including (a)(4),
        # the paragraph this desk most needs.
        #
        # ITS OUTER LABEL IS PLACED LIKE ANY OTHER, AND THAT IS THE WHOLE POINT.
        # Written to reset the stack to the two labels it read, this produced a
        # second `26 CFR 1.446-1(d)(1)` from `(e)(2)(ii)(d) Changes involving
        # depreciable or amortizable assets—(1) Scope.` -- a lower-case letter at
        # a FOURTH level, which is the exact shape that makes `extract_ecfr`
        # refuse this section. `record.load` caught the duplicate and the factory
        # deleted the desk rather than ship it; this is the reader agreeing with
        # that refusal instead of relying on it.
        runin = _RUNIN.match(text)
        if runin:
            outer, inner = runin.group(1), runin.group(2)
            depth = place(outer)
            if depth is None:
                excluded.append(f"({outer}) run-in: {text[:50]}")
                continue
            stack = stack[:depth] + [outer, inner]
            kept.append(("26 CFR 1.446-1" + "".join(f"({p})" for p in stack),
                         text))
            continue

        lead = _LEAD.match(text)
        if not lead:
            excluded.append(text[:60])
            continue
        label = _LABEL.search(lead.group(1)).group(1)

        depth = place(label)
        if depth is None:
            excluded.append(f"({label}) {text[:50]}")
            continue

        stack = stack[:depth] + [label]
        kept.append(("26 CFR 1.446-1" + "".join(f"({p})" for p in stack), text))

    return kept, excluded


#: Publication 583's own section headings, which are how a publication is cited.
#: `Reconciling the checking account.` is the one this desk turns on; the others
#: are the surrounding recordkeeping rules a desk should be able to reach for.
PUB_SECTIONS = (
    "Kinds of Records To Keep",
    "Supporting Documents",
    "Reconciling the checking account.",
    "Bookkeeping System",
)

#: THE RECONCILIATION SECTION IS SPLIT IN TWO, because it states two rules and
#: they have opposite answers. The publication itself makes the division: it
#: first names what the STATEMENT did not yet include, and later says which
#: items the BOOKS are updated for. A single citation over both cannot carry a
#: position -- one citation admits one ratified answer, and these need two.
#:
#: Split at the sentence the publication turns on, and REFUSE if it has moved.
#: The publication is revised; a marker that no longer matches must be re-read
#: by a person, never matched loosely, because a loose match here would store
#: half a rule under a citation naming the whole one.
RECONCILING_SPLIT = "By reconciling your checking account, you will:"

#: What each half is cited as. The suffix is part of the citation, not a
#: comment: a reader following it has to land on the rule, not the section.
TIMING = "what the statement did not yet include"
UPDATING = "what the books are updated for"

#: A section longer than this is REFUSED, not trimmed. The first version capped
#: the body at 2,400 characters and returned what fitted -- which silently
#: dropped "Update your checkbook and journals for items shown on the
#: reconciliation as not recorded (such as service charges) or recorded
#: incorrectly", the single sentence this desk most depends on. A cap that
#: truncates is a partial read wearing a limit's clothes.
SECTION_LIMIT = 8000

#: NOT STORED, ON PURPOSE. The worked reconciliation is where the answers are
#: read from, so it is the answer key and never authority.
PUB_WORKED_EXAMPLE = "7. Bank Reconciliation"


def pub583_sections(html_path: Path) -> list[tuple[str, str]]:
    """One passage per named section, from the publication's body.

    The body is taken rather than the table of contents by reading the LAST
    occurrence of each heading: the contents lists every heading first, so the
    first match is a link and carries no text at all.
    """
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style|nav|header|footer)\b.*?</\1>", " ", raw)
    flat = _html.unescape(re.sub(r"(?s)<[^>]+>", "\n", raw))
    lines = [" ".join(l.split()) for l in flat.split("\n")]
    lines = [l for l in lines if l]

    out = []
    for heading in PUB_SECTIONS:
        hits = [i for i, l in enumerate(lines) if l == heading]
        if not hits:
            raise ValueError(
                f"Publication 583 has no section {heading!r}. The publication is "
                f"revised, so a heading that has moved must be re-read rather "
                f"than matched loosely -- a fuzzy match here would store text "
                f"under a citation naming a section it did not come from."
            )
        start = hits[-1]
        body = []
        for line in lines[start + 1:]:
            if line in PUB_SECTIONS or line.startswith(PUB_WORKED_EXAMPLE):
                break
            if line.startswith(("Table ", "How To Get Tax Help")):
                break
            body.append(line)
        text = " ".join(body)
        if len(text) > SECTION_LIMIT:
            raise ValueError(
                f"section {heading!r} is {len(text)} characters, over the "
                f"{SECTION_LIMIT} this reader will store. It REFUSES rather "
                f"than trimming: the first version capped the body and silently "
                f"dropped the sentence this desk turns on. Split it or raise "
                f"the limit deliberately."
            )
        cite = f'IRS Pub. 583 (12/2024), "{heading.rstrip(".")}"'

        if heading.startswith("Reconciling"):
            if RECONCILING_SPLIT not in text:
                raise ValueError(
                    f"{RECONCILING_SPLIT!r} is not in the reconciliation "
                    f"section any more. The publication has been revised and "
                    f"the split has to be re-read by a person; matching loosely "
                    f"would store half a rule under a citation naming the whole."
                )
            head, tail = text.split(RECONCILING_SPLIT, 1)
            out.append((f"{cite} — {TIMING}", head.strip()))
            out.append((f"{cite} — {UPDATING}",
                        (RECONCILING_SPLIT + tail).strip()))
            continue

        out.append((cite, text))
    return out


# ── the problems: facts composed, ANSWERS read off the publication ───────────
#
# THE ANSWERS ARE NOT OURS AND THE FACTS ARE. That asymmetry is stated rather
# than hidden. Publication 583's worked reconciliation puts every item on one
# side or the other, and which side it puts an item on IS the answer; the fact
# patterns below are composed from its line items because the example states them
# as a table of figures rather than as a scenario. What must not be ours is the
# conclusion, and it is not.
#
# THE EXAMPLE'S OWN LAYOUT IS THE CONCLUSION, so it is withheld: "Add deposits
# not credited" and "Subtract outstanding checks" are the answer written on the
# page. None of that wording reaches `Facts`.

BANK_SIDE = "a reconciling item, no entry in the books"
BOOKS_SIDE = "an entry in the books"

RECONCILING = 'IRS Pub. 583 (12/2024), "Reconciling the checking account"'
BY_TIMING = f"{RECONCILING} — {TIMING}"
BY_UPDATING = f"{RECONCILING} — {UPDATING}"

#: EACH PROBLEM CITES THE RULE ITS FACTS FALL UNDER, not the section both sit
#: in. Keyed to one shared citation, all four would rest on one ratified
#: position -- and a position carries one answer, so two of the four would be
#: refused as contradicting it whatever a desk said. Measured before ratifying:
#: with a single citation, every problem including the correct ones came back
#: `wrong_caught / contradicts_ratified_position`.
PROBLEMS = (
    ("CB1", "A deposit made on the last day of the month", BY_TIMING,
     BANK_SIDE,
     "A deposit of $516.08 was made on 31 January and recorded in the books "
     "that day. It does not appear on the bank statement for the month ended "
     "31 January."),
    ("CB2", "A check that has not cleared", BY_TIMING,
     BANK_SIDE,
     "Check number 94 for $150.00 was written on 20 January, sent to the payee, "
     "and recorded in the books. The bank statement for the month ended "
     "31 January does not show it among the checks paid."),
    ("CB3", "A deposit recorded for the wrong amount", BY_UPDATING,
     BOOKS_SIDE,
     "A deposit of $600.40 made on 8 January was entered in the checkbook and "
     "the books as $594.40. The bank statement shows the deposit at $600.40."),
    ("CB4", "A charge the bank made and nobody entered", BY_UPDATING,
     BOOKS_SIDE,
     "The bank statement for the month ended 31 January shows a service charge "
     "of $10.00. Nothing for it appears in the checkbook or the books."),
)


def draft(cfr: list[tuple[str, str]], pub: list[tuple[str, str]],
          checked: str) -> factory.DeskDraft:
    """The whole proposal, assembled from what was actually read."""
    sources = (
        factory.SourceDraft(
            id="S1",
            title="Treasury Regulation § 1.446-1 — General rule for methods of "
                  "accounting",
            tier="primary", access="public_fetch", may_store="full_text",
            citation_prefix="26 CFR 1.446-1", checked=checked,
            url="https://www.ecfr.gov/current/title-26/section-1.446-1",
            licence="A work of the United States Government, so 17 U.S.C. § 105 "
                    "places it in the public domain and it is storable in full. "
                    "IT DEFERS RATHER THAN DECIDES, and that is why it is here: "
                    "(a)(2) treats a method as clearly reflecting income where it "
                    "applies GAAP “in accordance with accepted conditions or "
                    "practices in that trade or business”, and (a)(4) requires "
                    "the records including “a reconciliation of any differences”. "
                    "The tax law points at the trade's practice and says nothing "
                    "about which side of a reconciliation an item belongs on.",
        ),
        factory.SourceDraft(
            id="S2",
            title="IRS Publication 583 (12/2024) — Starting a Business and "
                  "Keeping Records",
            tier="secondary", access="public_fetch", may_store="full_text",
            citation_prefix="IRS Pub. 583", checked=checked,
            url="https://www.irs.gov/publications/p583",
            licence="A work of the United States Government, so 17 U.S.C. § 105 "
                    "places it in the public domain and it is storable in full. "
                    "SECONDARY, and doubly so. An IRS publication is the "
                    "Service's own plain-language explanation, not authority a "
                    "taxpayer may rely on — and this is a TAX publication about "
                    "an ACCOUNTING convention, so it illustrates the treatment "
                    "without being the thing that settles it. It is stored "
                    "because it is what can be reached, not because it governs: "
                    "the literature that governs is FASB ASC, which is "
                    "human_only, and every other accounting-side source "
                    "(fasab.gov, tfm.fiscal.treasury.gov, ffiec.gov, "
                    "pcaobus.org, gao.gov) is refused by this environment's "
                    "network policy. That gap is why POS1 exists.",
        ),
    )

    problems = tuple(
        factory.ProblemDraft(id=pid, title=title, citation=citation,
                             answer=answer, facts=facts)
        for pid, title, citation, answer, facts in PROBLEMS
    )

    passages = tuple(
        [factory.PassageDraft(citation=c, source_id="S1", checked=checked, text=t)
         for c, t in cfr]
        + [factory.PassageDraft(citation=c, source_id="S2", checked=checked, text=t)
           for c, t in pub]
    )

    return factory.DeskDraft(
        name="cash-and-bank",
        title="When a difference between the books and the bank is a "
              "reconciling item rather than an entry in the books",
        fires_on=(
            "cash", "bank", "bank statement", "reconcile", "reconciled",
            "reconciles", "reconciling", "reconciliation", "outstanding check",
            "outstanding checks", "deposit in transit", "deposits in transit",
            "uncleared", "cleared", "checkbook", "service charge", "bank charge",
            "petty cash", "1.446-1", "446",
        ),
        sources=sources,
        problems=problems,
        passages=passages,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        sys.exit("usage: build_cash_desk.py <446.xml> <p583.html> <repo-root> "
                 "<branch> <YYYY-MM-DD>")
    xml_path, html_path, repo_root, branch, checked = (
        Path(argv[0]), Path(argv[1]), Path(argv[2]), argv[3], argv[4])

    cfr, excluded = cfr_paragraphs(xml_path)
    pub = pub583_sections(html_path)

    # THE DENOMINATOR FIRST, before anything is written. A clean result from a
    # reader that placed a handful of paragraphs and dropped the rest silently
    # is worse than a dirty one.
    print(f"§ 1.446-1: {len(cfr)} paragraph(s) placed, {len(excluded)} left out")
    for e in excluded:
        print(f"  not placed: {e}")
    print(f"Pub. 583: {len(pub)} section(s); the worked reconciliation is the "
          f"answer key and is NOT stored")

    d = draft(cfr, pub, checked)
    out = factory.emit(d, repo_root, branch=branch)
    print(f"\n{len(d.passages)} passage(s), {len(d.problems)} problem(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
