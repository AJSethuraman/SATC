@echo off
REM One-command setup + launch for the EDGAR Industry Assumption-Set Tool (Windows).
REM
REM   run.bat                                    (first run: setup, then self-test)
REM   run.bat --sic 5140 --years 7 --out food_dist
REM
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "VENV=.venv"

REM 1. Virtualenv + install (only on first run).
if not exist "%VENV%" (
  echo ^>^> Creating virtual environment in %VENV% ...
  python -m venv "%VENV%"
)
call "%VENV%\Scripts\activate.bat"

if not exist "%VENV%\.installed" (
  echo ^>^> Installing the tool and its dependencies ...
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -e ".[test]"
  type nul > "%VENV%\.installed"
)

REM 2. Resolve SEC-required contact email.
set "HAVE_UA="
for %%a in (%*) do (
  if "%%a"=="--user-agent" set "HAVE_UA=1"
)

set "UA_ARGS="
if not defined HAVE_UA (
  if defined EDGAR_USER_AGENT (
    set "UA=%EDGAR_USER_AGENT%"
  ) else if exist ".edgar_contact" (
    set /p UA=<.edgar_contact
  ) else (
    echo.
    echo SEC EDGAR requires a contact email in every request's User-Agent.
    set /p EMAIL=">> Enter your contact email: "
    set "UA=SATC EDGAR assumption tool !EMAIL!"
    <nul set /p="!UA!" > .edgar_contact
    echo.
    echo ^>^> Saved to .edgar_contact (reused next time).
  )
  set "UA_ARGS=--user-agent "!UA!""
)

REM 3. Launch (self-test when no args).
if "%~1"=="" (
  echo.
  echo ^>^> No arguments — running --self-test. Example real run:
  echo ^>^>   run.bat --sic 5140 --years 7 --out food_dist
  echo.
  python edgar_assumptions.py --self-test %UA_ARGS%
) else (
  python edgar_assumptions.py %* %UA_ARGS%
)
endlocal
