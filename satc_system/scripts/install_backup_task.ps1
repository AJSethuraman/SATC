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

param(
    # Set by the elevated re-launch below. Carries the name of the user the
    # task must RUN as, which is not necessarily the admin who approved UAC.
    [string]$ForUser = $env:USERNAME
)

$ErrorActionPreference = "Stop"

# REGISTERING A TASK NEEDS ELEVATION, RUNNING IT MUST NOT.
#
# `Register-ScheduledTask` writes to the root task store, which a standard user
# cannot do -- it fails with `Access is denied` / HRESULT 0x80070005. So this
# re-launches itself through UAC.
#
# The task it then registers runs as the ORIGINAL user, not as the admin who
# approved the prompt, and only while that user is logged on (`-LogonType
# Interactive`, `-RunLevel Limited`). That is not a detail: the job has to see
# that user's OneDrive folder, and a task running as SYSTEM or as a different
# account would find nothing there and back up nothing, successfully.
$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$elevated  = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $elevated) {
    Write-Host "  Not elevated. Registering a scheduled task requires it -- asking for consent."
    Write-Host "  (The job itself will run as $($env:USERNAME), unelevated, so it can see your OneDrive.)"
    Write-Host ""
    $argv = @(
        "-ExecutionPolicy", "Bypass",
        "-NoProfile",
        "-File", "`"$PSCommandPath`"",
        "-ForUser", "`"$($env:USERNAME)`""
    )
    try {
        $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argv `
                           -Verb RunAs -Wait -PassThru
        exit $p.ExitCode
    } catch {
        Write-Host "  UAC was declined, so the task was not installed." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Nothing is broken -- the backup script itself needs no admin rights."
        Write-Host "  You can run a backup by hand at any time with:"
        Write-Host "    python `"$env:USERPROFILE\.satc\backup_client_data.py`" --verify-restore"
        exit 1
    }
}

$TaskName = "SATC - Back up client data to OneDrive"

# The profile of the user the job RUNS as. When UAC was approved with a
# different admin account, `$env:USERPROFILE` is that admin's -- and pointing
# the backup at the wrong profile would find no OneDrive and no data.
$Home_ = Join-Path (Split-Path $env:USERPROFILE -Parent) $ForUser
if (-not (Test-Path $Home_)) { $Home_ = $env:USERPROFILE }

$Script   = Join-Path $Home_ ".satc\backup_client_data.py"
$Log      = Join-Path $Home_ ".satc\backup.log"
Write-Host "  running as $ForUser, profile $Home_"

# Deploy the script next to where it will run from, so the task does not depend
# on which branch a working checkout happens to be sitting on.
$SourceScript = Join-Path $PSScriptRoot "backup_client_data.py"
New-Item -ItemType Directory -Force -Path (Split-Path $Script) | Out-Null
Copy-Item $SourceScript $Script -Force
Write-Host "  deployed  $Script"

# Plain system Python: the script is stdlib-only, so it must not depend on a venv.
#
# `python.exe`, NOT `pythonw.exe`. The windowed build has no console and its
# `sys.stdout` can be invalid, so a run that failed could write nothing to the
# log and look exactly like a run that never happened. A console that flashes
# for a second once a day is a much better trade than a silent backup.
$Py = Join-Path $Home_ "AppData\Local\Programs\Python\Python312\python.exe"
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

# RUNS AS THE OWNER, ONLY WHILE THEY ARE LOGGED ON.
#
# `Interactive` and `Limited` on purpose. The job needs that user's OneDrive
# folder, which only exists inside their session; running it as SYSTEM or with
# the highest privileges would find nothing and report success at backing up
# nothing. It also means no stored password.
$principalObj = New-ScheduledTaskPrincipal `
    -UserId    $ForUser `
    -LogonType Interactive `
    -RunLevel  Limited

Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $action `
    -Trigger     $triggers `
    -Settings    $settings `
    -Principal   $principalObj `
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
