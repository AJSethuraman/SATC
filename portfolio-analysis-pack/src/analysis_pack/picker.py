"""The picker: designation at the desk by number, with nothing to edit.

`pack setup EXTRACT` (from the bundle, `python build_pack.py --setup
EXTRACT.csv`) lists the extract's columns with a number beside each, asks one
question at a time, writes the question file from the answers, checks it, and
builds the pack. The person types numbers; for four things they type words
or a date: the word for the event, what reacts to the contradiction today,
the as-of date, and (if they want it stamped) the run date.

The firm, 22 September 2026: "I want no editing at the desk of Python or
script this is meant to be straight forward." Before this module the desk
filled twenty-one slots in Notepad (`pack init`); that path stays for
scripts and the harness.

What the picker proposes it takes from the data and shows (the one column
whose every value is distinct, the one date-like column, the quartiles of a
column as band edges); it never fills a slot the person did not answer. An
answer that would make the loader refuse — a column known only later used in
the rule — is refused on the spot and asked again, so the file the picker
writes is one the tool accepts.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from typing import Callable

import yaml

from .config import Config, ConfigError, load_config
from .ingest import Table, is_blank, parse_number, Bad

Ask = Callable[[str], str]
Say = Callable[[str], None]

PROMPT_END = "> "        # every question ends with this; a walk's renderer finds the answers by it
NUMERIC = ("integer", "decimal")


class Abandoned(Exception):
    """The person stopped answering (input ended)."""


def _say_stderr(text: str) -> None:
    print(text, file=sys.stderr)


def _ask_stderr(prompt: str) -> str:
    """Prompt on stderr (stdout may be redirected), read one line from stdin."""
    sys.stderr.write(prompt)
    sys.stderr.flush()
    line = sys.stdin.readline()
    if line == "":
        raise Abandoned("no answer: input ended")
    return line.rstrip("\r\n")


def _nice(x: float) -> float:
    """A cut point rounded to two significant figures, so a band edge reads
    like one a person would have chosen."""
    if x == 0:
        return 0.0
    import math
    mag = 10 ** (math.floor(math.log10(abs(x))) - 1)
    return float(round(x / mag) * mag)


def _quartile_edges(values: list[float]) -> list[float]:
    vals = sorted(values)
    if len(vals) < 8:
        return []
    out = []
    for q in (0.25, 0.5, 0.75):
        idx = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
        out.append(_nice(vals[idx]))
    edges = []
    for e in out:
        if not edges or e > edges[-1]:
            edges.append(e)
    return edges


def _fmt(x: float) -> str:
    return f"{x:,.10g}"


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return s or "question"


class Picker:
    """Asks the questions, holds the answers, writes the file."""

    def __init__(self, table: Table, report: list[dict], ask: Ask = _ask_stderr, say: Say = _say_stderr):
        self.table = table
        self.report = report
        self.columns = [e["column"] for e in report]
        self.by_name = {e["column"]: e for e in report}
        self.ask = ask
        self.say = say
        self.answers: dict = {}

    # -- the screen -----------------------------------------------------------

    def show_columns(self) -> None:
        self.say(f"The columns of {self.table.path.replace(chr(92), '/').split('/')[-1]} ({len(self.table.rows):,} rows):")
        width = max(len(c) for c in self.columns)
        for i, e in enumerate(self.report, start=1):
            blank = "blank n/a" if e["null_share"] is None else f"blank {e['null_share']:.0%}"
            kind = e["kind"]
            if (e.get("dates") or {}).get("resolved"):
                kind = "date"
            samples = ", ".join(" ".join(str(s).split())[:18] for s in e["samples"][:3])
            self.say(f"  {i:>3}  {e['column']:<{width}}  {kind:<9} {blank:<10} e.g. {samples}")
        self.say("")

    # -- one question at a time ---------------------------------------------------

    def _one(self, question: str, candidates: list[str], default: str | None = None, hint: str = "") -> str:
        """A column, by number or by name. Enter takes the default when there is one."""
        while True:
            tail = f" (Enter for {self.columns.index(default) + 1} = {default})" if default else ""
            line = self.ask(f"{question}{tail}{(' ' + hint) if hint else ''}\n{PROMPT_END}").strip()
            if not line and default:
                return default
            col = self._resolve(line)
            if col is None:
                self.say("  type the number beside the column (or its name exactly)")
                continue
            if col not in candidates:
                why = self._why_not(col, candidates)
                self.say(f"  {col} cannot be used here: {why}")
                continue
            return col

    def _many(self, question: str, candidates: list[str], hint: str = "") -> list[str]:
        """Several columns, numbers separated by commas; Enter for none."""
        while True:
            line = self.ask(f"{question} (numbers separated by commas; Enter for none){(' ' + hint) if hint else ''}\n{PROMPT_END}").strip()
            if not line:
                return []
            picked, bad = [], []
            for part in re.split(r"[,\s]+", line):
                if not part:
                    continue
                col = self._resolve(part)
                if col is None or col not in candidates:
                    bad.append(part)
                elif col not in picked:
                    picked.append(col)
            if bad:
                self.say(f"  not usable here: {', '.join(bad)} — type numbers from the list")
                continue
            return picked

    def _choice(self, question: str, options: list[str], default: int = 1) -> int:
        """One of a few numbered options; returns the 1-based index."""
        while True:
            lines = "\n".join(f"    {i}  {opt}" for i, opt in enumerate(options, start=1))
            line = self.ask(f"{question}\n{lines}\n  (Enter for {default})\n{PROMPT_END}").strip()
            if not line:
                return default
            if line.isdigit() and 1 <= int(line) <= len(options):
                return int(line)
            self.say(f"  type a number from 1 to {len(options)}")

    def _number(self, question: str, default: float | None) -> float:
        while True:
            tail = f" (Enter for {_fmt(default)})" if default is not None else ""
            line = self.ask(f"{question}{tail}\n{PROMPT_END}").strip().replace(",", "")
            if not line and default is not None:
                return default
            try:
                return float(line)
            except ValueError:
                self.say("  type a number")

    def _edges(self, question: str, default: list[float]) -> list[float]:
        while True:
            tail = f" (Enter for {', '.join(_fmt(e) for e in default)})" if default else ""
            line = self.ask(f"{question}{tail}\n{PROMPT_END}").strip()
            if not line and default:
                return list(default)
            try:
                edges = [float(p) for p in re.split(r"[,\s]+", line.replace("_", "")) if p]
            except ValueError:
                self.say("  type numbers separated by commas, smallest first")
                continue
            if len(edges) < 1 or any(edges[i] >= edges[i + 1] for i in range(len(edges) - 1)):
                self.say("  the edges must rise: smallest first, no repeats")
                continue
            return edges

    def _text(self, question: str, default: str | None = None, required: bool = False) -> str:
        while True:
            tail = f" (Enter for {default})" if default else ""
            line = self.ask(f"{question}{tail}\n{PROMPT_END}").strip()
            if not line and default is not None:
                return default
            if not line and required:
                self.say("  this one needs an answer")
                continue
            return line

    def _date(self, question: str, required: bool = True) -> date | None:
        while True:
            line = self.ask(f"{question} (YYYY-MM-DD{'' if required else '; Enter for none'})\n{PROMPT_END}").strip()
            if not line and not required:
                return None
            try:
                return date.fromisoformat(line)
            except ValueError:
                self.say("  type the date as YYYY-MM-DD, e.g. 2026-06-30")

    def _resolve(self, token: str) -> str | None:
        if token.isdigit() and 1 <= int(token) <= len(self.columns):
            return self.columns[int(token) - 1]
        return token if token in self.by_name else None

    def _why_not(self, col: str, candidates: list[str]) -> str:
        kind = self.by_name[col]["kind"]
        if col in self.answers.get("used", {}):
            return f"it is already the {self.answers['used'][col]}"
        if kind not in NUMERIC and any(self.by_name[c]["kind"] in NUMERIC for c in candidates):
            return f"it reads as {kind}, and this needs a number column"
        if kind != "date-like" and all(self.by_name[c]["kind"] == "date-like" for c in candidates):
            return f"it reads as {kind}, and this needs a date column"
        return "it is not one of the columns this question can take"

    def _use(self, col: str, role: str) -> None:
        self.answers.setdefault("used", {})[col] = role

    def _free(self, kinds: tuple[str, ...] | None = None) -> list[str]:
        used = self.answers.get("used", {})
        return [c for c in self.columns if c not in used and (kinds is None or self.by_name[c]["kind"] in kinds)]

    def _values(self, col: str) -> list[float]:
        out = []
        for r in self.table.rows:
            v = r.get(col)
            if is_blank(v):
                continue
            n = parse_number(v)
            if not isinstance(n, Bad):
                out.append(float(n))
        return out

    # -- the questions, in order --------------------------------------------------

    def run(self) -> dict:
        a = self.answers
        n_rows = len(self.table.rows)
        self.show_columns()

        distinct = [e["column"] for e in self.report
                    if e["null_share"] == 0 and e["distinct"] == n_rows and e["kind"] != "date-like"]
        a["loan_id"] = self._one("1. Which column numbers the loans, one value per loan?",
                                 self._free(), default=distinct[0] if len(distinct) == 1 else None,
                                 hint="" if len(distinct) == 1 else f"({len(distinct)} columns have a different value on every row)")
        self._use(a["loan_id"], "loan number")

        dates = [c for c in self._free(("date-like",))]
        a["origination_date"] = self._one("2. Which column holds the date the loan was made?", self._free(),
                                          default=dates[0] if len(dates) == 1 else None)
        self._use(a["origination_date"], "origination date")

        numeric = self._free(NUMERIC)
        a["field_a"] = self._one("3. The rule compares two number columns. Which is the first (the top of a ratio)?", numeric)
        self._use(a["field_a"], "first rule column")
        a["field_b"] = self._one("4. Which is the second (the bottom of the ratio)?", self._free(NUMERIC))
        self._use(a["field_b"], "second rule column")
        k = self._choice("5. Compare them as", [f"a ratio: {a['field_a']} ÷ {a['field_b']}",
                                                f"a difference: {a['field_a']} − {a['field_b']}"])
        a["kind"] = "ratio" if k == 1 else "difference"
        word = "ratio" if k == 1 else "difference"
        a["fires_value"] = self._number(f"6. The flag fires when the {word} is above what?", 1.0 if k == 1 else 0.0)
        va, vb = self._values(a["field_a"]), self._values(a["field_b"])
        if k == 1:
            default_edges = [0.5, 1.0, 2.0, 5.0]
        else:
            pairs = [x - y for x, y in zip(va, vb)]
            default_edges = _quartile_edges(pairs) or [0.0]
        a["buckets"] = self._edges(f"7. Edges for the steps of the {word} in the gradient (numbers, smallest first)", default_edges)

        form = self._choice("8. How does the extract say a loan went bad?",
                            ["a column with the date it happened",
                             "a yes/no column the bank already set (1 = yes)",
                             "a measure at the as-of date, from two number columns (e.g. utilisation)"])
        if form == 1:
            col = self._one("9. Which column has the date it happened?", self._free(("date-like",)) or self._free())
            self._use(col, "outcome date")
            a["outcome"] = {"date_field": col}
        elif form == 2:
            col = self._one("9. Which column is the flag?", self._free(("integer",)) or self._free(NUMERIC),
                            hint="(a whole-number column, 1 for yes)")
            self._use(col, "outcome flag")
            val = self._number("10. Which value means yes?", 1.0)
            # the bank applied its own window before the extract; the pack records that and does not re-window
            a["outcome"] = {"field": col, "op": "==", "value": val, "basis": "windowed_by_bank"}
        else:
            ma = self._one("9. The measure's first column (the top of the ratio)?", self._free(NUMERIC))
            self._use(ma, "measure column")
            mb = self._one("10. The measure's second column (the bottom)?", self._free(NUMERIC))
            self._use(mb, "measure column")
            mk = self._choice("11. Combine them as", [f"a ratio: {ma} ÷ {mb}", f"a difference: {ma} − {mb}"])
            cut = self._choice("12. One cut, or several bands?", ["one cut: a loan is bad at or above a value",
                                                                  "several bands, one outcome per edge"])
            out = {"measure": {"kind": "ratio" if mk == 1 else "difference", "field_a": ma, "field_b": mb},
                   "basis": "snapshot_at_asof"}
            if cut == 1:
                out["op"] = ">="
                out["value"] = self._number("13. Bad at or above what value?", None)
            else:
                out["edges"] = self._edges("13. The edges (numbers, smallest first)", [])
            a["outcome"] = out
        a["label"] = self._text("Next: the word every tab will use for the event (e.g. default, charge-off)", required=True)

        a["window_months"] = int(self._number("Months a loan needs on book before it counts", 24))
        a["asof"] = self._date("The as-of date the pack is built at")

        self.say("")
        self.say("Step 4 tests whether the flag still matters inside groups of similar loans. Without any")
        self.say("group, the pack cannot tell an effect from something else in disguise.")
        # a rule column can be a confounder too (loan size is often the denominator);
        # the loan number, the origination date and the outcome cannot
        fixed = {"loan number", "origination date", "outcome date", "outcome flag", "measure column"}
        conf_candidates = [c for c in self.columns if a["used"].get(c) not in fixed]
        conf = self._many("Which columns might the effect be hiding in (size, product, region …)?",
                          conf_candidates, hint="— number columns are banded, text columns taken level by level")
        a["confounders"] = []
        for col in conf:
            if col not in a["used"]:
                self._use(col, "confounder")
            if self.by_name[col]["kind"] in NUMERIC:
                q = _quartile_edges(self._values(col))
                edges = self._edges(f"Band edges for {col} (numbers, smallest first)", q)
                a["confounders"].append({"name": col, "field": col, "edges": edges})
            else:
                a["confounders"].append({"name": col, "field": col})

        a["existing_control"] = self._text("What at the bank reacts to this contradiction today?", default="none")

        # what was known when: the outcome column is known later; anything else
        # the person names as later is refused where it would leak
        used = [c for c in self.columns if c in a["used"]]
        while True:
            later = self._many("Of the columns in use, which were known only AFTER the loan was made (other than the outcome)?",
                               used)
            clash = [c for c in later if a["used"][c] not in ("outcome date", "outcome flag", "measure column")]
            if not clash:
                a["later"] = later
                break
            for c in clash:
                self.say(f"  {c} is the {a['used'][c]}; a column known only later cannot be used there, "
                         f"because it would leak what happened into the test. Leave it out here, or start again "
                         f"and pick another column for that.")
        a["run_date"] = self._date("Today's date, to stamp on the pack", required=False)
        a["name"] = _slug(f"{a['field_a']}_vs_{a['field_b']}")
        return a

    # -- the file ---------------------------------------------------------------

    def question(self) -> dict:
        a = self.answers
        outcome_cols = set(a["outcome"].get("measure", {}).values()) - {"ratio", "difference"}
        for key in ("date_field", "field"):
            if key in a["outcome"]:
                outcome_cols.add(a["outcome"][key])
        fields = {}
        for col in self.columns:
            if col not in a["used"]:
                continue
            known = "later" if (col in outcome_cols or col in a.get("later", [])) else "at_origination"
            fields[col] = {"known": known}
        out = {"label": a["label"], **a["outcome"]}
        return {
            "name": a["name"],
            "schema_version": 1,
            "rule_type": "contradiction",
            "population": {"loan_id": a["loan_id"], "origination_date": a["origination_date"]},
            "fields": fields,
            "rule": {"kind": a["kind"], "field_a": a["field_a"], "field_b": a["field_b"],
                     "fires_when": {"op": ">", "value": a["fires_value"]}, "buckets": a["buckets"]},
            "outcome": out,
            "window_months": a["window_months"],
            "confounders": a["confounders"],
            "controls": [{"name": "origination_year", "derived": "origination_year"}],
            "decompose_by": [c["name"] for c in a["confounders"]] + ["origination_year"],
            "existing_control": a["existing_control"],
            "model": {"tree_depth": 3, "min_leaf_events": 10, "min_leaf_loans": 100},
            "intervals": {"confidence": 0.95, "method": "wilson"},
            "survives_threshold": 0.5,
        }

    def to_yaml(self) -> str:
        head = ("# Question file written by the picker from your answers. Run the setup again\n"
                "# to answer differently; nothing here needs editing by hand.\n")
        return head + yaml.safe_dump(self.question(), sort_keys=False, allow_unicode=True)


def check(path) -> Config:
    """The loader's verdict on the file the picker wrote; raises ConfigError."""
    return load_config(path)


__all__ = ["Picker", "Abandoned", "PROMPT_END", "check", "ConfigError"]
