"""Make the kit that goes to the bank: one zip, nothing installed but openpyxl.

Run from threshold-engine/ (needs the internet once, for the add-ons):

    python tools/bank_kit.py

Writes ThresholdEngine-kit/ in your home folder:

    ThresholdEngine.zip   the window, the code, the practice data (public),
                          the add-ons as files, the checklist, VERSION.txt
    ON-SITE-CHECKLIST.pdf if docs/ON-SITE-CHECKLIST.pdf exists

The add-ons are openpyxl and et-xmlfile, both pure Python: one wheel each
works on every Windows Python from 3.9 up. Nothing from the bank is read, and
nothing internal goes in: the practice data is the public tests/data files.
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADD_ONS = ["openpyxl", "et-xmlfile"]
PRACTICE = ["cards_nco_ttm.csv", "mortgage_nco_ttm.csv", "home_equity_nco_ttm.csv",
            "other_consumer_as_filed_nco_ttm.csv", "other_consumer_with_auto_nco_ttm.csv"]


def files():
    """(path on disk, path in the zip) for everything the bank needs."""
    out = [(ROOT / n, n) for n in ("Thresholds.pyw", "README.md", "pyproject.toml")]
    for p in sorted((ROOT / "src" / "threshold_engine").rglob("*.py")):
        out.append((p, p.relative_to(ROOT).as_posix()))
    for p in sorted((ROOT / "config").rglob("*")):
        if p.is_file():
            out.append((p, p.relative_to(ROOT).as_posix()))
    for n in ("WHAT-IT-DOES.md", "ON-SITE-CHECKLIST.md", "ON-SITE-CHECKLIST.pdf"):
        if (ROOT / "docs" / n).exists():
            out.append((ROOT / "docs" / n, "docs/" + n))
    for n in PRACTICE:
        out.append((ROOT / "tests" / "data" / n, "practice/" + n))
    return out


def version():
    sys.path.insert(0, str(ROOT / "src"))
    from threshold_engine import VERSION
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head, dirty = "unknown (not a git checkout)", ""
    return VERSION, head + (" plus uncommitted changes" if dirty else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path.home() / "ThresholdEngine-kit"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wheels = Path(tmp)
        subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--no-deps",
                        "--dest", str(wheels)] + ADD_ONS, check=True)
        got = sorted(wheels.glob("*.whl"))
        if len(got) != len(ADD_ONS) or not all(w.name.endswith("py3-none-any.whl") or "-py2.py3-" in w.name
                                               for w in got):
            raise SystemExit("expected one pure-Python wheel per add-on, got %s" % [w.name for w in got])
        ver, head = version()
        stamp = ("threshold-engine %s\ncommit %s\nkit made %s\nadd-ons: %s\n"
                 % (ver, head, date.today().isoformat(), ", ".join(w.name for w in got)))
        z = out / "ThresholdEngine.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, arc in files():
                zf.write(src, "ThresholdEngine/" + arc)
            for w in got:
                zf.write(w, "ThresholdEngine/add-ons/" + w.name)
            zf.writestr("ThresholdEngine/VERSION.txt", stamp)
        pdf = ROOT / "docs" / "ON-SITE-CHECKLIST.pdf"
        if pdf.exists():
            shutil.copy2(pdf, out / pdf.name)
    digest = hashlib.sha256(z.read_bytes()).hexdigest()
    print("Wrote %s (%d KB, SHA-256 %s)" % (z, z.stat().st_size // 1024, digest))
    print(stamp.rstrip())


if __name__ == "__main__":
    main()
