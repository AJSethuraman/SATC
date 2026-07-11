@echo off
REM ===================================================================
REM  Double-click launcher for the stock-helper Streamlit UI (Windows).
REM  Works even if you have never used the terminal:
REM   1. prefers `uv` if it is installed and on PATH,
REM   2. otherwise falls back to a plain-Python virtual environment,
REM   3. creates .env from .env.example on first run,
REM   4. then launches the UI in your browser.
REM ===================================================================
setlocal enableextensions
cd /d "%~dp0"

REM --- first-run: make sure a .env exists so SEC_USER_AGENT can be set ---
if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example.
    echo IMPORTANT: open .env in Notepad and set SEC_USER_AGENT to your name + email
    echo before fetching SEC data ^(SEC fair-access rules require it^).
    echo.
  )
)

REM --- path 1: uv is available -> use it (fast, no manual venv) ---
where uv >nul 2>nul
if %errorlevel%==0 (
  echo Using uv...
  uv run stock-helper-ui
  goto :done
)

echo uv is not installed. Falling back to a plain-Python virtual environment.
echo ^(To use the faster uv path instead, install it from https://docs.astral.sh/uv/ ^)
echo.

REM --- locate a Python interpreter ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo.
  echo ERROR: Python was not found.
  echo Install Python 3.11+ from https://www.python.org/downloads/ ^(tick
  echo "Add python.exe to PATH" in the installer^), then double-click this file again.
  echo.
  pause
  goto :eof
)

REM --- first-run: create the venv and install the app ---
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment in .venv ^(one-time, ~1-2 min^)...
  %PY% -m venv .venv || goto :failed
  call ".venv\Scripts\activate.bat"
  echo Installing stock-helper and dependencies...
  python -m pip install --upgrade pip >nul
  python -m pip install -e ".[dev]" || goto :failed
) else (
  call ".venv\Scripts\activate.bat"
)

echo Launching the UI...
stock-helper-ui
goto :done

:failed
echo.
echo Setup failed. Scroll up for the error. Common fixes:
echo  - make sure you have internet access to install packages,
echo  - install Python 3.11+ from https://www.python.org/downloads/.
echo.

:done
pause
