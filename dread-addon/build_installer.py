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

WOW = r"C:\Program Files (x86)\World of Warcraft\_forever_"

# One double-click that gathers what a play session recorded: Dread's saved data (the game's own record of what happened) and the
# newest screenshots (taken automatically at deaths, bosses and rare finds) into one zip on the Desktop. Same rule as the installer:
# no parenthesised blocks, because the ")" in "(x86)" ends them early.
COLLECT = r"""@echo off
setlocal
set "WOW=__WOW__"
set "OUT=%USERPROFILE%\Desktop\Dread-report.zip"
title Collect Dread report

if not exist "%WOW%" goto nofolder

echo Collecting what Dread recorded...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ErrorActionPreference='Continue';" ^
 "$tmp = Join-Path $env:TEMP 'dread-report';" ^
 "if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force };" ^
 "New-Item -ItemType Directory -Path $tmp | Out-Null;" ^
 "$sv = @(); $sv += Get-ChildItem -Path '%WOW%\WTF\Account\*\SavedVariables\Dread.lua' -ErrorAction SilentlyContinue; $sv += Get-ChildItem -Path '%WOW%\WTF\Account\*\*\*\SavedVariables\Dread.lua' -ErrorAction SilentlyContinue;" ^
 "$n = 0; foreach ($f in $sv) { $n++; Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $tmp ('Dread-saved-' + $n + '.lua')) };" ^
 "$pics = Get-ChildItem -Path '%WOW%\Screenshots\*' -Include *.jpg,*.jpeg,*.png,*.tga -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) } | Sort-Object LastWriteTime -Descending | Select-Object -First 20;" ^
 "foreach ($p in $pics) { Copy-Item -LiteralPath $p.FullName -Destination $tmp };" ^
 "$count = @(Get-ChildItem -LiteralPath $tmp).Count;" ^
 "if ($count -eq 0) { Write-Host 'Nothing found. In WoW type /reload first, then run this again.'; exit 2 };" ^
 "if (Test-Path -LiteralPath '%OUT%') { Remove-Item -LiteralPath '%OUT%' -Force };" ^
 "Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath '%OUT%';" ^
 "Write-Host ('Saved ' + $n + ' saved-data file(s) and ' + @($pics).Count + ' screenshot(s).')"
if errorlevel 1 goto failed
echo.
echo Done: %OUT%
echo Send that file over. (If it has no saved data, type /reload in WoW first, then run this again.)
goto finish

:nofolder
echo Could not find: %WOW%
echo Edit the WOW line at the top of this file to your game folder, then run it again.
goto finish

:failed
echo.
echo Nothing was collected. In WoW type /reload (that writes Dread's data to disk), then run this again.

:finish
echo.
pause
exit /b
"""


def collect_text():
    return COLLECT.replace("__WOW__", WOW)


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
    with open("dist/Collect-Dread-Report.bat", "w", newline="") as fh:
        fh.write(collect_text().replace("\n", "\r\n"))
    with zipfile.ZipFile("dist/Install-Dread.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write("dist/Install-Dread.bat", "Install-Dread.bat")
        z.write("dist/Collect-Dread-Report.bat", "Collect-Dread-Report.bat")
    print("wrote dist/Install-Dread.bat, dist/Collect-Dread-Report.bat, dist/Install-Dread.zip and dist/Dread.zip")

if __name__ == "__main__":
    main()
