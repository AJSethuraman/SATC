@echo off
setlocal

if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --onefile --windowed main.py --name FileReviewScanner

echo Build complete. Executable is in dist\FileReviewScanner.exe
endlocal
