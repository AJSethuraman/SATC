@echo off
REM Start the SATC app bound to the Tailscale interface only.
REM
REM SATC_BIND          which address to listen on. The Tailscale interface, so
REM                    the app is NOT listening on the local network at all.
REM SATC_ALLOWED_HOSTS which Host headers the app will answer to. An ALLOWLIST:
REM                    the app's H2 guard still refuses anything not named here,
REM                    which is what keeps DNS-rebinding blocked.
REM
REM Loopback stays allowed, so the Forge itself keeps working as before.

set SATC_BIND=100.125.166.122
set SATC_ALLOWED_HOSTS=100.125.166.122,satc-forge
set SATC_NO_BROWSER=1

cd /d "%~dp0..\satc_system"
echo.
echo   Starting SATC on the tailnet. Leave this window open.
echo   From another device on your tailnet:  http://100.125.166.122:5050
echo.
".venv\Scripts\python.exe" -m satc.app.server
