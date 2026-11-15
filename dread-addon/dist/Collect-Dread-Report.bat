@echo off
setlocal
set "WOW=C:\Program Files (x86)\World of Warcraft\_forever_"
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
