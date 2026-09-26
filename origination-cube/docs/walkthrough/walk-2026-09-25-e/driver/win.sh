#!/bin/sh
# win.sh OUTPNG EXTRACT ACTION... : one session of the launcher window on a virtual display.
# HOME and CUBE_MEMORY point at scratch so nothing lands in the real home; CUBE_SRC is the frozen build
# (commit 5ef61df, from `git archive` into $WALK/code).
W=${WALK:?set WALK to the scratch folder}
export HOME=$W/home CUBE_MEMORY=$W/home/memory.yaml CUBE_SRC=${CUBE_SRC:-$W/code/origination-cube/src}
exec xvfb-run -a -s "-screen 0 900x700x24" ${PY:-/usr/bin/python3.12} "$(dirname "$0")/drive.py" "$@"
