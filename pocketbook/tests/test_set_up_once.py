"""Set up does each piece of reading once (found 26 Sep 2026: at 17,000 loans by
80 columns it took 158 seconds, 84% of them in date detection).

Three things were done again and again: every value, plain numbers included,
was tried against all eight date patterns with strptime; each column's facts
were worked out four times over (and classify detected its dates a fifth);
and one Run parsed settings.yaml up to 45 times. Each is now done once, and
each fix is held to giving exactly the answer it gave before."""

import random
from datetime import date, datetime, timedelta
from importlib import resources

import yaml

from conftest import table
from pocketbook import book, control, ingest, look, meanings, profile, synth
from pocketbook.ingest import DATE_PATTERNS, DateDetection, is_blank


# --------------------------------------------------------------------------
# 1. The date gates


def _old_detect(column, values):
    """The detector as it was before the gates: strptime on every value, every pattern."""
    texts, typed = [], 0
    for v in values:
        if is_blank(v):
            continue
        if isinstance(v, (datetime, date)):
            typed += 1
            continue
        texts.append(str(v).strip())
    fits = {}
    for pat in DATE_PATTERNS:
        n = 0
        for s in texts:
            try:
                datetime.strptime(s, pat)
                n += 1
            except ValueError:
                pass
        fits[pat] = n
    full = tuple(p for p in DATE_PATTERNS if texts and fits[p] == len(texts))
    return DateDetection(column=column, total=len(texts) + typed, typed=typed, fits=fits,
                         resolved=full[0] if len(full) == 1 else None, ambiguous=full if len(full) > 1 else (),
                         sample=texts[0] if texts else None)


def _reads(s, pat):
    try:
        datetime.strptime(s, pat)
        return True
    except ValueError:
        return False


#: Values strptime reads that a tidy regex would turn away: each one a way the first draft of a gate was wrong.
EDGES = {
    "%m/%d/%Y": [" 5/ 6/2024", "5/ 6/2024", "12/31/2024", "1/1/2024", "02/29/2024"],
    "%d/%m/%Y": [" 6/5/2024", "31/12/2024"],
    "%Y-%m-%d": ["2024-1-5", "2024-01- 5", "2024-12-31"],
    "%m/%d/%y": ["1/ 5/24", "12/31/99"],
    "%Y%m%d": ["20241105", "2024111", "202411", "20241 5", "202411 5", "2024011"],
    "%d-%b-%Y": ["5-Jan-2024", " 5-jan-2024", "05-JAN-2024"],
    "%b %d, %Y": ["Jan 5, 2024", "jan 05, 2024", "Jan  5, 2024", "Jan\t5,\t2024", "DEC 31,   2024",
                  "Jan 5,\n2024"],
    "%Y-%m-%dT%H:%M:%S": ["2024-01-05T10:00:00", "2024-1-5t1:2:3", "2024-01- 5T23:59:59"],
}


def _values(rng):
    """A wide spread: numbers of every shape, dates in every pattern (padded, unpadded, odd case, odd spacing),
    near-misses made by damaging real dates, junk and blanks."""
    out = ["", " ", "na", "N/A", "-", "null", None]
    for _ in range(300):
        out += [str(rng.randint(-10**9, 10**9)), f"{rng.gauss(50, 30):.2f}", f"{rng.uniform(0, 1):.4f}",
                f"${rng.randint(0, 10**6):,}", f"({rng.randint(1, 999)})", str(rng.randint(0, 99)),
                str(rng.randint(10**5, 10**8)), f"{rng.randint(1, 99)}%", rng.choice("ABCDE") * rng.randint(1, 3)]
    start = date(1969, 1, 1)
    for _ in range(400):
        d = start + timedelta(days=rng.randint(0, 40000))
        t = datetime(d.year, d.month, d.day, rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59))
        for pat in DATE_PATTERNS:
            s = t.strftime(pat)
            out.append(s)
            out.append(s.replace("/0", "/ ").replace("-0", "- "))       # space-padded
            out.append(s.replace("/0", "/").replace("-0", "-").lstrip("0"))    # unpadded
            out.append(s.upper() if rng.random() < 0.5 else s.lower())
            out.append(s.replace(" ", "  ").replace(",", ",\t"))
            chars = list(s)                                              # damaged: one character dropped,
            i = rng.randrange(len(chars))                               # changed, or added
            k = rng.random()
            if k < 0.33:
                del chars[i]
            elif k < 0.66:
                chars[i] = rng.choice("0123456789 /-:,Tt.xA")
            else:
                chars.insert(i, rng.choice("0123456789 /-:,T"))
            out.append("".join(chars))
        out.append(d.strftime("%Y") + str(d.month) + str(d.day))          # 2024111
        out.append(d.strftime("%Y") + str(d.month) + " " + str(d.day))    # 20241 5
    out += ["٢٠٢٤-٠١-٠٥", "٢٠٢٤٠١٠٥", "2024-02-30", "2023-02-29", "13/13/2024", "0/5/2024", "Janu 5, 2024",
            "5-Janv-2024", "2024-01-05 10:00:00", "2024-01-05T24:00:00", "abc", "1e10", "12/31/2024 ",
            "\t5/6/2024\t", datetime(2024, 1, 5), date(2024, 1, 5)]
    for vs in EDGES.values():
        out += vs
    return out


def test_the_date_gates_turn_away_nothing_strptime_reads():
    values = [str(v).strip() for v in _values(random.Random(26)) if isinstance(v, str)]
    assert len(values) > 20000
    missed = [(pat, s) for s in values for pat in DATE_PATTERNS
              if ingest._DATE_GATES[pat](s) is None and _reads(s, pat)]
    assert missed == []
    # and not so loose they gate nothing: a plain decimal is turned away by every one
    assert all(ingest._DATE_GATES[p]("52.31") is None for p in DATE_PATTERNS)


def test_space_padded_short_and_iso_values_still_read_as_dates():
    for pat, vs in EDGES.items():
        for s in (v.strip() for v in vs):                   # stripped, as the detector strips: " 5/ 6/2024"
            assert _reads(s, pat), (pat, s)                 # strptime reads it: the edge is real
            assert ingest._DATE_GATES[pat](s) is not None, (pat, s)
        got = ingest.detect_date_format("D", vs)
        assert got == _old_detect("D", vs) and got.fits[pat] == len(vs), (pat, got.fits)


def test_the_new_detector_counts_exactly_what_strptime_alone_counted():
    rng = random.Random(7)
    pool = _values(rng)
    columns = [pool[i:i + 97] for i in range(0, len(pool), 97)]                    # mixed columns
    columns += [[v for v in pool if isinstance(v, str) and _reads(v.strip(), p)][:200] for p in DATE_PATTERNS]
    columns += [rng.sample(pool, 150) for _ in range(40)] + [[], [None, ""], ["2024111", "20241105"]]
    for i, col in enumerate(columns):
        assert ingest.detect_date_format(f"C{i}", col) == _old_detect(f"C{i}", col), i


def test_plain_numbers_never_reach_strptime(monkeypatch):
    calls = []

    class Counting(datetime):
        @classmethod
        def strptime(cls, s, fmt):
            calls.append((s, fmt))
            return datetime.strptime(s, fmt)

    monkeypatch.setattr(ingest, "datetime", Counting)
    got = ingest.detect_date_format("BAL", ["52.31", "1,204.50", "-7", "$300", "0.25", "41.1"])
    assert calls == [] and max(got.fits.values()) == 0
    ingest.detect_date_format("D", ["1/5/2024"])
    assert calls                                              # a value shaped like a date still goes to strptime


# --------------------------------------------------------------------------
# 2. Facts once per column, numbers once per value


def _extract(tmp_path, n=400):
    return synth.write_extract(tmp_path, n=n)


def test_set_up_works_out_each_columns_facts_once(tmp_path, monkeypatch):
    x = _extract(tmp_path)
    seen, detected = [], []
    real_facts, real_detect = meanings.facts, meanings.detect_date_format
    monkeypatch.setattr(meanings, "facts", lambda t, c: seen.append(c) or real_facts(t, c))
    monkeypatch.setattr(meanings, "detect_date_format", lambda c, v: detected.append(c) or real_detect(c, v))
    made = book.set_up(x, memory_path=tmp_path / "memory.yaml")
    assert made.ok, made.lines
    columns = ingest.read_table(x).columns
    assert sorted(seen) == sorted(columns) and sorted(detected) == sorted(columns)


def test_look_reads_no_number_set_up_already_read(tmp_path, monkeypatch):
    x = _extract(tmp_path)
    calls = []
    real = look.parse_number
    monkeypatch.setattr(look, "parse_number", lambda v: calls.append(v) or real(v))
    made = book.set_up(x, memory_path=tmp_path / "memory.yaml")
    assert made.ok and "Look" in __import__("openpyxl").load_workbook(made.book).sheetnames
    assert calls == []


def test_facts_handed_down_give_the_same_answers_as_facts_worked_out_again():
    rng = random.Random(3)
    rows = [{"ID": f"L{i}", "FICO": rng.choice([rng.randint(560, 820), "", "n/a", 9999]),
             "BAL": f"{rng.uniform(1000, 90000):,.2f}", "CHAN": rng.choice(["Broker", "Branch", "Web", ""]),
             "OPENED": rng.choice(["1/5/2024", "12/31/2023", "", "2/ 9/2024"]), "BAD": rng.choice([0, 1, "x"]),
             "ONE": "same", "EMPTY": ""} for i in range(600)]
    t = table(rows)
    known = meanings.facts_of(t)
    assert profile.classify(t, 12, 50, known) == profile.classify(t, 12, 50)
    sugg = meanings.suggest(t)
    assert meanings.suggest(t, known=known) == sugg
    assert meanings.review(t, sugg, known=known) == meanings.review(t, sugg)
    for c in t.columns:
        assert look.shape_of(t, c, known[c]) == look.shape_of(t, c), c
    cols = profile.classify(t, 12, 50)
    assert look.number_columns(t, cols, 12, known) == look.number_columns(t, cols, 12)


# --------------------------------------------------------------------------
# 3. settings.yaml once per Run, and never stale


def test_a_run_reads_settings_yaml_once(tmp_path, monkeypatch):
    from test_book import _answer
    x = _extract(tmp_path, n=3000)
    reads = []
    real = control._read_settings
    monkeypatch.setattr(control, "_read_settings", lambda path=None: reads.append(path) or real(path))
    made = book.set_up(x, memory_path=tmp_path / "memory.yaml")
    assert made.ok and reads == [None]
    _answer(made.book)
    reads.clear()
    ran = book.run(made.book, memory_path=tmp_path / "memory.yaml")
    assert ran.ok, ran.lines
    assert reads == [None]


def test_an_edit_to_settings_between_two_runs_is_read(tmp_path):
    p = tmp_path / "settings.yaml"
    text = resources.files("pocketbook").joinpath("settings.yaml").read_text(encoding="utf-8")
    p.write_text(text, encoding="utf-8")

    @control.settings_once
    def a_run():
        first = control.load_settings(p)
        return first, control.load_settings(p)

    one, again = a_run()
    assert [s.question for s in one] == [s.question for s in again]
    raw = yaml.safe_load(text)
    raw["groups"][0]["settings"][0]["question"] = "Edited between two runs"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    two, _ = a_run()
    assert two[0].question == "Edited between two runs" != one[0].question
    raw["groups"][0]["settings"][0]["question"] = "Edited after the run"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert control.load_settings(p)[0].question == "Edited after the run"       # outside a run: read fresh
