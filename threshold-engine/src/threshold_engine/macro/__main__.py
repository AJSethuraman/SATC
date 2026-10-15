"""python -m threshold_engine.macro list | pull | show | settings-template | rate

    list                         every series in the catalog, and what is not read yet
    pull --cache DIR [KEY ...]   download into DIR/<today>/, keeping every earlier pull
    show --cache DIR KEY         one series as read from the newest pull (or --vintage)
    settings-template OUT.json   the firm's settings, every answer empty, to fill in
    rate --cache DIR --settings FILE [--workbook OUT.xlsx]
                                 every rating from the newest pull (or --vintage);
                                 refuses, naming each gap, until every answer is in
"""
import argparse
import json
import sys

from .catalog import BY_KEY, DERIVED, NOT_YET, SERIES
from .pull import load, pull
from .rate import Pull, rate_all
from .settings import Refused, load as load_settings, write_template


def cmd_list(_):
    rated = [s for s in SERIES if s.rated]
    print("%d series in the catalog (%d rated, %d inputs to a derived reading)\n"
          % (len(SERIES), len(rated), len(SERIES) - len(rated)))
    for s in SERIES:
        if s.key.startswith("unemployment_") and s.key != "unemployment_ak":
            continue
        name = "Unemployment rate by state (51: AK ... WY)" if s.key == "unemployment_ak" else s.title
        print("  %-26s %-10s %-9s from %-10s %-18s %s" % (
            "unemployment_<state>" if s.key == "unemployment_ak" else s.key, s.group, s.frequency, s.starts,
            s.stress or "firm sets direction", name))
    print("\nDerived from two of the above:")
    for d in DERIVED:
        print("  %-26s %-10s %-9s %-29s %s" % (d.key, d.group, d.frequency, d.stress or "firm sets direction",
                                              d.title))
    print("\nIn the ready-to-rate group but not read yet:")
    for what, why in NOT_YET:
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
    print(json.dumps({"key": s.key, "title": s.title, "publisher": s.publisher, "unit": s.unit,
                      "vintage": vintage, "breaks": [list(b) for b in s.breaks]}, indent=1))
    for d, v in points[-a.tail:]:
        print(d, "missing" if v is None else v)


def cmd_settings_template(a):
    print("wrote %s: fill in every \"answer\", then run rate --settings %s" % (write_template(a.out), a.out))


def cmd_rate(a):
    settings = load_settings(a.settings)
    p = Pull(a.cache, a.vintage)
    result = rate_all(a.cache, settings, pull=p)
    if a.workbook:
        from .workbook import build
        print("wrote %s" % build(a.workbook, result, p), file=sys.stderr)
    if a.json:
        print(json.dumps(result, indent=1))
        return 0
    s = result["settings"]
    print("Ratings from the pull of %s. History: %s. Change over %d months. Cut-offs for 2 to 5: %s "
          "(on the line: %s).\n" % (result["vintage"], s["history"] if s["history"] == "full" else
                                    "last %d years" % s["history"]["years"], s["change_months"],
                                    ", ".join("%g" % c for c in s["cutoffs"]), s["on_the_line"]))
    for r in sorted(result["ratings"], key=lambda r: (-r["rating"], r["key"], r["reading"])):
        print("  %d  %-26s %-8s %s" % (r["rating"], r["key"], r["reading"], r["sentence"]))
    for x in result["alongside"]:
        print("\n  %s" % x["sentence"])
    if result["not_rated"]:
        print("\nNot rated:")
        for x in result["not_rated"]:
            print("  %-26s %-8s %s" % (x["key"], x["reading"], x["why"]))
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
    pr = sub.add_parser("rate", help="every rating from a pull")
    pr.add_argument("--cache", required=True)
    pr.add_argument("--settings", required=True)
    pr.add_argument("--vintage")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--workbook", metavar="OUT.xlsx", help="also write the workbook the teams read")
    a = p.parse_args(argv)
    commands = {"list": cmd_list, "pull": cmd_pull, "show": cmd_show,
                "settings-template": cmd_settings_template, "rate": cmd_rate}
    try:
        return commands[a.command](a) or 0
    except Refused as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
