"""Ratings: where each series stands in its own history, 1 Low to 5 High.

Two readings, following the report's rules by type of series:

    position  the latest value against every value in the history window
    change    the change over the firm's horizon against every such change in
              the window, in points for a rate or spread and in percent for a
              level that grows

Each reading is a percentile: the share of the window that the latest reading
is at or above (where higher is worse) or at or below (where lower is worse).
The latest reading is part of its own window, so a new record is 100%. The
firm's four cut-offs turn the percentile into a rating. Nothing here has a
default; the settings refuse until every answer is in.

Every rating carries what a reader needs to judge it: the value and its date,
the percentile and how many readings it is measured against, where that
history starts, the pull the data came from, and how long the series has held
the rating, with each earlier reading rated against the same window. The
report asks for the last because of 2022-25: a one-month crossing should look
like one.
"""
import bisect
import calendar
import datetime
import hashlib
import json
import pathlib

from . import pull as P
from .catalog import BY_KEY, DERIVED_BY_KEY, HIGHER, RATED
from .settings import NOT_RATED, Refused, readings_of

#: Sahm, Hamilton Project 2019 (report, "Published flags"): the 3-month average
#: unemployment rate 0.50 points or more above its low of the prior 12 months.
#: Shown beside the rating, never used to make it.
SAHM_TRIGGER = 0.50

#: How far from the date a horizon earlier a reading may be and still count as
#: "then". Only weekly readings get leeway, for a release moved by a holiday.
NEAREST_DAYS = {"daily": 0, "weekly": 3, "monthly": 0, "quarterly": 0}


def _day(d):
    return datetime.date.fromisoformat(d[:10])


def months_back(day, n):
    """The same day of the month ``n`` months earlier (the month's last day if shorter)."""
    y, m = divmod(day.year * 12 + day.month - 1 - n, 12)
    return datetime.date(y, m + 1, min(day.day, calendar.monthrange(y, m + 1)[1]))


def then_date(day, months, frequency):
    """The date a horizon of ``months`` before ``day``. Weekly and daily series
    count whole weeks (12 months is 52), as FRED's own change from a year ago
    does: a daily reading is compared with the same weekday, and a week whose
    release moved for a holiday with the same week a year before. Monthly and
    quarterly series count calendar months. Checked 15 Oct 2026 against FRED's
    change from a year ago for 13 series, every date: all agree."""
    if frequency in ("weekly", "daily"):
        return day - datetime.timedelta(weeks=round(months * 52 / 12))
    return months_back(day, months)


def changes(points, months, frequency, change_in):
    """Every change over ``months``: each reading against the one nearest the
    date that horizon earlier (on a tie, the earlier one). A reading with
    nothing close enough then has no change; nothing is filled in."""
    present = [(_day(d), v) for d, v in points if v is not None]
    days = [d for d, _ in present]
    allowed = NEAREST_DAYS[frequency]
    out = []
    for d, v in present:
        target = then_date(d, months, frequency)
        i = bisect.bisect_left(days, target)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(days) and days[j] < d and abs((days[j] - target).days) <= allowed:
                if best is None or abs((days[j] - target).days) < abs((days[best] - target).days):
                    best = j
        if best is None:
            continue
        then = present[best][1]
        if change_in == "percent":
            if then <= 0:
                continue
            out.append((d.isoformat(), round(100.0 * (v / then - 1), 10)))
        elif change_in == "points":
            out.append((d.isoformat(), round(v - then, 10)))
        else:
            raise ValueError("a change is counted in points or percent, not %r" % (change_in,))
    return out


def in_window(dated, history):
    """The readings inside the firm's history window, which ends at the latest."""
    if history == "full" or not dated:
        return list(dated)
    start = months_back(_day(dated[-1][0]), 12 * history["years"])
    return [(d, v) for d, v in dated if _day(d) > start]


def percentile(x, ordered, direction):
    """The share of ``ordered`` (sorted ascending) that ``x`` is at or beyond, in
    the direction of stress: at or above where higher is worse, at or below
    where lower is worse."""
    if direction == HIGHER:
        k = bisect.bisect_right(ordered, x)
    else:
        k = len(ordered) - bisect.bisect_left(ordered, x)
    return 100.0 * k / len(ordered)


def rating(pct, cutoffs, on_the_line):
    """1 plus the number of the firm's cut-offs the percentile reaches."""
    if on_the_line == "worse":
        return 1 + sum(1 for c in cutoffs if pct >= c)
    return 1 + sum(1 for c in cutoffs if pct > c)


def sahm(points):
    """The Sahm reading each month: the 3-month average unemployment rate minus
    its lowest 3-month average in the 12 months before. Where one month has no
    value (October 2025), the average is taken from the two that do, as FRED's
    SAHMCURRENT does; this reproduces all 931 of its values (15 Oct 2026)."""
    vals = [v for _, v in points]
    avgs = []
    for i in range(len(vals)):
        have = [x for x in vals[max(0, i - 2):i + 1] if x is not None]
        avgs.append(sum(have) / len(have) if i >= 2 and len(have) >= 2 else None)
    out = []
    for i, (d, _) in enumerate(points):
        prior = avgs[i - 12:i] if i >= 12 else []
        if avgs[i] is None or len(prior) < 12 or None in prior:
            continue
        out.append((d, round(avgs[i] - min(prior), 10)))
    return out


def derive(item, inputs):
    """A derived reading's points from its inputs' points (both from one pull)."""
    if item.key == "house_price_to_income":
        income = dict(inputs["income_per_person"])
        out = []
        for d, v in inputs["house_prices"]:
            y, m = int(d[:4]), int(d[5:7])
            months = [income.get("%04d-%02d-01" % (y, m + i)) for i in range(3)]
            if v is None or None in months:
                out.append((d, None))
            else:
                out.append((d, round(v / (sum(months) / 3 / 1000), 10)))
        return out
    if item.key == "mortgage_spread":
        tsy = [(_day(d), v) for d, v in inputs["treasury_10y"] if v is not None]
        days = [d for d, _ in tsy]
        out = []
        for d, v in inputs["mortgage_rate"]:
            i = bisect.bisect_right(days, _day(d)) - 1
            if v is None or i < 0 or (_day(d) - days[i]).days > 6:
                out.append((d, None))
            else:
                out.append((d, round(v - tsy[i][1], 10)))
        return out
    raise ValueError("no way to derive %r" % item.key)


def _when(d, frequency):
    day = _day(d)
    if frequency == "quarterly":
        return "%d Q%d" % (day.year, (day.month - 1) // 3 + 1)
    if frequency == "monthly":
        return "%s %d" % (calendar.month_abbr[day.month], day.year)
    return "%d %s %d" % (day.day, calendar.month_abbr[day.month], day.year)


def _num(x):
    a = abs(x)
    if a >= 1000:
        return "{:,.0f}".format(x)
    if a >= 1:
        return ("%.2f" % x).rstrip("0").rstrip(".")
    return "0" if x == 0 else "%.3g" % x


def rate_reading(item, reading, points, settings, direction):
    """One rating, or None with the reason when there is nothing to rate."""
    if reading == "position":
        dated = [(d, v) for d, v in points if v is not None]
    else:
        dated = changes(points, settings["change_months"], item.frequency, item.change_in)
    window = in_window(dated, settings["history"])
    if not window:
        # Said as the cause, in a sentence (Fable on #452: "no changes readings in the pull", for a quarterly
        # series whose pull held every quarter and whose horizon no change could land on).
        if dated:
            return None, "none of its %s falls in the last %d years" % (
                "values" if reading == "position" else "changes", settings["history"]["years"])
        if reading == "position":
            return None, "the pull holds no values for it"
        return None, "no change over %d months can be counted: no reading has one that far before it" % (
            settings["change_months"])
    ordered = sorted(v for _, v in window)
    cut, line = settings["cutoffs"], settings["on_the_line"]

    def rated(v):
        return rating(percentile(v, ordered, direction), cut, line)

    date, value = window[-1]
    pct = percentile(value, ordered, direction)
    r = rated(value)
    # Where each rating starts, in the reading's own units: the least extreme
    # value in this history that took it. None if no value in it reached it.
    lines = {}
    for want in range(2, 6):
        scan = ordered if direction == HIGHER else reversed(ordered)
        lines[str(want)] = next((v for v in scan if rated(v) >= want), None)
    counts = {str(k): 0 for k in range(1, 6)}       # how many readings in this history took each rating
    for v in ordered:
        counts[str(rated(v))] += 1
    held, since = 0, date
    for d, v in reversed(window):
        if rated(v) != r:
            break
        held, since = held + 1, d
    side = "above" if direction == HIGHER else "below"
    when, start = _when(date, item.frequency), _when(window[0][0], item.frequency)
    if reading == "position":
        what = "%s: %s %s" % (when, _num(value), item.unit)
        among = "%s readings since %s" % ("{:,}".format(len(window)), start)
    else:
        sign = "+" if value > 0 else ""
        unit = "%" if item.change_in == "percent" else " points"
        what = "Change over %d months to %s: %s%s%s" % (settings["change_months"], when, sign, _num(value), unit)
        among = "%s such changes since %s" % ("{:,}".format(len(window)), start)
    nxt = "; %d starts at %s%%" % (r + 1, _num(cut[r - 1])) if r < 5 else ""
    sentence = "%s: at or %s %.1f%% of the %s. Rated %d%s. Rated %d since %s (%s %s)." % (
        what, side, pct, among, r, nxt, r, _when(since, item.frequency), "{:,}".format(held),
        "reading" if held == 1 else "readings")
    return {
        "key": item.key, "title": item.title, "group": item.group, "reading": reading,
        "direction": direction, "direction_from": "research" if item.stress else "firm",
        "unit": item.unit if reading == "position" else ("percent" if item.change_in == "percent" else "points"),
        "frequency": item.frequency, "date": date, "value": value, "percentile": pct, "rating": r,
        "readings": len(window), "history_from": window[0][0], "since": since, "held": held,
        "lines": lines, "counts": counts, "low": ordered[0], "high": ordered[-1],
        "sentence": sentence, "breaks": [list(b) for b in item.breaks],
    }, None


class Pull:
    """One pull folder: its manifest, and each series' points read once.

    ``points`` gives a list of (date, value), or a string saying why there is
    none (the series failed or is not in this pull). Each file is read once;
    ``read_sha`` gives the SHA-256 of each file's bytes as they were read."""

    def __init__(self, cache, vintage=None):
        folder = pathlib.Path(cache) / vintage if vintage else P.latest(cache)
        if folder is None or not (folder / "manifest.json").exists():
            raise Refused("no pull %sunder %s: run python -m threshold_engine.macro pull --cache %s"
                          % ("named %s " % vintage if vintage else "", cache, cache))
        self.cache, self.folder, self.vintage = cache, folder, folder.name
        self.manifest = json.loads((folder / "manifest.json").read_text("utf-8"))
        self._loaded, self._bytes = {}, {}

    def _get(self, key):
        if key not in self._loaded:
            recorded = self.manifest.get("series", {}).get(key, {}).get("error")
            if recorded:
                # The pull already recorded that it could not fetch or read this one: not rated, with its
                # reason. Reading it again raised what nothing caught (Fable on #452: an HTML page where
                # FHFA's zip belonged stopped every rating with BadZipFile).
                self._loaded[key] = "not in the pull of %s (%s)" % (self.vintage, recorded)
                return self._loaded[key]
            try:
                self._loaded[key] = P.load(self.cache, key, self.vintage, read=self._bytes)[0]
            except SystemExit as e:
                self._loaded[key] = "not in the pull of %s (%s)" % (self.vintage, e)
            except Exception as e:  # a file that no longer reads: recorded as the pull records one
                self._loaded[key] = "not in the pull of %s (could not read: %s)" % (self.vintage, e)
        return self._loaded[key]

    @property
    def read_sha(self):
        return {name: hashlib.sha256(data).hexdigest() for name, data in self._bytes.items()}

    def points(self, item):
        if item.key in DERIVED_BY_KEY:
            got = {k: self._get(k) for k in item.inputs}
            bad = [v for v in got.values() if isinstance(v, str)]
            return bad[0] if bad else derive(item, got)
        return self._get(item.key)


def rate_all(cache, settings, vintage=None, pull=None):
    """Every rating the settings call for, from one pull of CACHE."""
    pull = pull or Pull(cache, vintage)
    ratings, not_rated, alongside = [], [], []
    for item in RATED:
        wanted = readings_of(item, settings["change_for"])
        points = pull.points(item)
        for reading in wanted:
            if isinstance(points, str):
                not_rated.append({"key": item.key, "reading": reading, "why": points})
                continue
            direction = item.stress or settings["directions"][(item.key, reading)]
            if direction == NOT_RATED:
                not_rated.append({"key": item.key, "reading": reading, "why": "the firm chose not to rate it"})
                continue
            out, why = rate_reading(item, reading, points, settings, direction)
            if out is None:
                not_rated.append({"key": item.key, "reading": reading, "why": why})
            else:
                ratings.append(out)
    if settings["show_sahm"]:
        u = pull.points(BY_KEY["unemployment"])
        s = sahm(u) if not isinstance(u, str) else []
        if s:
            d, v = s[-1]
            alongside.append({
                "key": "unemployment", "what": "Sahm reading", "date": d, "value": v, "trigger": SAHM_TRIGGER,
                "sentence": "Sahm reading for %s: %.2f points (3-month average unemployment minus its lowest in "
                            "the 12 months before; Sahm's published trigger is 0.50). Shown, not rated."
                            % (_when(d, "monthly"), v)})
    shown = dict(settings, directions=[[k, r, v] for (k, r), v in sorted(settings["directions"].items())])
    return {"vintage": pull.vintage, "settings": shown, "ratings": ratings, "not_rated": not_rated,
            "alongside": alongside}
