# Do the walkthrough in Excel: type each step's values, let Excel recalculate,
# read each cell back from Excel, photograph what the step names, then put the
# typed cells back as they were. Writes out/observed.json and the pictures.
#
# Run from threshold-engine/ after expected.py and the build (WALKTHROUGH.md).
param([string]$Workbook = "docs\walkthrough\out\rehearsal.xlsx", [string]$StepsFile = "steps.json",
      [string]$ObservedFile = "observed.json")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$steps = (Get-Content (Join-Path $here $StepsFile) -Raw | ConvertFrom-Json).steps
$out = Join-Path $here "out"
$pics = Join-Path $here "pictures"
New-Item -ItemType Directory -Force $pics | Out-Null

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
$wb = $xl.Workbooks.Open((Resolve-Path $Workbook).Path)
$xl.CalculateFull()
$observed = @{ excel = $xl.Version; workbook = $wb.FullName; sheets = @(); steps = @() }
foreach ($ws in $wb.Worksheets) { $observed.sheets += $ws.Name }

function Picture($p) {
    $file = Join-Path $pics $p.file
    if (Test-Path $file) { Remove-Item $file }
    $ws = $wb.Worksheets.Item($p.sheet)
    if ($p.chart) {
        $null = $ws.ChartObjects($p.chart).Chart.Export($file)
    } else {
        $rng = $ws.Range($p.range)
        $ws.Activate()
        $null = $rng.CopyPicture(1, 2)                                 # as on screen, as a bitmap
        $co = $ws.ChartObjects().Add(0, 0, $rng.Width + 4, $rng.Height + 4)
        $co.Activate()
        Start-Sleep -Milliseconds 300
        $co.Chart.Paste()
        $null = $co.Chart.Export($file)
        $co.Delete()
    }
    return $p.file
}

# Excel hands an error back as a number; name it, so #N/A reads as #N/A even
# in a hidden helper column, where the cell's displayed text is blank.
$ERRORS = @{ -2146826281 = "#DIV/0!"; -2146826246 = "#N/A"; -2146826259 = "#NAME?"; -2146826288 = "#NULL!";
             -2146826252 = "#NUM!"; -2146826265 = "#REF!"; -2146826273 = "#VALUE!" }
function Read($r) {
    if ($r.sheet -eq "=") {
        $v = $xl.Evaluate($r.cell)
        if ($v -is [System.__ComObject]) { $v = $v.Value2 }          # a formula that returns a cell
        $t = "$v"
    } else {
        $c = $wb.Worksheets.Item($r.sheet).Range($r.cell)
        $v = $c.Value2
        $t = $c.Text
    }
    if ($v -is [int] -and $ERRORS.ContainsKey($v)) { $t = $ERRORS[$v] }
    return @{ value = $v; text = $t }
}

foreach ($s in $steps) {
    $saved = @()
    foreach ($a in $s.actions) {
        $c = $wb.Worksheets.Item($a.sheet).Range($a.cell)
        $saved += ,@($a.sheet, $a.cell, $c.Formula)
        # Typed as a person types it: the text of the value, which Excel parses
        # (0.75 a number, FALSE a logical, 2007Q4 and "one" text).
        $v = $a.value
        if ($v -is [bool]) { $v = if ($v) { "TRUE" } else { "FALSE" } }
        $c.Formula = [string]::Format([cultureinfo]::InvariantCulture, "{0}", $v)
    }
    $xl.CalculateFull()
    $reads = @()
    foreach ($r in $s.reads) {
        $got = Read $r
        $reads += @{ sheet = $r.sheet; cell = $r.cell; value = $got.value; text = $got.text }
    }
    $taken = @()
    foreach ($p in $s.picture) { $taken += Picture $p }
    [array]::Reverse($saved)
    foreach ($x in $saved) { $wb.Worksheets.Item($x[0]).Range($x[1]).Formula = $x[2] }
    $xl.CalculateFull()
    $observed.steps += @{ id = $s.id; reads = $reads; pictures = $taken }
    Write-Output ("{0}: {1} cells read" -f $s.id, $reads.Count)
}

# After every step, the workbook must be back as built: the as-built Check column, blank.
$observed.check_after = @(5..8 | ForEach-Object { $wb.Worksheets.Item("Thresholds").Range("M$_").Text })
$wb.Close($false)
$xl.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
$observed | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $out $ObservedFile)
Write-Output "Excel $($observed.excel): $($observed.steps.Count) steps"
