"""Double-click launcher for the Streamlit UI.

``main()`` initializes the local database, picks a free port, launches
``streamlit run ui/app.py`` as a subprocess, opens the browser, and blocks until
the server exits — with a clean Ctrl-C. This is the entry point behind the
``stock-helper-ui`` console script and the repo-root double-click wrappers.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "ui" / "app.py"


def _free_port(preferred: int = 8501) -> int:
    """Return ``preferred`` if it is bindable, else an OS-assigned free port."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", candidate))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def _open_browser_when_up(url: str, host: str, port: int, timeout: float = 20.0) -> None:
    """Poll the port until the server accepts a connection, then open the browser."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.3)


def main() -> int:
    """Init DB, launch Streamlit on a free port, open the browser, block cleanly."""
    from stock_helper.core.config import get_settings
    from stock_helper.core.logging import configure_logging
    from stock_helper.storage.db import init_db

    settings = get_settings()
    configure_logging(settings.log_level)
    init_db(settings)

    host = "127.0.0.1"
    port = _free_port(8501)
    url = f"http://{host}:{port}"

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(APP_PATH),
        "--server.address", host,
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    print(f"stock-helper UI → {url}  (Ctrl-C to stop)")
    opener = threading.Thread(target=_open_browser_when_up, args=(url, host, port), daemon=True)
    opener.start()

    proc = subprocess.Popen(cmd)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down stock-helper UI…")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
