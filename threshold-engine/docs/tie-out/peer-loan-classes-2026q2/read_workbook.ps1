# The "ours" side of the tie-out: every class row on the workbook's Peer loan
# classes tab, read out of Excel as a reader opens it (after a full
# recalculation), and the summary row each bank's sums land in.
#   powershell -File read_workbook.ps1 -Path consumer-credit.xlsx -Out ours.json
param([string]$Path, [string]$Out)
$xl = New-Object -ComObject Excel.Application
try {
    $xl.Visible = $false; $xl.DisplayAlerts = $false
    $wb = $xl.Workbooks.Open((Resolve-Path $Path).Path, 0, $true)
    $xl.CalculateFull()
    $ws = $wb.Worksheets.Item("Peer loan classes")
    $used = $ws.UsedRange.Rows.Count
    $head = $null; $sum = $null
    for ($r = 1; $r -le $used; $r++) {
        $b = [string]$ws.Cells.Item($r, 2).Text
        if ($b -eq "Class, as the filing labels it") { $head = $r }
        if ($b -eq "Student loans" -and $null -eq $sum) { $sum = $r }
    }
    $classes = @()
    for ($r = $head + 1; $r -le $used; $r++) {
        $bank = [string]$ws.Cells.Item($r, 1).Text
        if (-not $bank) { break }
        $classes += [ordered]@{ row = $r; bank = $bank; name = [string]$ws.Cells.Item($r, 2).Text
            value = $ws.Cells.Item($r, 3).Value2; shown = [string]$ws.Cells.Item($r, 3).Text
            kind = [string]$ws.Cells.Item($r, 4).Text; how = [string]$ws.Cells.Item($r, 6).Text
            where = [string]$ws.Cells.Item($r, 7).Text; link = [string]$ws.Cells.Item($r, 5).Hyperlinks.Item(1).Address }
    }
    $summary = @()
    for ($r = $sum + 1; $r -le $head; $r++) {
        $bank = [string]$ws.Cells.Item($r, 1).Text
        if (-not $bank) { break }
        $summary += [ordered]@{ row = $r; bank = $bank; student = [string]$ws.Cells.Item($r, 2).Text
            unsecured = [string]$ws.Cells.Item($r, 3).Text; secured = [string]$ws.Cells.Item($r, 4).Text
            mixed = [string]$ws.Cells.Item($r, 5).Text; comparison = [string]$ws.Cells.Item($r, 6).Text }
    }
    $errors = 0
    foreach ($c in $ws.UsedRange.Cells) { if ([string]$c.Text -like "#*") { $errors++ } }
    [ordered]@{ file = (Resolve-Path $Path).Path; excel = $xl.Version; classes = $classes; summary = $summary
        errors = $errors } | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 $Out
    "read $($classes.Count) classes and $($summary.Count) banks; error cells: $errors"
    $wb.Close($false)
} finally { $xl.Quit() }
