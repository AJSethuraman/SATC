@echo off
cd /d "%~dp0"
echo Tax Document Sorter setup is starting...
echo.
py -3.12 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3.12 setup_tax_doc_sorter.py
) else (
    py setup_tax_doc_sorter.py
)
echo.
echo Setup window will remain open so you can read any messages above.
pause
