#!/usr/bin/env bash
# Double-clickable macOS installer — just runs install.sh from this folder.
cd "$(dirname "$0")"
exec bash ./install.sh
