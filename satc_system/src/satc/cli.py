"""SATC command-line entry point.

    satc app                 launch the local web GUI (opens your browser)
    satc doctor              check what's ready on this machine (OCR, Ollama, ...)
    satc build [out.xlsx]    build the demo workpaper workbook (and recalc note)
    satc sort FOLDER         classify + re-label a folder of client documents
    satc chase [--dir DIR]   who owes us a document, longest wait first
    satc seed [--dir DIR]    initialize the SQLite store from synthetic fixtures
    satc export [out.xlsx]   export the data mart to Excel
    satc reset [--dir DIR]   delete the local databases (start fresh)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _speak_utf8() -> None:
    """Let this CLI print its own output on a Windows console.

    `doctor` reports each row with a ✅ or a ⚠️, and a default Windows console
    is cp1252, which has neither. On 3 September 2026 — the first time this was
    run on the firm's own machine rather than in a Linux container — `satc
    doctor` did not report a problem, it *crashed* with
    `UnicodeEncodeError: 'charmap' codec can't encode character '✅'`.

    A readiness check that dies on the machine whose readiness it is checking
    is worse than no check, so this is fixed here rather than by asking anyone
    to set `PYTHONIOENCODING`. `errors="replace"` is deliberate: on a console
    that genuinely cannot draw a glyph, a `?` in one column still leaves the
    rest of the report readable.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):       # a redirected/closed stream
                pass


def main(argv: list[str] | None = None) -> int:
    _speak_utf8()
    parser = argparse.ArgumentParser(prog="satc", description="SATC tax tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("app", help="launch the local web GUI")
    sub.add_parser("doctor", help="check what's ready on this machine")

    p_build = sub.add_parser("build", help="build the demo workpaper workbook")
    p_build.add_argument("out", nargs="?", default=None)
    p_build.add_argument("--tax-year", type=int, default=2024)

    p_sort = sub.add_parser("sort", help="classify + re-label a folder of documents")
    p_sort.add_argument("folder")
    p_sort.add_argument("--apply", action="store_true",
                        help="copy files into the clean tree (default: preview only)")
    p_sort.add_argument("--dest", default=None, help="destination root (default: FOLDER/_SATC_Sorted)")

    p_collect = sub.add_parser(
        "collect", help="collect what clients uploaded to the synced drop folder")
    p_collect.add_argument("folder", nargs="?", default=None,
                           help="the synced SharePoint upload folder "
                                "(default: $SATC_DROP_FOLDER)")
    p_collect.add_argument("--apply", action="store_true",
                           help="file the documents (default: preview only)")
    p_collect.add_argument("--library", default=None,
                           help="where filed documents go (default: $SATC_LIBRARY)")
    p_collect.add_argument("--dir", default=None,
                           help="the store holding the engagements, so an "
                                "arriving document closes the request that "
                                "asked for it (default: the usual one)")

    sub.add_parser("corpus", help="score the classifier against the real IRS blanks")
    p_pay = sub.add_parser("paystub-corpus",
                           help="score the paystub reader against the synthetic stubs")
    p_pay.add_argument("--reader", choices=["columns", "lines"], default="columns",
                       help="columns = reads the printed headings; "
                            "lines = the older reader that counts figures on a line")
    p_pay.add_argument("--out", default="", help="where to write the rendered stubs")

    p_chase = sub.add_parser(
        "chase", help="who owes us a document, longest wait first")
    p_chase.add_argument("--dir", default=None)

    p_seed = sub.add_parser("seed", help="initialize the SQLite store from fixtures")
    p_seed.add_argument("--dir", default=None)

    p_export = sub.add_parser("export", help="export the data mart to Excel")
    p_export.add_argument("out", nargs="?", default="SATC_DataMart.xlsx")
    p_export.add_argument("--dir", default=None)

    p_reset = sub.add_parser("reset", help="delete the local databases")
    p_reset.add_argument("--dir", default=None)
    p_reset.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")

    args = parser.parse_args(argv)

    if args.cmd == "app":
        from satc.app.server import main as app_main
        app_main()
        return 0

    if args.cmd == "doctor":
        from satc.doctor import format_report
        print(format_report())
        return 0

    if args.cmd == "build":
        from satc.build import build_demo_workbook
        out = build_demo_workbook(args.out, args.tax_year) if args.out else build_demo_workbook(tax_year=args.tax_year)
        print(f"Built {out}  (run scripts/recalc.py on it to evaluate formulas)")
        return 0

    if args.cmd == "sort":
        from satc.ingest import sort_folder
        plan = sort_folder(args.folder, args.dest, apply=args.apply)
        if not plan.items:
            print(f"No files found in {args.folder}")
            return 0
        verb = "Copied" if plan.applied else "Would copy"
        print(f"{'Sorted' if plan.applied else 'Plan for'} {len(plan.items)} files "
              f"({plan.classified} identified) -> {plan.dest}\n")
        width = max(len(it.original_name) for it in plan.items)
        for it in plan.items:
            print(f"  {it.original_name:<{width}}  {it.label:<22}  "
                  f"[{it.method}/{it.confidence}]  ->  {it.new_relpath}")
        if not plan.applied:
            print(f"\n{verb} into {plan.dest}.  Re-run with --apply to write the copies.")
        return 0

    if args.cmd == "collect":
        import os

        from satc import collect as collect_mod
        from satc.collect import SyncedFolder, collect
        from satc.ingest.client_library import library_root

        folder = args.folder or os.environ.get("SATC_DROP_FOLDER")
        if not folder:
            print("No drop folder given. Pass one, or set SATC_DROP_FOLDER to the\n"
                  "folder OneDrive syncs your SharePoint uploads into.")
            return 2
        lib = args.library or library_root()

        # THE STORE IS HALF THE COMMAND. `collect` takes an optional store and
        # closes the intake request each arriving document satisfies; without
        # one it only files. This call passed no store, so on the only path a
        # person actually runs, `reconcile_received` was never reached and the
        # report's own "closes ..." / "still waiting on ..." lines could not
        # print. The capability was built, tested and unreachable -- front to
        # back or it is not delivered (S28).
        from satc.persistence import SATCStore
        store = SATCStore(args.dir)
        report = collect(SyncedFolder(folder), library=lib, apply=args.apply,
                         store=store)

        if not report.drops:
            print(f"Nothing waiting in {folder}")
            return 0
        print(f"{'Collected from' if report.applied else 'Waiting in'} "
              f"{report.source}\n")
        for dr in report.drops:
            who = f"{dr.drop.ref} {dr.drop.label}".strip() or dr.drop.path.name
            print(f"  {who}")
            for a in dr.arrivals:
                year = f" {a.tax_year}" if a.tax_year else ""
                where = f"  ->  {a.filed_to}" if a.filed_to else ""
                print(f"      {a.name:<24} {a.label}{year} "
                      f"[{a.method}/{a.confidence}]{where}")
                # A REQUEST NAMING SEVERAL FORMS IS NOT CLOSED BY ONE OF THEM.
                # Printed here because the collection report is where the firm
                # decides a client has sent everything.
                if a.satisfied and a.awaiting:
                    print(f"      {'':<24} ↳ part of “{a.satisfied}” — "
                          f"still waiting on {a.awaiting}")
                elif a.satisfied:
                    print(f"      {'':<24} ↳ closes “{a.satisfied}”")
                elif a.wrong_year_for:
                    # The one that reads as fine and is not: the client sent a
                    # form we asked for, from the wrong year.
                    print(f"      {'':<24} ↳ “{a.wrong_year_for}” asked for this "
                          f"form, but for a different year — nothing closed")
            for name in dr.not_downloaded:
                # Loudly, and with the remedy. This is the one that used to be
                # filed as Unclassified and never seen again.
                print(f"      {name:<24} NOT DOWNLOADED — right-click it in "
                      f"Explorer and choose Always keep on this device")
            if dr.aged:
                # REPORTED, NEVER REMOVED. See collect.RETENTION_YEARS -- the
                # period is the one the engagement letter already promises, and
                # deleting a client's documents is a person's act, not a run's.
                shown = ", ".join(dr.aged[:3])
                more = f" (+{len(dr.aged) - 3} more)" if len(dr.aged) > 3 else ""
                print(f"      · {len(dr.aged)} file(s) past {collect_mod.RETENTION_YEARS} "
                      f"years: {shown}{more}")
            if dr.unresolved:
                print(f"      ! {dr.unresolved}")
        print(f"\n  {report.collected} document(s)"
              + (f", {report.refused} not downloaded" if report.refused else ""))
        if not report.applied:
            print("  Preview only. Re-run with --apply to file them.")
        return 0

    if args.cmd == "corpus":
        from satc.ingest.corpus import report, score

        s = score()
        print("SATC classifier — scored against the real IRS blanks\n")
        print(report(s))
        # Non-zero when the classifier is confidently WRONG about a real form.
        # Unclassified is not a failure here: it leaves the request open and asks
        # a human. A wrong answer files the document under another form and
        # closes that form's request, which is the failure that costs money.
        return 1 if s.wrong else 0

    if args.cmd == "paystub-corpus":
        # `Path` is imported at the top of this module. Importing it again HERE
        # made it a local of `main()` for the whole function, so `cmd_reset`'s
        # `Path(args.dir)` three hundred lines down raised UnboundLocalError on
        # every OTHER command. Three tests caught it; nothing in this file's own
        # branch would have.
        import tempfile

        from satc.ingest.paystub_corpus import score

        out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="satc-paystubs-"))
        s = score(out, reader=args.reader)
        print("SATC paystub reader — scored against the synthetic stubs\n")
        print(s.report())
        print(f"\n  Stubs written to {out}")
        print("  These are invented layouts, not anybody's paystub. What they")
        print("  measure is whether a figure can be read out of the wrong column;")
        print("  they cannot tell you how the reader does on a stub a client sent.")
        # Non-zero on a WRONG figure only. A refusal is the reader stopping and
        # saying so, which is the design working; a wrong figure becomes a return.
        return 1 if s.wrong else 0

    if args.cmd == "chase":
        import textwrap

        from satc.intake.chasing import waiting
        from satc.persistence import SATCStore

        sweep = waiting(SATCStore(args.dir))
        print()
        # NOTHING OUTSTANDING AND NOTHING EXAMINED ARE DIFFERENT REPORTS, and
        # only one of them is good news. S2: a check that looked at nothing must
        # say so rather than print the sentence a clear register prints.
        if sweep.examined_nothing:
            print("  Nothing looked at: this store holds no document requests and no\n"
                  "  engagements, so there is nothing here to chase yet. `satc seed`\n"
                  "  loads the demo data; `satc app` is where a real one starts.\n")
            return 0
        if not sweep.rows:
            print(f"  Nothing outstanding — {sweep.documents} register row(s) read "
                  f"across {sweep.clients} client(s),\n"
                  f"  {sweep.engagements} engagement(s).")
        else:
            print(f"  {len(sweep.rows)} request(s) outstanding, longest wait first:\n")
            for w in sweep.rows:
                days = w.waiting_days()
                wait = f"{days}d" if days is not None else "?"
                year = f"  ({w.tax_year})" if w.tax_year else ""
                print(f"  {wait:>6}  {w.client_id}  {w.client[:26]:28}"
                      f"{w.doc_type}{year}")
                if days is None:
                    # Said out loud, every time. A blank in this column would
                    # read as "just asked", which is the one thing it is not.
                    print("          no date on this request — how long it has "
                          "waited is not known")
                for line in textwrap.wrap(w.asked_for, 64):
                    print(f"          {line}")
                # A REQUEST NAMING SEVERAL FORMS IS NOT CLOSED BY ONE OF THEM,
                # so the chase has to name the ones still out. "Still
                # outstanding" gets skimmed past; "still waiting on the 1099-B"
                # is what gets a document into the office.
                bundle = ""
                if w.part_way:
                    bundle = (f"↳ {w.part_way}: {w.here} — still waiting on "
                              f"{w.still_missing}")
                elif w.still_missing:
                    bundle = (f"↳ names {w.named} forms, none here yet: "
                              f"{w.still_missing}")
                if bundle:
                    print(textwrap.fill(bundle, 74, initial_indent=" " * 10,
                                        subsequent_indent=" " * 12))
            print(f"\n  {len(sweep.rows)} outstanding of {sweep.documents} "
                  f"register row(s) read, across {sweep.clients} client(s),\n"
                  f"  {sweep.engagements} engagement(s).")
        if sweep.opened_today:
            print(f"  {sweep.opened_today} more asked for today — held back, "
                  f"because chasing on the morning\n  you asked is noise, not a "
                  f"chase.")
        print()
        return 0

    if args.cmd == "seed":
        from satc.persistence import SATCStore
        store = SATCStore(args.dir)
        seeded = store.seed_if_empty()
        print(f"{'Seeded' if seeded else 'Already populated'}: {store.dir}")
        return 0

    if args.cmd == "export":
        from satc.persistence import SATCStore, export_mart_to_excel
        store = SATCStore(args.dir)
        store.seed_if_empty()
        out = export_mart_to_excel(store, args.out)
        print(f"Exported {out}")
        return 0

    if args.cmd == "reset":
        from satc.persistence.store import DEFAULT_DIR
        d = Path(args.dir) if args.dir else DEFAULT_DIR
        if not args.yes:
            print(f"This permanently deletes the SATC databases in {d}")
            print("(including the identity vault — client names and SSNs). This cannot be undone.")
            if input("Type YES to confirm: ").strip() != "YES":
                print("Aborted.")
                return 1
        for name in ("satc_vault.db", "satc_mart.db"):
            (d / name).unlink(missing_ok=True)
        print(f"Reset store in {d}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
