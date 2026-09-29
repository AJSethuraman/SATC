"""The isolation guard. Runs BEFORE any `satc` or client-documents import.

The simulator drives the real code through its real doors, and both projects
bind their stores at import time: `satc.app.state` builds `STATE = AppState()`
the moment it is imported, and client-documents binds `engagements.STORE` to
its own folder. So the only safe order is: decide every path, pin every
variable, refuse anything that points at a live store -- and only then import.

What it refuses (path arithmetic only; nothing here opens, stats or lists a
live path):

  * a run directory under the live checkout, the stale checkout, `~/.satc`,
    `C:\\Occam`, any `C:\\DRAKE*`, or the worktree itself;
  * a process where `satc` or `engagements` is already imported, because then
    the store was bound before this guard could choose it.

What it pins, by ASSIGNMENT and never `setdefault` (`satc_system/tests/
conftest.py` uses `setdefault`, so an exported value there wins -- here it must
not): the data dir, the engagements store, the library, the intake root, a fixed
Flask secret, the launcher role (`SATC_ROLE=owner`, firm decision D2,
`LOG.md:846`) and the local model switched off.

What it removes: every other `SATC_*` variable (the Square token among them,
`registry/payments.yaml` `token_env`), `ANTHROPIC_API_KEY`.

After import, `install_bans()` replaces the socket layer, the Square processor,
the Windows credential-store lookups and desktop Outlook with functions that
raise `SimRefused`. A simulator that reached any of them would be a simulator
that can charge a card or open a window on the firm's desk.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

HOME = Path.home()

# Live or foreign locations. Compared as paths, never touched.
FORBIDDEN_ROOTS: tuple[Path, ...] = (
    HOME / ".satc",
    HOME / "Documents" / "Main",
    HOME / "SATC",
    Path("C:/Occam"),
    Path("C:/DRAKEDDM"),
)
FORBIDDEN_PREFIXES: tuple[str, ...] = ("c:/drake",)   # C:\DRAKE* of any suffix

# Environment the two projects read. Everything SATC_* is cleared first, then
# only these are set; see module docstring.
REMOVED_EXTRA = ("ANTHROPIC_API_KEY",)


class SimRefused(RuntimeError):
    """The simulator tried to do something it must never do."""


@dataclass(frozen=True)
class Isolation:
    run: Path
    satc_data: Path
    engagements: Path
    library: Path
    intake_root: Path
    out: Path

    def as_dict(self) -> dict[str, str]:
        return {k: str(v) for k, v in self.__dict__.items()}


def _norm(p: Path) -> str:
    """Case-folded, forward-slashed, absolute. A Windows drive path stays a drive
    path on every OS, so `C:\\DRAKE25` is refused on the CI runner too."""
    text = str(p).replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", text):
        return str(PureWindowsPath(text)).replace("\\", "/").lower().rstrip("/")
    return os.path.abspath(text).replace("\\", "/").lower().rstrip("/")


def is_under(child: Path, parent: Path) -> bool:
    """Path arithmetic only: is `child` equal to or below `parent`?"""
    c, p = _norm(child), _norm(parent)
    return c == p or c.startswith(p + "/")


def refuses(path: Path, worktree: Path) -> str:
    """Why `path` may not hold simulator state, or '' when it may."""
    for root in FORBIDDEN_ROOTS:
        if is_under(path, root):
            return f"{path} is under {root}, a live or foreign store"
    n = _norm(path)
    for prefix in FORBIDDEN_PREFIXES:
        if n.startswith(prefix):
            return f"{path} is under C:\\DRAKE*, Drake's own folders"
    if is_under(path, worktree):
        return (f"{path} is inside the worktree {worktree}; a harness writes "
                f"outside the repository (docs/SOFTWARE-TENETS.md S22 rule 4)")
    return ""


def default_run_dir(seed: int, label: str = "") -> Path:
    # Short on purpose: the Windows path budget (satc_system/tests/conftest.py).
    tag = f"{seed}-{label or os.getpid()}"
    return Path(tempfile.gettempdir()) / "satc-sim" / tag


def pin_environment(run: Path, worktree: Path) -> Isolation:
    """Choose every path, refuse live ones, and pin the environment."""
    run = Path(os.path.abspath(str(run)))
    why = refuses(run, worktree)
    if why:
        raise SimRefused(f"refusing to run: {why}")
    for name in ("satc", "engagements", "satc.app.state"):
        if name in sys.modules:
            raise SimRefused(
                f"{name!r} was imported before the guard ran, so its store was "
                f"bound to whatever the environment said at that moment. Run the "
                f"guard first, in a fresh process.")
    iso = Isolation(run=run, satc_data=run / "satc_data", engagements=run / "engagements",
                    library=run / "library", intake_root=run / "intake",
                    out=run / "out")
    for p in (iso.satc_data, iso.engagements, iso.library, iso.intake_root, iso.out):
        again = refuses(p, worktree)
        if again:
            raise SimRefused(f"refusing to run: {again}")
        p.mkdir(parents=True, exist_ok=True)

    for key in [k for k in os.environ if k.upper().startswith("SATC_")]:
        os.environ.pop(key, None)
    for key in REMOVED_EXTRA:
        os.environ.pop(key, None)
    os.environ["SATC_DATA_DIR"] = str(iso.satc_data)
    os.environ["SATC_ENGAGEMENTS"] = str(iso.engagements)
    os.environ["SATC_LIBRARY"] = str(iso.library)
    os.environ["SATC_INTAKE_ROOT"] = str(iso.intake_root)
    # Fixed, so no flask_secret.key is written (server.py:53-71) and the
    # session cookie is the same from run to run.
    os.environ["SATC_SECRET_KEY"] = "season-simulator-not-a-secret"
    # The launcher-set role (D2). Without it a headless caller is refused.
    os.environ["SATC_ROLE"] = "owner"
    os.environ["SATC_OLLAMA"] = "0"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    return iso


def _raiser(what: str):
    def refuse(*_a, **_k):
        raise SimRefused(f"the simulator may not use {what}")
    return refuse


class _NoSocket:
    def __init__(self, *a, **k):
        raise SimRefused("the simulator may not open a socket")


BANNED_CALLS: list[str] = []


def install_bans() -> list[str]:
    """Replace every door to the outside world with a refusal. Returns what was banned.

    Called after the two projects are importable (their modules must exist to
    be patched) and before anything is driven.
    """
    import socket

    socket.socket = _NoSocket                                  # type: ignore[misc]
    socket.create_connection = _raiser("socket.create_connection")  # type: ignore[assignment]
    banned = ["socket.socket", "socket.create_connection"]

    import payments
    import square_setup
    payments.processor = _raiser("Square (payments.processor)")
    payments._remembered = _raiser("the Windows credential store (payments._remembered)")
    square_setup.stored_token = _raiser("the Windows credential store (square_setup.stored_token)")
    banned += ["payments.processor", "payments._remembered", "square_setup.stored_token"]

    from satc.intake import email_draft
    # Exactly the shape satc_system/tests/conftest.py `_no_desktop_outlook` uses.
    email_draft.open_outlook_draft = lambda **kw: email_draft.DraftResult(
        False, "unavailable", "disabled in the season simulator: it never drives Outlook")
    email_draft.outlook_available = lambda: False
    banned += ["email_draft.open_outlook_draft", "email_draft.outlook_available"]
    BANNED_CALLS[:] = banned
    return banned
