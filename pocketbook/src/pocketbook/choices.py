"""What the launcher chose before the workbook was written.

The firm, 26 Sep 2026: *"just select the workbook first, configure what you
can, and then do the workbook config items so that there are suggestions to be
made"*. The launcher's Choose tests step picks what runs: the kind of run, the
columns cut into bands, the segments and the split (or, for new variables, the
outcome, the inputs and what is held fixed), and the two limits Set up reads
the columns with. Set up writes these into Control's "Chosen in the launcher"
block, and the run reads them from there.

Pure data, with no openpyxl, PyYAML or Tk, so the launcher can hold one before
it has checked the add-ons (ruling OC-34).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

BLEED, NEW_VARIABLE = "bleed", "new_variable"
#: the Control rows the launcher writes that aren't settings, in the order they show, with their labels
ROWS = (("bands", "Cut into bands"), ("segments", "Segment by"), ("split", "Split every pocket by"),
        ("filter", "Filter the Grids by"), ("outcome", "Tested against"), ("test", "Inputs tested"),
        ("hold", "Held fixed"))
KEY = "launcher"                  # Control's key column reads "launcher|bands" and so on
#: what the bands and segments rows read when nobody narrowed them: every column its meaning cuts
EVERY = {"bands": "Every number column", "segments": "Every category"}
#: the most values a category may split every pocket by (the firm, 29 Sep 2026: "I know it can't break down too
#: far"), blanks aside: a blank is a part of its own, as it is a segment of its own
SPLIT_MOST_VALUES = 6
#: the most values the Grids' "Only loans where" may offer (the firm, 30 Sep 2026: a separate Filter by, "Yes hoping
#: to have this by morning"), blanks and loans with no date aside: each value is every grid built again on its loans
FILTER_MOST_VALUES = 6
#: the one column the launcher offers that the extract doesn't have: the year each loan was made, read from the column
#: marked Origination date (engine.origination_years works it out, for Split by and Filter by alike). A loan whose
#: date can't be read is in NO_DATE, a value of its own, so every loan is still shown
ORIG_YEAR, ORIG_YEAR_LABEL, NO_DATE = "ORIG_YEAR", "Origination year", "(no date)"


def too_many_values(column: str, n: int) -> str | None:
    """The refusal when a category has too many values to split the pockets by, in the words the launcher and the
    Run both give; None when it has few enough."""
    if n <= SPLIT_MOST_VALUES:
        return None
    return (f"{column} has {n:,} values. A category can split the pockets by {SPLIT_MOST_VALUES} values at most: "
            f"with more, each pocket's parts are too thin to read. Split by a column with fewer values, or by none.")


def too_many_to_filter(column: str, n: int) -> str | None:
    """The refusal when a column has too many values to filter the Grids by, in the words the launcher and the Run
    both give; None when it has few enough."""
    if n <= FILTER_MOST_VALUES:
        return None
    return (f"{column} has {n:,} values. The Grids can be filtered by a column of {FILTER_MOST_VALUES} values at "
            f"most: with more, each value's loans are too few to fill a grid. Filter by a column with fewer values, "
            f"or by none.")


def names(text) -> tuple[str, ...]:
    """'FICO, ORIG_BAL' as ('FICO', 'ORIG_BAL')."""
    return tuple(x.strip() for x in str(text or "").split(",") if x.strip())


def pct(share: float) -> str:
    return f"{share * 100:.0f}%"


@dataclass(frozen=True)
class Choices:
    run_kind: str | None = None             # BLEED or NEW_VARIABLE; None leaves Control's answer as it was
    bands: tuple[str, ...] | None = None    # None: every column whose meaning cuts it into bands
    segments: tuple[str, ...] | None = None  # None: every column whose meaning makes it a segment
    split: str | None = None
    filter: str | None = None               # the Grids' "Only loans where" column, whatever the split does
    outcome: str | None = None
    test: tuple[str, ...] = ()
    hold: tuple[str, ...] = ()
    shortlist: str | None = None            # the saved pre-spec file, confirmed instead of finding
    few_values: int = 12
    many_values: int = 50

    def cut(self) -> set[str] | None:
        """Every column chosen to cut, bands and segments together; None when neither was narrowed."""
        if self.bands is None and self.segments is None:
            return None
        return set(self.bands or ()) | set(self.segments or ())

    def rows(self) -> dict[str, str | None]:
        """The block's non-setting rows as Control shows them."""
        new = self.run_kind == NEW_VARIABLE
        out = {"bands": EVERY["bands"] if self.bands is None else ", ".join(self.bands) or "None",
               "segments": EVERY["segments"] if self.segments is None else ", ".join(self.segments) or "None",
               "split": self.split,
               "filter": None if new else self.filter,
               "outcome": self.outcome if new else None,
               "test": ", ".join(self.test) if new and self.test else None,
               "hold": ", ".join(self.hold) if new and self.hold else None}
        return out

    @classmethod
    def from_rows(cls, got: dict, **settings) -> "Choices":
        """Back from the block: `got` maps each row key to its cell's text."""
        def listed(k):
            v = got.get(k)
            if v in (None, "") or v == EVERY.get(k):
                return None
            return () if v == "None" else names(v)
        return cls(bands=listed("bands"), segments=listed("segments"), split=got.get("split") or None,
                   filter=got.get("filter") or None,
                   outcome=got.get("outcome") or None, test=names(got.get("test")), hold=names(got.get("hold")),
                   **settings)

    def but(self, **changes) -> "Choices":
        return replace(self, **changes)
