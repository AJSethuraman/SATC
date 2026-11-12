@echo off
title Service Inviter installer
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Asking for administrator permission to write to Program Files...
  if "%~1"=="" (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  ) else (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%~1' -Verb RunAs"
  )
  exit /b
)
set TI_ACTION=%~1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText('%~f0'); $i=$t.IndexOf('#PS'+'-BEGIN'); Invoke-Expression $t.Substring($i)"
echo.
pause
exit /b
#PS-BEGIN
$ErrorActionPreference = 'Stop'
$preferred = 'C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns'
$fallbacks = @(
  'C:\Program Files\World of Warcraft\_forever_\Interface\AddOns',
  'D:\World of Warcraft\_forever_\Interface\AddOns',
  'C:\World of Warcraft\_forever_\Interface\AddOns'
)
$dest = $null
foreach ($c in @($preferred) + $fallbacks) {
  if (Test-Path -LiteralPath $c) { $dest = $c; break }
}
if (-not $dest) {
  Write-Host "Could not find the Forever AddOns folder at:" -ForegroundColor Yellow
  Write-Host "  $preferred"
  $dest = Read-Host "Paste the full path to your Forever AddOns folder (or press Enter to quit)"
  if (-not $dest -or -not (Test-Path -LiteralPath $dest)) { Write-Host "Nothing installed."; return }
}
$target = Join-Path $dest 'ServiceInviter'

if ($env:TI_ACTION -eq 'uninstall') {
  if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force; Write-Host "Removed $target" -ForegroundColor Green }
  else { Write-Host "Service Inviter was not installed in $dest" }
  return
}

$b64 = @'
{PAYLOAD}
'@
$bytes = [Convert]::FromBase64String(($b64 -replace '\s',''))
$zip = Join-Path $env:TEMP 'ServiceInviter-install.zip'
[IO.File]::WriteAllBytes($zip, $bytes)
if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
Remove-Item -LiteralPath $zip -Force

$toc = Join-Path $target 'ServiceInviter.toc'
$lua = Join-Path $target 'ServiceInviter.lua'
if ((Test-Path -LiteralPath $toc) -and (Test-Path -LiteralPath $lua)) {
  Write-Host ""
  Write-Host "Installed Service Inviter to:" -ForegroundColor Green
  Write-Host "  $target"
  Write-Host ""
  Write-Host "In game: type /reload (or restart WoW), then /si setup for every message and option, /si for the customer list."
  # Retire the old Trade Inviter: move it OUT of AddOns into a backup folder (nothing is deleted).
  $old = Join-Path $dest 'TradeInviter'
  if (Test-Path -LiteralPath $old) {
    $backup = Join-Path (Split-Path -Parent $dest) 'TradeInviter-backup'
    if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Recurse -Force }
    Move-Item -LiteralPath $old -Destination $backup
    Write-Host "Trade Inviter was moved out of AddOns to:" -ForegroundColor Green
    Write-Host "  $backup"
    Write-Host "Service Inviter now does the inviting itself. Your old settings were already copied over."
    Write-Host "Make sure 'Invite people who ask for a summon/port' is ticked in /si setup."
  }
  Write-Host "If it is greyed out in the AddOns list, tick 'Load out of date AddOns'."
} else {
  Write-Host "Install failed: files are missing from $target" -ForegroundColor Red
}
