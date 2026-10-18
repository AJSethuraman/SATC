# Read the figure out of the workbook the firm opens, in Excel, and photograph it.
#
#   (from threshold-engine/)
#   powershell -ExecutionPolicy Bypass -File docs\tie-out\keybank-card-nonaccrual-2026-10-14\scripts\read_workbook.ps1 `
#       -Workbook C:\path\to\book.xlsx -Out C:\path\to\folder
#
# Opens the workbook in a NEW Excel (never one somebody else started), recalculates
# in full, reads every hop of the chain - Summary, Decide's headline after picking
# the three slicers, Thresholds row J, the Data tab column - and writes them, with
# the formula behind each, to OUT\workbook-reads.json. Pictures go to OUT\*.png,
# taken by Excel itself (Range.CopyPicture), not redrawn from Python.
# Nothing is saved: the workbook is closed without saving, Excel is quit in finally.
#
# The series is a parameter, so the firm's own build, or another figure, can be
# tied out the same way: -Product, -Measure, -Source.
param(
    [Parameter(Mandatory = $true)][string]$Workbook,
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Product = "Credit card",
    [string]$Measure = "Nonaccrual",
    [string]$Source = "KeyBank"
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Out | Out-Null
$Out = (Resolve-Path $Out).Path              # Excel resolves a relative path against its own folder, not ours
$label = "$Product - $Measure - $Source"

$ERRORS = @{ -2146826281 = "#DIV/0!"; -2146826246 = "#N/A"; -2146826259 = "#NAME?"; -2146826288 = "#NULL!";
             -2146826252 = "#NUM!"; -2146826265 = "#REF!"; -2146826273 = "#VALUE!" }

$xl = New-Object -ComObject Excel.Application
try {
    $xl.Visible = $false
    $xl.DisplayAlerts = $false
    $wb = $xl.Workbooks.Open((Resolve-Path $Workbook).Path, 0, $true)     # read-only
    $xl.CalculateFull()

    function Cell($sheet, $addr) {
        $c = $wb.Worksheets.Item($sheet).Range($addr)
        $v = $c.Value2
        $t = $c.Text
        if ($v -is [int] -and $ERRORS.ContainsKey($v)) { $t = $ERRORS[$v] }
        return [ordered]@{ sheet = $sheet; cell = $addr; value = $v; text = $t; formula = $c.Formula;
                           value_r17 = $(if ($v -is [double]) { $v.ToString("R", [cultureinfo]::InvariantCulture) } else { "$v" }) }
    }

    # The cell the figure sits in gets a thick red border for the picture only; the
    # workbook is open read-only and closed without saving, so nothing is kept.
    function Picture($sheet, $addr, $file, $mark) {
        $path = Join-Path $Out $file
        if (Test-Path $path) { Remove-Item $path }
        $ws = $wb.Worksheets.Item($sheet)
        $null = $ws.Activate()
        if ($mark) { $null = $ws.Range($mark).MergeArea.BorderAround(1, -4138, [Type]::Missing, 214) }   # red 214,0,0
        $rng = $ws.Range($addr)
        $null = $rng.CopyPicture(1, 2)                                   # as on screen, as a bitmap
        $co = $ws.ChartObjects().Add(0, 0, $rng.Width + 4, $rng.Height + 4)
        $null = $co.Activate()
        Start-Sleep -Milliseconds 400
        $null = $co.Chart.Paste()
        $null = $co.Chart.Export($path)
        $null = $co.Delete()
        return $file
    }

    function FindRow($sheet, $col, $first, $last, $text) {
        $ws = $wb.Worksheets.Item($sheet)
        $hits = @()
        for ($r = $first; $r -le $last; $r++) { if ($ws.Range("$col$r").Text -eq $text) { $hits += $r } }
        if ($hits.Count -ne 1) { throw "$sheet column $col rows $first-${last}: '$text' found $($hits.Count) times" }
        return $hits[0]
    }

    $reads = [ordered]@{ excel = $xl.Version; workbook = $wb.FullName; series = $label;
                         read_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }

    # ---- Summary: the row for product and measure, the column group for the source
    $sm = $wb.Worksheets.Item("Summary")
    $srow = $null
    $prod = ""
    for ($r = 7; $r -le $sm.UsedRange.Rows.Count + 5; $r++) {
        if ($sm.Range("A$r").Text -ne "") { $prod = $sm.Range("A$r").Text }
        if ($prod -eq $Product -and $sm.Range("B$r").Text -eq $Measure) { $srow = $r; break }
    }
    if (-not $srow) { throw "Summary: no row for $Product / $Measure" }
    $scol = $null
    foreach ($c in @("C", "E", "G")) { if ($sm.Range("${c}5").Text -eq $Source) { $scol = $c } }
    if (-not $scol) { throw "Summary: no column group headed $Source in row 5" }
    $rcol = [char]([int][char]$scol + 1)
    $reads.summary = [ordered]@{ row = $srow; column = $scol;
        group = (Cell "Summary" "${scol}5"); heading = (Cell "Summary" "${scol}6"); measure = (Cell "Summary" "B$srow");
        latest = (Cell "Summary" "$scol$srow"); rating = (Cell "Summary" "$rcol$srow"); quarter_line = (Cell "Summary" "A2") }
    $sumpic = Picture "Summary" ("A5:I" + ($srow + 1)) "ours-summary.png" "$scol$srow"

    # ---- Thresholds: the row whose Series is the label
    $trow = FindRow "Thresholds" "A" 5 99 $label
    $reads.thresholds = [ordered]@{ row = $trow; series = (Cell "Thresholds" "A$trow");
        quarter = (Cell "Thresholds" "I$trow"); latest = (Cell "Thresholds" "J$trow");
        rating = (Cell "Thresholds" "K$trow"); rating_name = (Cell "Thresholds" "L$trow"); check = (Cell "Thresholds" "M$trow");
        header_j = (Cell "Thresholds" "J4") }
    $th = $wb.Worksheets.Item("Thresholds")
    $hide = @()
    if ($trow -gt 5) { $hide += "5:" + ($trow - 1) }
    $hide += ("" + ($trow + 1) + ":99")
    foreach ($h in $hide) { $th.Rows($h).Hidden = $true }
    $thpic = Picture "Thresholds" ("A3:L$trow") "ours-thresholds.png" "J$trow"
    foreach ($h in $hide) { $th.Rows($h).Hidden = $false }

    # ---- Data: the column headed by the label, its last row
    $dt = $wb.Worksheets.Item("Data")
    $dcol = $null
    $ncols = $dt.UsedRange.Columns.Count
    for ($c = 2; $c -le $ncols; $c++) { if ($dt.Cells(1, $c).Text -eq $label) { $dcol = $c; break } }
    if (-not $dcol) { throw "Data: no column headed '$label'" }
    $letter = ($dt.Cells(1, $dcol).Address($false, $false)) -replace "\d", ""
    $last = $dt.Cells($dt.Rows.Count, 1).End(-4162).Row                   # xlUp
    $reads.data = [ordered]@{ column = $letter; last_row = $last; header = (Cell "Data" "${letter}1");
        quarter = (Cell "Data" "A$last"); latest = (Cell "Data" "$letter$last");
        previous_quarter = (Cell "Data" ("A" + ($last - 1))); previous = (Cell "Data" ("$letter" + ($last - 1))) }
    $dt.Range("B:" + ($dt.Cells(1, $dcol - 1).Address($false, $false) -replace "\d", "")).EntireColumn.Hidden = $true
    $dt.Rows("2:" + ($last - 4)).Hidden = $true
    $dpic = Picture "Data" ("A1:$letter$last") "ours-data.png" "$letter$last"
    $dt.Rows("2:" + ($last - 4)).Hidden = $false
    $dt.Range("B:" + ($dt.Cells(1, $dcol - 1).Address($false, $false) -replace "\d", "")).EntireColumn.Hidden = $false

    # ---- Decide: pick the three slicers as a person clicks them, then read the headline
    function Pick($cache, $item) {
        $sc = $wb.SlicerCaches.Item($cache)
        $sc.SlicerItems.Item($item).Selected = $true
        foreach ($it in $sc.SlicerItems) { if ($it.Name -ne $item) { $it.Selected = $false } }
        $picked = @($sc.SlicerItems | Where-Object { $_.Selected } | ForEach-Object { $_.Name })
        if ($picked.Count -ne 1 -or $picked[0] -ne $item) { throw "$cache did not end on $item alone: $picked" }
        return $item
    }
    $null = Pick "Slicer_Product" $Product
    $null = Pick "Slicer_Measure" $Measure
    $null = Pick "Slicer_Source" $Source
    $xl.CalculateFull()
    $dc = $wb.Worksheets.Item("Decide")
    $hrow = $null
    for ($r = 100; $r -le 200; $r++) { if ($dc.Range("B$r").Text -eq "Where it stands now") { $hrow = $r + 1; break } }
    if (-not $hrow) { throw "Decide: no 'Where it stands now' band" }
    $reads.decide = [ordered]@{ selected_series = (Cell "Decide" "AA1"); series_shown = (Cell "Decide" "AA2");
        thresholds_row = (Cell "Decide" "AA3"); headline_row = $hrow; headline = (Cell "Decide" "B$hrow") }
    $cmp = @()
    for ($r = $hrow + 2; $r -le $hrow + 8; $r++) {
        if ($dc.Range("B$r").Text -eq $Source) { $cmp += [ordered]@{ row = $r; source = (Cell "Decide" "B$r"); latest = (Cell "Decide" "E$r"); rating = (Cell "Decide" "F$r") } }
    }
    $reads.decide.compare_row = $cmp
    $dpic1 = Picture "Decide" "B1:N11" "ours-decide-slicers.png" $null
    $dpic2 = Picture "Decide" ("B" + ($hrow - 1) + ":N" + ($hrow + 6)) "ours-decide-headline.png" "B$hrow"
    $reads.pictures = @($sumpic, $thpic, $dpic, $dpic1, $dpic2)

    $wb.Close($false)
    $reads | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Out "workbook-reads.json")
    Write-Output ("Excel {0}: Summary {1}{2} = {3}; Thresholds J{4} = {5}; Data {6}{7} = {8}; Decide B{9}: {10}" -f
        $reads.excel, $scol, $srow, $reads.summary.latest.value_r17, $trow, $reads.thresholds.latest.value_r17,
        $letter, $last, $reads.data.latest.value_r17, $hrow, $reads.decide.headline.text)
}
finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
