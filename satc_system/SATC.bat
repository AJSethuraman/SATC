@echo off
REM Double-click to start SATC (Windows). Opens the app in your browser.
cd /d "%~dp0"
if not exist .venv (
  echo SATC isn't installed yet - running the installer first...
  call install.bat
)
call .venv\Scripts\activate.bat
satc app
