"""SATC command-line entry point.

    satc app                 launch the local web GUI (opens your browser)
    satc doctor              check what's ready on this machine (OCR, Ollama, ...)
    satc drill               run the nightly trap drill against a synthetic practice
    satc build [out.xlsx]    build the demo workpaper workbook (and recalc note)
    satc sort FOLDER         classify + re-label a folder of client documents
    satc seed [--dir DIR]    initialize the SQLite store from synthetic fixtures
    satc export [out.xlsx]   export the data mart to Excel
    satc reset [--dir DIR]   delete the local databases (start fresh)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="satc", description="SATC tax tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("app", help="launch the local web GUI")
    sub.add_parser("doctor", help="check what's ready on this machine")
    sub.add_parser(
        "drill",
        help="run the nightly trap drill against a synthetic practice "
             "(docs/AUTONOMY-CHARTER.md section 7)")
    p_new = sub.add_parser(
        "comms-new",
        help="draft a new client-letter template from a one-line description")
    p_new.add_argument("description",
                       help='what the letter is for, e.g. "reminds a client their '
                            'quarterly estimate is due soon"')
    p_new.add_argument("--name", default="", help="display name (default: the description)")
    p_new.add_argument("--kind", default="email", choices=["email", "letter"])
    p_new.add_argument("--stage", default="5 · Relationship")
    p_new.add_argument("--subject", default="", help="subject line for an email")
    p_new.add_argument("--write", action="store_true",
                       help="install it into configs/comms/ (default: preview only)")

    p_score = sub.add_parser(
        "scoreboard",
        help="measure document-reading accuracy against the local corpus")
    p_score.add_argument("--dir", default="", help="corpus directory (default: corpus/)")

    p_build = sub.add_parser("build", help="build the demo workpaper workbook")
    p_build.add_argument("out", nargs="?", default=None)
    p_build.add_argument("--tax-year", type=int, default=2024)

    p_sort = sub.add_parser("sort", help="classify + re-label a folder of documents")
    p_sort.add_argument("folder")
    p_sort.add_argument("--apply", action="store_true",
                        help="copy files into the clean tree (default: preview only)")
    p_sort.add_argument("--dest", default=None, help="destination root (default: FOLDER/_SATC_Sorted)")

    sub.add_parser("prices",
                   help="check and print the service catalogue and rate plans")

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

    if args.cmd == "drill":
        from datetime import date

        from satc.autonomy.traps import run_drill

        result = run_drill(today=date.today())
        width = max((len(t.key) for t in result.traps), default=10)
        for t in result.traps:
            mark = "PASS" if t.passed else "MISS"
            print(f"[{mark}] {t.key:<{width}}  ({t.capability})")
            print(f"       {t.why}")
        print()
        if result.misses:
            print(f"{len(result.misses)} of {len(result.traps)} trap(s) missed: "
                  f"{', '.join(result.misses)}")
            print(f"Demoted to draft_only: {', '.join(result.demotions)}")
            return 1
        print(f"All {len(result.traps)} traps held. Nothing demoted.")
        return 0

    if args.cmd == "comms-new":
        from satc.comms.author import author, install

        try:
            drafted = author(args.description, name=args.name, kind=args.kind,
                             stage=args.stage, subject=args.subject)
        except Exception as exc:  # noqa: BLE001 - surface, do not stack-trace
            print(f"Could not draft it: {exc}")
            return 1

        print(f"--- {drafted.name}  ({drafted.kind}, {drafted.key}) ---")
        if drafted.subject:
            print(f"Subject: {drafted.subject}")
            print()
        print(drafted.body)
        if drafted.unknown_fields:
            print()
            print("Stripped merge fields that do not exist: "
                  + ", ".join(drafted.unknown_fields))
        if not args.write:
            print()
            print("Preview only. Re-run with --write to add it to the library.")
            return 0
        path = install(drafted)
        print()
        print(f"Written to {path}")
        print("Edit that file any time — it is an ordinary template now.")
        return 0

    if args.cmd == "prices":
        # Prices are edited by hand, in YAML, often in a hurry. This is the
        # check you run after editing — before the file's first client sees it.
        from satc.billing.catalogue import by_category, default_plan_key, plans
        from satc.config import ConfigError

        try:
            groups, rate_plans, fallback = by_category(), plans(), default_plan_key()
        except ConfigError as exc:
            print(f"The billing config will not load:\n\n  {exc}\n")
            print("Nothing can be invoiced until that is fixed.")
            return 1

        for category, items in groups:
            print(f"\n{category}")
            for svc in items:
                unit = {"per_form": " each", "per_hour": " /hr", "fixed": ""}[svc.unit]
                free = "   (no charge)" if svc.is_free else ""
                print(f"  {svc.code:<20} {svc.standard_rate:>8,.2f}{unit:<5} "
                      f"{svc.label_for_client}{free}")

        print("\nRate plans")
        for key, rate_plan in rate_plans.items():
            mark = "  <- default" if key == fallback else ""
            needs = " needs a written reason" if rate_plan.requires_basis else ""
            print(f"  {key:<20} {rate_plan.discount_pct:>3g}% off   "
                  f"{rate_plan.name}{needs}{mark}")

        print(f"\n{sum(len(i) for _, i in groups)} services, {len(rate_plans)} plans. "
              f"Both load cleanly.")
        print("Edit configs/billing/*.yaml — the app picks changes up on the next "
              "page load, no restart.")
        return 0

    if args.cmd == "scoreboard":
        # NOTE: no local "from pathlib import Path" here. Path is imported at
        # module level, and a function-local import of the same name makes it
        # local for the WHOLE function — which turned every other branch's use
        # of Path into an UnboundLocalError.
        from satc.ingest.scoreboard import score

        board = score(directory=Path(args.dir) if args.dir else None)
        print(board.report())
        # Non-zero ONLY on a silent error — a value accepted without review and
        # wrong. Missed reads and caught errors are not failures; treating them
        # as such would train the owner to ignore the exit code.
        return 0 if board.is_acceptable else 1

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
        for name in (
            "satc_vault.db", "satc_mart.db",
            # The pre-store autonomy preconditions ledger (see
            # satc.app.autonomy_views's module docstring) — a legacy file
            # from before that gate moved into satc_mart.db. Left behind
            # un-imported, it would resurrect exactly the confirmations this
            # reset exists to clear the next time the autonomy screen loads
            # and migrates it in. A reset has to remove every copy of the
            # gate, not just the one inside the database files, including
            # the renamed markers a prior import already left behind.
            "autonomy_preconditions.json",
            "autonomy_preconditions.json.imported",
            "autonomy_preconditions.json.unreadable",
        ):
            (d / name).unlink(missing_ok=True)
        print(f"Reset store in {d}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
