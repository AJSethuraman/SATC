"""Readings: where each series sits in its own history, and whether its change
is inside its normal movement. Nothing is rated (the firm, 22 Oct 2026: "We
are not rating these. At most these are directional").

Two readings, following the report's rules by type of series:

    position  the latest value, and the share of every value in the history
              window it is at or above, counted from the lowest. It says where
              the reading sits, not whether that is good or bad.
    change    the change over the firm's horizon, in points for a rate or a
              spread and in percent for a level that grows, against its normal
              movement: the median of every such change in the window, plus or
              minus the firm's width of typical moves. A typical move is 1.4826
              times the median distance of the changes from their median, the
              measure the loss thresholds use for ordinary year-to-year movement
              (threshold-engine scale.py); a spike does not widen it. Inside the
              range the change reads Stable; at or past its top edge,
              Increasing; at or past its bottom edge, Decreasing. A change on an
              edge reads as moving, as a tie went to the warning when the tool
              rated (the firm's settings, 16 Oct 2026).

The quarters the firm leaves out are taken out before anything is measured: a
reading in one is not part of any history, and a change with either end in one
is not counted. The latest reading is part of its own window.

Every reading carries what a reader needs to judge it: the value and its date,
how many readings it is measured against and where that history starts, the
pull the data came from, and for a change its normal range and how long it has
read the same way, each earlier change read against the same range. The report
asks for the last because of 2022-25: a one-month crossing should look like
one. Nothing here has a default; the settings refuse until every answer is in.
"""
import bisect
import calendar
import datetime
import hashlib
import json
import pathlib
import statistics

from . import pull as P
from .catalog import BY_KEY, DERIVED_BY_KEY, READ
from .settings import Refused, left_out_set, quarter_of, readings_of

#: Book 1's scale (threshold-engine scale.py): a median absolute deviation times this is a standard deviation
#: for changes shaped like a bell.
TYPICAL = 1.4826
INCREASING, STABLE, DECREASING = "Increasing", "Stable", "Decreasing"
DIRECTIONS = (DECREASING, STABLE, INCREASING)

#: Sahm, Hamilton Project 2019 (report, "Published flags"): the 3-month average
#: unemployment rate 0.50 points or more above its low of the prior 12 months.
#: Shown beside the change, never used to read it.
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


def percentile(x, ordered):
    """The share of ``ordered`` (sorted ascending) that ``x`` is at or above, counted from the lowest: the
    highest reading is 100%."""
    return 100.0 * bisect.bisect_right(ordered, x) / len(ordered)


def normal_range(values, width):
    """(median, typical move, low edge, high edge) of a history of changes."""
    med = statistics.median(values)
    typical = TYPICAL * statistics.median(abs(v - med) for v in values)
    return med, typical, med - width * typical, med + width * typical


def direction(v, low, high):
    """Which way a change reads against its normal range. A change on an edge reads as moving."""
    if v >= high:
        return INCREASING
    if v <= low:
        return DECREASING
    return STABLE


def kept(points, left_out):
    """``points`` with every reading in a quarter left out made missing, so nothing measures against it and
    no change has an end in it."""
    if not left_out:
        return list(points)
    out_ = left_out_set(left_out)
    return [(d, None if quarter_of(d) in out_ else v) for d, v in points]


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


def sahm_kept(points, left_out):
    """The Sahm reading from the months kept, and none dated in a quarter left out: its average borrows the
    months either side of a gap, as FRED's does, so a month left out would otherwise still be dated (Codex on
    #471)."""
    out_ = left_out_set(left_out)
    return [(d, v) for d, v in sahm(kept(points, left_out)) if quarter_of(d) not in out_]


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
    if item.key == "real_wages_eci":
        prices = dict(inputs["cpi_nsa"])
        out = []
        for d, v in inputs["wages_eci_nsa"]:
            price = prices.get("%s-%02d-01" % (d[:4], int(d[5:7]) + 2))      # the quarter's last month
            out.append((d, None) if v is None or price is None else (d, round(v / price * 100, 10)))
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


def _unit(item, reading):
    return item.unit if reading == "position" else ("percent" if item.change_in == "percent" else "points")


def _signed(item, v):
    """A change in words: +0.4 points, -2.1%."""
    return "%s%s%s" % ("+" if v > 0 else "", _num(v), "%" if item.change_in == "percent" else " points")


def window_of(item, reading, points, settings):
    """The readings a reading is measured against, or None with the reason there are none."""
    points = kept(points, settings["left_out"])
    if reading == "position":
        dated = [(d, v) for d, v in points if v is not None]
    else:
        dated = changes(points, settings["change_months"], item.frequency, item.change_in)
    window = in_window(dated, settings["history"])
    if window:
        return window, None
    # Said as the cause, in a sentence (Fable on #452: "no changes readings in the pull", for a quarterly
    # series whose pull held every quarter and whose horizon no change could land on).
    if dated:
        return None, "none of its %s falls in the last %d years" % (
            "values" if reading == "position" else "changes", settings["history"]["years"])
    if reading == "position":
        return None, ("the pull holds no values for it" if not settings["left_out"] else
                      "the pull holds no values for it outside the quarters left out")
    return None, "no change over %d months can be counted: no reading has one that far before it%s" % (
        settings["change_months"], " outside the quarters left out" if settings["left_out"] else "")


def _left_out_after(item, points, date, settings):
    """The latest published reading, when it is later than ``date`` and falls in a quarter left out."""
    published = [d for d, v in points if v is not None]
    if settings["left_out"] and published and published[-1] > date and \
            quarter_of(published[-1]) in left_out_set(settings["left_out"]):
        return published[-1]
    return None


def _base(item, reading, points, settings, window):
    date, value = window[-1]
    out = {"key": item.key, "title": item.title, "group": item.group, "reading": reading,
           "unit": _unit(item, reading), "frequency": item.frequency, "date": date, "value": value,
           "readings": len(window), "history_from": window[0][0], "care": bool(getattr(item, "care", "")),
           # The wording the publisher's licence requires wherever its data are shown, carried with the data so
           # every output that prints them can print it (Codex on #452).
           **({"credit": item.credit} if getattr(item, "credit", "") else {})}
    later = _left_out_after(item, points, date, settings)
    if later:
        out["left_out_after"] = later
    return out


def describe_level(item, points, settings):
    """Where the latest value sits in its history window, or None with the reason there is none."""
    window, why = window_of(item, "position", points, settings)
    if window is None:
        return None, why
    ordered = sorted(v for _, v in window)
    out = _base(item, "position", points, settings, window)
    pct = percentile(out["value"], ordered)
    out.update(percentile=pct, lowest=ordered[0], highest=ordered[-1])
    out["sentence"] = "%s: %s %s, at or above %.1f%% of the %s readings since %s (lowest %s, highest %s).%s" % (
        _when(out["date"], item.frequency), _num(out["value"]), item.unit, pct, "{:,}".format(len(window)),
        _when(window[0][0], item.frequency), _num(ordered[0]), _num(ordered[-1]), _later(out, item))
    return out, None


def _later(out, item):
    if "left_out_after" not in out:
        return ""
    return " Later readings, to %s, fall in quarters left out." % _when(out["left_out_after"], item.frequency)


def describe_change(item, points, settings):
    """The latest change against its normal movement, or None with the reason there is none."""
    window, why = window_of(item, "change", points, settings)
    if window is None:
        return None, why
    if len(window) < 2:
        return None, "only one change over %d months in its history, so it has no normal movement to read " \
                     "against" % settings["change_months"]
    values = [v for _, v in window]
    width = settings["normal_width"]
    med, typical, low, high = normal_range(values, width)
    if typical == 0:
        return None, ("at least half of its %s changes over %d months equal the median change, so its typical "
                      "move is zero and no range is normal" % ("{:,}".format(len(values)), settings["change_months"]))
    out = _base(item, "change", points, settings, window)
    v = out["value"]
    now = direction(v, low, high)
    held, since = 0, out["date"]
    for d, x in reversed(window):
        if direction(x, low, high) != now:
            break
        held, since = held + 1, d
    movement = (v - med) / typical
    ordered = sorted(values)
    out.update(direction=now, median=med, typical=typical, normal_low=low, normal_high=high, movement=movement,
               width=width, since=since, held=held, lowest=ordered[0], highest=ordered[-1])
    moves = "one typical move" if width == 1 else "%s typical moves" % _num(width)
    out["sentence"] = (
        "Change over %d months to %s: %s, %s typical moves %s the median change. Normal range %s to %s: the "
        "median, %s, plus or minus %s of %s, from %s changes since %s. %s since %s (%s %s).%s" % (
            settings["change_months"], _when(out["date"], item.frequency), _signed(item, v), "%.1f" % abs(movement),
            "above" if movement >= 0 else "below", _signed(item, low), _signed(item, high), _signed(item, med),
            moves, _signed(item, typical).lstrip("+"), "{:,}".format(len(window)),
            _when(window[0][0], item.frequency), now, _when(since, item.frequency), "{:,}".format(held),
            "reading" if held == 1 else "readings", _later(out, item)))
    return out, None


def describe(item, reading, points, settings):
    return (describe_level if reading == "position" else describe_change)(item, points, settings)


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

    def raw(self, name):
        """A file's bytes as this run read them, the ones read_sha fingerprints; None when nothing read it."""
        return self._bytes.get(name)

    def points(self, item):
        if item.key in DERIVED_BY_KEY:
            got = {k: self._get(k) for k in item.inputs}
            bad = [v for v in got.values() if isinstance(v, str)]
            return bad[0] if bad else derive(item, got)
        return self._get(item.key)


def read_all(cache, settings, vintage=None, pull=None):
    """Every reading the catalog holds, from one pull of CACHE: the core group, then the usable-with-care
    group, each series on its level (where that means something) and its change."""
    pull = pull or Pull(cache, vintage)
    out, not_read, alongside = [], [], []
    for item in READ:
        points = pull.points(item)
        for reading in readings_of(item):
            got, why = (None, points) if isinstance(points, str) else describe(item, reading, points, settings)
            if got is None:
                not_read.append({"key": item.key, "reading": reading, "why": why,
                                 "care": bool(getattr(item, "care", ""))})
            else:
                out.append(got)
    if settings["show_sahm"]:
        u = pull.points(BY_KEY["unemployment"])
        # Worked from the months kept, as every reading is (Codex on #471: a quarter left out still moved it).
        s = sahm_kept(u, settings["left_out"]) if not isinstance(u, str) else []
        if s:
            d, v = s[-1]
            alongside.append({
                "key": "unemployment", "what": "Sahm reading", "date": d, "value": v, "trigger": SAHM_TRIGGER,
                "sentence": "Sahm reading for %s: %.2f points (3-month average unemployment minus its lowest in "
                            "the 12 months before; Sahm's published trigger is 0.50). Shown beside the change, "
                            "never used to read it." % (_when(d, "monthly"), v)})
    # The fingerprint of every file as this run read it, kept with the readings it produced, so a workbook built
    # from another Pull can be checked against it (Codex on #452).
    return {"vintage": pull.vintage, "settings": dict(settings), "readings": out, "not_read": not_read,
            "alongside": alongside, "read_sha": dict(pull.read_sha)}
