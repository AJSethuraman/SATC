"""Back the client data up somewhere that is not this disk.

Written 3 September 2026, the day the survey found that the Storage Spaces
mirror described in `docs/satc-forge.md` does not exist. There is one drive in
the Forge. It holds the data mart, the identity vault, and the only copy of
both, and `docs/satc-forge.md` has carried the line "git backs up the code and
nothing backs up the clients" since the day real client data arrived.

WHAT IT COPIES, AND THE ONE THING IT WILL NOT

  satc_mart.db    the de-identified working data mart
  satc_vault.db   the AES-256 encrypted identity vault -- names and TINs

  vault.key       NEVER. This is the whole design.

`vault.key` lives in the same directory as the vault it decrypts. Copying both
to the same cloud folder would mean the tenant holds the ciphertext and the key
side by side, and the encryption would be protecting nothing that the account
password was not already protecting. The firm chose, on 3 September 2026, that
the vault goes up and the key stays off-cloud.

So this script does not merely omit the key. It **checks the destination and
refuses** if a key is sitting there, because the failure it is guarding against
is somebody helpfully dragging the folder across one afternoon, and a rule that
only lives in a comment does not survive that.

**The key needs a home of its own.** Off this machine, not in the same place as
the backup: a password manager, a printed copy in a drawer, a USB stick that
lives somewhere else. Without it the backup is unreadable, which is the point
and also the risk. `--check-key` prints where the key is and what it would take
to lose it.

WHY NOT `copy`

A SQLite database being written to is not safe to copy byte-for-byte; you can
capture a file with a half-finished transaction in it and not find out until
the restore. `sqlite3`'s online backup API takes a consistent snapshot of a live
database, so this is safe to run while the app is open. Every copy is then
reopened and queried before the run is called a success -- an unverified backup
is the thing this repository has a tenet about.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# The two that matter. `flask_secret.key` is a session secret the app
# regenerates; `SATC_DataMart_export.xlsx` is derived and can be re-exported.
DATABASES = ("satc_mart.db", "satc_vault.db")

# Never copied, and refused if found at the destination.
FORBIDDEN = ("vault.key",)

DEFAULT_SOURCE = Path.home() / "Documents" / "Main" / "repos" / "SATC" / \
    "satc_system" / "build" / "data"


def find_onedrive() -> Path | None:
    """The SATC tenant's OneDrive folder, if it has been signed in.

    `OneDriveCommercial` is set by the client once a work account is connected;
    the personal account sets `OneDriveConsumer` instead and is deliberately not
    accepted here. Client data does not go in somebody's personal drive.
    """
    commercial = os.environ.get("OneDriveCommercial")
    if commercial and Path(commercial).is_dir():
        return Path(commercial)
    # The client sets the variable at logon, so a session started before
    # sign-in will not see it. Look for the folder it creates.
    for path in sorted(Path.home().glob("OneDrive - *")):
        if path.is_dir():
            return path
    return None


def snapshot(src: Path, dst: Path) -> int:
    """One consistent copy of a live SQLite database. Returns bytes written."""
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    try:
        target = sqlite3.connect(dst)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return dst.stat().st_size


def verify(path: Path) -> tuple[bool, str]:
    """Open the copy and make it answer a question. Reads no client rows."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            ok, = con.execute("PRAGMA integrity_check").fetchone()
            if ok != "ok":
                return False, f"integrity_check said {ok!r}"
            tables = con.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            if not tables:
                return False, "no tables -- the copy is empty"
            return True, f"{tables} table(s), integrity ok"
        finally:
            con.close()
    except sqlite3.Error as exc:
        return False, f"will not open: {exc}"


def table_counts(path: Path) -> dict[str, int]:
    """{table -> row count}. Counts rows; never reads a value out of one."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {n: con.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0]
                for n in names}
    finally:
        con.close()


def verify_restore(source: Path, backup: Path, scratch: Path) -> bool:
    """Restore the newest backup somewhere harmless and prove it came back.

    `docs/satc-forge.md`: "A backup nobody has restored from is a hope." This
    is the part that stops that sentence being true here -- it copies the
    backup back out, opens it, and checks every table against the live one.

    The scratch copy is DELETED afterwards, always. A restored vault sitting
    in a temp directory is exactly the stray-copy problem the survey found on
    30 July, and producing another one while proving the backup works would be
    a poor trade.
    """
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        ok = True
        for name in DATABASES:
            if not (backup / name).exists():
                print(f"    MISSING  {name} is not in {backup.name}")
                ok = False
                continue
            shutil.copy2(backup / name, scratch / name)
            live, back = table_counts(source / name), table_counts(scratch / name)
            same = live == back
            ok &= same
            print(f"    {'MATCH' if same else 'DIFFER'}    {name:16s} "
                  f"{len(back):>2} table(s), {sum(back.values()):>4} row(s)"
                  f"{'' if same else '   ROW COUNTS DIFFER FROM LIVE'}")
            for table in sorted(set(live) | set(back)):
                if live.get(table) != back.get(table):
                    print(f"               {table}: live={live.get(table)} "
                          f"restored={back.get(table)}")
        return ok
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def prune(root: Path, keep: int) -> list[str]:
    """Keep the newest `keep` dated folders. Returns what was removed."""
    dated = sorted((d for d in root.glob("20*-*") if d.is_dir()), reverse=True)
    removed = []
    for old in dated[keep:]:
        shutil.rmtree(old, ignore_errors=True)
        removed.append(old.name)
    return removed


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):        # Windows consoles are cp1252
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help="the live data directory")
    ap.add_argument("--dest", type=Path, default=None,
                    help="where backups go (default: the SATC OneDrive folder)")
    ap.add_argument("--keep", type=int, default=14,
                    help="how many dated copies to keep (default 14)")
    ap.add_argument("--check-key", action="store_true",
                    help="say where vault.key is and what losing it costs")
    ap.add_argument("--verify-restore", action="store_true",
                    help="restore the newest backup to a temp dir and check it, "
                         "then delete it")
    args = ap.parse_args(argv)

    if args.check_key:
        key = args.source / "vault.key"
        print()
        print("  THE KEY, AND WHY IT IS NOT IN THE BACKUP")
        print(f"    {key}")
        print(f"    {'present' if key.exists() else 'MISSING'}"
              f"{f', {key.stat().st_size} bytes' if key.exists() else ''}")
        print()
        print("  This key decrypts satc_vault.db -- every client's legal name")
        print("  and TIN. It is deliberately NOT copied to OneDrive, because a")
        print("  vault and its key in one folder is not an encrypted vault.")
        print()
        print("  Which means: if this disk dies and you do not have the key")
        print("  somewhere else, the backup restores a file nobody can read.")
        print("  Put a copy somewhere off this machine -- a password manager,")
        print("  a printed copy, a USB stick kept elsewhere -- and do it before")
        print("  you rely on the backup.")
        print()
        return 0

    if not args.source.is_dir():
        print(f"  no such data directory: {args.source}", file=sys.stderr)
        return 2

    dest_root = args.dest
    if dest_root is None:
        found = find_onedrive()
        if found is None:
            print("  Cannot find the SATC OneDrive folder.", file=sys.stderr)
            print("  Sign in to OneDrive with the SATC work account "
                  "(tenant: Sethuraman Accounting Tax and Consulting LLP),",
                  file=sys.stderr)
            print("  or pass --dest explicitly.", file=sys.stderr)
            return 3
        dest_root = found / "SATC Backups" / "client-data"

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")
    out = dest_root / stamp
    out.mkdir(parents=True, exist_ok=True)

    print()
    print("  Backing up the client data")
    print(f"    from  {args.source}")
    print(f"    to    {out}")
    print()

    failures = 0
    for name in DATABASES:
        src = args.source / name
        if not src.exists():
            print(f"    MISSING  {name} -- not at the source")
            failures += 1
            continue
        size = snapshot(src, out / name)
        ok, detail = verify(out / name)
        mark = "ok   " if ok else "FAIL "
        print(f"    {mark}    {name:16s} {size:>9,} bytes   {detail}")
        if not ok:
            failures += 1

    # THE GUARD. Not "we did not copy it" -- "it is not there", whoever put it
    # there and however they did it.
    print()
    for name in FORBIDDEN:
        stray = list(dest_root.rglob(name))
        if stray:
            print(f"    REFUSED  {name} is in the backup destination:")
            for s in stray:
                print(f"               {s}")
            print(f"    The vault and its key must not share a home. Remove it")
            print(f"    from the destination and keep it off this cloud folder.")
            failures += 1
        else:
            print(f"    ok       {name} is NOT in the destination, as intended")

    if args.verify_restore:
        print()
        print("    RESTORE TEST -- reading the backup back and comparing")
        if verify_restore(args.source, out,
                          Path(os.environ.get("TEMP", ".")) / "satc-restore-check"):
            print("    ok       a restore was performed and matched the live data")
        else:
            print("    FAIL     the restored copy does not match")
            failures += 1

    removed = prune(dest_root, args.keep)
    if removed:
        print(f"\n    pruned   {len(removed)} old copy(ies), keeping {args.keep}")

    print()
    if failures:
        print(f"  {failures} problem(s). This run did NOT produce a backup you "
              f"can rely on.")
        return 1
    print("  Backed up and verified. Every copy was reopened and checked.")
    print("  Remember: the key is not in here. `--check-key` says why.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
