<#
  Invoicer - Windows one-shot setup & run script.

  What it does (idempotent - safe to run repeatedly):
    1. Finds Python 3 (installs it via winget if missing).
    2. Creates a local virtual environment in .venv
    3. Installs the Python dependencies (pure pip - no native libraries,
       no GTK, no admin needed).
    4. Creates .env from the template if you don't have one.
    5. Starts the app and opens http://localhost:5000 in your browser.

  PDF rendering uses the pure-Python engine (xhtml2pdf), so there is nothing
  else to install for PDFs to work.

  How to run (from this folder):
    powershell -ExecutionPolicy Bypass -File .\run.ps1

  Stop the app with Ctrl+C.
#>

# Don't let a non-zero exit from a native command (e.g. a probe) abort the
# whole script; we check exit codes explicitly where it matters.
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
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
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { throw "Virtual environment creation failed." }

# --------------------------------------------------------------------------
# 3. Python dependencies
# --------------------------------------------------------------------------
Write-Step "Installing Python dependencies (this can take a minute)"
& $venvPy -m pip install --upgrade pip *> $null
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed. See the output above." }

# --------------------------------------------------------------------------
# 4. .env
# --------------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Step "Created .env"
    Write-Host "Optional: edit .env to add Stripe / SMTP / API_KEY. The app runs fine without them."
}

# --------------------------------------------------------------------------
# 5. Run
# --------------------------------------------------------------------------
Write-Step "Starting Invoicer"
Write-Host "Opening http://localhost:5000  (press Ctrl+C here to stop)" -ForegroundColor Green

# Open the browser a few seconds after the server starts.
Start-Job -ScriptBlock { Start-Sleep -Seconds 4; Start-Process "http://localhost:5000" } | Out-Null

# Use the pure-Python PDF engine on Windows (no GTK needed).
$env:PDF_ENGINE = "xhtml2pdf"
$env:FLASK_APP = "app"
& $venvPy -m flask run --host 127.0.0.1 --port 5000
