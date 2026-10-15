"""Write ``Consumer credit thresholds.pyzw``: the whole tool in one file.

    python tools/make_app.py OUT_FOLDER

The file is a Python zip application (``zipapp``): this package, the consumer
book (``books/consumer-public.json``, its series list, ``config/peers.json``)
and ``openpyxl`` with ``et_xmlfile``, the one dependency, with their licences.
On Windows, double-clicking a ``.pyzw`` runs it with Python and no console
(the Python launcher installs that association), and the window in
``threshold_engine/app.py`` opens. The work machine needs Python 3.9 or later
from python.org and nothing else installed."""
import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "Consumer credit thresholds.pyzw"
MAIN = "from threshold_engine.app import main\nmain()\n"


def _copy_package(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _licence(dist_name: str, dst: Path) -> None:
    from importlib import metadata
    dist = metadata.distribution(dist_name)
    for f in dist.files or []:
        if Path(str(f)).name.upper().startswith(("LICENCE", "LICENSE")):
            shutil.copy(dist.locate_file(f), dst / ("%s-%s" % (dist_name, Path(str(f)).name)))


def make(out_dir) -> Path:
    import et_xmlfile
    import openpyxl

    sys.path.insert(0, str(ROOT / "src"))
    from threshold_engine import app

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "app"
        _copy_package(ROOT / "src" / "threshold_engine", stage / "threshold_engine")
        bundle = stage / "threshold_engine" / "bundle"
        bundle.mkdir()
        for name, path in app.BUNDLE:
            shutil.copy(path, bundle / name)
        for mod in (openpyxl, et_xmlfile):
            _copy_package(Path(mod.__file__).parent, stage / mod.__name__)
        for dist in ("openpyxl", "et_xmlfile"):
            _licence(dist, stage)
        (stage / "__main__.py").write_text(MAIN, encoding="utf-8")
        target = out_dir / NAME
        zipapp.create_archive(stage, target, compressed=True)
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/make_app.py OUT_FOLDER")
    print(make(sys.argv[1]))
