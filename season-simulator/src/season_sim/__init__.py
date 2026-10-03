"""The 2027 tax season, simulated day by day through the real SATC code.

Importing this package imports neither satc_system nor client-documents: the
isolation guard (`season_sim.guard`) has to choose every path first.
"""

import sys

# No bytecode from here on: the launcher runs from the worktree, and a
# __pycache__ beside these modules is a write into the repository. (The
# package's own __init__ is compiled before this line runs; `python -B` covers
# that too, which is why every documented command uses it.)
sys.dont_write_bytecode = True

__version__ = "0.1.0"
