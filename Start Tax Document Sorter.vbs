On Error Resume Next
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "tax_doc_sorter_app.pyw")

Err.Clear
exitCode = shell.Run("pyw -3.12 """ & appPath & """", 0, True)
firstError = Err.Number

If firstError <> 0 Or exitCode <> 0 Then
    Err.Clear
    exitCode = shell.Run("pyw """ & appPath & """", 0, True)
    secondError = Err.Number
End If

If firstError <> 0 Or secondError <> 0 Or exitCode <> 0 Then
    MsgBox "Tax Document Sorter could not start." & vbCrLf & vbCrLf & _
           "Please run Setup Tax Document Sorter.bat or install Python 3.12, then try again.", _
           vbCritical, "Tax Document Sorter"
End If
