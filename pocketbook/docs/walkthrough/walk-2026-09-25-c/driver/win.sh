#!/bin/sh
# win.sh OUTPNG EXTRACT ACTION... : one session of the launcher window on a virtual display.
# HOME and CUBE_MEMORY point at scratch so nothing lands in the real home; CUBE_SRC is the frozen build.
W=${WALK:-/tmp/claude-0/-home-user-SATC/b4305bfc-8769-5da1-bd67-4db589c3cc31/scratchpad}
export HOME=$W/home CUBE_MEMORY=$W/home/memory.yaml CUBE_SRC=${CUBE_SRC:-$W/code/origination-cube/src}
exec xvfb-run -a -s "-screen 0 900x700x24" /usr/bin/python3.12 "$(dirname "$0")/drive.py" "$@"
