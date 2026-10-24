"""pytest runs the suite from this folder in CI (`pytest -q` in the project
directory, like every other project in the matrix). unittest discovery puts
the working directory on sys.path; pytest does not, so `import arena` inside
tests/ needs this one line. Nothing else lives here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
