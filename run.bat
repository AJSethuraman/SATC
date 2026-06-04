@echo off
REM One-command launch for Linesheet Builder (Windows).
REM Creates a virtualenv + installs deps on first run, then starts the app.
setlocal
cd /d "%~dp0"

set "VENV=.venv"

if not exist "%VENV%\" (
  echo Creating virtual environment in %VENV% ...
  python -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"

if not exist "%VENV%\.deps-installed" (
  echo Installing dependencies ...
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt
  type nul > "%VENV%\.deps-installed"
)

echo Starting Linesheet Builder at http://localhost:8501  (press Ctrl+C to stop)
streamlit run app.py
