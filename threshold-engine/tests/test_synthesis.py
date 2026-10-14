"""synthesis: the three perspectives side by side, each line taken from the
source the firm names. The series are made up; the right answers are worked
from scale.py and the stated translations, independently of the module."""
import statistics

import pytest

from conftest import SCALE
from threshold_engine.cli import main
from threshold_engine.profile import percentile
from threshold_engine.scale import scale, score
from threshold_engine.series import Point
from threshold_engine.synthesis import synthesize

SETTINGS = dict(direction="higher_is_worse", halfwidth=SCALE["halfwidth"], low_step=SCALE["low_step"],
                high_z=SCALE["high_z"], floor_at_zero=True, on_the_line="worse")


def qe(year, q):
    return "%d-%s" % (year, ("03-31", "06-30", "09-30", "12-31")[q - 1])


def series(first_year, values):
    return [Point(qe(first_year + i // 4, i % 4 + 1), v) for i, v in enumerate(values)]


#: Industry 2006-2025 with a crisis in 2009-10; internal 2014-2025 running at
#: about 0.8 of it; filed about 1.25 x internal; five peers.
WAVE = [0.0, 0.1, 0.2, 0.1, 0.0, -0.1, -0.2, -0.1]
INDUSTRY = series(2006, [1.0 + WAVE[i % 8] + (2.5 if 12 <= i < 20 else 0.0) for i in range(80)])
INTERNAL = series(2014, [0.8 * (1.0 + WAVE[(i + 32) % 8]) + 0.01 * (i % 3) for i in range(48)])
FILED = [Point(p.date, p.value * 1.25) for p in INTERNAL]
PEERS = {"p%d" % k: series(2014, [m * (1.0 + 0.05 * WAVE[i % 8]) for i in range(48)])
         for k, m in enumerate([0.6, 0.9, 1.0, 1.3, 2.0])}
PCT = [20, 40, 75, 95]


def run(leads, **kw):
    args = dict(SETTINGS, translation="median ratio", peer_percentiles=PCT, leads=leads)
    args.update(kw)
    return synthesize(INTERNAL, INDUSTRY, FILED, PEERS, **args)


def test_each_candidate_is_worked_independently():
    r = run(["internal", "internal", "internal", "industry"])
    # A calm history: the scale refuses High (nothing kept could rate it), and
    # lines 2-4 still stand, worked from the median and the typical yearly move.
    ref = scale([p.value for p in INTERNAL], "higher_is_worse", 0.5, 1.0, 2.5, True)
    assert ref["bounds"] is None and ref["refused"].startswith("High would begin beyond the worst")
    med, move = ref["median"], ref["typical_yearly_move"]
    own = [med - 1.0 * move, med - 0.5 * move, med + 0.5 * move]
    assert r["candidates"]["internal"]["lines"][:3] == pytest.approx(own)
    assert r["candidates"]["internal"]["lines"][3] is None
    assert r["candidates"]["internal"]["refused"].startswith("line 5: High would begin")
    ratio = statistics.median(a.value / b.value for a, b in zip(INTERNAL, INDUSTRY[32:]))
    ind = scale([p.value for p in INDUSTRY], "higher_is_worse", 0.5, 1.0, 2.5, True)["bounds"]
    assert r["candidates"]["industry"]["ratio"] == pytest.approx(ratio)
    assert r["candidates"]["industry"]["lines"] == pytest.approx([b * ratio for b in ind])
    meds = sorted(statistics.median(p.value for p in pts) for pts in PEERS.values())
    assert r["candidates"]["peers"]["lines"] == pytest.approx([percentile(meds, p) * 0.8 for p in PCT])
    assert r["chosen"] == pytest.approx(own[:3] + [ind[3] * ratio])
    last = INTERNAL[-1]
    assert r["latest"] == ("2025Q4", last.value)
    assert r["rating"] == score(last.value, r["chosen"], "higher_is_worse", "worse", True)


def test_the_competitive_check_is_a_count_not_a_verdict():
    r = run(["internal", "internal", "internal", "industry"])
    kb = statistics.median(p.value for p in FILED)
    assert r["check"]["filed_median"] == pytest.approx(kb)
    assert r["check"]["worse_than"] == sum(1 for pts in PEERS.values()
                                           if statistics.median(p.value for p in pts) < kb)
    assert r["check"]["peers"] == 5


def test_none_takes_the_industry_lines_as_they_are():
    r = run(["internal", "internal", "internal", "industry"], translation="none")
    ind = scale([p.value for p in INDUSTRY], "higher_is_worse", 0.5, 1.0, 2.5, True)["bounds"]
    assert r["candidates"]["industry"]["lines"] == pytest.approx(ind)


def test_lines_out_of_order_are_refused_by_name():
    with pytest.raises(ValueError, match="5 High .*does not begin beyond 4 Moderate-High"):
        run(["internal", "internal", "industry", "peers"], peer_percentiles=[1, 2, 3, 4])


@pytest.mark.parametrize("bad", [["internal"] * 3, ["internal", "internal", "internal", "fed"], "internal"])
def test_every_line_needs_a_named_source(bad):
    with pytest.raises(ValueError, match="leads names the source"):
        run(bad)


def test_peers_lead_nothing_without_peer_series():
    with pytest.raises(ValueError, match="led by peers, which has no such line: not built"):
        synthesize(INTERNAL, INDUSTRY, None, {}, translation="median ratio", peer_percentiles=None,
                   leads=["internal", "internal", "internal", "peers"], **SETTINGS)
    r = synthesize(INTERNAL, INDUSTRY, None, {}, translation="median ratio", peer_percentiles=None,
                   leads=["internal", "internal", "internal", "industry"], **SETTINGS)
    assert r["check"] is None and r["candidates"]["peers"]["lines"] is None


@pytest.mark.parametrize("pct", [None, [20, 40, 40, 95], [20, 40, 75, 101]])
def test_peer_percentiles_are_required_with_peers_and_must_rise(pct):
    with pytest.raises(ValueError, match="peer percentiles"):
        run(["internal", "internal", "internal", "industry"], peer_percentiles=pct)


def test_no_shared_quarter_cannot_translate():
    with pytest.raises(ValueError, match="led by industry, which has no such line: the internal and industry"):
        synthesize(INTERNAL, series(1990, [1.0] * 20), FILED, PEERS, translation="median ratio",
                   peer_percentiles=PCT, leads=["internal", "internal", "internal", "industry"], **SETTINGS)


def test_the_command(tmp_path, capsys):
    def write(name, pts):
        f = tmp_path / name
        f.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, p.value) for p in pts), encoding="utf-8")
        return str(f)
    base = ["synthesize", "--internal", write("i.csv", INTERNAL), "--industry", write("x.csv", INDUSTRY),
            "--unit", "%", "--direction", "higher_is_worse", "--moderate-halfwidth", "0.5", "--low-step", "1.0",
            "--high-z", "2.5", "--on-the-line", "worse", "--floor-at-zero", "yes", "--translation", "median ratio"]
    peers = ["--filed", write("f.csv", FILED)] + [x for k, v in PEERS.items()
                                                  for x in ("--peer", "%s=%s" % (k, write(k + ".csv", v)))]
    assert main(base + peers + ["--peer-percentiles", "20", "40", "75", "95",
                                "--leads", "internal", "internal", "internal", "industry"]) == 0
    out = capsys.readouterr().out
    assert "5 High" in out and "industry" in out and "worse than" in out and "rating" in out
    assert main(base + ["--leads", "internal", "internal", "internal", "peers"]) == 2
    assert "not built" in capsys.readouterr().err


def test_a_line_the_source_cannot_draw_cannot_be_led_from_it():
    with pytest.raises(ValueError, match="line 5 High is led by internal, which has no such line: line 5"):
        run(["internal"] * 4)


def test_a_line_2_at_or_below_zero_is_refused_under_the_floor():
    """scale.py checks High beyond the worst before Moderate-Low at or below
    zero; the partial lines must still refuse a line 2 at or below zero
    (review, 14 Oct 2026: it chose -0.156)."""
    calm = series(2014, [0.3, 0.6, 0.2, 0.7, 0.25, 0.65, 0.3, 0.6, 0.2, 0.7, 0.3, 0.5])
    args = dict(SETTINGS, low_step=5.0, high_z=3.0, translation="median ratio", peer_percentiles=None,
                leads=["internal", "internal", "internal", "industry"])
    with pytest.raises(ValueError, match="led by internal, which has no such line: Moderate-Low would "
                                         "begin at or below zero"):
        synthesize(calm, INDUSTRY, None, {}, **args)


def test_a_gap_or_a_bad_date_is_refused_by_name():
    gapped = INTERNAL[:10] + INTERNAL[12:]
    with pytest.raises(ValueError, match="the internal series: .*A missing period is refused"):
        synthesize(gapped, INDUSTRY, FILED, PEERS, translation="median ratio", peer_percentiles=PCT,
                   leads=["internal", "internal", "internal", "industry"], **SETTINGS)
    bad = dict(PEERS, p0=[Point("2014-13-31", 1.0)] + PEERS["p0"][1:])
    with pytest.raises(ValueError, match="peer p0: '2014-13-31' is not a calendar date"):
        synthesize(INTERNAL, INDUSTRY, FILED, bad, translation="median ratio", peer_percentiles=PCT,
                   leads=["internal", "internal", "internal", "industry"], **SETTINGS)


def test_peers_without_the_filed_series_say_so():
    with pytest.raises(ValueError, match=r"give it \(--filed\)"):
        synthesize(INTERNAL, INDUSTRY, None, PEERS, translation="median ratio", peer_percentiles=PCT,
                   leads=["internal", "internal", "internal", "industry"], **SETTINGS)


def test_a_peer_named_twice_is_refused(tmp_path, capsys):
    f = tmp_path / "p.csv"
    f.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, p.value) for p in PEERS["p0"]), encoding="utf-8")
    i = tmp_path / "i.csv"
    i.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, p.value) for p in INTERNAL), encoding="utf-8")
    args = ["synthesize", "--internal", str(i), "--industry", str(i), "--filed", str(i),
            "--peer", "a=%s" % f, "--peer", "a=%s" % f, "--unit", "%", "--direction", "higher_is_worse",
            "--moderate-halfwidth", "0.5", "--low-step", "1.0", "--high-z", "2.5", "--on-the-line", "worse",
            "--floor-at-zero", "yes", "--translation", "none", "--peer-percentiles", "20", "40", "75", "95",
            "--leads", "internal", "internal", "internal", "internal"]
    assert main(args) == 2 and "names a twice" in capsys.readouterr().err
