"""Drive the real Streamlit app against the seeded demo universe and capture
screenshots of the Screener and Company Valuation pages with Playwright.

Prereq: run scripts/demo_seed.py first (same DATA_DIR). Usage:
    DATA_DIR=demo_data ENABLE_PRICE_DATA=true uv run python scripts/demo_screenshot.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("demo/screenshots")
PORT = 8677


def _free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ENABLE_PRICE_DATA": "true",
           "SEC_USER_AGENT": os.environ.get("SEC_USER_AGENT", "demo (demo@example.com)")}
    app = Path(__file__).resolve().parent.parent / "src/stock_helper/ui/app.py"
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(app),
         "--server.headless", "true", "--server.port", str(PORT),
         "--browser.gatherUsageStats", "false"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(60):
            if not _free(PORT):
                break
            time.sleep(1)
        time.sleep(6)  # let the first script run settle
        # Use the pre-installed Chromium (this environment ships one under
        # /opt/pw-browsers and blocks `playwright install`).
        import glob
        exe = next(iter(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))), None)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=exe)
            page = browser.new_page(viewport={"width": 1440, "height": 1600})
            base = f"http://127.0.0.1:{PORT}"

            page.goto(base, wait_until="networkidle", timeout=60000)
            time.sleep(8)  # Streamlit first render + cross-section build
            page.screenshot(path=str(OUT / "01_screener.png"), full_page=True)
            print("captured screener")

            # Switch to Company Valuation via the sidebar radio.
            try:
                page.get_by_text("Company Valuation", exact=True).click(timeout=15000)
                time.sleep(8)
                page.screenshot(path=str(OUT / "02_valuation.png"), full_page=True)
                print("captured valuation")
            except Exception as exc:  # noqa: BLE001
                print(f"valuation page nav failed: {exc}")

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
