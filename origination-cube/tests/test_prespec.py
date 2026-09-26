"""The pre-spec (NEXT-GOAL 3.15): the confirmatory run's settings, written and
committed before the holdout is looked at. It refuses rather than defaults,
names the commit it was read from, says in words where a run strays from it,
and counts the loans a run took from the holdout."""

from __future__ import annotations

import copy
import shutil
import subprocess

from datetime import date, datetime
from pathlib import Path

import pytest

from origination_cube import prespec as P

EXAMPLE = Path(__file__).resolve().parents[1] / "docs" / "prespec-example.yaml"

BASE = {
    "prespec": 1,
    "written": date(2026, 10, 1),
    "column": "income_to_sales",
    "bins": [0.1, 0.25, 0.5, 1.0, 2.0],
    "reference": "0.25 - 0.49",
    "strata": ["FICO", "CHANNEL"],
    "window_months": 18,
    "confidence": 0.95,
    "holdout": {"from": date(2024, 1, 1), "to": date(2024, 12, 31)},
    "development": {"from": date(2022, 1, 1), "to": date(2023, 12, 31)},
}

#: What a run that followed the pre-spec to the letter would report.
MATCHING = {
    "column": "income_to_sales",
    "bins": [0.1, 0.25, 0.5, 1.0, 2.0],
    "reference": "0.25 - 0.49",
    "strata": ["FICO", "CHANNEL"],
    "window_months": 18,
    "confidence": 0.95,
    "holdout": {"from": date(2024, 1, 1), "to": date(2024, 12, 31)},
}


def spec(**overrides) -> P.PreSpec:
    raw = copy.deepcopy(BASE)
    for k, v in overrides.items():
        if v is None:
            raw.pop(k, None)
        else:
            raw[k] = v
    return P.parse(raw)


def refused(**overrides) -> list[str]:
    with pytest.raises(P.PreSpecError) as exc:
        spec(**overrides)
    return exc.value.problems


# --------------------------------------------------------------------------
# The file

def test_the_committed_example_loads_as_the_docstring_says():
    s = P.load(EXAMPLE)
    assert s.column == "income_to_sales"
    assert s.bins == (0.1, 0.25, 0.5, 1.0, 2.0)
    assert s.groups == ("up to 0.09", "0.10 - 0.24", "0.25 - 0.49", "0.50 - 0.99", "1.00 - 1.99", "2.00 and up")
    assert (s.reference, s.reference_index) == ("0.25 - 0.49", 2)
    assert s.strata == ("FICO", "CHANNEL")
    assert (s.window_months, s.confidence) == (18, 0.95)
    assert s.holdout == P.DateRange(date(2024, 1, 1), date(2024, 12, 31))
    assert s.development == P.DateRange(date(2022, 1, 1), date(2023, 12, 31))
    assert s.written == date(2026, 10, 1)
    assert s.text == EXAMPLE.read_text(encoding="utf-8")      # what Check will echo, byte for byte


def test_the_reference_can_be_given_by_its_number():
    s = spec(reference=2)
    assert (s.reference, s.reference_index) == ("0.25 - 0.49", 2)


@pytest.mark.parametrize("written,index", [("0.01 - 0.09", 0), ("up to 0.09", 0), ("2.00 - 7.40", 5),
                                           ("2.00 and up", 5), ("0.25  -  0.49", 2)])
def test_the_end_groups_can_be_named_as_a_grid_shows_them(written, index):
    """A grid prints the lowest and highest groups with the data's own range
    once it has seen the data; either way of writing them names the same group."""
    assert spec(reference=written).reference_index == index


def test_dates_may_be_quoted():
    s = spec(written="2026-10-01", holdout={"from": "2024-01-01", "to": "2024-12-31"})
    assert s.written == date(2026, 10, 1) and s.holdout.start == date(2024, 1, 1)


def test_no_strata_must_be_said_and_then_is_accepted():
    assert spec(strata=[]).strata == ()


@pytest.mark.parametrize("key", P.KEYS)
def test_each_missing_line_is_refused_with_the_line_to_add(key):
    problems = refused(**{key: None})
    assert any(p.startswith(f"missing line `{key}:`") and "\n" + key + ":" in p for p in problems), problems


def test_an_unknown_line_is_refused():
    assert "unknown line `confidense:`" in refused(confidense=0.95)[0]


def test_an_unanswered_line_is_refused_and_named_once():
    problems = refused(confidence="[CONFIRM: 0.95 or 0.99?]")
    assert problems == ["`confidence` still reads '[CONFIRM: 0.95 or 0.99?]': replace it with your answer"]


def test_another_version_is_refused():
    assert "this tool reads pre-spec version 1" in refused(prespec=2)[0]


@pytest.mark.parametrize("bins,words", [
    ([0.1, 0.5, 0.25], "must rise"),
    ([0.1, 0.25, 0.25, 1.0], "must rise"),
    ([], "must be a list of cut points"),
    ([0.1, "a quarter"], "must be a list of cut points"),
    ([0.1, float("nan"), 1.0], "must be a list of cut points"),
    (0.25, "must be a list of cut points"),
])
def test_bins_must_be_numbers_that_rise(bins, words):
    assert words in refused(bins=bins)[0]


@pytest.mark.parametrize("ref", ["0.25-0.50", "0.30 - 0.49", 6, -1, True, 2.0, "abc - 0.09", "2.00 - 1.50"])
def test_the_reference_must_be_one_of_the_groups(ref):
    problems = refused(reference=ref)
    assert len(problems) == 1 and "is not one of the groups the bins make" in problems[0], problems
    assert "up to 0.09; 0.10 - 0.24; 0.25 - 0.49" in problems[0]         # and it lists them


@pytest.mark.parametrize("conf", [95, 1.0, 0.4, "high", True])
def test_confidence_must_be_a_share(conf):
    assert refused(confidence=conf) == [
        f"`confidence:` must be a share between 0.5 and 1, such as 0.95 for 95%; got {conf!r}"]


@pytest.mark.parametrize("window", [0, -3, 18.5, True, "18"])
def test_the_window_is_a_positive_whole_number(window):
    assert refused(window_months=window) == [
        f"`window_months:` must be a whole number of months, 1 or more; got {window!r}"]


@pytest.mark.parametrize("key", ["holdout", "development"])
def test_a_range_that_runs_backwards_is_refused(key):
    problems = refused(**{key: {"from": date(2025, 6, 30), "to": date(2025, 1, 1)}})
    assert problems == [f"`{key}:` runs backwards: from 2025-06-30 is after to 2025-01-01"]


def test_a_holdout_overlapping_development_is_refused():
    problems = refused(holdout={"from": date(2023, 7, 1), "to": date(2024, 6, 30)})
    assert len(problems) == 1 and problems[0].startswith(
        "the holdout (2023-07-01 to 2024-06-30) overlaps development (2022-01-01 to 2023-12-31)")


def test_sharing_one_day_is_overlapping():
    """Both ends are inclusive, so a holdout that starts on development's last day shares that day."""
    assert "overlaps development" in refused(holdout={"from": date(2023, 12, 31), "to": date(2024, 12, 31)})[0]


def test_the_day_after_development_ends_may_start_the_holdout():
    assert spec(holdout={"from": date(2024, 1, 1), "to": date(2024, 1, 1)}).holdout.text() == "2024-01-01 to 2024-01-01"


@pytest.mark.parametrize("rng", [{"from": date(2024, 1, 1)}, {"from": date(2024, 1, 1), "to": date(2024, 2, 1),
                                                               "through": date(2024, 3, 1)}, [2024, 2025]])
def test_a_range_is_exactly_from_and_to(rng):
    assert refused(holdout=rng)[0].startswith("`holdout:` must be {from: 2024-01-01, to: 2024-12-31}")


@pytest.mark.parametrize("bad", ["2024-13-01", "last year", 20240101, datetime(2024, 1, 1, 9, 30)])
def test_a_date_must_be_a_date(bad):
    assert refused(written=bad) == [f"`written:` must be a date written like 2024-01-01; got {bad!r}"]


@pytest.mark.parametrize("strata,words", [
    (["FICO", "FICO"], "names FICO more than once"),
    (["FICO", "income_to_sales"], "includes `income_to_sales`, the column being tested"),
    ("FICO", "must list the columns the pockets are cut by"),
    (["FICO", ""], "must list the columns the pockets are cut by"),
])
def test_strata_are_distinct_columns_other_than_the_one_tested(strata, words):
    assert words in refused(strata=strata)[0]


def test_every_problem_is_listed_at_once():
    problems = refused(bins=[2.0, 1.0], confidence=95, window_months=0, column=None,
                      holdout={"from": date(2025, 1, 1), "to": date(2024, 1, 1)})
    assert len(problems) == 5, problems


def test_a_file_that_is_not_yaml_or_not_there_is_refused_plainly(tmp_path):
    bad = tmp_path / "p.yaml"
    bad.write_text("prespec: 1\nwritten: 2024-13-01\n", encoding="utf-8")
    with pytest.raises(P.PreSpecError, match="not readable as YAML: month must be in 1..12"):
        P.load(bad)
    with pytest.raises(P.PreSpecError, match="cannot be read"):
        P.load(tmp_path / "missing.yaml")


# --------------------------------------------------------------------------
# Where it came from

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed on this machine")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                           "-c", "commit.gpgsign=false", *args],
                          cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fresh repository holding one committed pre-spec, in a folder below its root."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    git(root, "init", "-q")
    f = root / "specs" / "prespec.yaml"
    f.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    git(root, "add", "specs/prespec.yaml")
    git(root, "commit", "-q", "-m", "pre-spec")
    return root, f


@needs_git
def test_provenance_names_the_commit_the_file_was_read_from(repo):
    root, f = repo
    got = P.provenance(f)
    assert got["commit"] == git(root, "rev-parse", "HEAD")
    assert datetime.fromisoformat(got["committed_at"]).tzinfo is not None
    assert (got["dirty"], got["reason"]) == (False, None)


@needs_git
def test_provenance_names_the_last_commit_that_touched_the_file_not_the_latest(repo):
    root, f = repo
    first = git(root, "rev-parse", "HEAD")
    (root / "other.txt").write_text("later work", encoding="utf-8")
    git(root, "add", "other.txt")
    git(root, "commit", "-q", "-m", "later")
    assert P.provenance(f)["commit"] == first != git(root, "rev-parse", "HEAD")


@needs_git
def test_an_edited_file_is_dirty(repo):
    root, f = repo
    f.write_text(f.read_text(encoding="utf-8").replace("confidence: 0.95", "confidence: 0.90"), encoding="utf-8")
    got = P.provenance(f)
    assert got["commit"] == git(root, "rev-parse", "HEAD")
    assert got["dirty"] is True
    assert got["reason"].startswith("changed since commit ")


@needs_git
def test_a_staged_but_uncommitted_edit_is_dirty_too(repo):
    root, f = repo
    f.write_text(f.read_text(encoding="utf-8") + "# later thought\n", encoding="utf-8")
    git(root, "add", "specs/prespec.yaml")
    assert P.provenance(f)["dirty"] is True


@needs_git
def test_a_file_never_committed_has_no_commit(repo):
    root, _ = repo
    new = root / "specs" / "second.yaml"
    new.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    assert P.provenance(new) == {"commit": None, "committed_at": None, "dirty": None,
                                 "reason": "not committed: a pre-spec only counts once it is committed"}


@needs_git
def test_a_file_in_a_repository_with_no_commits_has_no_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    git(tmp_path, "init", "-q")
    f = tmp_path / "p.yaml"
    f.write_text("prespec: 1\n", encoding="utf-8")
    assert P.provenance(f)["reason"] == "not committed: a pre-spec only counts once it is committed"


@needs_git
def test_a_file_outside_any_repository_has_no_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    (tmp_path / "loose").mkdir()
    f = tmp_path / "loose" / "p.yaml"
    f.write_text("prespec: 1\n", encoding="utf-8")
    got = P.provenance(f)
    assert got["commit"] is None and got["dirty"] is None
    assert got["reason"] == "not in a git repository, so not committed: a pre-spec only counts once it is committed"


def test_without_git_it_says_so_and_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "GIT", str(tmp_path / "no-such-git"))
    f = tmp_path / "p.yaml"
    f.write_text("prespec: 1\n", encoding="utf-8")
    got = P.provenance(f)
    assert got["commit"] is None
    assert got["reason"].startswith("git is not installed here") and got["reason"].endswith("once it is committed")


def test_a_git_that_hangs_does_not_hang_or_raise(tmp_path, monkeypatch):
    def hang(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="git", timeout=P.GIT_TIMEOUT)
    monkeypatch.setattr(P.subprocess, "run", hang)
    f = tmp_path / "p.yaml"
    f.write_text("prespec: 1\n", encoding="utf-8")
    got = P.provenance(f)
    assert got["commit"] is None and "did not answer within" in got["reason"]


def test_a_missing_file_has_no_commit(tmp_path):
    got = P.provenance(tmp_path / "nowhere.yaml")
    assert got["commit"] is None and "is not a file" in got["reason"]


# --------------------------------------------------------------------------
# Where the run strays from it

def test_a_run_that_follows_the_pre_spec_has_no_deviations():
    assert P.deviations(spec(), MATCHING) == []


def test_the_same_run_said_differently_is_still_the_same_run():
    """Edges for bins, the reference by number or with the data's range, strata in another
    order, the holdout as a pair of ISO strings, and the rest of Control alongside."""
    s = spec(reference="0.01 - 0.09")
    same = {**MATCHING, "bins": None, "edges": (0.1, 0.25, 0.5, 1, 2), "reference": 0,
            "strata": ["CHANNEL", "FICO"], "holdout": ("2024-01-01", "2024-12-31"), "min_loans": 30}
    assert P.deviations(s, same) == []


@pytest.mark.parametrize("key,value,sentence", [
    ("column", "loan_to_sales",
     "The column tested is `loan_to_sales` on Control; the pre-spec says `income_to_sales`."),
    ("bins", [0.1, 0.25, 0.5, 1.0],
     "The bins are 0.1, 0.25, 0.5, 1 on Control; the pre-spec says 0.1, 0.25, 0.5, 1, 2."),
    ("reference", "0.50 - 0.99",
     "The reference group is `0.50 - 0.99` on Control; the pre-spec says `0.25 - 0.49`."),
    ("reference", 3,
     "The reference group is `0.50 - 0.99` on Control; the pre-spec says `0.25 - 0.49`."),
    ("strata", ["FICO"],
     "Pockets are cut by FICO on Control; the pre-spec says FICO, CHANNEL."),
    ("strata", [],
     "Pockets are cut by nothing (the whole book is one pocket) on Control; the pre-spec says FICO, CHANNEL."),
    ("window_months", 12,
     "The outcome window is 12 months on Control; the pre-spec says 18 months."),
    ("confidence", 0.90,
     "Confidence is 90% on Control; the pre-spec says 95%."),
    ("holdout", {"from": date(2024, 1, 1), "to": date(2024, 6, 30)},
     "The holdout is 2024-01-01 to 2024-06-30 on Control; the pre-spec says 2024-01-01 to 2024-12-31."),
])
def test_each_setting_that_differs_is_said_in_words(key, value, sentence):
    assert P.deviations(spec(), {**MATCHING, key: value}) == [sentence]


@pytest.mark.parametrize("key", P.IN_USE_KEYS)
def test_a_setting_the_run_did_not_state_is_a_deviation_not_a_pass(key):
    in_use = {k: v for k, v in MATCHING.items() if k != key}
    got = P.deviations(spec(), in_use)
    assert len(got) == 1 and " not set on Control; the pre-spec says " in got[0], got


def test_a_confidence_that_differs_past_the_printed_digits_shows_every_digit():
    got = P.deviations(spec(), {**MATCHING, "confidence": 0.9500001})
    assert got == ["Confidence is 0.9500001 on Control; the pre-spec says 0.95."]


def test_nonsense_in_the_run_is_a_deviation_not_a_crash():
    got = P.deviations(spec(), {**MATCHING, "bins": "five", "holdout": "2024", "reference": "middle"})
    assert got == ["The bins are 'five' on Control; the pre-spec says 0.1, 0.25, 0.5, 1, 2.",
                   "The reference group is `middle`, which is not one of its bins' groups on Control; "
                   "the pre-spec says `0.25 - 0.49`.",
                   "The holdout is '2024', which is not a date range on Control; "
                   "the pre-spec says 2024-01-01 to 2024-12-31."]


def test_where_the_setting_was_read_is_the_callers_to_say():
    assert P.deviations(spec(), {**MATCHING, "window_months": 1}, where="in this run") == [
        "The outcome window is 1 month in this run; the pre-spec says 18 months."]


# --------------------------------------------------------------------------
# Whether the run touched the holdout

def test_holdout_touch_counts_both_ends_of_the_range():
    """The holdout's from and to dates are both inside; the day either side of it is not."""
    dates = [date(2023, 12, 31), date(2024, 1, 1), date(2024, 7, 4), date(2024, 12, 31), date(2025, 1, 1), None]
    assert P.holdout_touch(spec(), dates) == (3, date(2024, 1, 1), date(2024, 12, 31))


def test_holdout_touch_on_an_extract_of_development_loans_only():
    assert P.holdout_touch(spec(), [date(2022, 3, 1), date(2023, 12, 31), None]) == (0, None, None)


def test_holdout_touch_reads_a_date_and_time_as_its_date():
    got = P.holdout_touch(spec(), [datetime(2024, 12, 31, 23, 59), datetime(2024, 1, 1, 0, 0)])
    assert got == (2, date(2024, 1, 1), date(2024, 12, 31))


def test_holdout_touch_refuses_something_that_is_not_a_date():
    with pytest.raises(TypeError, match="reads dates or None"):
        P.holdout_touch(spec(), ["2024-06-01"])
