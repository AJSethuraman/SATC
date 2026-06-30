Attribute VB_Name = "FREDDashboard"
'================================================================================
' FRED Credit-Risk Dashboard -- extractor macro (BUILD SPEC section 5, simplified)
'
' The workbook is already the finished product: every dashboard, formula, KPI
' tile, chart and heat rule is built in. The data is the only thing missing.
'
' "Extract" (run ExtractFiles, or the ExtractAndRun alias, via Alt+F8):
'   1. Writes runner.py from the _code_py tab into the workbook's folder.
'   2. Writes run_fred.bat -- a launcher that runs runner.py against this file.
'
' NOTHING runs inside Excel (no shell-out, no xlwings, no save-from-VBA). After
' extracting: SAVE and CLOSE the workbook, then double-click run_fred.bat. It
' pulls FRED per _config and writes the data into the closed workbook via
' openpyxl. Reopen and the formulas recalc into the finished dashboards.
'
' This is a readable/portable reference copy; the identical text lives in the
' _code_vba tab so the workbook stays the single source of truth.
'================================================================================
Option Explicit

Private Const STATUS_SHEET As String = "Dashboard_Consumer"

' Kept as an alias so the old name / any assigned button still works.
Public Sub ExtractAndRun()
    ExtractFiles
End Sub

Public Sub ExtractFiles()
    Dim folder As String, runnerPath As String, batPath As String
    On Error GoTo Fail

    folder = ThisWorkbook.Path
    If Len(folder) = 0 Then
        MsgBox "Save the workbook to a folder first, then run Extract.", vbExclamation
        Exit Sub
    End If

    runnerPath = folder & Application.PathSeparator & "runner.py"
    WriteTabToFile "_code_py", runnerPath

    batPath = folder & Application.PathSeparator & "run_fred.bat"
    WriteRunBat batPath

    SetStatus "Extracted", "runner.py + run_fred.bat written -- save & close, then run run_fred.bat."
    MsgBox "Extracted into this workbook's folder:" & vbCrLf & _
           "    runner.py" & vbCrLf & _
           "    run_fred.bat" & vbCrLf & vbCrLf & _
           "Next steps:" & vbCrLf & _
           "  1. Save and CLOSE this workbook." & vbCrLf & _
           "  2. Double-click run_fred.bat (in the same folder)." & vbCrLf & _
           "  3. Reopen the workbook -- the dashboards will be populated." & vbCrLf & vbCrLf & _
           "Demo data needs no key: set _config demo_mode = TRUE first. For live " & _
           "FRED data, set the FRED_API_KEY environment variable or the _config cell.", _
           vbInformation, "Extract complete"
    Exit Sub

Fail:
    MsgBox "Extract failed: " & Err.Description, vbCritical
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

' Write a Windows launcher that runs runner.py against this workbook (closed).
' Quotes are built with Chr(34) so this source stays paste-safe.
Private Sub WriteRunBat(filePath As String)
    Dim q As String, nl As String, wb As String, body As String
    q = Chr(34)
    nl = vbCrLf
    wb = ThisWorkbook.Name
    body = "@echo off" & nl
    body = body & "cd /d " & q & "%~dp0" & q & nl
    body = body & "set " & q & "PY=python" & q & nl
    body = body & "where python >nul 2>nul || set " & q & "PY=py" & q & nl
    body = body & "echo Pulling FRED data into " & wb & " ..." & nl
    body = body & "%PY% runner.py --workbook " & q & "%~dp0" & wb & q & " --backend openpyxl" & nl
    body = body & "echo." & nl
    body = body & "echo Done. Reopen " & wb & " to see the dashboards." & nl
    body = body & "pause" & nl

    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile(filePath, True, False)   ' ANSI is fine for a .bat
    ts.Write body
    ts.Close
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
' PaintSparklines) to draw the Trend (8q) sparklines. Native sparklines can't be
' written by openpyxl, so the data path leaves that one column empty; everything
' else renders from formulas with no macro. Guarded so it can never error out.
Public Sub PaintSparklines()
    On Error Resume Next
    PaintLaneSparklines "Dashboard_Consumer", "Raw_Consumer"
    PaintLaneSparklines "Dashboard_Commercial", "Raw_Commercial"
    PaintLaneSparklines "Dashboard_Price", "Raw_Price"
    MsgBox "Trend sparklines painted. Save the workbook to keep them.", vbInformation
End Sub

Private Sub PaintLaneSparklines(dashName As String, rawName As String)
    On Error Resume Next
    Const HDR As Long = 7          ' header band row; data begins at row 8
    Const SID_COL As Long = 3      ' Series ID column (C)
    Const SPK_COL As Long = 9      ' Trend (8q) column (I)
    Dim dash As Worksheet, raw As Worksheet
    Set dash = ThisWorkbook.Worksheets(dashName)
    Set raw = ThisWorkbook.Worksheets(rawName)
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
                src = "'" & rawName & "'!B" & r0 & ":B" & (r0 + 7)
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
