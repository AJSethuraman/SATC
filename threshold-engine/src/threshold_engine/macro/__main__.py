"""python -m threshold_engine.macro list | pull | show | settings-template | read

    list                         every series in the catalog, and what is not read
    pull --cache DIR [KEY ...]   download into DIR/<today>/, keeping every earlier pull
    show --cache DIR KEY         one series as read from the newest pull (or --vintage)
    settings-template OUT.json   the firm's settings, every answer empty, to fill in
    read --cache DIR --settings FILE [--compare WHAT-IF.json]
         [--workbook OUT.xlsx [--zoom 2019Q1:2026Q2]]
                                 every reading from the newest pull (or --vintage):
                                 where each level sits, and whether each change is
                                 Increasing, Stable or Decreasing against its normal
                                 movement; refuses, naming each gap, until every
                                 answer is in. --compare reads the same pull with a
                                 second settings file and reports every change whose
                                 direction differs. --zoom draws the workbook's charts
                                 over those quarters only; no reading changes with it
"""
import argparse
import json
import pathlib
import sys

from .catalog import BY_KEY, CARE, CARE_DERIVED, CARE_NOT_READ, DERIVED, NOT_YET, SERIES
from .pull import load, pull
from .readings import Pull, read_all
from .settings import QUARTER, Refused, load as load_settings, quarter_index, write_template


def direction(s):
    """What list says of a series: an input, or which way the research reads stress in it."""
    if not s.read_alone:
        return "input, not read alone"
    return "research: " + s.stress if s.stress else "research: no direction"


def cmd_list(_):
    alone = [s for s in SERIES if s.read_alone]
    print("%d series in the catalog (%d read, %d of them usable with care; %d inputs to a derived reading)\n"
          % (len(SERIES), len(alone), len(CARE), len(SERIES) - len(alone)))
    for s in SERIES:
        if s.care:
            continue
        if s.key.startswith("unemployment_") and s.key != "unemployment_ak":
            continue
        name = "Unemployment rate by state (51: AK ... WY)" if s.key == "unemployment_ak" else s.title
        print("  %-26s %-10s %-9s from %-10s %-24s %s" % (
            "unemployment_<state>" if s.key == "unemployment_ak" else s.key, s.group, s.frequency, s.starts,
            direction(s), name))
    print("\nDerived from two of the above:")
    for d in DERIVED:
        if d.care:
            continue
        print("  %-26s %-10s %-9s from %-10s %-24s %s" % (d.key, d.group, d.frequency, "(inputs)",
                                                          direction(d), d.title))
    print("\nIn the ready-to-rate group but not read yet:")
    for what, why in NOT_YET:
        print("  %s: %s" % (what, why))
    print("\nThe usable-with-care group (why each needs care is on its workbook tab):")
    for s in CARE:
        print("  %-26s %-10s %-9s from %-10s %-24s %s" % (s.key, s.group, s.frequency, s.starts, direction(s),
                                                          s.title))
    for d in CARE_DERIVED:
        print("  %-26s %-10s %-9s from %-10s %-24s %s" % (d.key, d.group, d.frequency, "(inputs)", direction(d),
                                                          d.title))
    print("\nIn the usable-with-care group but not read:")
    for what, why in CARE_NOT_READ:
        print("  %s: %s" % (what, why))


def cmd_pull(a):
    m = pull(a.cache, keys=a.keys or None)
    ok = len(m["series"]) - len(m["failed"])
    print("pulled %d of %d series into %s/%s" % (ok, len(m["series"]), a.cache, m["pulled"]))
    for k in m["failed"]:
        print("  FAILED %s: %s" % (k, m["series"][k]["error"]))
    return 1 if m["failed"] else 0


def cmd_show(a):
    if a.key not in BY_KEY:
        raise SystemExit("not in the catalog: %s" % a.key)
    points, vintage = load(a.cache, a.key, a.vintage)
    s = BY_KEY[a.key]
    # A licence that asks for wording gets it wherever the data are printed: here, before and after them
    # (Codex on #452: show printed the NY Fed survey's numbers without it).
    print(json.dumps(dict({"key": s.key, "title": s.title, "publisher": s.publisher, "unit": s.unit,
                           "vintage": vintage, "breaks": [list(b) for b in s.breaks]},
                          **({"credit": s.credit} if s.credit else {})), indent=1))
    for d, v in points[-a.tail:]:
        print(d, "missing" if v is None else v)
    if s.credit:
        print("\n" + s.credit)


def cmd_settings_template(a):
    print("wrote %s: fill in every \"answer\", then run read --settings %s" % (write_template(a.out), a.out))


def zoom_of(text):
    """--zoom FROM:TO as two quarters, the first not after the second; Refused otherwise."""
    if text is None:
        return None
    first, _, last = text.partition(":")
    a, b = quarter_index(first), quarter_index(last)
    if not (QUARTER.match(first) and QUARTER.match(last)) or a > b:
        raise Refused("--zoom needs two quarters, the first not after the second, such as 2019Q1:2026Q2; got %r"
                      % text)
    return [first, last]


def cmd_read(a):
    settings = load_settings(a.settings)
    zoom = zoom_of(a.zoom)
    if zoom and not a.workbook:
        raise Refused("--zoom draws the workbook's charts over those quarters, so it needs --workbook")
    other = None
    if a.compare:
        try:
            other = load_settings(a.compare)
        except Refused as e:
            raise Refused("the what-if settings in %s: %s" % (a.compare, e))
    p = Pull(a.cache, a.vintage)
    result = read_all(a.cache, settings, pull=p)
    whatif = None
    if other is not None:
        from .compare import compare
        whatif = compare(result, read_all(a.cache, other, pull=p), pathlib.Path(a.settings).name,
                         pathlib.Path(a.compare).name)
    if a.workbook:
        from .workbook import build
        print("wrote %s" % build(a.workbook, result, p, whatif=whatif, zoom=zoom), file=sys.stderr)
    if a.json:
        print(json.dumps(dict(result, compare=whatif) if whatif else result, indent=1))
        return 0
    if whatif:
        from .compare import lines
        print("\n".join(lines(whatif)))
        return 0
    from .compare import plain
    s = result["settings"]
    print("Readings from the pull of %s. History: %s. Change over %d months. Normal movement: %s. Quarters left "
          "out: %s.\n" % (result["vintage"], plain("history", s), s["change_months"], plain("normal_width", s),
                          plain("left_out", s)))
    order = {"Increasing": 0, "Decreasing": 1, "Stable": 2}
    for group, care in (("Core", False), ("Usable with care", True)):
        print(group + ":")
        mine = [r for r in result["readings"] if r["care"] == care]
        for r in sorted(mine, key=lambda r: (r["reading"] != "change", order.get(r.get("direction"), 3),
                                             -abs(r.get("movement", 0)), r["key"])):
            print("  %-10s %-26s %-8s %s" % (r.get("direction", ""), r["key"], r["reading"], r["sentence"]))
        print()
    for x in result["alongside"]:
        print("  %s\n" % x["sentence"])
    missed = result["not_read"] + result.get("picked_not_read", [])
    if missed:
        print("Not read:")
        for x in missed:
            print("  %-26s %-8s %s" % (x["key"], x["reading"], x["why"]))
    for credit in sorted({x["credit"] for x in result["readings"] if x.get("credit")}):
        print("\n  %s" % credit)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m threshold_engine.macro", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="every series in the catalog")
    pp = sub.add_parser("pull", help="download into DIR/<today>/")
    pp.add_argument("--cache", required=True)
    pp.add_argument("keys", nargs="*")
    ps = sub.add_parser("show", help="one series from a pull")
    ps.add_argument("--cache", required=True)
    ps.add_argument("key")
    ps.add_argument("--vintage")
    ps.add_argument("--tail", type=int, default=12)
    pt = sub.add_parser("settings-template", help="the firm's settings to fill in")
    pt.add_argument("out")
    pr = sub.add_parser("read", help="every reading from a pull")
    pr.add_argument("--cache", required=True)
    pr.add_argument("--settings", required=True)
    pr.add_argument("--vintage")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--workbook", metavar="OUT.xlsx", help="also write the workbook the teams read")
    pr.add_argument("--zoom", metavar="FROM:TO", help="draw the workbook's charts over these quarters only, "
                    "such as 2019Q1:2026Q2; no reading changes")
    pr.add_argument("--compare", metavar="WHAT-IF.json",
                    help="a second settings file: read the same pull with it and show what changes")
    a = p.parse_args(argv)
    commands = {"list": cmd_list, "pull": cmd_pull, "show": cmd_show,
                "settings-template": cmd_settings_template, "read": cmd_read}
    try:
        return commands[a.command](a) or 0
    except Refused as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
