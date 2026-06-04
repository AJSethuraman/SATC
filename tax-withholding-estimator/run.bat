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

rem --- Install or update the app ---------------------------------
"%VPY%" -c "import twe" >nul 2>nul
if errorlevel 1 (
  echo   Installing the Tax Withholding Estimator...
  "%VPY%" -m pip install --upgrade pip >nul 2>nul
  "%VPY%" -m pip install -e ".[paystub]"
  if errorlevel 1 (
    echo.
    echo   Installation failed. See the messages above.
    pause
    exit /b 1
  )
)

rem --- Launch ----------------------------------------------------
echo.
echo   Starting the Tax Withholding Estimator...
echo   Your web browser will open automatically.
echo   Leave this window open while you use the app.
echo   To stop: close this window, or press Ctrl+C.
echo.
"%VPY%" -m twe.cli serve

pause
endlocal
