@echo off
REM One-step SATC install (Windows). Double-click this file.
REM Creates a private virtual environment and installs SATC for fully-local use.
cd /d "%~dp0"

echo.
echo   Installing SATC (this stays entirely on your computer)...
echo.

where py >nul 2>nul && (set "PY=py") || (set "PY=python")
%PY% --version >nul 2>nul || (
  echo   X Python is not installed. Get it from https://www.python.org/downloads/ ^(check "Add to PATH"^) and re-run.
  pause
  exit /b 1
)

%PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -e ".[local]"

echo.
where tesseract >nul 2>nul && (
  echo   Local OCR ^(Tesseract^) is installed - scanned docs will be read on this machine.
) || (
  echo   Optional: install Tesseract to read scans locally:
  echo       https://github.com/UB-Mannheim/tesseract/wiki
)

echo.
echo   Installed.  Start SATC by double-clicking SATC.bat
echo.
call .venv\Scripts\satc.exe doctor
pause
