#!/usr/bin/env python3
"""Best-effort dependency installer for the local tax document sorter prototype.

The sorter needs Python packages from requirements.txt plus the Tesseract OCR
application. This helper keeps setup simple by installing Python packages and,
when possible, installing Tesseract with a common OS package manager.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REQUIREMENTS_FILE = Path(__file__).with_name("requirements.txt")


def run_command(command: list[str], dry_run: bool = False) -> int:
    """Print and run a command, returning its exit code."""

    print("$ " + " ".join(command))
    if dry_run:
        return 0
    try:
        return subprocess.run(command, check=False).returncode
    except FileNotFoundError:
        return 127


def install_python_packages(dry_run: bool = False) -> bool:
    """Install Python dependencies from requirements.txt."""

    if not REQUIREMENTS_FILE.exists():
        print(f"Could not find {REQUIREMENTS_FILE}")
        return False

    upgrade_code = run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"], dry_run=dry_run
    )
    if upgrade_code != 0:
        print("WARNING: pip upgrade failed; continuing with requirements install.")

    install_code = run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        dry_run=dry_run,
    )
    return install_code == 0


def tesseract_available() -> bool:
    """Return True when Tesseract is available by the sorter's detection rules."""

    try:
        from sort_tax_docs import find_tesseract_executable

        return find_tesseract_executable() is not None
    except Exception:
        return shutil.which("tesseract") is not None


def tesseract_install_command() -> tuple[list[str] | None, str]:
    """Choose a best-effort Tesseract install command for this machine."""

    system = platform.system().lower()

    if system == "darwin" and shutil.which("brew"):
        return ["brew", "install", "tesseract"], "Homebrew"

    if system == "linux":
        if shutil.which("apt-get"):
            return ["sudo", "apt-get", "install", "-y", "tesseract-ocr"], "apt-get"
        if shutil.which("dnf"):
            return ["sudo", "dnf", "install", "-y", "tesseract"], "dnf"
        if shutil.which("yum"):
            return ["sudo", "yum", "install", "-y", "tesseract"], "yum"
        if shutil.which("pacman"):
            return ["sudo", "pacman", "-S", "--noconfirm", "tesseract"], "pacman"

    if system == "windows":
        if shutil.which("winget"):
            return ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "-e"], "winget"
        if shutil.which("choco"):
            return ["choco", "install", "tesseract", "-y"], "Chocolatey"

    return None, "manual installation"


def install_tesseract(skip_system: bool = False, dry_run: bool = False) -> bool:
    """Install Tesseract OCR when possible, or explain manual fallback steps."""

    if tesseract_available():
        print("Tesseract is already installed or available in a common install location.")
        return True

    if skip_system:
        print("Skipping system Tesseract installation because --skip-system was used.")
        return False

    command, method = tesseract_install_command()
    if command:
        print(f"Tesseract was not found. Attempting install with {method}.")
        return run_command(command, dry_run=dry_run) == 0

    print("Tesseract was not found and no supported package manager was detected.")
    print_manual_tesseract_fix()
    return False


def print_manual_tesseract_fix() -> None:
    """Print manual Tesseract fallback instructions."""

    print("Install Tesseract manually, then rerun: python sort_tax_docs.py --check-dependencies")
    print("  Windows: winget install --id UB-Mannheim.TesseractOCR -e")
    print(r"           If needed, install to C:\Program Files\Tesseract-OCR\ and reopen your terminal.")
    print("  macOS:   brew install tesseract")
    print("  Ubuntu:  sudo apt-get update && sudo apt-get install -y tesseract-ocr")


def run_sorter_dependency_check() -> bool:
    """Run the same dependency check used by sort_tax_docs.py."""

    try:
        from sort_tax_docs import check_dependencies
    except Exception as exc:
        print(f"Could not import sorter dependency check: {exc}")
        return False
    return check_dependencies(verbose=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Install dependencies for the local tax document sorter prototype."
    )
    parser.add_argument(
        "--skip-system",
        action="store_true",
        help="Install Python packages only; do not try to install Tesseract.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show commands without running them.",
    )
    return parser.parse_args()


def main() -> int:
    """Install dependencies and print a short status summary."""

    args = parse_args()
    print("Setting up the local tax document sorter...")
    python_ok = install_python_packages(dry_run=args.dry_run)
    tesseract_ok = install_tesseract(skip_system=args.skip_system, dry_run=args.dry_run)

    dependency_check_ok = False if args.dry_run else run_sorter_dependency_check()

    print("\nSetup summary:")
    print(f"  Python packages: {'OK' if python_ok else 'FAILED'}")
    print(f"  Tesseract OCR:   {'OK' if tesseract_ok else 'NEEDS ATTENTION'}")
    print(f"  Final dependency check: {'OK' if dependency_check_ok else 'NEEDS ATTENTION'}")

    if dependency_check_ok:
        print("\nSetup complete.")
        print("Put client files in the Uploads folder.")
        print("Then run:")
        print("  python run_sorter.py")
        return 0

    if args.dry_run:
        print("\nDry run complete. No installation commands were actually run.")
        print("When ready, run: python setup_tax_doc_sorter.py")
        return 0

    print("\nSetup did not fully complete.")
    if not tesseract_available():
        print_manual_tesseract_fix()
    print("After fixing the issue, run: python sort_tax_docs.py --check-dependencies")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
