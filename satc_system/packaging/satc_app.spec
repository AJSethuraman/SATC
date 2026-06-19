# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the zero-install SATC desktop app.

Build (from the ``satc_system/`` directory):

    pip install -e ".[local,build]"
    pyinstaller packaging/satc_app.spec

Produces a single double-clickable executable named ``SATC`` in ``dist/``.

What gets bundled as data (and where it lands inside the bundle):
  * ``configs/``                 -> ``configs``                 (YAML line sheets,
                                    crosswalk, extraction maps, workflows, etc.)
  * ``src/satc/app/templates``   -> ``satc/app/templates``       (Jinja2 templates)
  * ``src/satc/app/static``      -> ``satc/app/static``          (CSS, if present)

``src/satc/config.py`` and ``src/satc/persistence/store.py`` are frozen-aware:
the configs are read from ``sys._MEIPASS/configs`` and the SQLite databases are
written to ``~/.satc/data`` (overridable with ``SATC_DATA_DIR``).
"""

import os

from PyInstaller.utils.hooks import collect_submodules

# The spec is invoked with the working directory at ``satc_system/``.
PROJECT_ROOT = os.path.abspath(os.getcwd())
SRC = os.path.join(PROJECT_ROOT, "src")


def _data(src_rel, dest):
    """Return a (source, dest) data tuple only if the source actually exists."""
    abs_src = os.path.join(PROJECT_ROOT, src_rel)
    return (abs_src, dest) if os.path.exists(abs_src) else None


datas = [
    d
    for d in (
        _data("configs", "configs"),
        _data(os.path.join("src", "satc", "app", "templates"), os.path.join("satc", "app", "templates")),
        _data(os.path.join("src", "satc", "app", "static"), os.path.join("satc", "app", "static")),
    )
    if d is not None
]

hiddenimports = [
    "flask",
    "jinja2",
    "yaml",
    "openpyxl",
    "pypdf",
    "reportlab",
    "sqlite3",
    "pymupdf",
    "fitz",
]
# Pull in everything under the satc package so dynamically imported modules
# (e.g. blueprints, doctor checks, ingest backends) are not missed.
hiddenimports += collect_submodules("satc")

# Outlook draft integration (Windows only). Listed so PyInstaller bundles the
# COM modules even though they're imported lazily; harmless if not installed.
hiddenimports += ["win32com", "win32com.client", "pythoncom", "pywintypes"]


a = Analysis(
    [os.path.join(PROJECT_ROOT, "packaging", "entry.py")],
    pathex=[SRC],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SATC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
