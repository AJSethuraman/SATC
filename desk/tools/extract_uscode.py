"""Slice a section of the United States Code into stored passages.

WHY THIS EXISTS. `extract_ecfr.py` reads the eCFR's XML and cannot read the
House's HTML, and the only thing that ever sliced a statute here was
`build_rewards_desk.py` -- a builder for a desk `dec-kill` deleted, whose SPEC
still writes one file per source into a folder that no longer exists. Its two
readers are what produced §§ 6041, 6041A, 6050W and 6071 (S18-S21), and those
passages tie out to the publisher, so they are REUSED here rather than
rewritten: `html_text` to read the page and `slice_out` to cut it. What is new
is only what those four never needed:

  - A PARAGRAPH IN PIECES. § 274(e) opens "Subsection (a) shall not apply to-",
    lists nine exceptions, and closes with a flush sentence that is (e)'s own:
    "For purposes of this subsection, any item referred to in subsection (a)
    shall be treated as an expense." That sentence belongs to (e), not to
    (e)(9), so (e) is stored as its two pieces joined on `ELLIPSIS` -- the mark
    `comparing.elided_match` already checks in order, segment by segment.
  - THE RECORD'S OWN FORMAT: `Kind: rule` and the 78-column wrap
    `extract_ecfr.py` uses, `break_on_hyphens=False` included, because the
    default wrap stores words the publisher never printed.

NOTHING IS RETYPED. Every character of a passage is sliced out of the fetched
page between two anchors, and an anchor that does not occur exactly as many
times as the SPEC says it does is refused -- an anchor that quietly starts
matching a second place would move a stored passage without a line here
changing. Whitespace is collapsed, which is the one normalisation S18-S21 carry.

HOW THE PAGE WAS FETCHED, over HTTP and never in a browser (27 September 2026):

    curl -sSL --compressed -o usc-274.html \\
      "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section274&num=0&edition=prelim"

Run:  python tools/extract_uscode.py <usc-274.html> <source-id> <YYYY-MM-DD>
      where the date is the day the page was FETCHED -- not today. It prints the
      page's own currency line and the passage blocks; it writes nothing.
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

from build_rewards_desk import html_text, slice_out          # noqa: E402
from comparing import ELLIPSIS                               # noqa: E402

#: `(citation, ((start, end, occurrences), ...))`. More than one piece joins
#: on `ELLIPSIS`. Starts carry their leading newline where the label alone
#: ("(3) Reimbursed expenses") would be too short to trust; `occurrences` is
#: how many times the START appears on the page, counted, not assumed.
S274 = (
    ("26 USC 274(a)", (
        ("(a) Entertainment, amusement, recreation, or qualified transportation fringes",
         "\n(1) In general\nNo deduction otherwise allowable", 1),)),
    ("26 USC 274(a)(1)", (
        ("\n(1) In general\nNo deduction otherwise allowable",
         "\n(2) Special rules\nFor purposes of applying paragraph (1)", 1),)),
    ("26 USC 274(a)(2)", (
        ("\n(2) Special rules\nFor purposes of applying paragraph (1)",
         "\n(3) Denial of deduction for club dues", 1),)),
    ("26 USC 274(a)(3)", (
        ("\n(3) Denial of deduction for club dues",
         "\n(4) Qualified transportation fringes", 1),)),
    ("26 USC 274(a)(4)", (
        ("\n(4) Qualified transportation fringes", "\n(b) Gifts", 1),)),
    ("26 USC 274(e)", (
        ("(e) Specific exceptions to application of subsection (a)",
         "\n(1) Food and beverages for employees", 1),
        ("For purposes of this subsection, any item referred to in subsection (a) "
         "shall be treated as an expense.", "\n(f) ", 1))),
    ("26 USC 274(e)(1)", (
        ("\n(1) Food and beverages for employees",
         "\n(2) Expenses treated as compensation", 1),)),
    ("26 USC 274(e)(2)", (
        ("\n(2) Expenses treated as compensation", "\n(3) Reimbursed expenses", 1),)),
    ("26 USC 274(e)(3)", (
        ("\n(3) Reimbursed expenses",
         "\n(4) Recreational, etc., expenses for employees", 1),)),
    ("26 USC 274(e)(4)", (
        ("\n(4) Recreational, etc., expenses for employees",
         "\n(5) Employees, stockholder, etc., business meetings", 1),)),
    ("26 USC 274(e)(5)", (
        ("\n(5) Employees, stockholder, etc., business meetings",
         "\n(6) Meetings of business leagues, etc.", 1),)),
    ("26 USC 274(e)(6)", (
        ("\n(6) Meetings of business leagues, etc.", "\n(7) Items available to public", 1),)),
    ("26 USC 274(e)(7)", (
        ("\n(7) Items available to public", "\n(8) Entertainment sold to customers", 1),)),
    ("26 USC 274(e)(8)", (
        ("\n(8) Entertainment sold to customers",
         "\n(9) Expenses includible in income of persons who are not employees", 1),)),
    ("26 USC 274(e)(9)", (
        ("\n(9) Expenses includible in income of persons who are not employees",
         "\nFor purposes of this subsection, any item referred to in subsection (a)", 1),)),
    # (o) LIMITS (e)(1), AND ITS DATE IS NOT IN ITS OWN WORDS. Codex on #403:
    # from 2026 no deduction is allowed for meals at an employer-operated
    # eating facility or for § 119 meals, which (e)(1) would otherwise except.
    # (e)(1) stored without (o) would let a 2026 question be answered
    # deductible under an exception that no longer reaches it. The date is in
    # the enacting law, which the page prints among its notes; that one
    # sentence is stored too, sliced the same way.
    # (o)'s OWN EXCEPTION. (o) denies "other than expenses described in
    # subsection (e)(8) or (n)(2)(C)", and Codex on #403 found (n)(2)(C) was
    # not on file: the crew, offshore-platform and fish-processing meals. (n)(2)
    # closes on a flush sentence that narrows (C)'s first two clauses, so (n)(2)
    # is stored as its lead-in and that sentence, joined on the omission mark,
    # exactly as (e) is.
    ("26 USC 274(n)(2)", (
        ("\n(2) Exceptions\nParagraph (1) shall not apply to any expense if-",
         "\n(A) such expense is described in paragraph (2), (3), (4), (7), (8), or (9)", 1),
        ("Clauses (i) and (ii) of subparagraph (C) shall not apply to vessels",
         "\n(3) Special rule for individuals subject to Federal hours of service", 1))),
    ("26 USC 274(n)(2)(C)", (
        ("\n(C) such expense is for food or beverages-", "\n(D) such expense is-", 1),)),
    ("26 USC 274(o)", (
        ("\n(o) Meals provided at convenience of employer",
         "\n(1) any expense for the operation of a facility described in section 132(e)(2)", 1),)),
    ("26 USC 274(o)(1)", (
        ("\n(1) any expense for the operation of a facility described in section 132(e)(2)",
         "\n(2) any expense for meals described in section 119(a).", 1),)),
    ("26 USC 274(o)(2)", (
        ("\n(2) any expense for meals described in section 119(a).",
         "\n(p) Regulatory authority", 1),)),
    ("26 USC 274 note, Pub. L. 115-97 § 13304(e)(2)", (
        ("Effective date for elimination of deduction for meals provided at convenience of employer",
         '"\nPub. L. 115–97,\n title I, §13310(b)', 1),)),
)

#: The enacting-law sentence that dates § 274(o).
O_DATE = "26 USC 274 note, Pub. L. 115-97 § 13304(e)(2)"

#: The page's own statement of how current it is, read off the page.
_CURRENCY = re.compile(r"Text contains those laws in effect on [A-Z][a-z]+ \d{1,2}, \d{4}")


def currency(text: str) -> str:
    """The currency line, exactly once, or a refusal -- never a guessed date."""
    hits = _CURRENCY.findall(text)
    if len(hits) != 1:
        raise ValueError(f"the page states its currency {len(hits)} times, not once")
    return hits[0]


def sliced(text: str, spec=S274, stem: str = "usc") -> list[tuple[str, str]]:
    """`(citation, words)` for every row of `spec`, cut from `text`."""
    out = []
    for citation, pieces in spec:
        words = f" {ELLIPSIS} ".join(
            slice_out(text, stem, start, end, 1, occurrences)
            for start, end, occurrences in pieces)
        out.append((citation, words))
    return out


def blocks(text: str, source_id: str, checked: str, spec=S274) -> list[str]:
    """The passage blocks, in the record's format. Pure: writes nothing."""
    wrap = lambda t: "\n".join(textwrap.wrap(t, 78, initial_indent="> ",
                                             subsequent_indent="> ",
                                             break_on_hyphens=False))
    return [f"## {citation}\n\n"
            f"**Source:** {source_id} · **Checked:** {checked} · **Kind:** rule\n\n"
            f"{wrap(words)}\n"
            for citation, words in sliced(text, spec)]


if __name__ == "__main__":                                  # pragma: no cover
    if len(sys.argv) != 4:
        sys.exit(__doc__.strip().splitlines()[-3].strip())
    page, sid, checked = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
        sys.exit("the date is the day the page was FETCHED, YYYY-MM-DD")
    text = html_text(page)
    print(currency(text), file=sys.stderr)
    print("\n".join(blocks(text, sid, checked)), end="")
