"""workpaper-studio: run the local application, check packs, or set up the demonstration.

    python -m workpaper_studio serve  [--data DIR] [--packs DIR] [--port 5077]
    python -m workpaper_studio check  [--packs DIR]       # every pack loads, or says exactly why not
    python -m workpaper_studio demo   [--data DIR]        # publish the three demo packs and confirm their limits
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(prog="workpaper-studio")
    ap.add_argument("command", choices=["serve", "check", "demo"])
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--packs", default=str(ROOT / "packs"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5077)
    a = ap.parse_args(argv)
    if a.command == "check":
        from .pack import load_dir
        good, bad = load_dir(a.packs)
        for p in good:
            print(f"ok      {p.file}  {p.name} {p.version}  {p.fingerprint}")
        for e in bad:
            print(f"REFUSED {e}")
        return 1 if bad else 0
    from .web import make_app, serve
    app = make_app(a.data, a.packs)
    if a.command == "demo":
        demo(app.st)
        return 0
    serve(app, a.host, a.port)
    return 0


def demo(st):
    """The demonstration organization's setup: each pack proposed by the designer and approved by someone else, and
    the limits each pack's author recommends confirmed by the admin. Synthetic people, fictional limits."""
    from .demo import write
    write(Path(st.db_path).parent)
    print("synthetic master database and sources.json written")
    good, bad = st.pack_files()
    for e in bad:
        print("REFUSED", e)
    for p in good:
        fp = st.propose("M. Okafor", p.file)
        st.approve_pack("K. Owens", fp)
        for _, b in p.calcs():
            st.confirm_limit("M. Okafor", p.name, b["id"], b["limit"])
        print(f"published {p.name} {p.version} ({fp}); limits confirmed")


if __name__ == "__main__":
    sys.exit(main())
