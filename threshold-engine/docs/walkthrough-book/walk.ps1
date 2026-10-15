# Do the book walkthrough in Excel 16 as a person would: click the slicers,
# type in the yellow row, save, close and reopen. Reads every answer back from
# Excel and photographs what the steps name. Writes out/observed.json.
#
# Run from threshold-engine/ after the build and expected.py (WALKTHROUGH.md).
# Works on a copy of the built workbook, because the steps save into it.
param([string]$Workbook = "docs\walkthrough-book\out\walk.xlsx")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$plan = Get-Content (Join-Path $here "steps.json") -Raw | ConvertFrom-Json
$out = Join-Path $here "out"
$pics = Join-Path $here "pictures"
New-Item -ItemType Directory -Force $pics | Out-Null
$path = (Resolve-Path $Workbook).Path

$ERRORS = @{ -2146826281 = "#DIV/0!"; -2146826246 = "#N/A"; -2146826259 = "#NAME?"; -2146826288 = "#NULL!";
             -2146826252 = "#NUM!"; -2146826265 = "#REF!"; -2146826273 = "#VALUE!" }

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFull()
    $observed = @{ excel = $xl.Version; workbook = $path; steps = @() }

    function Cache($caption) {
        foreach ($c in $wb.SlicerCaches) { foreach ($s in $c.Slicers) { if ($s.Caption -eq $caption) { return $c } } }
        throw "no slicer captioned $caption"
    }
    function Picked() {
        $o = [ordered]@{}
        foreach ($c in $wb.SlicerCaches) {
            $sel = @(); foreach ($it in $c.SlicerItems) { if ($it.Selected) { $sel += $it.Name } }
            $o[$c.Slicers.Item(1).Caption] = ($sel -join " | ")
        }
        return $o
    }
    function Visible($sheet) {
        $ws = $wb.Worksheets.Item($sheet)
        $lo = $ws.ListObjects.Item(1)
        $rows = @()
        foreach ($r in $lo.DataBodyRange.Rows) { if (-not $r.EntireRow.Hidden) { $rows += $r.Row } }
        return ,$rows
    }
    # Errors a reader can see: on visible tabs, outside hidden rows and columns.
    # The rest (hidden helper columns, the hidden Peers workings tab) are
    # counted by kind, so "they are all #N/A, the gaps a chart leaves" is
    # shown rather than assumed.
    function Errors() {
        $n = 0; $where = @(); $hidden = @{}
        foreach ($ws in $wb.Worksheets) {
            $e = $null
            try { $e = $ws.UsedRange.SpecialCells(-4123, 16) } catch { $e = $null }
            if ($e -ne $null) {
                # Visible is what Excel itself calls visible (SpecialCells
                # xlCellTypeVisible), taken once per tab: asking each cell
                # whether its column is hidden counted a hidden #N/A as seen
                # on one run in two (15 Oct 2026, Decide!AZ65, then Internal!IU50).
                $ve = $null
                if ($ws.Visible -eq -1) {
                    try { $ve = $xl.Intersect($e, $ws.UsedRange.SpecialCells(12)) } catch { $ve = $null }
                }
                if ($ve -ne $null) {
                    foreach ($c in $ve.Cells) {
                        $n++; if ($where.Count -lt 5) { $where += "$($ws.Name)!$($c.Address(0,0))" }
                    }
                }
                foreach ($c in $e.Cells) {
                    if ($ve -ne $null -and $xl.Intersect($c, $ve) -ne $null) { continue }
                    $k = "$($ws.Name) $($c.Text)"; if (-not $c.Text) { $k = "$($ws.Name) " + $ERRORS[[int]$c.Value2] }
                    $hidden[$k] = 1 + [int]$hidden[$k]
                }
            }
        }
        $h = ($hidden.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name): $($_.Value)" }) -join "; "
        return @{ count = $n; where = (@($where) + @("hidden: " + $h)) }
    }
    function Picture($p) {
        $file = Join-Path $pics $p.file
        if (Test-Path $file) { Remove-Item $file }
        $ws = $wb.Worksheets.Item($p.sheet)
        $ws.Activate()
        $rng = $ws.Range($p.range)
        $null = $rng.CopyPicture(1, 2)
        $co = $ws.ChartObjects().Add(0, 0, $rng.Width + 4, $rng.Height + 4)
        $co.Activate()
        Start-Sleep -Milliseconds 400
        $co.Chart.Paste()
        $null = $co.Chart.Export($file)
        $co.Delete()
        return $p.file
    }

    foreach ($s in $plan.steps) {
        foreach ($a in $s.actions) {
            if ($a.type -eq "slicer") {
                $c = Cache $a.caption
                $c.SlicerItems.Item($a.value).Selected = $true
                foreach ($it in $c.SlicerItems) { if ($it.Name -ne $a.value) { $it.Selected = $false } }
            } elseif ($a.type -eq "cell") {
                $cell = $wb.Worksheets.Item($a.sheet).Range($a.cell)
                $v = $a.value
                $cell.Formula = [string]::Format([cultureinfo]::InvariantCulture, "{0}", $v)
            } elseif ($a.type -eq "reopen") {
                $wb.Save()
                $wb.Close($false)
                $wb = $xl.Workbooks.Open($path)
            }
        }
        $xl.Calculate()
        $reads = @()
        foreach ($r in $s.reads) {
            $got = $null; $text = $null
            switch ($r.special) {
                "active" { $got = $wb.ActiveSheet.Name }
                "sheets" { $got = @($wb.Worksheets | ForEach-Object { $_.Name }) }
                "slicers" { $got = Picked }
                "visible_rows" { $got = Visible $r.sheet }
                "links" { $l = $wb.LinkSources(1); $got = if ($l) { @($l) } else { @() } }
                "errors" { $e = Errors; $got = $e.count; $text = ($e.where -join ", ") }
                default {
                    $cell = $wb.Worksheets.Item($r.sheet).Range($r.cell)
                    $got = $cell.Value2; $text = $cell.Text
                    if ($got -is [int] -and $ERRORS.ContainsKey($got)) { $text = $ERRORS[$got] }
                }
            }
            $reads += @{ special = $r.special; sheet = $r.sheet; cell = $r.cell; value = $got; text = $text }
        }
        $taken = @()
        foreach ($p in $s.picture) { $taken += Picture $p }
        $observed.steps += @{ id = $s.id; reads = $reads; pictures = $taken }
        Write-Output ("{0}: {1} reads" -f $s.id, $reads.Count)
    }
    $wb.Save()
    $wb.Close($false)
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
$observed | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 (Join-Path $out "observed.json")
Write-Output "Excel $($observed.excel): $($observed.steps.Count) steps"
