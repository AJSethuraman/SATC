from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from occam_template_desk.setup_samples import ensure_sample_assets


def pytest_sessionstart(session):
    ensure_sample_assets(force=True)
