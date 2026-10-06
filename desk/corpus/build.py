"""Emit this desk's `extracted/` and `PROBLEMS.md` from the fetched documents.

Nothing here retypes authority. Every quoted string is sliced out of a file in
`build-fixtures/`, so a transcription error is impossible rather than unlikely,
and anybody can re-run it offline and diff the result against what is committed.

`build-fixtures/` holds exactly what came back on 2026-09-05:

    s1.xml    curl -sS --compressed -G -o s1.xml \
                "https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/title-26.xml" \
                --data-urlencode part=1 --data-urlencode "section=1.263(a)-1"
    s2.xml    the same, with section=1.162-3
    tpr.html  curl -sS --compressed -o tpr.html \
                "https://www.irs.gov/businesses/small-businesses-self-employed/tangible-property-final-regulations"

The eCFR API returns HTTP 406 without --compressed, and a future date 404s;
2026-01-01 is the issue that was actually served. `tpr.html` printed
"Page Last Reviewed or Updated: 04-Aug-2026", which is the revision recorded in
SOURCES.md -- read off the page, never assumed.

Run: python build.py    (from this directory; it rewrites extracted/ and
PROBLEMS.md in place and touches nothing else. SOURCES.md, SUBJECTS.md and
positions/ are hand-written and are NOT generated -- judgement is not emitted.)
"""
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent / "build-fixtures"
DESK = Path(__file__).resolve().parent
CHECKED = "2026-09-05"


def paragraphs(xml_path):
    x = Path(xml_path).read_text(encoding="utf-8")
    x = re.sub(r'<I>|</I>|<E T="[^"]*">|</E>', "", x)
    return [" ".join(html.unescape(re.sub(r"<[^>]+>", "", p)).split())
            for p in re.findall(r"<P>(.*?)</P>", x, re.S)]


def examples(xml_path):
    """`{title: body}` — the <HED> and the <PSPACE> kept apart on purpose.

    The heading announces what the example is about ("Unit of property that
    costs $200 or less"), which is half the answer. It never reaches Facts.
    """
    x = Path(xml_path).read_text(encoding="utf-8")
    x = re.sub(r'<I>|</I>|<E T="[^"]*">|</E>', "", x)
    out = {}
    for m in re.finditer(r"<EXAMPLE>(.*?)</EXAMPLE>", x, re.S):
        blk = m.group(1)
        hed = re.search(r"<HED>(.*?)</HED>", blk, re.S)
        body = re.sub(r"<HED>.*?</HED>", "", blk, flags=re.S)
        title = " ".join(html.unescape(re.sub(r"<[^>]+>", "", hed.group(1))).split())
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", body)).split())
        out[title] = text
    return out


def irs_lines(path):
    x = Path(path).read_text(encoding="utf-8")
    x = re.sub(r"(?s)<(script|style).*?</\1>", "", x)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", x))
    return [" ".join(l.split()) for l in t.splitlines() if l.strip()]


S1 = paragraphs(HERE / "s1.xml")
S2 = paragraphs(HERE / "s2.xml")
S1EX = examples(HERE / "s1.xml")
S2EX = examples(HERE / "s2.xml")
IRS = irs_lines(HERE / "tpr.html")


def irs(fragment):
    hits = [l for l in IRS if fragment in l]
    assert len(hits) == 1, (fragment, len(hits))
    return hits[0]


# ── extracted/S1.md — 26 CFR 1.263(a)-1 ───────────────────────────────────────

S1_PASSAGES = [
    ("26 CFR 1.263(a)-1(a)", S1[0]),
    ("26 CFR 1.263(a)-1(a)(1)", S1[1]),
    ("26 CFR 1.263(a)-1(a)(2)", S1[2]),
    ("26 CFR 1.263(a)-1(f)(1)", S1[18]),
    ("26 CFR 1.263(a)-1(f)(1)(i)", S1[19]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(A)", S1[20]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(B)", S1[21]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(B)(1)", S1[22]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(B)(2)", S1[23]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(C)", S1[24]),
    ("26 CFR 1.263(a)-1(f)(1)(i)(D)", S1[25]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)", S1[26]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(A)", S1[27]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(B)", S1[28]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(B)(1)", S1[29]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(B)(2)", S1[30]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(C)", S1[31]),
    ("26 CFR 1.263(a)-1(f)(1)(ii)(D)", S1[32]),
    ("26 CFR 1.263(a)-1(f)(1)(iii)", S1[33]),
    ("26 CFR 1.263(a)-1(f)(2)", S1[34]),
    ("26 CFR 1.263(a)-1(f)(2)(i)", S1[35]),
    ("26 CFR 1.263(a)-1(f)(2)(ii)", S1[36]),
    ("26 CFR 1.263(a)-1(f)(2)(iii)", S1[37]),
    ("26 CFR 1.263(a)-1(f)(2)(iv)", S1[38]),
    ("26 CFR 1.263(a)-1(f)(3)(i)", S1[39]),
    ("26 CFR 1.263(a)-1(f)(3)(ii)", S1[40]),
    ("26 CFR 1.263(a)-1(f)(3)(iii)", S1[41]),
    ("26 CFR 1.263(a)-1(f)(3)(iv)", S1[42]),
    ("26 CFR 1.263(a)-1(f)(3)(v)", S1[43]),
    ("26 CFR 1.263(a)-1(f)(3)(vi)", S1[44]),
    ("26 CFR 1.263(a)-1(f)(3)(vii)", S1[45]),
    ("26 CFR 1.263(a)-1(f)(4)", S1[46]),
    ("26 CFR 1.263(a)-1(f)(5)", S1[53]),
    ("26 CFR 1.263(a)-1(f)(6)", S1[54]),
    ("26 CFR 1.263(a)-1(f)(6)(i)", S1[55]),
    ("26 CFR 1.263(a)-1(f)(6)(ii)", S1[56]),
]

S2_PASSAGES = [
    ("26 CFR 1.162-3(a)(1)", S2[0]),
    ("26 CFR 1.162-3(a)(2)", S2[1]),
    ("26 CFR 1.162-3(a)(3)", S2[2]),
    ("26 CFR 1.162-3(c)(1)", S2[4]),
    ("26 CFR 1.162-3(c)(1)(i)", S2[5]),
    ("26 CFR 1.162-3(c)(1)(ii)", S2[6]),
    ("26 CFR 1.162-3(c)(1)(iii)", S2[7]),
    ("26 CFR 1.162-3(c)(1)(iv)", S2[8]),
    ("26 CFR 1.162-3(c)(1)(v)", S2[9]),
    ("26 CFR 1.162-3(c)(2)", S2[10]),
    ("26 CFR 1.162-3(d)(1)", S2[34]),
    ("26 CFR 1.162-3(f)", S2[48]),
    ("26 CFR 1.162-3(g)", S2[49]),
]

S3_PASSAGES = [
    # THE ONE PASSAGE THAT IS NOT A SINGLE SLICE, said here rather than left to
    # be noticed: the page breaks this sentence around an inline link to the
    # notice, so the text extractor yields it as four fragments. They are
    # rejoined in the page's own order, with the link's own words in place and
    # its "PDF" affordance dropped. Nothing is added.
    ('IRS Tangible Property Final Regulations, "A de minimis safe harbor '
     'election" — Note on Notice 2015-82 (sentence rejoined across the page\'s '
     'inline link)',
     " ".join([
         irs("Effective for taxable years beginning on or after Jan. 1, 2016"),
         "Notice 2015-82",
         irs("increased the de minimis safe harbor threshold from $500 to $2500"),
     ])),
    ('IRS Tangible Property Final Regulations, "What is the de minimis safe '
     'harbor election?"',
     irs("you may use the safe harbor to deduct amounts up to $2,500")),
    ('IRS Tangible Property Final Regulations, "If you use the de minimis safe '
     'harbor, do you have to capitalize all expenses that exceed the '
     'limitations?"',
     irs("aren't subject to the de minimis safe harbor election")),
    ('IRS Tangible Property Final Regulations, "If you don\'t have an AFS, are '
     'you required to have a written accounting procedure at the beginning of '
     'your taxable year?"',
     irs("you are not required to have written accounting procedures")),
    ('IRS Tangible Property Final Regulations, "What if your book policy '
     'exceeds the de minimis safe harbor ceiling?"',
     irs("as long as you can show that your reporting policy clearly reflects")),
    ('IRS Tangible Property Final Regulations, "How do you elect to use the de '
     'minimis safe harbor?"',
     irs('You should attach a statement titled "Section 1.263(a)-1(f) de '
         'minimis safe harbor election"')),
    ('IRS Tangible Property Final Regulations, "How does the de minimis safe '
     'harbor affect the deductions you typically take for materials and '
     'supplies or repairs and maintenance?"',
     irs("materials and supplies that also qualify under your de minimis safe")),
    ('IRS Tangible Property Final Regulations, "When can you deduct the costs '
     'of materials and supplies?" — non-incidental',
     irs("If the materials and supplies are not incidental, then you deduct")),
    ('IRS Tangible Property Final Regulations, "When can you deduct the costs '
     'of materials and supplies?" — incidental',
     irs("If the materials and supplies are incidental, i.e., of minor")),
]

EXTRACT_PREAMBLE = """# Authority — someone else's words, checkable line by line

Every line here is verbatim from the document named on it, fetched on the
`Checked` date, and sliced out of the fetched file in `build-fixtures/` by
`build.py` in this directory rather than retyped — so a transcription error is
impossible rather than unlikely, and re-running the script reproduces this file
byte for byte. **Judgement does not live here.** What the firm decided goes in
`positions/`, where the diff is read; `guards.no_positions_in_extracted` fails
the build rather than trusting anyone to notice a position that rode along
inside an extraction.

---

"""


def emit_extract(path, passages, source_id):
    out = [EXTRACT_PREAMBLE]
    for citation, text in passages:
        assert text.strip(), citation
        out.append(f"## {citation}\n\n"
                   f"**Source:** {source_id} · **Checked:** {CHECKED}\n\n"
                   f"> {text}\n\n")
    Path(path).write_text("".join(out), encoding="utf-8")


# ── PROBLEMS.md ───────────────────────────────────────────────────────────────

APPLIES = "the de minimis safe harbor applies; the amount is not capitalized"
NO_APPLY = "the de minimis safe harbor does not apply to the amount"
IS_MS = "a material or supply, deductible in the taxable year first used or consumed"
NOT_MS = "not a material or supply; treated under §§ 1.263(a)-2 and 1.263(a)-3"


def facts(store, title, cut):
    body = store[title]
    i = body.find(cut)
    assert i > 0, (title, cut)
    return body[:i].strip()


PROBLEMS = [
    # ── § 1.263(a)-1(f)(7), the de minimis safe harbour's own examples ────────
    ("CD1", "Ten printers at $250, no financial statement",
     "26 CFR 1.263(a)-1(f)(1)(ii)", APPLIES,
     facts(S1EX, "Example 1. De minimis safe harbor; taxpayer without AFS.",
           "The amounts paid for the printers meet the requirements"),
     "§ 1.263(a)-1(f)(7) Example 1 — the withheld sentences read: “The amounts "
     "paid for the printers meet the requirements for the de minimis safe "
     "harbor under paragraph (f)(1)(ii) of this section. … A may not capitalize "
     "the amounts paid for the 10 printers.”"),

    ("CD2", "Ten computers at $600, no financial statement",
     "26 CFR 1.263(a)-1(f)(1)(ii)", NO_APPLY,
     facts(S1EX, "Example 2. De minimis safe harbor; taxpayer without AFS.",
           "The amounts paid for the printers do not meet"),
     "§ 1.263(a)-1(f)(7) Example 2 — “The amounts paid for the printers do not "
     "meet the requirements for the de minimis safe harbor under paragraph "
     "(f)(1)(ii) of this section because the amount paid for the property "
     "exceeds $500 per invoice … B may not apply the de minimis safe harbor "
     "election.” (The regulation says “printers” where its own facts say "
     "computers; quoted as written.)"),

    ("CD3", "1,250 computers at $5,000 each, group financial statement",
     "26 CFR 1.263(a)-1(f)(1)(i)", APPLIES,
     facts(S1EX, "Example 3. De minimis safe harbor; taxpayer with AFS.",
           "The amounts paid for the computers meet the requirements"),
     "§ 1.263(a)-1(f)(7) Example 3 — “The amounts paid for the computers meet "
     "the requirements for the de minimis safe harbor under paragraph (f)(1)(i) "
     "of this section. … C may not capitalize the amounts paid for the 1,250 "
     "computers.”"),

    ("CD4", "800 machines at $6,000 each against a $15,000 book policy",
     "26 CFR 1.263(a)-1(f)(1)", NO_APPLY,
     facts(S1EX, "Example 4. De minimis safe harbor; taxpayer with AFS.",
           "D may not apply the de minimis safe harbor election"),
     "§ 1.263(a)-1(f)(7) Example 4 — “D may not apply the de minimis safe "
     "harbor election to the amounts paid for the 800 elliptical machines under "
     "paragraph (f)(1) of this section because the amount paid for the property "
     "exceeds $5,000 per invoice (or per item as substantiated by the "
     "invoice).”"),

    ("CD5", "Routers whose delivery and installation are on the same invoice",
     "26 CFR 1.263(a)-1(f)(1)(i)", APPLIES,
     facts(S1EX, "Example 5. De minimis safe harbor; additional invoice costs.",
           "The amounts paid for each router, including the allocable"),
     "§ 1.263(a)-1(f)(7) Example 5 — “The amounts paid for each router, "
     "including the allocable additional invoice costs, meet the requirements "
     "for the de minimis safe harbor under paragraph (f)(1)(i) of this "
     "section.”"),

    ("CD6", "Devices and tablets with a useful life of twelve months or less",
     "26 CFR 1.263(a)-1(f)(1)(ii)", APPLIES,
     facts(S1EX, "Example 7. De minimis safe harbor; 12-month economic useful life.",
           "The amounts paid for the hand-held devices and the tablet computers "
           "meet the requirements"),
     "§ 1.263(a)-1(f)(7) Example 7 — “The amounts paid for the hand-held "
     "devices and the tablet computers meet the requirements for the de minimis "
     "safe harbor under paragraph (f)(1)(ii) of this section.”"),

    ("CD7", "Computers, chairs and briefcases expensed on a $5,000 policy",
     "26 CFR 1.263(a)-1(f)(1)(i)", APPLIES,
     facts(S1EX, "Example 9. De minimis safe harbor; materials and supplies.",
           "The amounts paid for computers, office chairs, and briefcases meet"),
     "§ 1.263(a)-1(f)(7) Example 9 — “The amounts paid for computers, office "
     "chairs, and briefcases meet the requirements for the de minimis safe "
     "harbor under paragraph (f)(1)(i) of this section.”"),

    ("CD8", "A used truck invoiced in four parts",
     "26 CFR 1.263(a)-1(f)(6)", NO_APPLY,
     facts(S1EX, "Example 11. De minimis safe harbor; anti-abuse rule.",
           "Under paragraph (f)(6) of this section, K has applied"),
     "§ 1.263(a)-1(f)(7) Example 11 — “Under paragraph (f)(6) of this section, "
     "K has applied the de minimis rule to amounts substantiated with invoices "
     "created to componentize property … As a result, K may not apply the de "
     "minimis rule to these amounts and is subject to appropriate "
     "adjustments.”"),

    # ── § 1.162-3(h), materials and supplies ─────────────────────────────────
    ("MS1", "Spare parts bought in one year and used to repair in the next",
     "26 CFR 1.162-3(c)(1)(i)", IS_MS,
     facts(S2EX, "Example 1 Non-rotable components.",
           "These parts are materials and supplies under paragraph (c)(1)(i)"),
     "§ 1.162-3(h) Example 1 — “These parts are materials and supplies under "
     "paragraph (c)(1)(i) of this section … the amounts that A paid for the "
     "spare parts in Year 1 are deductible in Year 2, the taxable year in which "
     "the spare parts are first used to repair and maintain the aircraft.”"),

    ("MS2", "Engines bought as part of the aircraft and later removed",
     "26 CFR 1.162-3(c)(1)(i)", NOT_MS,
     facts(S2EX, "Example 4 Rotable part acquired as part of a single unit of "
                 "property; not material or supply.",
           "Because the engines were acquired as part of the aircraft"),
     "§ 1.162-3(h) Example 4 — “Because the engines were acquired as part of "
     "the aircraft, a single unit of property, the engines are not materials or "
     "supplies under paragraph (c)(1)(i) of this section … Rather, D must apply "
     "the rules under §§ 1.263(a)-2 and 1.263(a)-3.”"),

    ("MS3", "A two-year supply of fuel bought on the last day of the year",
     "26 CFR 1.162-3(c)(1)(ii)", IS_MS,
     facts(S2EX, "Example 5 Consumable property.",
           "The jet fuel that E purchased in Year 1 is a material or supply"),
     "§ 1.162-3(h) Example 5 — “The jet fuel that E purchased in Year 1 is a "
     "material or supply under paragraph (c)(1)(ii) of this section … E may "
     "deduct in Year 2 the amounts paid for the portion of jet fuel used.”"),

    ("MS4", "Small rental items bought in one year and put into service the next",
     "26 CFR 1.162-3(c)(1)(iv)", IS_MS,
     facts(S2EX, "Example 6 Unit of property that costs $200 or less.",
           "The rental items are materials and supplies under paragraph "
           "(c)(1)(iv)"),
     "§ 1.162-3(h) Example 6 — “The rental items are materials and supplies "
     "under paragraph (c)(1)(iv) of this section … the amounts that F paid for "
     "the rental items in Year 1 are deductible in Year 2, the taxable year in "
     "which the rental items are first used in F's business.”"),

    ("MS5", "One box costing more than $200 holding ten items that do not",
     "26 CFR 1.162-3(c)(1)(iv)", IS_MS,
     facts(S2EX, "Example 9 Unit of property that costs $200 or less; bulk "
                 "purchase.",
           "The toner cartridges are materials and supplies under paragraph "
           "(c)(1)(iv)"),
     "§ 1.162-3(h) Example 9 — “The toner cartridges are materials and supplies "
     "under paragraph (c)(1)(iv) of this section because even though purchased "
     "in one box costing more than $200, the allocable cost of each unit of "
     "property equals $50. Therefore … deductible in Year 1, the taxable year "
     "in which H first uses each of those cartridges.”"),
]

# The three rows below rest on the IRS's own explanation, which is SECONDARY.
# `_check` refuses `authority_permits_choice` before any conclusion is compared,
# so these can only ever grade `escalated` — never `correct`. They are here
# because they are the only rows that exercise the escalation half of the
# design at all, and they are labelled so nobody reads them as answered.
IRS_PROBLEMS = [
    ("TP1", "A purchase over the ceiling, by a taxpayer who elected the harbor",
     'IRS Tangible Property Final Regulations, "If you use the de minimis safe '
     'harbor, do you have to capitalize all expenses that exceed the '
     'limitations?"',
     "no; an amount over the threshold is treated under the normal rules and "
     "may still be currently deductible",
     "A taxpayer without an applicable financial statement elected the de "
     "minimis safe harbor for the year. One amount paid to acquire tangible "
     "property is above the $2,500 threshold. Everything else about the "
     "purchase is ordinary. Must that amount be capitalized because it is over "
     "the threshold?",
     "Read off the answer the IRS gives under that heading: “No. Amounts paid "
     "for the acquisition or production of tangible property that exceed the "
     "safe harbor limitations aren't subject to the de minimis safe harbor "
     "election. … If an amount doesn't qualify under the de minimis safe "
     "harbor, you should treat the amount under the normal rules that apply, "
     "i.e., currently deductible if paid for incidental materials and supplies "
     "or for repair and maintenance.”"),

    ("TP2", "Whether the book policy has to be in writing without a financial statement",
     'IRS Tangible Property Final Regulations, "If you don\'t have an AFS, are '
     'you required to have a written accounting procedure at the beginning of '
     'your taxable year?"',
     "no written procedure is required without an AFS, but a consistent policy "
     "must exist at the beginning of the taxable year",
     "A business with no applicable financial statement wants to use the "
     "$2,500 de minimis threshold for the coming year. It has never written its "
     "expensing policy down. Does the threshold require a written accounting "
     "procedure?",
     "Read off the answer the IRS gives under that heading: “If you don't have "
     "an AFS, you are not required to have written accounting procedures; "
     "however, you must expense amounts on your books and records for the "
     "taxable year in accordance with a consistent accounting procedure or "
     "policy existing at the beginning of the taxable year. If you have AFS, "
     "you must have the accounting procedures in writing.”"),

    ("TP3", "A book policy set above the ceiling",
     'IRS Tangible Property Final Regulations, "What if your book policy '
     'exceeds the de minimis safe harbor ceiling?"',
     "the amounts may still be deducted for federal tax purposes if the "
     "reporting policy clearly reflects income",
     "A business with no applicable financial statement has a book policy of "
     "expensing anything under $4,000 — above the $2,500 threshold. It wants to "
     "know what happens to the amounts between the two figures.",
     "Read off the answer the IRS gives under that heading: “If you don't have "
     "an AFS and have a policy for your books and records of deducting amounts "
     "more than $2,500 ($500 prior to Jan. 1, 2016), you may properly deduct "
     "these amounts for federal tax purposes, as long as you can show that your "
     "reporting policy clearly reflects your income.”"),
]

PROBLEMS_PREAMBLE = """# Problems — the denominator

**The answers are not ours.** Every row's conclusion is read off the authority's
own worked example or the publication's own answer, and `Answer read from` names
where, quoting the sentence that decided it. A score against answers we wrote
would measure agreement, not correctness.

**The conclusion is withheld from the facts.** `Facts` is the regulation's
example verbatim, cut at the first sentence in which the regulation announces
its outcome — and the example's own HEADING is dropped, because "Unit of
property that costs $200 or less" is half the answer.

**Two rules, stated before the rows so they are not chosen row by row.**

1. On § 1.263(a)-1 the **citation** is the paragraph the regulation's withheld
   analysis names for the safe harbour result, and the **answer** is whether the
   safe harbour applies. Note that CD1 and CD2 share one citation with opposite
   answers, as do CD3/CD5/CD7 against CD4 — a desk cannot get these by mapping
   a citation to a conclusion.
2. On § 1.162-3 the **citation** is the definitional paragraph the analysis
   names as deciding whether the property is a material or supply, and the
   **answer** is the treatment the regulation states. MS1 and MS2 share
   (c)(1)(i) with opposite answers.

## What was left out, and why

| Example | Why it is not a problem |
|---|---|
| § 1.263(a)-1(f)(7) Example 6 | States two outcomes — the furniture qualifies AND the designer's fee need not be capitalised. Nothing reduces to one scorable conclusion. |
| § 1.263(a)-1(f)(7) Example 8 | Its facts are "Assume the facts as in Example 7", so they are not self-contained; and its analysis names two paragraphs, neither containing the other. |
| § 1.263(a)-1(f)(7) Example 10 | Concludes only that amounts "may be subject to capitalization under section 263A" — a conditional, not a conclusion. |
| § 1.162-3(h) Examples 2, 3 | Turn on the optional method for rotable parts, which this desk does not store. |
| § 1.162-3(h) Examples 7, 8 | Example 8's facts are "the same facts as in Example 7"; Example 7 alone repeats Example 6's conclusion on the same paragraph. |
| § 1.162-3(h) Examples 11, 12 | Both end in "may be subject to capitalization under section 263A" — conditional. |
| § 1.162-3(h) Example 13 | States two outcomes: deductible on disposal, or capitalised if the taxpayer elects. |
| § 1.162-3(h) Example 14 | Three outcomes across two classes of property, one of them conditional on an election. |

## The three rows that can only ever escalate

`TP1`, `TP2` and `TP3` rest on an IRS explanation, which is **secondary**.
`engine._check` refuses `authority_permits_choice` before any conclusion is
compared, so these rows grade `escalated` whatever is answered — they can never
grade `correct`. They are here because they are the only rows on this desk that
exercise the escalation half of the design at all. Read them as a test of the
tier gate, not as questions the desk answers. **Their FACTS are this session's,
not the IRS's** — the page poses each as a question rather than as a worked
example, so the fact pattern is a restatement of the IRS's own question and only
the CONCLUSION is read off the page. That is exactly the shape the other thirteen
rows avoid, and it is survivable only because the tier gate stops these rows
before any conclusion is compared. If the firm ratifies POS2 and these rows begin
to grade against a position, they need real fact patterns first or they must
go. If the firm ratifies POS2, the
position outranks the passage and TP-row grading changes shape; that is the
mechanism working, and it is why the proposal exists.

---

"""


def emit_problems(path):
    out = [PROBLEMS_PREAMBLE]
    for pid, title, citation, answer, fact, read_from in PROBLEMS + IRS_PROBLEMS:
        out.append(
            f"## {pid} · {title}\n\n"
            f"**Citation:** {citation}\n\n"
            f"**Answer:** {answer}\n\n"
            f"**Facts:** {fact}\n\n"
            f"**Answer read from:** {read_from}\n\n"
            f"---\n\n"
        )
    Path(path).write_text("".join(out), encoding="utf-8")


if __name__ == "__main__":
    (DESK / "extracted").mkdir(parents=True, exist_ok=True)
    (DESK / "positions").mkdir(parents=True, exist_ok=True)
    emit_extract(DESK / "extracted" / "S1.md", S1_PASSAGES, "S1")
    emit_extract(DESK / "extracted" / "S2.md", S2_PASSAGES, "S2")
    emit_extract(DESK / "extracted" / "S3.md", S3_PASSAGES, "S3")
    emit_problems(DESK / "PROBLEMS.md")
    print("passages:", len(S1_PASSAGES) + len(S2_PASSAGES) + len(S3_PASSAGES))
    print("problems:", len(PROBLEMS) + len(IRS_PROBLEMS))
