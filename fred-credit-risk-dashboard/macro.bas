Attribute VB_Name = "FREDDashboard"
'================================================================================
' FRED Credit-Risk Dashboard -- bootstrap macro (BUILD SPEC section 5)
'
' "Extract & Run" button:
'   1. Reads the _code_py tab (one source line per cell, column A) and writes it
'      to runner.py in the workbook's own folder.
'   2. Shells out to Python to execute runner.py against THIS workbook.
'   3. The runner pulls FRED per _config and writes the Raw_* tabs (xlwings into
'      the open book; openpyxl on the file as a fallback). Formulas recalc the
'      dashboards automatically.
'   4. Reports success/failure (timestamp, series pulled, stale warnings) in the
'      status cells, and surfaces Python's stderr -- no silent failures.
'
' This is a readable/portable reference copy; the identical text lives in the
' _code_vba tab so the workbook stays the single source of truth.
'================================================================================
Option Explicit

Private Const STATUS_SHEET As String = "Dashboard_Consumer"

Public Sub ExtractAndRun()
    Dim folder As String, pyPath As String, runnerPath As String
    Dim pyExe As String, cmd As String
    Dim out As String, err As String, code As Long

    On Error GoTo Fail
    Application.StatusBar = "Extracting runner.py ..."
    SetStatus "Running", "Extracting runner.py from _code_py ..."

    folder = ThisWorkbook.Path
    If Len(folder) = 0 Then
        MsgBox "Save the workbook to a folder first, then click Extract & Run.", vbExclamation
        SetStatus "Error", "Workbook is unsaved -- save it to a folder first."
        Exit Sub
    End If

    ' Make sure the on-disk copy reflects the latest _config edits.
    ThisWorkbook.Save

    runnerPath = folder & Application.PathSeparator & "runner.py"
    WriteTabToFile "_code_py", runnerPath

    ' Locate a Python interpreter on PATH.
    pyExe = FindPython()
    If Len(pyExe) = 0 Then
        SetStatus "Error", "Python not found on PATH. Install Python 3 and the deps " & _
            "(pip install fredapi xlwings openpyxl pandas), then reopen and retry."
        MsgBox "Python was not found on PATH." & vbCrLf & _
               "Install Python 3, then run:  pip install fredapi xlwings openpyxl pandas", vbExclamation
        Exit Sub
    End If

    SetStatus "Running", "Pulling FRED and rebuilding (this can take a minute) ..."
    Application.StatusBar = "Running FRED pull ..."

    ' Quote paths to survive spaces. The runner reads _config from the workbook.
    cmd = """" & pyExe & """ """ & runnerPath & """ --workbook """ & _
          ThisWorkbook.FullName & """ --backend auto"

    code = RunAndCapture(cmd, out, err)

    If code <> 0 Then
        SetStatus "Error", "Python exited " & code & ". " & FirstLine(err)
        MsgBox "The FRED runner reported an error (exit " & code & "):" & vbCrLf & vbCrLf & _
               IIf(Len(err) > 0, err, out), vbExclamation, "Extract & Run failed"
        Application.StatusBar = False
        Exit Sub
    End If

    ' On the openpyxl fallback path the file changed on disk while open; the
    ' xlwings path already wrote into this instance. Either way, recalc.
    Application.CalculateFull
    PaintSparklines                      ' paint the Trend (8q) column now data has landed
    SetStatus "OK", "Last run " & Format(Now, "yyyy-mm-dd hh:nn") & ". " & FirstLine(out)
    Application.StatusBar = False
    Exit Sub

Fail:
    SetStatus "Error", "Macro error: " & Err.Description
    Application.StatusBar = False
    MsgBox "Extract & Run failed: " & Err.Description, vbCritical
End Sub

' Write one tab's column A (one source line per cell) to a UTF-8-ish text file.
Private Sub WriteTabToFile(tabName As String, filePath As String)
    Dim ws As Worksheet, fso As Object, ts As Object
    Dim lastRow As Long, r As Long, line As String, body As String
    Set ws = ThisWorkbook.Worksheets(tabName)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile(filePath, True, False)
    For r = 1 To lastRow
        line = CStr(ws.Cells(r, 1).Value)
        body = body & line & vbLf
    Next r
    ts.Write body
    ts.Close
End Sub

' Try common Python launchers; return the first that responds, else "".
Private Function FindPython() As String
    Dim candidates As Variant, i As Long, o As String, e As String
    candidates = Array("python", "python3", "py -3")
    For i = LBound(candidates) To UBound(candidates)
        If RunAndCapture(candidates(i) & " --version", o, e) = 0 Then
            FindPython = candidates(i)
            Exit Function
        End If
    Next i
    FindPython = ""
End Function

' Run a command, capture stdout+stderr, return the exit code.
Private Function RunAndCapture(cmd As String, ByRef outText As String, ByRef errText As String) As Long
    Dim sh As Object, exec As Object
    Set sh = CreateObject("WScript.Shell")
    On Error GoTo ExecErr
    Set exec = sh.exec("cmd /c " & cmd)
    Do While exec.Status = 0
        DoEvents
        If Not exec.StdOut.AtEndOfStream Then outText = outText & exec.StdOut.ReadAll
        If Not exec.StdErr.AtEndOfStream Then errText = errText & exec.StdErr.ReadAll
    Loop
    If Not exec.StdOut.AtEndOfStream Then outText = outText & exec.StdOut.ReadAll
    If Not exec.StdErr.AtEndOfStream Then errText = errText & exec.StdErr.ReadAll
    RunAndCapture = exec.ExitCode
    Exit Function
ExecErr:
    errText = errText & "Shell error: " & Err.Description
    RunAndCapture = 9999
End Function

Private Function FirstLine(s As String) As String
    Dim p As Long
    s = Replace(s, vbCrLf, vbLf)
    p = InStr(s, vbLf)
    If p > 0 Then FirstLine = Left(s, p - 1) Else FirstLine = s
End Function

Private Sub SetStatus(state As String, msg As String)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(STATUS_SHEET)
    If ws Is Nothing Then Exit Sub
    ' Column L (12), row 4 — the masthead status panel (free of the merged
    ' banner/KPI cells the runner fills on rows 1-2).
    ws.Cells(4, 12).Value = state & " -- " & msg
End Sub

' Paint a KeyBank sparkline into the Trend (8q) column of each dashboard, one per
' row, sourced from that series' own 8-quarter raw window (newest-first). Native
' sparklines can't be written by openpyxl, so the button owns this column. Fully
' guarded: a failure here never breaks a refresh (the data is already in place).
Private Sub PaintSparklines()
    On Error Resume Next
    PaintLaneSparklines "Dashboard_Consumer", "Raw_Consumer"
    PaintLaneSparklines "Dashboard_Commercial", "Raw_Commercial"
    PaintLaneSparklines "Dashboard_Price", "Raw_Price"
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
                    .SeriesColor.Color = RGB(87, 83, 75)                  ' SLATE line
                    .Points.Markers.Visible = False
                    .Points.Highlight(xlSparkColumnFirst).Visible = True  ' newest is leftmost
                    .Points.Highlight(xlSparkColumnFirst).Color.Color = RGB(204, 0, 0)  ' KEY_RED
                End With
            End If
        End If
    Next r
End Sub
