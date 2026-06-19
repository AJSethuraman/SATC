<#
  Invoicer - Windows one-shot setup & run script.

  What it does (idempotent - safe to run repeatedly):
    1. Finds Python 3 (installs it via winget if missing).
    2. Creates a local virtual environment in .venv
    3. Installs the Python dependencies.
    4. Installs the GTK runtime that WeasyPrint needs to render PDFs
       (only if it isn't already available).
    5. Creates .env from the template if you don't have one.
    6. Starts the app and opens http://localhost:5000 in your browser.

  How to run (from this folder):
    powershell -ExecutionPolicy Bypass -File .\run.ps1

  Stop the app with Ctrl+C.
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# --------------------------------------------------------------------------
# 1. Find (or install) Python 3
# --------------------------------------------------------------------------
Write-Step "Checking for Python 3"

$pyExe = $null
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = "py"; $pyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pyExe = "python3" }

if (-not $pyExe) {
    Write-Host "Python not found. Installing via winget..." -ForegroundColor Yellow
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python and winget are both missing. Install Python 3 from https://python.org and re-run."
    }
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    # Refresh PATH for the current session so the new python is visible.
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = "py"; $pyArgs = @("-3") }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = "python" }
    else { throw "Python install did not complete. Restart PowerShell and re-run .\run.ps1" }
}
Write-Host "Using: $pyExe $($pyArgs -join ' ')"

# --------------------------------------------------------------------------
# 2. Virtual environment
# --------------------------------------------------------------------------
Write-Step "Setting up virtual environment (.venv)"
if (-not (Test-Path ".venv")) {
    & $pyExe @pyArgs -m venv .venv
}
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { throw "Virtual environment creation failed." }

# --------------------------------------------------------------------------
# 3. Python dependencies
# --------------------------------------------------------------------------
Write-Step "Installing Python dependencies (this can take a minute)"
& $venvPy -m pip install --upgrade pip | Out-Null
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

# --------------------------------------------------------------------------
# 4. GTK runtime for WeasyPrint (PDF rendering)
# --------------------------------------------------------------------------
Write-Step "Checking PDF engine (WeasyPrint / GTK)"
$gtkBin = "C:\Program Files\GTK3-Runtime Win64\bin"

& $venvPy -c "import weasyprint" 2>$null
$weasyOk = ($LASTEXITCODE -eq 0)

if (-not $weasyOk) {
    if (-not (Test-Path $gtkBin)) {
        Write-Host "Installing the GTK runtime WeasyPrint needs..." -ForegroundColor Yellow
        $gtkUrl = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"
        $gtkExe = Join-Path $env:TEMP "gtk3-runtime-installer.exe"
        try {
            Invoke-WebRequest -Uri $gtkUrl -OutFile $gtkExe
            # Installer writes to Program Files, so run it elevated and silent.
            Start-Process -FilePath $gtkExe -ArgumentList "/S" -Verb RunAs -Wait
        } catch {
            Write-Warning "Automatic GTK install failed: $($_.Exception.Message)"
            Write-Warning "Install it manually from $gtkUrl then re-run .\run.ps1"
        }
    }
    # Make the GTK DLLs visible to this session (and the child flask process).
    if (Test-Path $gtkBin) { $env:Path = "$gtkBin;" + $env:Path }

    & $venvPy -c "import weasyprint" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "WeasyPrint still cannot load GTK in this session."
        Write-Warning "Close PowerShell, open a new window, and run .\run.ps1 again so the PATH update takes effect."
    } else {
        Write-Host "GTK runtime ready."
    }
} else {
    Write-Host "PDF engine ready."
}

# --------------------------------------------------------------------------
# 5. .env
# --------------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Step "Created .env"
    Write-Host "Optional: edit .env to add Stripe / SMTP / API_KEY. The app runs fine without them."
}

# --------------------------------------------------------------------------
# 6. Run
# --------------------------------------------------------------------------
Write-Step "Starting Invoicer"
Write-Host "Opening http://localhost:5000  (press Ctrl+C here to stop)" -ForegroundColor Green

# Open the browser a few seconds after the server starts.
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://localhost:5000" } | Out-Null

$env:FLASK_APP = "app"
& $venvPy -m flask run --host 127.0.0.1 --port 5000
