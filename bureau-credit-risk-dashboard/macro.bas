Attribute VB_Name = "CreditRiskMonitor"
'================================================================================
' Consumer Credit-Risk Monitor (bureau feed) -- extractor macro
' (BUILD_SPEC_BUREAU.md Section 5: EXTRACT-ONLY).
'
' The workbook is already the finished product: every dashboard, formula, KPI
' tile and heat rule is built in. The data is the only thing missing.
'
' "Extract" (run ExtractFiles, or the ExtractAndRun alias, via Alt+F8):
'   1. Writes runner.py from the _code_py tab into the workbook's folder.
'   2. Writes requirements.txt (the Python dependencies).
'   3. Writes RUN.txt (the exact PowerShell commands).
'
' NOTHING runs inside Excel (no shell-out, no xlwings, no save-from-VBA). After
' extracting: SAVE and CLOSE the workbook, then follow RUN.txt from PowerShell.
' runner.py writes the data into the CLOSED workbook via openpyxl. Reopen and the
' formulas recalc into the finished dashboards.
'
' This is a readable/portable reference copy; the identical text lives in the
' _code_vba tab so the workbook stays the single source of truth.
'================================================================================
Option Explicit

Private Const STATUS_SHEET As String = "Dashboard_Balances"

' Kept as an alias so the old name / any assigned button still works.
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
           "Just trying it out? Use the --demo command in RUN.txt (offline, no key).", _
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
        "Consumer Credit-Risk Monitor -- run from PowerShell (workbook must be CLOSED)" & nl & nl & _
        "1) Install dependencies (once):" & nl & _
        "   python -m pip install -r requirements.txt" & nl & nl & _
        "2) Try-the-button demo data (offline, no key):" & nl & _
        "   python .\runner.py --workbook " & q & ".\" & wb & q & " --demo" & nl & nl & _
        "3) Live data (downloads the NY Fed HHDC public tables):" & nl & _
        "   python .\runner.py --workbook " & q & ".\" & wb & q & nl & nl & _
        "A licensed (Class C) feed is a v2 swap; it reads its secret from the env " & _
        "var NAMED in _config (secret_env) -- never hardcoded. Absent var = fail fast." & nl & nl & _
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
    ' Column L (12), row 4 -- the masthead status panel (free of the merged
    ' banner/KPI cells the runner fills on rows 1-2).
    ws.Cells(4, 12).Value = state & " -- " & msg
End Sub

' OPTIONAL: after reopening the populated workbook, run this (Alt+F8 ->
' PaintSparklines) to draw the Trend (8) sparklines. Native sparklines can't be
' written by openpyxl, so the data path leaves that one column empty; everything
' else renders from formulas with no macro. Guarded so it can never error out.
' All three dashboards read from the single Raw_HHDC tab.
Public Sub PaintSparklines()
    On Error Resume Next
    PaintLaneSparklines "Dashboard_Balances"
    PaintLaneSparklines "Dashboard_Delinquency"
    PaintLaneSparklines "Dashboard_Originations"
    MsgBox "Trend sparklines painted. Save the workbook to keep them.", vbInformation
End Sub

Private Sub PaintLaneSparklines(dashName As String)
    On Error Resume Next
    Const HDR As Long = 7          ' header band row; data begins at row 8
    Const SID_COL As Long = 2      ' Series ID column (B)
    Const SPK_COL As Long = 7      ' Trend (8) column (G)
    Const RAW_NAME As String = "Raw_HHDC"
    Dim dash As Worksheet, raw As Worksheet
    Set dash = ThisWorkbook.Worksheets(dashName)
    Set raw = ThisWorkbook.Worksheets(RAW_NAME)
    If dash Is Nothing Or raw Is Nothing Then Exit Sub
    Dim lastRow As Long, r As Long, sid As String, m As Variant, r0 As Long
    Dim src As String, addr As String
    lastRow = dash.Cells(dash.Rows.Count, SID_COL).End(xlUp).Row
    For r = HDR + 1 To lastRow
        sid = CStr(dash.Cells(r, SID_COL).Value)
        If Len(sid) > 0 Then
            m = Application.Match(sid, raw.Columns(1), 0)
            If Not IsError(m) Then
                r0 = CLng(m) + 2                          ' first_data_row = header + 2
                src = "'" & RAW_NAME & "'!B" & r0 & ":B" & (r0 + 7)
                addr = dash.Cells(r, SPK_COL).Address(False, False)
                dash.Range(addr).SparklineGroups.Clear
                dash.Range(addr).SparklineGroups.Add Type:=xlSparkLine, SourceData:=src
                With dash.Range(addr).SparklineGroups.Item(1)
                    .SeriesColor.Color = RGB(87, 83, 75)         ' SLATE line
                    .Points.Markers.Visible = False
                    .Points.Firstpoint.Visible = True            ' newest is leftmost
                    .Points.Firstpoint.Color.Color = RGB(204, 0, 0)   ' KEY_RED
                End With
            End If
        End If
    Next r
End Sub
