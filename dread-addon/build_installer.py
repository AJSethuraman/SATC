"""Builds dist/Install-Dread.bat: one double-click file that carries the addon inside it and
copies it into the Forever AddOns folder. Run again after any change to Dread/.

    python build_installer.py
"""
import base64, io, os, zipfile

TARGET = r"C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns"

HEAD = r"""@echo off
setlocal
set "ADDONS=__TARGET__"
title Install Dread

rem No parenthesised blocks anywhere in this file: the ")" in "(x86)" ends a block early and
rem closes the window with a syntax error. Everything branches with goto instead.

net session >nul 2>&1
if errorlevel 1 goto elevate
if not exist "%ADDONS%" goto nofolder

echo Installing Dread into %ADDONS%\Dread ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ErrorActionPreference='Stop';" ^
 "$b64 = (Get-Content -LiteralPath '%~f0' | Where-Object { $_.StartsWith('::B64:') } | ForEach-Object { $_.Substring(6) }) -join '';" ^
 "$zip = Join-Path $env:TEMP 'Dread.zip';" ^
 "[IO.File]::WriteAllBytes($zip, [Convert]::FromBase64String($b64));" ^
 "$old = Join-Path '%ADDONS%' 'Dread'; if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force };" ^
 "Expand-Archive -LiteralPath $zip -DestinationPath '%ADDONS%' -Force;" ^
 "Remove-Item -LiteralPath $zip;" ^
 "Get-ChildItem -LiteralPath (Join-Path '%ADDONS%' 'Dread') | Select-Object -ExpandProperty Name"
if errorlevel 1 goto failed
echo.
echo Done. In WoW, type /reload and then /dread
goto finish

:elevate
echo Asking for administrator permission to write to Program Files...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:nofolder
echo Could not find: %ADDONS%
echo Edit the ADDONS line at the top of this file to your AddOns folder, then run it again.
goto finish

:failed
echo.
echo Something went wrong. Copy the message above and send it over.

:finish
echo.
pause
exit /b

"""

def stamp():
    """Dread/Build.lua says when this install was built, and the window title shows it, so 'which version do you have' has an answer."""
    import datetime
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %H:%M UTC")
    with open("Dread/Build.lua", "w") as fh:
        fh.write('-- Written by build_installer.py. Do not edit.\nlocal _, ns = ...\nns = ns or {}\nns.BUILD = "%s"\n' % when)


def main():
    stamp()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir("Dread")):
            z.write(os.path.join("Dread", f), "Dread/" + f)
    b64 = base64.b64encode(buf.getvalue()).decode()
    lines = [b64[i:i + 100] for i in range(0, len(b64), 100)]
    text = HEAD.replace("__TARGET__", TARGET) + "\n".join("::B64:" + l for l in lines) + "\n"
    os.makedirs("dist", exist_ok=True)
    with open("dist/Install-Dread.bat", "w", newline="") as fh:
        fh.write(text.replace("\n", "\r\n"))
    with open("dist/Dread.zip", "wb") as fh:
        fh.write(buf.getvalue())
    with zipfile.ZipFile("dist/Install-Dread.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write("dist/Install-Dread.bat", "Install-Dread.bat")
    print("wrote dist/Install-Dread.bat, dist/Install-Dread.zip and dist/Dread.zip")

if __name__ == "__main__":
    main()
