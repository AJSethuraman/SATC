<#
Open a workbook with hand-written table slicers in Excel 16, prove it opens
without a repair, click a different button, and prove the table follows.

    powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_slicers_in_excel.ps1 `
        -Path OUT.xlsx -Sheet Pick -Table Picks -Shapes 3 `
        -Expect 'Slicer_Product=Credit card|Slicer_Measure=Net charge-offs|Slicer_Source=Industry' `
        -SwitchCache Slicer_Source -SwitchTo 'Peers <10>'

-Expect is one string, cache=selected pairs joined by | (powershell -File
passes no arrays). -Shapes is how many shapes the sheet should hold (slicers
plus any charts), so a chart dropped on open is a failure too.

Works on a copy (<name>.excel-check.xlsx beside the original); the original
is not touched. Prints one line per fact and ends with RESULT: PASS or FAIL.

How "no repair" is proved -- two ways, because Excel repairs in two ways:
  1. The prompt. The copy is opened as a user opens it: a new, visible
     Excel (excel.exe /x <file>), its own process. Every visible window that
     process shows is listed until the workbook's window is up and 5 s more.
     Anything but the splash (MsoSplash) and the main window (XLMAIN) is a
     dialog, and fails the check. Seen on a control with a malformed slicers
     part: a NUIDialog at 0.5 s (the "We found a problem with some content"
     prompt). Under COM automation the same file gives no prompt at all,
     only "Unable to get the Open property", which is why this step is not
     done over COM.
  2. The silent repair. A part that is well-formed but wrong -- a slicer
     cache naming a table column that is not there -- is dropped without
     any prompt, interactively or over COM, with no repair log and no
     "[Repaired]" in the caption (seen on a control). So everything written
     is counted after opening over COM: slicer caches, slicers, captions,
     shapes, the selection, and the rows the table shows.
Run it on a deliberately broken file with -ExpectRepair to see it fire.

Every Excel it starts is its own process, known by id, and closed or (if it
will not close) stopped by that id. Any Excel the user has open is left alone.
#>
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Sheet,
    [Parameter(Mandatory = $true)][string]$Table,
    [Parameter(Mandatory = $true)][string]$Expect,
    [Parameter(Mandatory = $true)][string]$SwitchCache,
    [Parameter(Mandatory = $true)][string]$SwitchTo,
    [int]$Shapes = -1,
    [switch]$ExpectRepair
)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class XlWindows {
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, EnumProc f, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    static string Text(IntPtr h) { var s = new StringBuilder(1024); GetWindowText(h, s, 1024); return s.ToString(); }
    static string Cls(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
    // Visible top-level windows of process pid: handle, class, title, child texts.
    public static string[][] List(uint pid) {
        var o = new List<string[]>();
        EnumWindows((h, l) => {
            uint p;
            GetWindowThreadProcessId(h, out p);
            if (p == pid && IsWindowVisible(h)) {
                var parts = new List<string>();
                EnumChildWindows(h, (c, l2) => { var t = Text(c); if (t.Length > 0) parts.Add(t); return true; }, IntPtr.Zero);
                o.Add(new string[] { h.ToInt64().ToString(), Cls(h), Text(h), string.Join(" / ", parts.ToArray()) });
            }
            return true;
        }, IntPtr.Zero);
        return o.ToArray();
    }
}
'@

$src = (Resolve-Path $Path).Path
$work = [IO.Path]::Combine([IO.Path]::GetDirectoryName($src),
        [IO.Path]::GetFileNameWithoutExtension($src) + '.excel-check.xlsx')
Copy-Item $src $work -Force
$failures = New-Object System.Collections.Generic.List[string]
function Fail($m) { $script:failures.Add($m); "  FAIL: $m" }

$want = [ordered]@{}
foreach ($e in ($Expect -split '\|')) { $k, $v = $e -split '=', 2; $want[$k] = $v }

function Stop-Ours($procId, $label) {
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p -and -not $p.WaitForExit(15000)) { Stop-Process -Id $procId -Force; [void]$p.WaitForExit(10000); "[$label] stopped our Excel (pid $procId), which did not exit" }
    else { "[$label] our Excel (pid $procId) has exited" }
}

function Open-AsAUser($file, $label) {
    # Step 1: the prompt a user would see. A new interactive Excel, watched.
    $exe = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe').'(default)'
    $base = [IO.Path]::GetFileNameWithoutExtension($file)
    $p = Start-Process -FilePath $exe -ArgumentList '/x', "`"$file`"" -PassThru
    $dialogs = @{}; $main = $null; $upAt = $null; $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        while ($sw.Elapsed.TotalSeconds -lt 60) {
            Start-Sleep -Milliseconds 250
            foreach ($w in [XlWindows]::List([uint32]$p.Id)) {
                $h, $cls, $title, $kids = $w
                if ($cls -eq 'XLMAIN') { $main = $h; if (-not $upAt -and $title -like "*$base*") { $upAt = $sw.Elapsed.TotalSeconds } }
                elseif ($cls -ne 'MsoSplash' -and -not $dialogs.ContainsKey($h)) {
                    $dialogs[$h] = "at $([math]::Round($sw.Elapsed.TotalSeconds, 1)) s: [$cls] '$title' $kids"
                }
            }
            if ($upAt -and $sw.Elapsed.TotalSeconds -ge $upAt + 5) { break }
        }
        if ($upAt) { "[$label] opened as a user would (excel.exe /x, pid $($p.Id)): workbook window up at $([math]::Round($upAt, 1)) s, watched 5 s more" }
        else { Fail "[$label] the workbook's window never came up in 60 s (pid $($p.Id))" }
        "[$label] dialogs shown: $($dialogs.Count)"
        foreach ($d in $dialogs.Values) { Fail "[$label] Excel showed a dialog $d" }
    }
    finally {
        if ($main -and -not $p.HasExited) { [void][XlWindows]::PostMessage([IntPtr][long]$main, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }
        Stop-Ours $p.Id $label
    }
}

function Visible-Rows($ws, $lo, $cols) {
    # Each data row Excel shows, as "col=value | ..." over the slicer columns.
    $out = @()
    $n = $lo.ListRows.Count
    for ($i = 1; $i -le $n; $i++) {
        $r = $lo.ListRows.Item($i).Range
        if (-not $r.EntireRow.Hidden) {
            $vals = foreach ($c in $cols) { "$c=" + $lo.ListColumns.Item($c).DataBodyRange.Cells.Item($i, 1).Text }
            $out += ("row " + $r.Row + ": " + ($vals -join ' | '))
        }
    }
    return , $out
}

function Expected-Count($lo, $sel) {
    # Read from the cells, not from the slicers: rows holding every selected value.
    $n = $lo.ListRows.Count; $k = 0
    for ($i = 1; $i -le $n; $i++) {
        $ok = $true
        foreach ($c in $sel.Keys) {
            if ($lo.ListColumns.Item($c).DataBodyRange.Cells.Item($i, 1).Text -ne $sel[$c]) { $ok = $false }
        }
        if ($ok) { $k++ }
    }
    return $k
}

function Report($wb, $label, $wantSel) {
    # Step 2: nothing dropped, and the table shows what the slicers say.
    $ws = $wb.Worksheets.Item($Sheet)
    $lo = $ws.ListObjects.Item($Table)
    "[$label] window caption: '$($wb.Windows.Item(1).Caption)'"
    if ($wb.Windows.Item(1).Caption -match 'Repaired') { Fail "[$label] caption says Repaired" }
    "[$label] SlicerCaches.Count = $($wb.SlicerCaches.Count) (expected $($wantSel.Count))"
    if ($wb.SlicerCaches.Count -ne $wantSel.Count) { Fail "[$label] slicer cache count" }
    $names = @(foreach ($s in $ws.Shapes) { $s.Name })
    "[$label] shapes on '$Sheet': $($names.Count) ($($names -join ', '))"
    if ($Shapes -ge 0 -and $names.Count -ne $Shapes) { Fail "[$label] $($names.Count) shapes, expected $Shapes" }
    $bycol = [ordered]@{}
    foreach ($name in $wantSel.Keys) {
        try { $c = $wb.SlicerCaches.Item($name) } catch { Fail "[$label] no slicer cache $name"; continue }
        $sl = $c.Slicers.Item(1)
        $items = @($c.SlicerItems | ForEach-Object { $_.Name })
        $selected = @($c.SlicerItems | Where-Object { $_.Selected } | ForEach-Object { $_.Name })
        "[$label] $name : source '$($c.SourceName)', table '$($c.ListObject.Name)', slicer '$($sl.Name)' caption '$($sl.Caption)', $($c.Slicers.Count) slicer(s), columns $($sl.NumberOfColumns), placement $($sl.Shape.Placement)"
        "[$label]   buttons: " + ($items -join ' ; ')
        "[$label]   selected: " + ($selected -join ' ; ')
        if ($selected.Count -ne 1 -or $selected[0] -ne $wantSel[$name]) { Fail "[$label] $name selected '$($selected -join ';')', expected '$($wantSel[$name])'" }
        $bycol[$c.SourceName] = $wantSel[$name]
    }
    $vis = Visible-Rows $ws $lo @($bycol.Keys)
    $exp = Expected-Count $lo $bycol
    "[$label] table rows shown: $($vis.Count) of $($lo.ListRows.Count); rows holding every selected value: $exp"
    foreach ($v in $vis) { "[$label]   $v" }
    if ($vis.Count -ne $exp) { Fail "[$label] shown rows $($vis.Count) != matching rows $exp" }
    foreach ($v in $vis) { foreach ($c in $bycol.Keys) { if ($v -notmatch [regex]::Escape("$c=" + $bycol[$c]) + '( \||$)') { Fail "[$label] shown row does not match: $v" } } }
}

try { Open-AsAUser $work 'as a user' } catch { Fail ("[as a user] exception: " + $_.Exception.Message) }

$xl = $null; $xlPid = 0; $wb = $null
try {
    $xl = New-Object -ComObject Excel.Application
    $p = [uint32]0; [void][XlWindows]::GetWindowThreadProcessId([IntPtr]$xl.Hwnd, [ref]$p); $xlPid = $p
    $xl.Visible = $false
    $xl.DisplayAlerts = $false
    "[com] Excel $($xl.Version) (build $($xl.Build)), pid $xlPid; checking a copy: $work"

    $wb = $xl.Workbooks.Open($work, 0, $false)
    Report $wb 'open' $want

    # click a different button: select it, then clear the others (as a click does)
    $c = $wb.SlicerCaches.Item($SwitchCache)
    $c.SlicerItems.Item($SwitchTo).Selected = $true
    foreach ($it in $c.SlicerItems) { if ($it.Name -ne $SwitchTo) { $it.Selected = $false } }
    $after = [ordered]@{}; foreach ($k in $want.Keys) { $after[$k] = $want[$k] }; $after[$SwitchCache] = $SwitchTo
    "[switch] $SwitchCache -> '$SwitchTo'"
    $c = $null; $it = $null
    Report $wb 'switch' $after

    $wb.Save(); $wb.Close($false); $wb = $null
    "[save] saved by Excel and closed"
    $wb = $xl.Workbooks.Open($work, 0, $false)
    Report $wb 'reopen' $after
    $wb.Close($false); $wb = $null
}
catch { Fail ("[com] exception: " + $_.Exception.Message) }
finally {
    if ($wb) { try { $wb.Close($false) } catch {} }
    $wb = $null; $c = $null; $it = $null
    if ($xl) {
        try { $xl.Quit() } catch {}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
        $xl = $null
    }
    # every COM object PowerShell still holds keeps Excel alive; let them go
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    if ($xlPid) { Stop-Ours $xlPid 'com' }
}

# the file Excel itself saved, opened once more as a user would
try { Open-AsAUser $work 'saved, as a user' } catch { Fail ("[saved, as a user] exception: " + $_.Exception.Message) }

if ($ExpectRepair) {
    if ($failures.Count) { "RESULT: PASS (a repair or loss was detected, as expected: $($failures.Count) finding(s))"; exit 0 }
    "RESULT: FAIL (expected a repair to be detected; none was)"; exit 1
}
if ($failures.Count) { "RESULT: FAIL ($($failures.Count))"; $failures | ForEach-Object { "  - $_" }; exit 1 }
"RESULT: PASS"
