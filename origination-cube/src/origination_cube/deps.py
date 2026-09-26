"""The add-ons the cube needs, whether this computer has them, and getting them.

Ruling OC-34 (the firm, 25 Sep 2026): *"add numpy; this is the kind of script
where it should outline what is missing and try to download it, right?"* The
launcher and `cube` both ask `missing()` before touching anything that needs an
add-on, so a bank machine without one gets a sentence and an offer instead of a
traceback.

Only the standard library is imported here, and nothing is imported just to
see whether it is there: `find_spec` looks without loading.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import os
import re
import site
import subprocess
import sys
from pathlib import Path

# pip's name -> (the name Python imports it by, what the cube uses it for)
NEEDED = {
    "numpy": ("numpy", "for the statistics"),
    "openpyxl": ("openpyxl", "to read and write Excel files"),
    "PyYAML": ("yaml", "for its settings files"),
}
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
# Added to the automatic install only: no prompt can hang it, no nag about pip's own version.
QUIET = ["--disable-pip-version-check", "--no-input", "--progress-bar", "off"]


def minimums() -> dict[str, str]:
    """The lowest version of each add-on the cube is declared to need: from
    pyproject.toml beside the source, else from the installed package's own
    record. An add-on with no minimum declared is only checked for being there."""
    lines: list[str] = []
    try:
        text = PYPROJECT.read_text(encoding="utf-8")
        if 'name = "origination-cube"' in text:
            lines = text.splitlines()
    except OSError:
        pass
    if not lines:
        try:
            lines = importlib.metadata.requires("origination-cube") or []
        except importlib.metadata.PackageNotFoundError:
            pass
    names = "|".join(re.escape(n) for n in NEEDED)
    out = {}
    for line in lines:
        m = re.search(rf"\b({names})\s*>=\s*([0-9][0-9.]*)", line, re.IGNORECASE)
        if m:
            pip = next(n for n in NEEDED if n.lower() == m.group(1).lower())
            out[pip] = m.group(2).rstrip(".")
    return out


def _v(version: str) -> tuple[int, ...]:
    m = re.match(r"\d+(?:\.\d+)*", version)
    return tuple(int(x) for x in m.group(0).split(".")) if m else ()


def _found(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):       # ValueError: already loaded without a spec, so it is there
        return sys.modules.get(mod) is not None


def _too_old(pip: str, low: dict[str, str]) -> tuple[str, str] | None:
    """(the version here, the version needed) when the copy here is older than declared."""
    need = low.get(pip)
    if not need:
        return None
    try:
        have = importlib.metadata.version(pip)
    except importlib.metadata.PackageNotFoundError:
        return None                          # it imports, and there is no record to say otherwise
    return (have, need) if _v(have) < _v(need) else None


def missing() -> list[str]:
    """The add-ons the cube can't use on this computer, by pip's name: not there,
    or older than the version the cube is declared to need."""
    low = minimums()
    return [pip for pip, (mod, _) in NEEDED.items() if not _found(mod) or _too_old(pip, low)]


def _and(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


def message(names: list[str]) -> str:
    """One line: what is missing, and what the cube uses each one for."""
    low = minimums()
    parts = []
    for n in names:
        mod, why = NEEDED[n]
        old = _too_old(n, low) if _found(mod) else None
        parts.append(f"{n} ({why}; the copy here is {old[0]} and it needs {old[1]} or later)" if old
                     else f"{n} ({why})")
    what = "an add-on" if len(parts) == 1 else "add-ons"
    return f"The cube needs {what} this computer doesn't have yet: {_and(parts)}."


def python_exe() -> str:
    """The Python to install into. A double-clicked .pyw runs under pythonw.exe,
    which prints nothing, so point at python.exe beside it when there is one."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
        return str(exe.with_name("python.exe"))
    return str(exe)


def _per_user() -> bool:
    """Install for this account only (no admin rights needed), except inside a
    virtual environment or where this Python ignores per-account add-ons."""
    return sys.prefix == sys.base_prefix and bool(site.ENABLE_USER_SITE)


def command(names: list[str]) -> list[str]:
    return [python_exe(), "-m", "pip", "install", *(["--user"] if _per_user() else []), "--upgrade", *names]


def command_text(names: list[str]) -> str:
    """The command as someone would type it, the Python's path quoted if it has spaces."""
    return " ".join(f'"{a}"' if " " in a else a for a in command(names))


def ask_it(names: list[str]) -> str:
    """The note to send IT when the install from here doesn't work."""
    whose = ", under my account" if _per_user() else ""
    these, them = ("this Python add-on", "it") if len(names) == 1 else ("these Python add-ons", "them")
    return (f"Please install {these} for {python_exe()}{whose}: {', '.join(names)}. "
            f"The Origination Cube needs {them}, and installing {them} from my computer didn't work. "
            f"The command is:\n\n{command_text(names)}")


def _see_new_installs() -> None:
    """Python only looks in the per-account add-ons folder if it existed when
    Python started, and the first install is what creates it. Look there now,
    so the window that just installed them can use them without a restart."""
    if site.ENABLE_USER_SITE:
        user = site.getusersitepackages()
        if os.path.isdir(user) and user not in sys.path:
            site.addsitedir(user)
    importlib.invalidate_caches()


def install(names: list[str], timeout: float = 900) -> tuple[bool, str]:
    """Run pip for `names` and return (ok, what pip said). ok means that,
    checked again afterwards, nothing the cube needs is missing: pip's own
    exit code is not taken on trust. Never raises; a failure comes back as words."""
    names = list(names)
    if not names:
        return not missing(), "Nothing to install."
    argv = command(names)
    argv[4:4] = QUIET
    rc = None
    try:
        r = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                           **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}))
        rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        out = f"The installer was still going after {timeout / 60:.0f} minutes, so it was stopped."
    except Exception as exc:  # noqa: BLE001 - pip or Python couldn't start; say so rather than raise
        out = f"The installer couldn't start: {exc}"
    try:
        _see_new_installs()
        still = missing()
    except Exception as exc:  # noqa: BLE001
        return False, f"{out}\nCouldn't check what is there afterwards: {exc}"
    if still and rc == 0:
        out += f"\nThe installer finished, but this window still can't find {', '.join(still)}."
    return not still, out
