@echo off
REM Double-click launcher for the stock-helper Streamlit UI (Windows).
cd /d "%~dp0"
uv run stock-helper-ui
pause
