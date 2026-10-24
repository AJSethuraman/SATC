"""Move the tie-out's working data to the Forge, and only that.

The firm, 7 September 2026: *"move to the forge - we will purge at some point"*.

The folder it has been living in is a shared scratch space with a few hundred
directories in it from many unrelated sessions -- mutation runs, pytest temp
dirs, half-built workbooks. Moving 5.4 GB of that to the Forge would preserve
mostly rubbish and leave the firm a folder they cannot reason about when the
purge comes.

So this copies **what the tools actually reference**, found by reading the
tools rather than by listing what happens to be on disk: every `SB / "..."`
in `tools/tieout/*.py`, plus the directories those paths sit in. Anything
referenced and missing is reported; a silent skip here would move a folder that
looks complete and is not.

Nothing is deleted. The old location stays until the firm is satisfied, and
`workdir()` prefers the Forge the moment it exists, so the switch happens by
this script finishing rather than by anything being removed.

    python tools/tieout/move_workdir_to_forge.py            # what it would do
    python tools/tieout/move_workdir_to_forge.py --copy     # do it
"""
import pathlib
import re
import shutil
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.workdir import (FORGE, IRREPLACEABLE,  # noqa: E402
                                  LEGACY, REBUILDABLE)

DO_IT = "--copy" in sys.argv
TOOLS = CS / "tools" / "tieout"

#: Every `SB / "name"` and `SB / "dir" / "name"` the tools mention. The names
#: are often built with a format string -- `"facts-%s-%s.json" % (...)` -- so
#: what is collected is the FIRST segment, which is the directory or the file,
#: and a directory is taken whole.
REF = re.compile(r'SB\s*/\s*"([^"]+)"')
wanted = set()
for tool in sorted(TOOLS.glob("*.py")):
    for name in REF.findall(tool.read_text(encoding="utf-8")):
        wanted.add(name)

present, missing, total = [], [], 0
for name in sorted(wanted):
    source = LEGACY / name
    if not source.exists():
        missing.append(name)
        continue
    size = (sum(f.stat().st_size for f in source.rglob("*") if f.is_file())
            if source.is_dir() else source.stat().st_size)
    present.append((name, source.is_dir(), size))
    total += size

print("referenced by the tools : %d names" % len(wanted))
print("present on disk         : %d  (%.1f GB)" % (len(present), total / 1e9))
print("referenced but absent   : %d  %s"
      % (len(missing), ", ".join(missing[:6]) + ("..." if len(missing) > 6 else "")))
print("\nfrom : %s\nto   : %s\n" % (LEGACY, FORGE))
for name, is_dir, size in sorted(present, key=lambda t: -t[2])[:12]:
    print("   %-28s %8.1f MB %s" % (name, size / 1e6, "dir" if is_dir else ""))
if len(present) > 12:
    print("   ... and %d smaller" % (len(present) - 12))

if not DO_IT:
    print("\nDry run. Add --copy to do it. Nothing is deleted either way; the "
          "old\nlocation stays and `workdir()` starts preferring the Forge as "
          "soon as it exists.")
    raise SystemExit(0)

FORGE.mkdir(parents=True, exist_ok=True)
copied = 0
for name, is_dir, _size in present:
    src, dst = LEGACY / name, FORGE / name
    if dst.exists():
        continue
    if is_dir:
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    copied += 1
    print("   copied %s" % name, flush=True)

readme = FORGE / "README.md"
readme.write_text(
    "# The tie-out's working data\n\n"
    "Moved here 7 September 2026 on the firm's instruction: *\"move to the "
    "forge - we will purge at some point\"*. It was in a Windows temp folder, "
    "one cleanup away from gone.\n\n"
    "Every check in `credit-suite` runs against what is in here. The location "
    "is a setting -- `src/credit_suite/workdir.py` -- so moving it again is "
    "one line, and `$CREDIT_SUITE_WORKDIR` overrides it for a single run.\n\n"
    "## When the purge comes, this is the half to keep\n\n"
    + "".join("- **`%s/`** -- %s\n" % (k, v) for k, v in IRREPLACEABLE.items())
    + "\nThose are not a cache. **442 of the 760 filings have been amended "
      "since the quarter they report**, so fetching them again does not get "
      "them back: the regulator serves whatever is current then. Delete them "
      "and a tie-out already done cannot be reproduced, only replaced with a "
      "different one.\n\n"
      "## And this is the half that rebuilds\n\n"
    + "".join("- `%s/` -- %s\n" % (k, v) for k, v in REBUILDABLE.items())
    + "\nAll of it regenerates from the two folders above, or from the FDIC, "
      "in under half an hour.\n", encoding="utf-8")

print("\ncopied %d of %d entries" % (copied, len(present)))
print("wrote %s" % readme)
print("\n`workdir()` now resolves here. The old folder is untouched -- delete "
      "it\nwhen you are satisfied, or leave it; nothing reads it any more.")
