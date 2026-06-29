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
    ws.Range("H6").Value = "Macro:"
    ws.Range("I6").Value = state & " -- " & msg
End Sub
