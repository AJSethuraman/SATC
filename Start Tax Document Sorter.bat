@echo off
cd /d "%~dp0"
echo Tax Document Sorter is starting...
echo Your browser should open automatically.
echo Keep this window open while using the app.
echo.
start "" http://127.0.0.1:5000
py -3.12 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3.12 app.py
) else (
    py app.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The app could not start. Dependencies may be missing.
    echo Please run Setup Tax Document Sorter.bat
    echo or run: py -3.12 setup_tax_doc_sorter.py
    echo.
)
pause
