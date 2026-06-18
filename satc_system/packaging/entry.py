"""PyInstaller entry point for the bundled SATC desktop app.

This is the script PyInstaller freezes into the ``SATC`` executable. It does
nothing but hand off to the normal Flask server launcher, so the frozen app
behaves exactly like ``satc app`` / ``python -m satc.app``: it picks a free
port, opens the browser, and serves the local GUI.
"""

from satc.app.server import main


if __name__ == "__main__":
    main()
