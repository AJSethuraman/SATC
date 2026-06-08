# PyInstaller spec for the SATC desktop app.
# Build with:  pyinstaller satc_app.spec   (run on the OS you want the build for)
# Output:      dist/SATC<.exe on Windows>
#
# PyInstaller builds for the OS it runs on, so run this on Windows for a .exe and on
# macOS for a .app. The CI workflow (.github/workflows/build-desktop.yml) builds all
# three automatically.

from PyInstaller.utils.hooks import collect_submodules

# Modules imported lazily (inside functions) or dynamically that static analysis can miss.
hiddenimports = [
    "batch",
    "preflight",
    "openpyxl",
    "docxtpl",
    "docx",
]
# pyhanko pulls in submodules dynamically for certificate signing.
hiddenimports += collect_submodules("pyhanko")
hiddenimports += collect_submodules("pyhanko_certvalidator")

# Ship the editable templates/config samples alongside the executable's resources.
datas = [("document_templates", "document_templates")]

block_cipher = None

a = Analysis(
    ["tax_doc_sorter_app.pyw"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SATC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # windowed GUI app (no terminal)
)
