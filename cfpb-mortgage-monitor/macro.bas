Attribute VB_Name = "MortgageMonitor"
'================================================================================
' County Mortgage Delinquency Monitor (CFPB Mortgage Performance Trends)
' extractor macro (BUILD_SPEC_CFPB.md Section 5: EXTRACT-ONLY).
'
' The workbook is already the finished product: every dashboard, formula and
' heat rule is built in, and the county list lives in _config [FOOTPRINT]. The
' data is the only thing missing.
'
' "Extract" (run ExtractFiles, or the ExtractAndRun alias, via Alt+F8):
'   1. Writes runner.py from the _code_py tab into the workbook's folder.
'   2. Writes requirements.txt (the Python dependencies).
'   3. Writes RUN.txt (the exact PowerShell commands, incl. --lookup).
'
' NOTHING runs inside Excel (no shell-out, no xlwings, no save-from-VBA). After
' extracting: SAVE and CLOSE the workbook, then follow RUN.txt from PowerShell.
' runner.py writes the data into the CLOSED workbook via openpyxl. Reopen and
' the formulas recalc into the finished dashboards.
'
' This is a readable/portable reference copy; the identical text lives in the
' _code_vba tab so the workbook stays the single source of truth.
'================================================================================
Option Explicit

Private Const STATUS_SHEET As String = "Dashboard_State"

' Kept as an alias so any assigned button still works.
Public Sub ExtractAndRun()
    ExtractFiles
End Sub

Public Sub ExtractFiles()
    Dim folder As String, sep As String
    On Error GoTo Fail

    folder = ThisWorkbook.Path
    If Len(folder) = 0 Then
        MsgBox "Save the workbook to a folder first, then run ExtractFiles.", vbExclamation
        Exit Sub
    End If
    sep = Application.PathSeparator

    WriteTabToFile "_code_py", folder & sep & "runner.py"          ' the data-path script
    WriteTextFile folder & sep & "requirements.txt", RequirementsText()
    WriteTextFile folder & sep & "RUN.txt", RunText()             ' the PowerShell commands

    SetStatus "Extracted", "runner.py + requirements.txt + RUN.txt written -- see RUN.txt."
    MsgBox "Extracted next to this workbook:" & vbCrLf & _
           "    runner.py" & vbCrLf & _
           "    requirements.txt" & vbCrLf & _
           "    RUN.txt   (the PowerShell commands)" & vbCrLf & vbCrLf & _
           "Open RUN.txt and follow it: install the deps, then run runner.py from " & _
           "PowerShell with this workbook CLOSED. Reopen to see the dashboards." & vbCrLf & vbCrLf & _
           "Just trying it out? Use the --demo command in RUN.txt (offline). " & _
           "Live pulls need NO API key -- the CFPB files are public domain.", _
           vbInformation, "Extract complete"
    Exit Sub

Fail:
    MsgBox "Extract failed: " & Err.Description, vbCritical
End Sub

Private Function RequirementsText() As String
    Dim nl As String
    nl = vbCrLf
    RequirementsText = "pandas>=1.5" & nl & "openpyxl>=3.0" & nl
End Function

Private Function RunText() As String
    Dim nl As String, q As String, wb As String
    nl = vbCrLf
    q = Chr(34)
    wb = ThisWorkbook.Name
    RunText = _
        "County Mortgage Delinquency Monitor -- run from PowerShell (workbook must be CLOSED)" & nl & nl & _
        "1) Install dependencies (once):" & nl & _
        "   python -m pip install -r requirements.txt" & nl & nl & _
        "2) Try-the-button demo data (offline, deterministic):" & nl & _
        "   python .\runner.py --workbook " & q & ".\" & wb & q & " --demo" & nl & nl & _
        "3) Live data (CFPB Mortgage Performance Trends -- KEYLESS, public domain):" & nl & _
        "   python .\runner.py --workbook " & q & ".\" & wb & q & nl & _
        "   The runner discovers the newest DATED files from the CFPB download page" & nl & _
        "   automatically. If that page ever changes, set the `vintage` key in the" & nl & _
        "   _config [SETTINGS] tab (e.g. thru-2025-09) to fetch that vintage directly." & nl & nl & _
        "4) Find a county's 5-digit FIPS to add to the _config [FOOTPRINT] table:" & nl & _
        "   python .\runner.py --lookup " & q & "Cook" & q & "            (live: greps the CFPB county file)" & nl & _
        "   python .\runner.py --lookup " & q & "Cook" & q & " --demo     (offline mini-index)" & nl & nl & _
        "The footprint lives in the _config [FOOTPRINT] table: slot | fips | name | state | active." & nl & _
        "Add a county = fill a free slot row + re-run (no rebuild). Remove = active FALSE." & nl & _
        "Keep fips cells TEXT-formatted so leading zeros survive. More counties than built" & nl & _
        "slots and the runner tells you the exact rebuild command." & nl & nl & _
        "A footprint county missing from the CFPB file shows SUPPRESSED (below the ~1,000-" & nl & _
        "sample threshold) -- monitor its state row instead. The data lags ~6-7 months by design." & nl & nl & _
        "If 'python' is not found, use 'py' instead. Reopen the workbook afterward." & nl
End Function

Private Sub WriteTextFile(filePath As String, content As String)
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile(filePath, True, False)
    ts.Write content
    ts.Close
End Sub

' Write one tab's column A (one source line per cell) to a UTF-8 text file.
' ADODB.Stream writes real UTF-8 (FSO would write ANSI, and Python, which reads
' source as UTF-8, would raise SyntaxError on any non-ASCII byte).
Private Sub WriteTabToFile(tabName As String, filePath As String)
    Dim ws As Worksheet, lastRow As Long, r As Long, body As String
    Set ws = ThisWorkbook.Worksheets(tabName)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    For r = 1 To lastRow
        body = body & CStr(ws.Cells(r, 1).Value) & vbLf
    Next r
    Dim stm As Object
    Set stm = CreateObject("ADODB.Stream")
    stm.Type = 2                 ' adTypeText
    stm.Charset = "utf-8"
    stm.Open
    stm.WriteText body
    stm.SaveToFile filePath, 2   ' adSaveCreateOverWrite
    stm.Close
End Sub

Private Sub SetStatus(state As String, msg As String)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(STATUS_SHEET)
    If ws Is Nothing Then Exit Sub
    ' Column L (12), row 5 -- the masthead status panel (free of the merged
    ' banner/KPI cells; the runner fills rows 1-4).
    ws.Cells(5, 12).Value = state & " -- " & msg
End Sub
