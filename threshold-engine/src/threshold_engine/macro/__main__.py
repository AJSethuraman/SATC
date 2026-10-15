"""python -m threshold_engine.macro list | pull | show

    list                         every series in the catalog, and what is not read yet
    pull --cache DIR [KEY ...]   download into DIR/<today>/, keeping every earlier pull
    show --cache DIR KEY         one series as read from the newest pull (or --vintage)
"""
import argparse
import json
import sys

from .catalog import BY_KEY, NOT_YET, SERIES
from .pull import load, pull


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
    a = p.parse_args(argv)
    return {"list": cmd_list, "pull": cmd_pull, "show": cmd_show}[a.command](a) or 0


if __name__ == "__main__":
    sys.exit(main())
