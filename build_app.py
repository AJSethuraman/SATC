#!/usr/bin/env python3
"""Build the SATC desktop app into a standalone executable for the current OS.

Usage:  python build_app.py

This installs PyInstaller if needed and runs it against satc_app.spec. The result
is a self-contained executable in dist/ (SATC.exe on Windows, SATC on macOS/Linux)
that runs without a separate Python install. Run it on the OS you want to target;
to build all three at once, use the GitHub Actions workflow instead.

Note: Tesseract OCR is an external program and is NOT bundled. Scanned PDFs/images
need it installed separately; the app degrades gracefully without it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "satc_app.spec"


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def main() -> int:
    if not SPEC.exists():
        print(f"Spec file not found: {SPEC}")
        return 1
    _ensure_pyinstaller()
    print(f"Building SATC for {sys.platform} ...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("Build failed.")
        return result.returncode

    dist = ROOT / "dist"
    artifacts = sorted(p.name for p in dist.iterdir()) if dist.is_dir() else []
    print(f"\nDone. Artifacts in {dist}: {', '.join(artifacts) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
