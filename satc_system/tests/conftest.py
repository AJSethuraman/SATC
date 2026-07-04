"""Test setup: isolate the SQLite store in a temp dir (don't touch build/data)."""

import os
import tempfile

# Must be set before satc.app.state (which builds the module-level STATE) imports.
os.environ.setdefault("SATC_DATA_DIR", tempfile.mkdtemp(prefix="satc_test_store_"))
