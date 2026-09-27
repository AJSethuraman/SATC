"""Make what to carry to the bank machine (docs/BANK-MACHINE-CHECKLIST.md, "Before you go").

    python pocketbook/tools/bank_kit.py                 # PocketBook.zip, in PocketBook-kit in your home folder
    python pocketbook/tools/bank_kit.py --add-ons       # and the add-ons for Windows, for a machine pip can't reach
    python pocketbook/tools/bank_kit.py --out DIR --add-ons --python 3.12 --platform win_amd64

Writes, into the kit folder:
  PocketBook.py              the window and its code as one plain-text script, for a bank that only lets text in:
                             paste it into a file of that name and run it. It writes the PocketBook folder beside
                             itself, checks each file against its SHA-256, and opens the window.
  PocketBook.zip             one folder, PocketBook, holding what the window needs to run (PocketBook.pyw, src,
                             the two install files, the checklist and the analyst's procedure) and VERSION.txt:
                             the version, the commit it was made from, and whether that commit had changes on top.
  PocketBook add-ons.zip     with --add-ons: PocketBook\\add-ons, every add-on and what each needs, as the files pip
                             installs from (wheels), for each Python version asked. Unzipped in the same place as
                             PocketBook.zip, it lands inside the PocketBook folder, where
                             "Install add-ons from this folder.bat" looks.

Standard library only, except pip for --add-ons. Nothing from the bank goes in: the zip is built from the files
listed in KEEP, and a test (tests/test_bank_checklist.py) holds that no extract, workbook or memory file is among them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "PocketBook"                     # the one folder both zips unzip to
#: files and folders taken from pocketbook/ into the zip, as they are named there
KEEP = ("PocketBook.pyw", "Install add-ons.bat", "Install add-ons from this folder.bat", "README.md",
        "TENETS.md", "pyproject.toml", "src/pocketbook", "docs/BANK-MACHINE-CHECKLIST.md",
        "docs/BANK-MACHINE-CHECKLIST.html", "docs/BANK-MACHINE-CHECKLIST.pdf",
        "docs/walkthrough/2026-09-27/PROCEDURE-pocketbook-analyst.pdf")
#: the add-ons, as pip names them, with the lowest versions pyproject.toml declares (scikit-learn is the optional one)
ADD_ONS = ("numpy>=1.22", "openpyxl>=3.1", "PyYAML>=6.0", "scikit-learn>=1.4")
PYTHONS = ("3.11", "3.12", "3.13", "3.14")


def files() -> list[tuple[Path, str]]:
    """(the file here, its name in the zip) for everything the zip holds but VERSION.txt."""
    out = []
    for keep in KEEP:
        p = ROOT / keep
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix not in (".pyc", ".pyo"):
                    out.append((f, f"{TOP}/{f.relative_to(ROOT).as_posix()}"))
        elif p.is_file():
            out.append((p, f"{TOP}/{keep}"))
        else:
            raise SystemExit(f"{keep} isn't in {ROOT}: build the checklist first (python3 docs/bank-machine/build.py).")
    return out


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def version_text() -> str:
    """What VERSION.txt says: enough for whoever reads a report from the bank to know which code ran."""
    sys.path.insert(0, str(ROOT / "src"))
    from pocketbook import __version__

    commit = _git("rev-parse", "HEAD") or "unknown (git wasn't there when the kit was made)"
    changed = _git("status", "--porcelain", "--", ".")
    return (f"PocketBook {__version__}\n"
            f"Commit: {commit}\n"
            f"Branch: {_git('rev-parse', '--abbrev-ref', 'HEAD') or 'unknown'}\n"
            f"Changes on top of that commit when the kit was made: {'yes' if changed else 'none'}\n"
            f"Kit made: {dt.datetime.now().strftime('%d %b %Y %H:%M')}\n")


def make_zip(out: Path) -> Path:
    z = out / "PocketBook.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f, name in files():
            zf.write(f, name)
        zf.writestr(f"{TOP}/VERSION.txt", version_text())
    return z


#: what goes into the one script to paste: the window and the code it runs, nothing else
PASTE_KEEP = ("PocketBook.pyw", "src/pocketbook")
#: the start of the script; the files follow it as comment lines, so the whole thing is one valid .py
PASTE_HEAD = '''\
# PocketBook, as one script. Paste all of it into a file called PocketBook.py and run:  py PocketBook.py
# It writes a folder called PocketBook beside itself, checks every file came through whole, and opens the window.
# Everything under "The files" is PocketBook's own code, each line kept after "#|". Nothing here is downloaded.
{version}
import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FOLDER = HERE / "PocketBook"


def unpack():
    lines = pathlib.Path(__file__).read_text(encoding="utf-8").splitlines()
    files, name, want, body, end = {{}}, None, None, [], None
    for line in lines:
        if line.startswith("#=== FILE "):
            name, want = line[10:].rsplit(" sha256=", 1)
            body = []
        elif line.startswith("#=== DONE ") and name:
            text = "".join(line + "\\n" for line in body)
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != want:
                sys.exit("The paste didn't come through whole: " + name + " doesn't match. Paste the script again.")
            files[name] = text
            name = None
        elif line.startswith("#=== END files="):
            end = int(line[15:])
        elif name is not None and line.startswith("#|"):
            body.append(line[2:])
    if end is None or len(files) != end:
        sys.exit("The paste stops early: " + str(len(files)) + " files came through, not " + str(end or "all")
                 + ". Copy the whole script, to its last line, and paste again.")
    for rel, text in files.items():
        p = FOLDER / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8", newline="\\n")
    return len(files)


sys.path.insert(0, str(FOLDER / "src"))
if __name__ == "__main__":
    print("Writing PocketBook into " + str(FOLDER) + " ...")
    print(str(unpack()) + " files, every one checked. Opening the window.")
    import multiprocessing

    multiprocessing.freeze_support()
    from pocketbook.launcher import main

    main()

# ---------------------------------------------------------------- The files
'''


def paste_files() -> list[tuple[Path, str]]:
    """(the file here, its path inside the PocketBook folder) for everything the paste-able script carries."""
    out = []
    for keep in PASTE_KEEP:
        p = ROOT / keep
        if p.is_dir():
            out += [(f, f.relative_to(ROOT).as_posix()) for f in sorted(p.rglob("*"))
                    if f.is_file() and "__pycache__" not in f.parts and f.suffix not in (".pyc", ".pyo")]
        else:
            out.append((p, keep))
    return out


def paste_text() -> str:
    """The whole paste-able script: a short program, then every file as '#|' comment lines with its SHA-256."""
    ver = "".join("# " + line + "\n" for line in version_text().splitlines())
    parts = [PASTE_HEAD.format(version=ver.rstrip("\n"))]
    fs = paste_files()
    for f, rel in fs:
        text = f.read_text(encoding="utf-8").replace("\r\n", "\n")
        if text and not text.endswith("\n"):
            text += "\n"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        parts.append(f"#=== FILE {rel} sha256={digest}\n")
        parts.append("".join("#|" + line + "\n" for line in text.splitlines()))
        parts.append(f"#=== DONE {rel}\n")
    parts.append(f"#=== END files={len(fs)}\n")
    return "".join(parts)


def make_paste(out: Path) -> Path:
    p = out / "PocketBook.py"
    p.write_text(paste_text(), encoding="utf-8", newline="\n")
    return p


def pip_download(dest: Path, python: str, platform: str) -> str:
    """Fetch the add-ons for one Python version and platform into dest; what pip said, last lines."""
    argv = [sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--only-binary=:all:",
            "--platform", platform, "--python-version", python, "--implementation", "cp", "-d", str(dest),
            *ADD_ONS]
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"pip couldn't fetch the add-ons for Python {python} ({platform}):\n"
                         + "\n".join((r.stdout + r.stderr).strip().splitlines()[-8:]))
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""


def make_add_ons(out: Path, pythons: list[str], platform: str) -> Path:
    z = out / "PocketBook add-ons.zip"
    with tempfile.TemporaryDirectory() as tmp:
        wheels = Path(tmp) / "add-ons"
        for py in pythons:
            print(f"  Python {py} ({platform}): {pip_download(wheels, py, platform)}")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:        # wheels are zips already
            for f in sorted(wheels.iterdir()):
                zf.write(f, f"{TOP}/add-ons/{f.name}")
    return z


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(Path.home() / "PocketBook-kit"), help="the kit folder (made if not there)")
    p.add_argument("--add-ons", action="store_true", help="also fetch the add-ons, for a machine pip can't reach")
    p.add_argument("--python", nargs="+", default=list(PYTHONS), help="the Python versions to fetch them for")
    p.add_argument("--platform", default="win_amd64", help="pip's name for the machine (win_amd64: 64-bit Windows)")
    a = p.parse_args(argv)
    out = Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    z = make_zip(out)
    print(f"Wrote {z} ({z.stat().st_size / 1e6:.1f} MB).")
    ps = make_paste(out)
    print(f"Wrote {ps} ({ps.stat().st_size / 1e6:.1f} MB): the same code as one script, to paste.")
    print("  " + version_text().replace("\n", "\n  ").rstrip())
    if a.add_ons:
        print(f"Fetching the add-ons for Python {', '.join(a.python)}:")
        az = make_add_ons(out, a.python, a.platform)
        print(f"Wrote {az} ({az.stat().st_size / 1e6:.1f} MB).")
    shutil.copy(ROOT / "docs" / "BANK-MACHINE-CHECKLIST.pdf", out / "BANK-MACHINE-CHECKLIST.pdf")
    print(f"Wrote {out / 'BANK-MACHINE-CHECKLIST.pdf'}: print it, or keep it open beside you.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
