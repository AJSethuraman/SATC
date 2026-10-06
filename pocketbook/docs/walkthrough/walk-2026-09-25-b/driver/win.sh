#!/bin/sh
# win.sh OUTPNG EXTRACT ACTION... : one session of the launcher window on a virtual display
export HOME=/tmp/walk2/home CUBE_MEMORY=/tmp/walk2/home/memory.yaml
exec xvfb-run -a -s "-screen 0 800x600x24" /usr/bin/python3.12 "$(dirname "$0")/drive.py" "$@"
