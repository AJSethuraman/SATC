"""The covering document: no figure it states about itself may be typed.

WHAT THIS IS FOR. Every wrong number three audit passes found in the delivered
feed had one shape: **a count that was true when somebody typed it, and was not
re-derived when the thing it counted changed.** Three of them, in the document
this guards:

  * *"Eight of the 87 fields"* -- there are 105, and ten of them.
  * a roster line printing `0` because the wording it searched for had been
    improved and the search had not, leaving the roster 114 short of the
    headline printed above it.
  * *"the 1,520 capital-ratio rows"*, *"all 22 of those"*, *"ten years"* --
    each right on the day, each one field away from being wrong.

The builder's own opening docstring already said none of its numbers is typed.
That was the line it did not follow, and a docstring is not a test.

HOW IT WORKS, and what it deliberately does not do. It reads every string
literal in the builder with `ast`, pulls every number out of them, and refuses
any that equals a quantity computed from the delivered files. It does NOT ban
numbers: 2016, 0.005 and 90 days are not counts of anything in the corpus, and
a test that banned them would be turned off within a week. It bans the numbers
that WILL go stale, which is the set that can be computed.

WHY THE ALLOWLIST IS NOT A LOOPHOLE. Two kinds of figure survive it, and both
are named one by one below with a reason: a count of something that happened in
the past and cannot be recomputed from today's data ("nineteen fields were
shipping with no units"), and the two figures read off the filed form by hand,
which the builder itself lists in `HAND_READ` and the document says out loud.
Anything else has to be computed or it does not ship.
"""
from __future__ import annotations

import ast
import csv
import pathlib
import re

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools" / "tieout"
BUILDER = TOOLS / "build_covering_document.py"
DATA = pathlib.Path(__file__).resolve().parents[1] / "verified-data"


def _rows(name):
    with (DATA / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def corpus():
    """Every quantity the document states about itself, computed here.

    Computed independently of the builder on purpose: importing the builder to
    get its own numbers and then checking it against them proves nothing, which
    is the mirror problem the tie-out skill is written about.
    """
    bank = _rows("bank-values.csv")
    macro = _rows("macro-observations.csv")
    fields = _rows("field-dictionary.csv")
    mergers = _rows("not-comparable-periods.csv")
    tied = sum(1 for r in bank if r["verified"] == "yes")
    tied += sum(1 for r in macro if r["verified"] == "yes")
    counts = {
        "bank values": len(bank),
        "macro observations": len(macro),
        "values delivered": len(bank) + len(macro),
        "values tied": tied,
        "bank fields": len(fields),
        "banks": len({r["cert"] for r in bank}),
        "quarters": len({r["report_date"] for r in bank}),
        "macro series": len({r["series_id"] for r in macro}),
        "merger quarters": len(mergers),
        "macro unsourced": sum(1 for r in macro if r["verified"] != "yes"),
        "capital ratio rows": sum(1 for r in bank
                                  if r["field"] in ("RBCRWAJ", "RBC1AAJ")),
        "FDIC-computed values": sum(1 for r in bank
                                    if "FDIC calculates" in r["verified_meaning"]),
        "paywalled series": len({r["series_id"] for r in macro
                                 if r["verified"] != "yes"
                                 and "S&P" in r["why_not_verified"]}),
    }
    # The FDIC ratios recomputed from their own checked parts. The document
    # states this figure; it was typed as "2,964 of 2,964" and that pair was
    # correct, which is exactly the state a count is in the day before it
    # stops being correct.
    import sys
    sys.path.insert(0, str(TOOLS))
    import check_fdic_ratios
    results = check_fdic_ratios.recompute()
    counts["FDIC ratios recomputed"] = sum(r["agree"] + r["differ"]
                                           for r in results.values())
    for label, probe in (("differs", "DOES NOT MATCH"),
                         ("merger rows", "spans a merger"),
                         ("base moved rows", "running total"),
                         ("not on that filing rows", "does not carry the line")):
        counts[label] = sum(1 for r in bank if probe in r["verified_meaning"])
    return counts


# --------------------------------------------------------------------------
# What may stay, each with the reason it is not a live count
# --------------------------------------------------------------------------
# A figure survives this test only by being listed here. The two kinds:
#
#   * a HISTORICAL finding -- how many things were wrong on a particular day.
#     It cannot be recomputed from data that has since been fixed, and the
#     sentence is about the past, not about the feed as it stands.
#   * a HAND-READ figure -- something printed on the filed form that this feed
#     carries no field for. The builder keeps both in `HAND_READ` and the
#     document tells the reader which they are.
ALLOWED = {
    "Nine values": "how many citations were wrong in September 2026; a past "
                   "event, and the citations have been fixed since",
    "sixteen quarters": "what a first pass had seen before the merger list "
                        "was widened; a past state of the code",
    "Nineteen fields": "how many fields shipped with no units, once; fixed, "
                       "and therefore not recomputable",
    "seven banks": "how many exhibits rendered with no pictures in them, "
                   "once; the builder refuses that now",
    "206904227": "the filing's own printed risk-weighted assets, read off the "
                 "form -- this feed has no such field. In HAND_READ.",
    "10.235700": "the leverage ratio as the filing prints it, read off the "
                 "form -- that row agrees, so no filed figure is recorded "
                 "beside it. In HAND_READ.",
}

#: Spelled-out counts are as stale-able as digits and harder to grep for. Any
#: of these words immediately before a countable noun has to come from `w()`.
#: One, two and three are left out for the same reason the digit scan ignores
#: anything under ten: "a quarter that mixes two banks" is English, not a
#: count, and a check that fires on it is a check somebody turns off.
_WORD = (r"\b(four|five|six|seven|eight|nine|ten|eleven|twelve|"
         r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
         r"twenty|thirty|forty|fifty)\b")
#: The noun may have another number in front of it -- "eight of the 87 fields"
#: is the sentence this whole file exists for, and a pattern that stopped at
#: "of the" would have walked straight past it.
_NOUN = (r"(?:of the\s+)?(?:[\d,]+\s+)?(fields?|banks?|quarters?|years?|"
         r"series|ratios?|values?|rows?|observations?|exhibits?)")
SPELLED = re.compile(_WORD + r"\s+" + _NOUN, re.I)


def literals(path: pathlib.Path):
    """Every string constant in the module, minus the docstrings.

    Docstrings are left out because they are the file explaining ITSELF to the
    next reader -- including, deliberately, quoting the stale numbers this test
    exists to stop. A docstring is not published to anybody.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc_nodes.add(id(body[0].value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in doc_nodes):
            yield node.lineno, node.value


def test_the_builder_has_string_literals_to_scan():
    """The denominator. A scan that found nothing would pass silently."""
    found = list(literals(BUILDER))
    assert len(found) > 100, "only %d literals -- did the parse work?" % len(found)


def test_no_corpus_count_is_typed_into_the_builder(corpus):
    """Every figure the document states about the feed is computed from it.

    This is the test the brief asked for, and it went red before it went green:
    on 19 September 2026 it caught `87` and `2,964` typed into the paragraph
    about FDIC-computed ratios, `1,520` in the paragraph about capital ratios,
    and `22` in the one about Case-Shiller.
    """
    forbidden = {}
    for what, value in corpus.items():
        if value < 10:
            continue          # 2 and 8 collide with dates, versions and prose
        forbidden["{:,}".format(value)] = what
        forbidden[str(value)] = what

    bad = []
    for line, text in literals(BUILDER):
        for token in re.findall(r"\d[\d,]*\d|\d", text):
            what = forbidden.get(token)
            if what and token not in ALLOWED:
                bad.append("line %d: %r is the %s, typed. Compute it."
                           % (line, token, what))
    assert not bad, "\n".join(bad)


def test_no_spelled_out_count_is_typed_where_a_figure_belongs(corpus):
    """`"eight of the 87 fields"` fails both halves of this file. The digits
    are caught above; the word is caught here, because a count spelled out is
    exactly as stale-able and much harder to find."""
    bad = []
    for line, text in literals(BUILDER):
        for hit in SPELLED.finditer(text):
            phrase = hit.group(0)
            if any(phrase.lower().startswith(ok.lower()) for ok in ALLOWED):
                continue
            bad.append("line %d: %r is a count written as a word. Put it "
                       "through w() so it is computed." % (line, phrase))
    assert not bad, "\n".join(bad)


def test_every_allowance_says_why_it_is_allowed():
    """An allowlist whose entries carry no reason becomes a list of things
    somebody could not be bothered to fix."""
    for phrase, why in ALLOWED.items():
        assert len(why) > 30, "%r is allowed for no stated reason" % phrase


def test_the_hand_read_figures_are_exactly_the_ones_allowed():
    """The builder names the figures it did not compute. This asserts that
    list has not grown quietly: two, and both are in ALLOWED above."""
    source = BUILDER.read_text(encoding="utf-8")
    block = source[source.index("HAND_READ = {"):]
    block = block[:block.index("}") + 1]
    values = re.findall(r":\s*([\d.]+)", block)
    assert len(values) == 2, "HAND_READ now holds %d figures, not two" % len(values)
    for value in values:
        assert value in ALLOWED, (
            "%s is read off the form by hand and is not in ALLOWED, so nothing "
            "records why it may be typed" % value)


# --------------------------------------------------------------------------
# the roster is a partition, which is what makes it add up
# --------------------------------------------------------------------------

def test_every_delivered_verdict_lands_on_exactly_one_roster_line():
    """The defect, at its root. Each delivered value must match one and only
    one of the builder's verdict probes, or the roster silently loses it."""
    source = BUILDER.read_text(encoding="utf-8")
    block = source[source.index("BANK_VERDICTS = ("):]
    probes = re.findall(r'\("([^"]+)", "([^"]+)"\)', block[:block.index("\n)")])
    assert len(probes) >= 4, probes
    bank = _rows("bank-values.csv")
    for row in bank:
        if row["verified"] == "yes":
            continue
        hits = [label for label, probe in probes
                if probe in row["verified_meaning"]]
        assert len(hits) == 1, (
            "%r matches %d roster lines: %s"
            % (row["verified_meaning"], len(hits), hits))
