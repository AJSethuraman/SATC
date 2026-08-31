<#
    Fetch the IRS's own blank fillable forms for the classifier corpus.

    The PowerShell twin of fetch.sh, for a Windows machine with no Git Bash.
    Same forms, same behaviour, same promise: it names every form it could not
    get instead of failing quietly, so a form the IRS has moved is something you
    can see rather than a silent gap in the corpus.

    RUN IT:
        powershell -ExecutionPolicy Bypass -File .\fetch.ps1

    The -ExecutionPolicy flag is there because an unsigned .ps1 will not run on a
    default Windows install, and that refusal looks like the script being broken
    rather than Windows doing its job. Nothing here needs admin.

    WHY THESE AND NOT MORE SYNTHETIC PAGES. Everything else in the corpus is text
    this repository generated, and generated text proves almost nothing: a page
    reading "Form W-2 / 1 Wages, tips, other compensation" classifies as a W-2 and
    always will. A real blank carries the REAL AcroForm field names, the REAL
    layout, and the REAL text-layer reading order -- the three things that
    actually decide the answer, and the three things that were wrong in the field
    while the synthetic tests stayed green.

    These are public IRS documents. No client data goes in this folder, ever.

    NOT RUN BY ITS AUTHOR. There is no PowerShell in the environment this was
    written in and irs.gov is blocked from it, so this script has never been
    executed. Its bash twin's failure path was exercised; this one's has not.
    If it misbehaves, that is why -- say so and it gets fixed rather than
    defended.
#>

# Invoke-WebRequest draws a progress bar that makes downloads roughly ten times
# slower on Windows PowerShell 5.1. Off before the first request, not after.
$ProgressPreference = 'SilentlyContinue'

# Windows PowerShell 5.1 still negotiates TLS 1.0 by default, which irs.gov
# refuses. Harmless on PowerShell 7, where it is already the default.
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.SecurityProtocolType]::Tls12 -bor [Net.ServicePointManager]::SecurityProtocol
} catch { }

$here = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

$forms = [ordered]@{
    'fw2'       = 'W-2        Wage and Tax Statement'
    'f1099int'  = '1099-INT   Interest Income'
    'f1099div'  = '1099-DIV   Dividends and Distributions'
    'f1099b'    = '1099-B     Proceeds From Broker Transactions'
    'f1099nec'  = '1099-NEC   Nonemployee Compensation'
    'f1099msc'  = '1099-MISC  Miscellaneous Information'
    'f1099r'    = '1099-R     Distributions From Pensions'
    'f1099g'    = '1099-G     Certain Government Payments'
    'f1098'     = '1098       Mortgage Interest Statement'
    'f1098t'    = '1098-T     Tuition Statement'
    'f1095a'    = '1095-A     Health Insurance Marketplace Statement'
    'f1040'     = '1040       U.S. Individual Income Tax Return'
    'f1040sc'   = 'Schedule C Profit or Loss From Business'
    'f1065sk1'  = 'K-1 (1065) Partner''s Share'
    'f1120ssk1' = 'K-1 (1120-S) Shareholder''s Share'
}

$ok = 0
$missing = @()

foreach ($form in $forms.Keys) {
    $url  = "https://www.irs.gov/pub/irs-pdf/$form.pdf"
    $dest = Join-Path $here "$form.pdf"
    Write-Host ("  {0,-12} " -f $form) -NoNewline

    try {
        # Invoke-WebRequest THROWS on a non-2xx rather than returning it, so the
        # only way to tell "moved" from "fetched" is this catch.
        Invoke-WebRequest -Uri $url -OutFile $dest -TimeoutSec 45 -UseBasicParsing
    } catch {
        # fall through to the size check, which is the real test
    }

    $file = Get-Item -LiteralPath $dest -ErrorAction SilentlyContinue
    if ($file -and $file.Length -gt 0) {
        Write-Host ("ok  ({0:N0} bytes)" -f $file.Length)
        $ok++
    } else {
        if ($file) { Remove-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue }
        Write-Host 'COULD NOT FETCH'
        $missing += $form
    }
}

Write-Host ''
Write-Host ("  {0} of {1} fetched." -f $ok, $forms.Count)

if ($missing.Count -gt 0) {
    Write-Host ''
    Write-Host ("  Not fetched: {0}" -f ($missing -join ' '))
    Write-Host '  Search irs.gov for the form by name and drop the PDF in this folder'
    Write-Host '  under the same base name. A missing form is not a failure -- the corpus'
    Write-Host '  uses whatever is here.'
}

Write-Host ''
Write-Host '  Nothing else to do. Committing these is fine: they are public IRS forms'
Write-Host '  and carry no client data.'
