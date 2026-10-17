"""The Glossary's custom terms (the firm, 17 Oct 2026).

The firm: "our custom terms - like bad / good loans, these i do want in the glossary along with our key terms as
fairly plain language and simple explanations to walk a user through what it means. keep my voice in mind". And on
the p-value: "luck is seriously only a term we will understand, make sure it's clear that luck is basically the
other side of confidence", which the Glossary now says through How sure and Significant at N%?.

The guard: every verdict word, reading, Show option, Measure option and Together reading the workbook can print has
a Glossary row whose term names it. Each word is read from the constant the tabs themselves print, so a reading
added later without a Glossary row fails here. Then every new entry renders in a built workbook, before and after
a Run, and the examples that use the book's own figures tie to the extract."""

from __future__ import annotations

import csv
import re
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from conftest import TEST_SHUFFLES
from pocketbook import book, choices as ch, glossary, live, perm, results, synth
from test_book import _answer

#: the rows added on 17 Oct 2026, in the order the Glossary shows them
NEW = ["Judged against", "Good loan", "Bad loans / Bad loans % / Bad loans ÷ Loans",
       "Bad dollars / Bad dollars ÷ Booked", "Loan size", "Two-way / Split by",
       "Across the bottom / Lines by / Panels by",
       "Excess / Bad loans above share / Dollars above share / Dollars short of band / Dollars short of book",
       "Worse? (Yes / Not sure / Too few losses / No)", "Material? / Material at",
       "Show (All / Worse and material / Worse or not sure)", "How sure / Significant at N%?",
       "Significant at N%? (Yes / Borderline / No)",
       "Too few losses to test / Too few loans to test / Nothing to compare with",
       "Profit line (How far profit must move before it counts as more or less)",
       "Not losing more / Under the Worse at line / Within the profit line",
       "Holds (column) fixed? / Mixed with (column)", "Could have caught", "Together", "Priced for it", "Net drain",
       "Strong", "Safe but idle", "Earns less, not from losses", "Losing more, profit holding",
       "Show on Line size (Pockets where something tripped / 2 or more signals / All pockets)",
       "Treat as (Real / Missing)", "Changes now / Needs a Run", "Comes to", "Worked out from the loans",
       "Last Run used / Status", "Lines in use now", "Gray rows under", "Found on / Held back", "Pre-spec",
       "Holds up? / Still holds?"]
#: the rows whose example uses the book's own figures after a Run, on the synthetic book (no split, no filter)
FROM_THE_BOOK = ["Judged against", "Good loan", "Bad loans / Bad loans % / Bad loans ÷ Loans",
                 "Bad dollars / Bad dollars ÷ Booked", "Loan size",
                 "Excess / Bad loans above share / Dollars above share / Dollars short of band / Dollars short of book",
                 "Worse? (Yes / Not sure / Too few losses / No)", "Material? / Material at",
                 "Show (All / Worse and material / Worse or not sure)", "How sure / Significant at N%?",
                 "Significant at N%? (Yes / Borderline / No)", "Profit line (How far profit must move before it "
                 "counts as more or less)", "Could have caught", "Together", "Priced for it", "Net drain", "Strong",
                 "Safe but idle", "Earns less, not from losses", "Losing more, profit holding",
                 "Treat as (Real / Missing)", "Comes to", "Lines in use now"]


def parts(term: str) -> list[str]:
    """A term's names: "Worse? (Yes / Not sure / No)" names Worse?, Yes, Not sure and No."""
    return [x.strip() for x in re.split(r" / |\(|\)", term) if x.strip()]


def named(word: str, terms: list[str]) -> list[str]:
    """The terms that name `word`: as one of their names, or with its own parenthetical dropped ("Months to
    charge-off (avg)"), or, for a word that is the start of a reading ("Mixed with FICO"), as that start."""
    bare = re.sub(r"\s*\([^)]*\)$", "", word).strip()
    return [t for t in terms if word.strip() in parts(t) or bare in parts(t)
            or (word.endswith(" ") and any(x.startswith(word.strip()) for x in parts(t)))]


def _readings() -> dict[str, list[str]]:
    """Everything the workbook can print as a verdict, a reading, a Show or Measure option or a Together reading,
    from the constants the tabs print."""
    split_by = results.split_label(SimpleNamespace(config=SimpleNamespace(split=("X", "own_median"))))
    return {
        "Worse?": [live.YES, live.NOT_SURE, live.TOO_FEW, live.NO],
        "Significant at N%?": [live.SIG_HEAD.format("N%"), live.SIG_YES, live.SIG_BORDER, live.SIG_NO,
                               live.FEW_LOSSES, live.FEW_LOANS, live.NO_REST, live.NOT_MORE, live.UNDER_WORSE,
                               live.UNDER_PROFIT, results.MIXED],
        "Show": list(results.SHOW) + list(results.LINE_SHOW),
        "Measure": list(results.PLAIN.values()) + [results.SIZE_NAME, results.CO_MONTHS_NAME]
                   + [x[1] for x in results.LINE_MEASURES],
        "Together": ["Together"] + list(results.TOGETHER.values()),
        "Pockets": [results.TWO_WAY, split_by.removesuffix(" X")],
        "Line size": [s[0] for s in results.SIGNALS],
        "Treat as": list(book.TREAT),
    }


# --------------------------------------------------------------------------
# the guard


@pytest.mark.parametrize("family", list(_readings()))
def test_every_word_the_tabs_can_print_has_a_glossary_row(family):
    terms = [t for t, _, _ in glossary.rows(None)]
    missing = [w for w in _readings()[family] if not named(w, terms)]
    assert not missing, (family, missing)


def test_each_verdict_rows_term_names_all_its_readings():
    """Worse?'s four readings in Worse?'s own row, Significant at N%?'s three in its own, and Tripped by's reasons
    in what Tripped by means."""
    rows = {t: (m, e) for t, m, e in glossary.rows(None)}
    worse = next(t for t in rows if t.startswith("Worse? ("))
    assert set(_readings()["Worse?"]) <= set(parts(worse)), worse
    sig = next(t for t in rows if t.startswith(live.SIG_HEAD.format("N%") + " ("))
    assert {live.SIG_YES, live.SIG_BORDER, live.SIG_NO} <= set(parts(sig)), sig
    assert all(r in rows["Tripped by"][0] for r in results.TRIPPED_BY)
    # the pairing the firm asked for: How sure and the p-value in one row, 95% to 5% to 1 in 20
    pair = rows[f"How sure / {live.SIG_HEAD.format('N%')}"][0]
    assert "95% sure" in pair and "under 5%" in pair and "1 in 20" in pair


def test_the_guard_fails_on_a_reading_with_no_row(monkeypatch):
    """The control: a Together reading added to the code without a Glossary row is caught."""
    monkeypatch.setitem(results.TOGETHER, ("less", "same"), "Quietly better")
    terms = [t for t, _, _ in glossary.rows(None)]
    assert len(terms) == len(set(terms))
    assert not named("Quietly better", terms)
    assert "Quietly better" in _readings()["Together"]


def test_no_glossary_row_says_luck_or_the_old_chance_words():
    text = " ".join(" ".join(r) for r in glossary.rows(None)).lower()
    for gone in ("luck", "how often by chance", "could be chance", "too close to call", "rarer than 1 in"):
        assert gone not in text, gone


# --------------------------------------------------------------------------
# in a built workbook, before and after a Run


@pytest.fixture(scope="module")
def books(tmp_path_factory):
    d = tmp_path_factory.mktemp("glossary-terms")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", TEST_SHUFFLES)
        x = synth.write_extract(d, n=3000)
        out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED))
        assert out.ok, out.lines
        set_up = load_workbook(out.book)
        _answer(out.book)
        ran = book.run(out.book)
        assert ran.ok, ran.lines
        return {"extract": x, "set_up": set_up, "run": load_workbook(out.book)}


def _rows(wb) -> dict[str, tuple[str, str]]:
    ws = wb[glossary.SHEET]
    head = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=glossary.TERM).value == "Term")
    return {ws.cell(row=r, column=glossary.TERM).value: (ws.cell(row=r, column=glossary.MEANS).value,
                                                        ws.cell(row=r, column=glossary.EXAMPLE).value)
            for r in range(head + 1, ws.max_row + 1) if ws.cell(row=r, column=glossary.TERM).value}


def test_every_new_entry_renders_before_and_after_a_run_in_the_glossarys_order(books):
    for when in ("set_up", "run"):
        got = _rows(books[when])
        assert [t for t in got if t in NEW] == NEW, when
        for t in NEW:
            means, example = got[t]
            assert means and example and means.endswith(".") and example.endswith("."), (when, t)


def test_after_a_run_the_examples_use_the_books_figures(books):
    before, after = _rows(books["set_up"]), _rows(books["run"])
    for t in FROM_THE_BOOK:
        assert after[t][1] != before[t][1], t
    # the rows the book has no figure for keep their made-up example, never one presented as the book's
    for t in set(NEW) - set(FROM_THE_BOOK):
        assert not after[t][1].startswith("This book"), t


def _num(v):
    try:
        return float(v.replace(",", ""))
    except (AttributeError, ValueError):
        return None


def test_good_bad_and_bad_dollars_examples_tie_to_the_extract(books):
    """Good loans, bad loans, Bad loans % and Bad dollars ÷ Booked, worked out from the CSV without PocketBook:
    BAD_FLAG 1 is bad and 0 is good, any other value is neither, and Bad dollars are those loans' ORIG_BAL."""
    good = bad = 0
    bad_usd = usd = 0.0
    with open(books["extract"], newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            flag, bal = r["BAD_FLAG"].strip(), _num(r["ORIG_BAL"])
            if flag not in ("0", "1"):
                continue
            good, bad = good + (flag == "0"), bad + (flag == "1")
            if bal is not None:
                usd += bal
                bad_usd += bal if flag == "1" else 0.0
    rows = _rows(books["run"])
    assert rows["Good loan"][1] == (f"{good:,} of this book's {good + bad:,} loans with an outcome are good, and "
                                    f"{bad:,} are bad.")
    assert f"so its Bad loans % is {bad / (good + bad):.2%}." in rows["Bad loans / Bad loans % / Bad loans ÷ Loans"][1]
    assert rows["Bad dollars / Bad dollars ÷ Booked"][1] == (
        f"This book's bad loans booked ${bad_usd:,.0f} of ${usd:,.0f}, so Bad dollars ÷ Booked is "
        f"{bad_usd / usd:.2%}.")


def test_the_significant_rows_name_pockets_with_the_readings_pockets_prints(books):
    """Significant at N%?'s example after a Run names this book's pockets, each with a reading in the tab's own
    format, a Yes first."""
    ex = _rows(books["run"])[f"{live.SIG_HEAD.format('N%')} ({live.SIG_YES} / {live.SIG_BORDER} / {live.SIG_NO})"][1]
    said = re.findall(r"(.+?) read ((?:Yes|Borderline|No) \(p [=<] [\d.]+%\)) on (GCOs \(\$\)|Bad loans)\.", ex)
    assert said, ex
    assert said[0][1].startswith("Yes")
