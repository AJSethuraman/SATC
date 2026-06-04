@echo off
rem ============================================================
rem  Tax Withholding Estimator - one-click launcher (Windows)
rem  Double-click this file to start the app.
rem  First run sets things up automatically; later runs are fast.
rem ============================================================
setlocal
cd /d "%~dp0"

rem --- Find Python -------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo.
  echo   Python 3.10 or newer was not found on this PC.
  echo   Install it from https://www.python.org/downloads/
  echo   and tick "Add python.exe to PATH" during setup, then run this again.
  echo.
  pause
  exit /b 1
)

rem --- Create a private environment on first run ------------------
if not exist ".venv\Scripts\python.exe" (
  echo   First-time setup. This happens only once and may take a minute...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo   Could not create the environment. See the messages above.
    pause
    exit /b 1
  )
)
set "VPY=.venv\Scripts\python.exe"

rem --- Install on first run --------------------------------------
rem  The core app has NO dependencies and always installs.
rem  Paystub import (PyMuPDF) is optional and installed best-effort,
rem  so it can never stop the app from launching.
"%VPY%" -c "import twe" >nul 2>nul
if errorlevel 1 (
  echo   Installing the Tax Withholding Estimator...
  "%VPY%" -m pip install --upgrade pip setuptools wheel > setup.log 2>&1
  "%VPY%" -m pip install -e . >> setup.log 2>&1
  if errorlevel 1 (
    echo.
    echo   Setup failed. Details below ^(also saved to setup.log^):
    echo   ------------------------------------------------------------
    type setup.log
    echo   ------------------------------------------------------------
    pause
    exit /b 1
  )
  echo   Adding optional paystub-import support ^(safe to skip if it fails^)...
  "%VPY%" -m pip install pymupdf >> setup.log 2>&1
  if errorlevel 1 (
    echo   Note: paystub import is unavailable on this PC, but everything
    echo   else works. You can still enter numbers by hand. ^(See setup.log^)
  )
)

rem --- Launch ----------------------------------------------------
echo.
echo   Starting the Tax Withholding Estimator...
echo   Your web browser should open at:  http://127.0.0.1:8765
echo   If it does not open, paste that address into your browser.
echo   Leave this window open while you use the app. Press Ctrl+C to stop.
echo.
"%VPY%" -m twe.cli serve
echo.
echo   The app has stopped. If you saw an error above, copy it so it can be fixed.
pause
endlocal
