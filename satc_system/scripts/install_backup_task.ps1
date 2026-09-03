<#
.SYNOPSIS
  Install the daily "back the client data up to OneDrive" scheduled task.

.DESCRIPTION
  The Forge has one disk. It holds the data mart, the identity vault, and the
  only copy of both. This registers the job that changes that.

  What the job does, every day at 12:30 and again at logon:

    * snapshots satc_mart.db and satc_vault.db with SQLite's online backup API,
      so it is safe to run while the app is open
    * writes them into the SATC OneDrive under "SATC Backups\client-data\<UTC stamp>"
    * NEVER copies vault.key, and REFUSES the whole run if a key is found at
      the destination -- a vault and its key in one folder is not an encrypted
      vault
    * restores the copy it just made into a temp directory, checks every table
      against the live database, and deletes the temp copy
    * keeps the newest 14 dated copies

  Both triggers exist on purpose. `docs/satc-forge.md` records that this machine
  starts several things at LOGON rather than at boot, so a daily-only trigger
  would silently do nothing across a reboot nobody logged back into.

.NOTES
  Run as the signed-in user -- NOT elevated. The job has to see that user's
  OneDrive folder, and a task running as SYSTEM or as another account cannot.

  Requires that OneDrive is signed in to the SATC work account
  (tenant: Sethuraman Accounting Tax and Consulting LLP). Until it is, the job
  runs and fails loudly with an explanation rather than backing up nothing
  quietly.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File satc_system\scripts\install_backup_task.ps1
#>

$ErrorActionPreference = "Stop"

$TaskName = "SATC - Back up client data to OneDrive"
$Home_    = $env:USERPROFILE
$Script   = Join-Path $Home_ ".satc\backup_client_data.py"
$Log      = Join-Path $Home_ ".satc\backup.log"

# Deploy the script next to where it will run from, so the task does not depend
# on which branch a working checkout happens to be sitting on.
$SourceScript = Join-Path $PSScriptRoot "backup_client_data.py"
New-Item -ItemType Directory -Force -Path (Split-Path $Script) | Out-Null
Copy-Item $SourceScript $Script -Force
Write-Host "  deployed  $Script"

# Plain system Python: the script is stdlib-only, so it must not depend on a venv.
$Py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe"
if (-not (Test-Path $Py)) {
    $Py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
}
if (-not (Test-Path $Py)) {
    $Py = (Get-Command python -ErrorAction Stop).Source
}
Write-Host "  python    $Py"

# cmd wrapper so both streams land in a log that can be read after the fact.
# A backup whose failure nobody sees is the failure mode this is guarding.
$Argument = '/c ""{0}" "{1}" --verify-restore >> "{2}" 2>&1"' -f $Py, $Script, $Log

$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $Argument

$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At 12:30pm),
    (New-ScheduledTaskTrigger -AtLogOn)
)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $action `
    -Trigger     $triggers `
    -Settings    $settings `
    -Description ("Snapshots satc_mart.db and satc_vault.db to the SATC OneDrive. " +
                  "Never copies vault.key and refuses if one is found at the destination. " +
                  "Verifies by restoring. Source: satc_system/scripts/backup_client_data.py") `
    -Force | Out-Null

Write-Host "  installed `"$TaskName`""
Write-Host ""
Write-Host "  Running it once now, so this is not a job nobody has watched work:"
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 20

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "    LastRunTime   $($info.LastRunTime)"
Write-Host "    LastTaskResult $($info.LastTaskResult)  (0 = success)"
Write-Host ""
if (Test-Path $Log) {
    Write-Host "  --- tail of $Log ---"
    Get-Content $Log -Tail 25 | ForEach-Object { "    $_" }
} else {
    Write-Host "  No log yet at $Log - give it a moment and check again."
}
Write-Host ""
Write-Host "  To remove it:  Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"
