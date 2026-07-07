#!/usr/bin/env bash
# Double-click launcher for the stock-helper Streamlit UI (macOS).
# Runs from this file's directory so it works from Finder.
cd "$(dirname "$0")" || exit 1
exec uv run stock-helper-ui
