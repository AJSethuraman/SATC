Attribute VB_Name = "Hygiene"
' Hygiene: profile a population, record a decision per column, and build the population from those decisions.
'
' The firm, 5 Oct 2026: "It'd be nice to be able to easily take a population and figure out basically how messed up
' it is or how we can fix it." Decided the same day: an Excel macro kept in the Personal Macro Workbook; Build writes
' plain values with a stamp, replacing live formulas and a separate export snapshot.
'
' Three macros, run in order:
'   HygieneProfile   - on the source sheet: writes Column Audit, one row per column. Decisions already typed there are
'                      kept, matched on the column's name.
'   HygieneBuild     - reads Column Audit's decisions and writes Final Population as values, plus Row Audit. Refuses
'                      while any column has no decision, or two kept columns would share a name.
'   HygieneSaveCopy  - saves Final Population alone, values only, as a new workbook beside this one.
'
' Nothing here changes the source sheet. Every run adds a line to the log on the Hygiene sheet, and so does any error,
' with the screen and status bar put back.

Option Explicit

Private Const AUDIT As String = "Column Audit"
Private Const FINAL As String = "Final Population"
Private Const ROWS_SHEET As String = "Row Audit"
Private Const CONTROL As String = "Hygiene"
Private Const BUILT As String = "_hygiene_built"

' Column Audit's columns
Private Const A_NAME As Long = 1
Private Const A_TYPE As Long = 2
Private Const A_BLANK As Long = 3
Private Const A_BLANK_PCT As Long = 4
Private Const A_DISTINCT As Long = 5
Private Const A_TOP As Long = 6
Private Const A_NUM_TEXT As Long = 7
Private Const A_DATE_TEXT As Long = 8
Private Const A_SPACES As Long = 9
Private Const A_ODD As Long = 10
Private Const A_CONSTANT As Long = 11
Private Const A_SAME_AS As Long = 12
Private Const A_KEEP As Long = 13
Private Const A_NEW_NAME As Long = 14
Private Const A_FLAG As Long = 15
Private Const A_NOTES As Long = 16
Private Const A_LAST As Long = 16

' the Hygiene sheet: settings and stamps in column B, the log from row LOG_FIRST
Private Const C_SOURCE As Long = 3
Private Const C_KEY As Long = 4
Private Const C_PROFILED As Long = 6
Private Const C_BUILT_AT As Long = 7
Private Const C_STATUS As Long = 8
Private Const C_ROWS As Long = 9
Private Const C_KEPT As Long = 10
Private Const C_DROPPED As Long = 11
Private Const C_FLAGS As Long = 12
Private Const C_BLANK_ROWS As Long = 13
Private Const C_DUP_KEYS As Long = 14
Private Const LOG_FIRST As Long = 17

Private Const KEEP_WORD As String = "Keep"
' True: messages go to the log only, never a dialog (the test harness sets it; nobody else needs to)
Public HygieneQuiet As Boolean
Private Const DROP_WORD As String = "Drop"
Private Const TOP_N As Long = 3
' Row Audit lists this many rows for one repeated key, then "... and N more": a cell holds at most 32,767 characters
Private Const ROWS_LISTED As Long = 20

' ---------------------------------------------------------------------------------------------------------------------
' Profile

Public Sub HygieneProfile()
    On Error GoTo failed
    Dim src As Worksheet
    Set src = ActiveSheet
    If src.Name = AUDIT Or src.Name = FINAL Or src.Name = ROWS_SHEET Or src.Name = CONTROL Then
        Say "Go to the sheet holding the population (its column names in row 1), then run Profile again.", _
               vbExclamation, "Profile"
        Exit Sub
    End If
    Dim nRows As Long, nCols As Long
    nRows = LastRow(src)
    nCols = LastCol(src)
    If nCols = 0 Or nRows < 2 Then
        Say "Sheet " & src.Name & " has no rows under its column names.", vbExclamation, "Profile"
        Exit Sub
    End If

    Dim ctl As Worksheet
    Set ctl = ControlSheet()
    Dim kept As Collection
    Set kept = KeptDecisions()

    Dim aud As Worksheet
    Set aud = FreshSheet(AUDIT, src)
    WriteAuditHeads aud

    Application.ScreenUpdating = False
    Dim names As Variant, blankNames As Long, sharedNames As Long
    names = DisplayNames(src, nCols, blankNames, sharedNames)
    Dim c As Long, r As Long, sigs() As String
    ReDim sigs(1 To nCols)
    For c = 1 To nCols
        Application.StatusBar = "Profile: column " & c & " of " & nCols
        r = c + 1
        WriteCell aud.Cells(r, A_NAME), names(c)
        sigs(c) = ProfileColumn(ColumnValues(src, c, nRows), nRows - 1, aud, r)
        RestoreDecision aud, r, names(c), kept
    Next c

    ' columns that repeat another column, row for row: compared only when the profile's own signature (blanks and
    ' distinct count) matches, and read again from the sheet then, so no more than two columns are held at once
    Dim d As Long
    For c = 2 To nCols
        For d = 1 To c - 1
            If sigs(c) = sigs(d) Then
                Application.StatusBar = "Profile: comparing column " & c & " with column " & d
                If SameColumn(ColumnValues(src, c, nRows), ColumnValues(src, d, nRows)) Then
                    WriteCell aud.Cells(c + 1, A_SAME_AS), names(d)
                    Exit For
                End If
            End If
        Next d
    Next c

    FinishAudit aud, nCols
    WriteCell ctl.Cells(C_SOURCE, 2), src.Name
    ctl.Cells(C_PROFILED, 2).Value = Format(Now, "yyyy-mm-dd hh:mm") & " - " & nCols & " columns, " & _
                                     (nRows - 1) & " rows"
    Application.StatusBar = False
    Application.ScreenUpdating = True
    AddLog "Profile", "Sheet " & src.Name & ": " & nCols & " columns, " & (nRows - 1) & " rows" & _
           IIf(blankNames > 0, "; " & blankNames & " columns have no name in row 1", "") & _
           IIf(sharedNames > 0, "; " & sharedNames & " columns share a name with an earlier one, marked (column n)", _
               "") & "; " & kept.Count & " earlier decisions read"
    aud.Activate
    Exit Sub
failed:
    Recover "Profile"
End Sub

' Each column's name as Column Audit shows it: row 1's text; "(no name, column 7)" when row 1 is blank; and
' "NAME (column 37)" for the second and later columns sharing a name (case ignored), so every column has its own row
' and Build finds the same column again. Profile and Build both name columns here. Returns a Variant holding the
' array: a function declared to return String() does not compile in LibreOffice, which the tests run on.
Private Function DisplayNames(src As Worksheet, nCols As Long, blankNames As Long, sharedNames As Long) As Variant
    Dim out() As String, c As Long, h As String, seen As New Collection
    ReDim out(1 To nCols)
    For c = 1 To nCols
        h = Trim(CellText(src.Cells(1, c).Value))
        If h = "" Then
            out(c) = "(no name, column " & c & ")"
            blankNames = blankNames + 1
        ElseIf Lookup(seen, "t" & LCase(h)) <> 0 Then
            out(c) = h & " (column " & c & ")"
            sharedNames = sharedNames + 1
        Else
            out(c) = h
            seen.Add c, KeyOf("t" & LCase(h))
        End If
    Next c
    DisplayNames = out
End Function

' Profiles one column's values (row 2 down) into Column Audit's row r. Returns its signature: blanks and distinct count.
Private Function ProfileColumn(v As Variant, n As Long, aud As Worksheet, r As Long) As String
    Dim i As Long, x As Variant, s As String, tag As String
    Dim blanks As Long, nums As Long, texts As Long, dates As Long, bools As Long, errs As Long
    Dim numText As Long, dateText As Long, spaces As Long, odd As Long
    Dim seen As New Collection, vals() As String, cnts() As Long, k As Long, nDistinct As Long
    ReDim vals(1 To 16)
    ReDim cnts(1 To 16)
    For i = 1 To n
        x = v(i, 1)
        s = ""
        If IsError(x) Then
            errs = errs + 1
        ElseIf IsEmpty(x) Then
            blanks = blanks + 1
        ElseIf VarType(x) = vbString Then
            s = CStr(x)
            If Trim(s) = "" Then
                blanks = blanks + 1
                If Len(s) > 0 Then spaces = spaces + 1
            Else
                texts = texts + 1
                If Trim(s) <> s Then spaces = spaces + 1
                If HasOdd(s) Then odd = odd + 1
                If LooksNumeric(Trim(s)) Then
                    numText = numText + 1
                ElseIf LooksLikeDate(Trim(s)) Then
                    dateText = dateText + 1
                End If
            End If
        ElseIf VarType(x) = vbDate Then
            dates = dates + 1
        ElseIf VarType(x) = vbBoolean Then
            bools = bools + 1
        Else
            nums = nums + 1
        End If
        If Not IsBlankValue(x) Then
            ' the value as text, and its kind: the number 1 and the text "1" are two values
            tag = TypedText(x)
            k = Lookup(seen, tag)
            If k = 0 Then
                nDistinct = nDistinct + 1
                If nDistinct > UBound(vals) Then
                    ReDim Preserve vals(1 To UBound(vals) * 2)
                    ReDim Preserve cnts(1 To UBound(cnts) * 2)
                End If
                vals(nDistinct) = Mid(tag, 2)
                cnts(nDistinct) = 1
                seen.Add nDistinct, KeyOf(tag)
            Else
                cnts(k) = cnts(k) + 1
            End If
        End If
    Next i
    aud.Cells(r, A_TYPE).Value = TypeWords(nums, texts, dates, bools, errs)
    aud.Cells(r, A_BLANK).Value = blanks
    aud.Cells(r, A_BLANK_PCT).Value = IIf(n > 0, blanks / n, 0)
    aud.Cells(r, A_DISTINCT).Value = nDistinct
    WriteCell aud.Cells(r, A_TOP), TopWords(vals, cnts, nDistinct)
    aud.Cells(r, A_NUM_TEXT).Value = numText
    aud.Cells(r, A_DATE_TEXT).Value = dateText
    aud.Cells(r, A_SPACES).Value = spaces
    aud.Cells(r, A_ODD).Value = odd
    If nDistinct = 1 And blanks = 0 Then
        aud.Cells(r, A_CONSTANT).Value = "Yes"
    ElseIf nDistinct = 0 Then
        aud.Cells(r, A_CONSTANT).Value = "All blank"
    Else
        aud.Cells(r, A_CONSTANT).Value = ""
    End If
    ProfileColumn = blanks & "|" & nDistinct
End Function

Private Function TypeWords(nums As Long, texts As Long, dates As Long, bools As Long, errs As Long) As String
    Dim parts As New Collection, kinds As Long
    If nums > 0 Then parts.Add nums & " number": kinds = kinds + 1
    If texts > 0 Then parts.Add texts & " text": kinds = kinds + 1
    If dates > 0 Then parts.Add dates & " date": kinds = kinds + 1
    If bools > 0 Then parts.Add bools & " TRUE/FALSE": kinds = kinds + 1
    If errs > 0 Then parts.Add errs & " error": kinds = kinds + 1
    If kinds = 0 Then
        TypeWords = "Empty"
    ElseIf kinds = 1 Then
        If nums > 0 Then TypeWords = "Number"
        If texts > 0 Then TypeWords = "Text"
        If dates > 0 Then TypeWords = "Date"
        If bools > 0 Then TypeWords = "TRUE/FALSE"
        If errs > 0 Then TypeWords = "Error"
    Else
        Dim i As Long, s As String
        For i = 1 To parts.Count
            s = s & IIf(i > 1, ", ", "") & parts(i)
        Next i
        TypeWords = "Mixed: " & s
    End If
End Function

' The TOP_N most common values with their counts: "Y (812), N (90), U (4)".
Private Function TopWords(vals() As String, cnts() As Long, n As Long) As String
    Dim used() As Boolean, t As Long, i As Long, best As Long, s As String
    If n = 0 Then Exit Function
    ReDim used(1 To n)
    For t = 1 To TOP_N
        best = 0
        For i = 1 To n
            If Not used(i) Then
                If best = 0 Then
                    best = i
                ElseIf cnts(i) > cnts(best) Then
                    best = i
                End If
            End If
        Next i
        If best = 0 Then Exit For
        used(best) = True
        s = s & IIf(t > 1, ", ", "") & Shorten(vals(best)) & " (" & cnts(best) & ")"
    Next t
    TopWords = s
End Function

Private Function Shorten(s As String) As String
    If Len(s) > 30 Then Shorten = Left(s, 27) & "..." Else Shorten = s
End Function

' A character no one types: control characters, the no-break space and the zero-width space.
Private Function HasOdd(s As String) As Boolean
    Dim i As Long, a As Long
    For i = 1 To Len(s)
        a = AscW(Mid(s, i, 1))
        If a < 0 Then a = a + 65536
        If a < 32 Or a = 160 Or a = 8203 Or a = 65279 Then
            HasOdd = True
            Exit Function
        End If
    Next i
End Function

' A number written as text: digits with at most one decimal point, an optional sign in front, thousands commas, and a
' leading $ or trailing %. Narrower than IsNumeric, which also takes "&H10" (hexadecimal) and "1D5" (an exponent).
Private Function LooksNumeric(s As String) As Boolean
    Dim t As String, i As Long, ch As String, digits As Long, points As Long
    t = s
    If Left(t, 1) = "-" Or Left(t, 1) = "+" Then t = Mid(t, 2)
    If Left(t, 1) = "$" Then t = Mid(t, 2)
    If Right(t, 1) = "%" Then t = Left(t, Len(t) - 1)
    If t = "" Then Exit Function
    For i = 1 To Len(t)
        ch = Mid(t, i, 1)
        If ch >= "0" And ch <= "9" Then
            digits = digits + 1
        ElseIf ch = "." Then
            points = points + 1
        ElseIf ch <> "," Then
            Exit Function
        End If
    Next i
    LooksNumeric = digits > 0 And points <= 1
End Function

' Text Excel would read as a date: something IsDate accepts that holds a date separator, so "1.5" and "12" are not
' dates.
Private Function LooksLikeDate(s As String) As Boolean
    If InStr(s, "/") = 0 And InStr(s, "-") = 0 Then Exit Function
    LooksLikeDate = IsDate(s)
End Function

Private Function SameColumn(a As Variant, b As Variant) As Boolean
    Dim i As Long
    For i = LBound(a, 1) To UBound(a, 1)
        If TypedText(a(i, 1)) <> TypedText(b(i, 1)) Then Exit Function
    Next i
    SameColumn = True
End Function

Private Function CellText(x As Variant) As String
    If IsError(x) Then
        CellText = "#ERROR"
    ElseIf IsEmpty(x) Then
        CellText = ""
    Else
        CellText = CStr(x)
    End If
End Function

' A value as text with its kind in front: t text, n number, d date, b TRUE/FALSE, e error, z blank.
Private Function TypedText(x As Variant) As String
    If IsError(x) Then
        TypedText = "e#ERROR"
    ElseIf IsEmpty(x) Then
        TypedText = "z"
    ElseIf VarType(x) = vbString Then
        TypedText = "t" & CStr(x)
    ElseIf VarType(x) = vbDate Then
        TypedText = "d" & Format(x, "yyyy-mm-dd hh:mm:ss")
    ElseIf VarType(x) = vbBoolean Then
        TypedText = "b" & CStr(x)
    Else
        TypedText = "n" & CStr(x)
    End If
End Function

' A Collection's keys ignore case, so "Y" and "y" would be one value. The key carries which letters are capitals.
Private Function KeyOf(ByVal s As String) As String
    Dim i As Long, m As String, ch As String
    If LCase(s) = s Then
        KeyOf = "k" & s
        Exit Function
    End If
    For i = 1 To Len(s)
        ch = Mid(s, i, 1)
        If ch <> LCase(ch) Then m = m & "1" Else m = m & "0"
    Next i
    KeyOf = "k" & s & ChrW(1) & m
End Function

Private Function Lookup(col As Collection, ByVal s As String) As Long
    On Error GoTo none
    Lookup = col(KeyOf(s))
    Exit Function
none:
    Lookup = 0
End Function

Private Sub WriteAuditHeads(aud As Worksheet)
    Dim heads As Variant, c As Long
    heads = Array("Column", "Type found", "Blank", "Blank %", "Distinct", "Most common", "Numbers as text", _
                  "Dates as text", "Extra spaces", "Odd characters", "Same value in every row", "Same as column", _
                  "Keep?", "New name", "Flag: 1 when", "Notes")
    For c = 0 To UBound(heads)
        aud.Cells(1, c + 1).Value = heads(c)
    Next c
    With aud.Range(aud.Cells(1, 1), aud.Cells(1, A_LAST))
        .Font.Bold = True
        .Interior.Color = RGB(31, 41, 55)
        .Font.Color = RGB(255, 255, 255)
    End With
End Sub

Private Sub FinishAudit(aud As Worksheet, nCols As Long)
    Dim last As Long
    last = nCols + 1
    aud.Range(aud.Cells(2, A_BLANK_PCT), aud.Cells(last, A_BLANK_PCT)).NumberFormat = "0.0%"
    ' the columns the analyst fills in, shaded so they read as inputs
    aud.Range(aud.Cells(2, A_KEEP), aud.Cells(last, A_NOTES)).Interior.Color = RGB(255, 247, 214)
    With aud.Range(aud.Cells(2, A_KEEP), aud.Cells(last, A_KEEP)).Validation
        .Delete
        .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, Formula1:=KEEP_WORD & "," & DROP_WORD
    End With
    aud.Columns(A_NAME).ColumnWidth = 28
    aud.Columns(A_TYPE).ColumnWidth = 24
    aud.Columns(A_TOP).ColumnWidth = 40
    aud.Columns(A_SAME_AS).ColumnWidth = 20
    aud.Columns(A_NEW_NAME).ColumnWidth = 20
    aud.Columns(A_FLAG).ColumnWidth = 16
    aud.Columns(A_NOTES).ColumnWidth = 30
    aud.Rows(1).WrapText = True
    aud.Range(aud.Cells(1, 1), aud.Cells(last, A_LAST)).AutoFilter
End Sub

' Decisions already on Column Audit, keyed by column name: Keep?, New name, Flag, Notes.
Private Function KeptDecisions() As Collection
    Dim out As New Collection, aud As Worksheet, r As Long, nm As String
    Set KeptDecisions = out
    If Not SheetExists(AUDIT) Then Exit Function
    Set aud = ThisBook().Worksheets(AUDIT)
    For r = 2 To LastRow(aud)
        nm = CellText(aud.Cells(r, A_NAME).Value)
        If nm <> "" Then
            If Lookup(out, nm) = 0 Then
                out.Add Array(aud.Cells(r, A_KEEP).Value, aud.Cells(r, A_NEW_NAME).Value, _
                              aud.Cells(r, A_FLAG).Value, aud.Cells(r, A_NOTES).Value), KeyOf(nm)
            End If
        End If
    Next r
End Function

Private Sub RestoreDecision(aud As Worksheet, r As Long, ByVal nm As String, kept As Collection)
    Dim d As Variant
    On Error GoTo none
    d = kept(KeyOf(nm))
    On Error GoTo 0
    WriteCell aud.Cells(r, A_KEEP), d(0)
    WriteCell aud.Cells(r, A_NEW_NAME), d(1)
    WriteCell aud.Cells(r, A_FLAG), d(2)
    WriteCell aud.Cells(r, A_NOTES), d(3)
    Exit Sub
none:
End Sub

' ---------------------------------------------------------------------------------------------------------------------
' Build

Public Sub HygieneBuild()
    On Error GoTo failed
    Dim ctl As Worksheet, aud As Worksheet, src As Worksheet
    If Not SheetExists(AUDIT) Then
        Say "Run Profile on the population first: Build reads the decisions on Column Audit.", vbExclamation, "Build"
        Exit Sub
    End If
    Set ctl = ControlSheet()
    Set aud = ThisBook().Worksheets(AUDIT)
    Dim srcName As String
    srcName = CellText(ctl.Cells(C_SOURCE, 2).Value)
    If srcName = "" Or Not SheetExists(srcName) Then
        Say "The source sheet named on the " & CONTROL & " sheet (" & IIf(srcName = "", "none", srcName) & _
               ") is not in this workbook. Run Profile on the population again.", vbExclamation, "Build"
        Exit Sub
    End If
    Set src = ThisBook().Worksheets(srcName)

    ' the source's columns, named as Profile named them
    Dim nSrcCols As Long, srcNames As Variant, nb As Long, ns As Long, byName As New Collection, c As Long
    nSrcCols = LastCol(src)
    srcNames = DisplayNames(src, nSrcCols, nb, ns)
    For c = 1 To nSrcCols
        byName.Add c, KeyOf(srcNames(c))
    Next c

    ' the decisions, refused whole when any is missing or two kept columns would share a name
    Dim nAud As Long, r As Long, problems As String, nProblems As Long
    nAud = LastRow(aud)
    Dim srcCol() As Long, outName() As String, flagOf() As String, nKeep As Long, nDrop As Long
    ReDim srcCol(1 To nAud)
    ReDim outName(1 To nAud)
    ReDim flagOf(1 To nAud)
    Dim names As New Collection
    For r = 2 To nAud
        Dim nm As String, decision As String
        nm = CellText(aud.Cells(r, A_NAME).Value)
        decision = Trim(CellText(aud.Cells(r, A_KEEP).Value))
        If StrComp(decision, KEEP_WORD, vbTextCompare) = 0 Then
            c = Lookup(byName, nm)
            If c = 0 Then
                problems = AddProblem(problems, nProblems, nm & ": kept, but no longer a column on " & srcName)
            Else
                nKeep = nKeep + 1
                srcCol(nKeep) = c
                outName(nKeep) = Trim(CellText(aud.Cells(r, A_NEW_NAME).Value))
                If outName(nKeep) = "" Then outName(nKeep) = nm
                flagOf(nKeep) = Trim(CellText(aud.Cells(r, A_FLAG).Value))
                If Lookup(names, LCase(outName(nKeep))) <> 0 Then
                    problems = AddProblem(problems, nProblems, outName(nKeep) & ": two kept columns would share this name")
                Else
                    names.Add nKeep, KeyOf(LCase(outName(nKeep)))
                End If
            End If
        ElseIf StrComp(decision, DROP_WORD, vbTextCompare) = 0 Then
            nDrop = nDrop + 1
        Else
            problems = AddProblem(problems, nProblems, nm & ": no decision in Keep?")
        End If
    Next r
    If nProblems > 0 Then
        AddLog "Build refused", nProblems & " to fix first. " & Replace(problems, vbLf, "; ")
        Say "Build did not run. " & nProblems & " to fix on Column Audit first:" & vbLf & vbLf & _
               FirstLines(problems, 15), vbExclamation, "Build"
        Exit Sub
    End If
    If nKeep = 0 Then
        AddLog "Build refused", "every column is Drop"
        Say "Build did not run: every column is marked Drop.", vbExclamation, "Build"
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Dim nRows As Long
    nRows = LastRow(src)
    Dim fin As Worksheet
    Set fin = FreshSheet(FINAL, aud)
    Dim k As Long, v As Variant, flags As Long, flagNotes As String
    For k = 1 To nKeep
        Application.StatusBar = "Build: column " & k & " of " & nKeep
        v = ColumnValues(src, srcCol(k), nRows)
        If flagOf(k) <> "" Then
            flagNotes = flagNotes & "; " & outName(k) & ": " & MakeFlag(v, flagOf(k))
            flags = flags + 1
        End If
        WriteCell fin.Cells(1, k), outName(k)
        WriteColumn fin, k, v
    Next k
    With fin.Range(fin.Cells(1, 1), fin.Cells(1, nKeep))
        .Font.Bold = True
        .Interior.Color = RGB(31, 41, 55)
        .Font.Color = RGB(255, 255, 255)
    End With

    Dim blankRows As Long, dupKeys As Long, keyName As String
    keyName = Trim(CellText(ctl.Cells(C_KEY, 2).Value))
    RowAudit fin, nKeep, nRows, keyName, blankRows, dupKeys

    ' the stamp, and the decisions it was built from, so a later change shows as out of date
    ctl.Cells(C_BUILT_AT, 2).Value = Format(Now, "yyyy-mm-dd hh:mm") & " from sheet " & srcName
    ctl.Cells(C_ROWS, 2).Value = nRows - 1
    ctl.Cells(C_KEPT, 2).Value = nKeep
    ctl.Cells(C_DROPPED, 2).Value = nDrop
    ctl.Cells(C_FLAGS, 2).Value = flags
    ctl.Cells(C_BLANK_ROWS, 2).Value = blankRows
    If keyName = "" Then
        ctl.Cells(C_DUP_KEYS, 2).Value = "Not checked: no key column named in B" & C_KEY
    Else
        ctl.Cells(C_DUP_KEYS, 2).Value = dupKeys
    End If
    SnapshotDecisions aud, nAud
    ctl.Cells(C_STATUS, 2).Formula = StatusFormula(nAud)
    Application.StatusBar = False
    Application.ScreenUpdating = True
    AddLog "Build", (nRows - 1) & " rows; " & nKeep & " columns kept, " & nDrop & " dropped; " & flags & " flags" & _
           flagNotes & "; " & blankRows & " rows with a blank" & IIf(keyName = "", "", "; " & dupKeys & _
           " duplicate " & keyName)
    fin.Activate
    Exit Sub
failed:
    Recover "Build"
End Sub

Private Function AddProblem(problems As String, n As Long, s As String) As String
    n = n + 1
    AddProblem = problems & IIf(problems = "", "", vbLf) & s
End Function

Private Function FirstLines(s As String, n As Long) As String
    Dim parts As Variant, i As Long, out As String
    parts = Split(s, vbLf)
    For i = 0 To UBound(parts)
        If i >= n Then
            out = out & vbLf & "... and " & (UBound(parts) - n + 1) & " more (all are in the log on the " & CONTROL & _
                  " sheet)"
            Exit For
        End If
        out = out & IIf(i > 0, vbLf, "") & parts(i)
    Next i
    FirstLines = out
End Function

' Turns a column into a flag in place: 1 where the trimmed value is one of `rule`'s values (separated by ";", case
' ignored), 0 where it is any other value, blank where it is blank. Returns the counts, for the log.
Private Function MakeFlag(v As Variant, rule As String) As String
    Dim want As Variant, i As Long, j As Long, s As String, hit As Boolean, ones As Long, zeros As Long, blanks As Long
    want = Split(rule, ";")
    For j = 0 To UBound(want)
        want(j) = UCase(Trim(want(j)))
    Next j
    For i = LBound(v, 1) To UBound(v, 1)
        s = UCase(Trim(CellText(v(i, 1))))
        If s = "" Then
            v(i, 1) = Empty
            blanks = blanks + 1
        Else
            hit = False
            For j = 0 To UBound(want)
                If s = want(j) Then hit = True
            Next j
            If hit Then
                v(i, 1) = 1
                ones = ones + 1
            Else
                v(i, 1) = 0
                zeros = zeros + 1
            End If
        End If
    Next i
    MakeFlag = ones & " ones, " & zeros & " zeros, " & blanks & " blank"
End Function

' Row Audit: every row of Final Population with a blank, and every key value that appears more than once.
Private Sub RowAudit(fin As Worksheet, nKeep As Long, nRows As Long, keyName As String, blankRows As Long, _
                     dupKeys As Long)
    Dim ra As Worksheet
    Set ra = FreshSheet(ROWS_SHEET, fin)
    Dim keyCol As Long, c As Long
    If keyName <> "" Then
        For c = 1 To nKeep
            If StrComp(CellText(fin.Cells(1, c).Value), keyName, vbTextCompare) = 0 Then keyCol = c
        Next c
    End If
    ra.Cells(1, 1).Value = "Row on Final Population"
    WriteCell ra.Cells(1, 2), IIf(keyCol > 0, keyName, "Key (none named)")
    ra.Cells(1, 3).Value = "Blank fields"
    ra.Cells(1, 4).Value = "Which (first 5)"
    WriteCell ra.Cells(1, 6), "Duplicate " & IIf(keyCol > 0, keyName, "key")
    ra.Cells(1, 7).Value = "Rows"
    ra.Cells(1, 8).Value = "Times"
    ra.Range("A1:H1").Font.Bold = True
    If nRows < 2 Then Exit Sub
    Dim data As Variant, r As Long, out As Long, n As Long, which As String
    data = BlockValues(fin, 2, 1, nRows, nKeep)
    out = 1
    For r = 1 To nRows - 1
        n = 0
        which = ""
        For c = 1 To nKeep
            If IsBlankValue(data(r, c)) Then
                n = n + 1
                If n <= 5 Then which = which & IIf(n > 1, ", ", "") & CellText(fin.Cells(1, c).Value)
            End If
        Next c
        If n > 0 Then
            out = out + 1
            blankRows = blankRows + 1
            ra.Cells(out, 1).Value = r + 1
            If keyCol > 0 Then WriteCell ra.Cells(out, 2), data(r, keyCol)
            ra.Cells(out, 3).Value = n
            WriteCell ra.Cells(out, 4), which
        End If
    Next r
    If keyCol = 0 Then
        WriteCell ra.Cells(2, 6), "Not checked: name a key column on the " & CONTROL & " sheet, cell B" & C_KEY
        Exit Sub
    End If
    ' keys compared as trimmed text, so "A1 " and "A1" are one key
    Dim seen As New Collection, k As Long, times() As Long, rowsOf() As String, vals() As String
    Dim nDistinct As Long, s As String
    ReDim times(1 To nRows)
    ReDim rowsOf(1 To nRows)
    ReDim vals(1 To nRows)
    For r = 1 To nRows - 1
        If Not IsBlankValue(data(r, keyCol)) Then
            s = Trim(CellText(data(r, keyCol)))
            k = Lookup(seen, s)
            If k = 0 Then
                nDistinct = nDistinct + 1
                vals(nDistinct) = s
                times(nDistinct) = 1
                rowsOf(nDistinct) = CStr(r + 1)
                seen.Add nDistinct, KeyOf(s)
            Else
                times(k) = times(k) + 1
                If times(k) <= ROWS_LISTED Then rowsOf(k) = rowsOf(k) & ", " & (r + 1)
            End If
        End If
    Next r
    out = 1
    For k = 1 To nDistinct
        If times(k) > 1 Then
            out = out + 1
            dupKeys = dupKeys + 1
            WriteCell ra.Cells(out, 6), vals(k)
            If times(k) > ROWS_LISTED Then rowsOf(k) = rowsOf(k) & " ... and " & (times(k) - ROWS_LISTED) & " more"
            WriteCell ra.Cells(out, 7), rowsOf(k)
            ra.Cells(out, 8).Value = times(k)
        End If
    Next k
End Sub

Private Function IsBlankValue(x As Variant) As Boolean
    If IsError(x) Then Exit Function
    If IsEmpty(x) Then
        IsBlankValue = True
    ElseIf VarType(x) = vbString Then
        IsBlankValue = (Trim(CStr(x)) = "")
    End If
End Function

' The decisions Build used, on a hidden sheet, so the status cell can say when Column Audit has changed since.
Private Sub SnapshotDecisions(aud As Worksheet, nAud As Long)
    Dim snap As Worksheet, r As Long, c As Long
    Set snap = FreshSheet(BUILT, aud)
    For r = 1 To nAud
        WriteCell snap.Cells(r, 1), aud.Cells(r, A_NAME).Value
        For c = 0 To 2
            WriteCell snap.Cells(r, 2 + c), aud.Cells(r, A_KEEP + c).Value
        Next c
    Next r
    snap.Visible = xlSheetHidden
End Sub

' "Current", or "Out of date" once a name, Keep?, New name or Flag on Column Audit differs from what Build used, or
' Column Audit has gained or lost rows.
Private Function StatusFormula(nAud As Long) As String
    Dim a As String, s As String
    a = "'" & AUDIT & "'!"
    s = "'" & BUILT & "'!"
    StatusFormula = "=IF(OR(COUNTA(" & a & "$A:$A)<>" & nAud & ",SUMPRODUCT(--(" & a & "$A$1:$A$" & nAud & "&""|""&" & _
                    a & "$M$1:$M$" & nAud & "&""|""&" & a & "$N$1:$N$" & nAud & "&""|""&" & a & "$O$1:$O$" & nAud & _
                    "<>" & s & "$A$1:$A$" & nAud & "&""|""&" & s & "$B$1:$B$" & nAud & "&""|""&" & s & "$C$1:$C$" & _
                    nAud & "&""|""&" & s & "$D$1:$D$" & nAud & "))>0),""Out of date: a decision changed since this " & _
                    "Build. Run Build again."",""Current"")"
End Function

' ---------------------------------------------------------------------------------------------------------------------
' Save a values-only copy

Public Sub HygieneSaveCopy()
    Dim copyBook As Workbook, wbk As Workbook
    On Error GoTo failed
    If Not SheetExists(FINAL) Then
        Say "There is no Final Population yet. Run Build first.", vbExclamation, "Save copy"
        Exit Sub
    End If
    Dim ctl As Worksheet, stat As String
    Set ctl = ControlSheet()
    stat = CellText(ctl.Cells(C_STATUS, 2).Value)
    If Left(stat, 11) = "Out of date" Then
        Say "Final Population is out of date: a decision changed since it was built. Run Build, then save.", _
               vbExclamation, "Save copy"
        Exit Sub
    End If
    Dim outPath As String, stem As String, sep As String
    Set wbk = ThisBook()
    If wbk.Path = "" Then
        Say "Save this workbook first: the copy is saved in the same folder.", vbExclamation, "Save copy"
        Exit Sub
    End If
    ' a workbook on OneDrive or SharePoint has a web address for its folder, which joins with "/"
    If LCase(Left(wbk.Path, 4)) = "http" Then sep = "/" Else sep = Application.PathSeparator
    stem = wbk.Name
    If InStrRev(stem, ".") > 0 Then stem = Left(stem, InStrRev(stem, ".") - 1)
    outPath = wbk.Path & sep & stem & " - Final Population " & Format(Now, "yyyy-mm-dd hhmm") & ".xlsx"
    ' Final Population holds values only, so a copy of the sheet is already values only
    wbk.Worksheets(FINAL).Copy
    Set copyBook = ActiveWorkbook
    Application.DisplayAlerts = False
    copyBook.SaveAs Filename:=outPath, FileFormat:=51
    Application.DisplayAlerts = True
    copyBook.Close SaveChanges:=False
    Set copyBook = Nothing
    wbk.Activate                                  ' the log is on this workbook, not on the copy just closed
    AddLog "Saved copy", outPath
    Say "Saved:" & vbLf & outPath, vbInformation, "Save copy"
    Exit Sub
failed:
    Application.DisplayAlerts = True
    If Not copyBook Is Nothing Then copyBook.Close SaveChanges:=False
    If Not wbk Is Nothing Then wbk.Activate
    Recover "Save copy"
End Sub

' ---------------------------------------------------------------------------------------------------------------------
' The Hygiene sheet, the log, and small helpers

Private Function ThisBook() As Workbook
    ' the workbook being worked on: the active one, never the Personal Macro Workbook the code lives in
    Set ThisBook = ActiveWorkbook
End Function

Private Function ControlSheet() As Worksheet
    Dim ws As Worksheet
    If SheetExists(CONTROL) Then
        Set ControlSheet = ThisBook().Worksheets(CONTROL)
        Exit Function
    End If
    Set ws = ThisBook().Worksheets.Add(Before:=ThisBook().Worksheets(1))
    ws.Name = CONTROL
    ws.Cells(1, 1).Value = "Hygiene"
    ws.Cells(1, 1).Font.Bold = True
    ws.Cells(1, 1).Font.Size = 14
    ws.Cells(C_SOURCE, 1).Value = "Source sheet"
    ws.Cells(C_KEY, 1).Value = "Key column (for duplicates)"
    ws.Cells(C_PROFILED, 1).Value = "Last Profile"
    ws.Cells(C_BUILT_AT, 1).Value = "Last Build"
    ws.Cells(C_STATUS, 1).Value = "Final Population is"
    ws.Cells(C_ROWS, 1).Value = "Rows"
    ws.Cells(C_KEPT, 1).Value = "Columns kept"
    ws.Cells(C_DROPPED, 1).Value = "Columns dropped"
    ws.Cells(C_FLAGS, 1).Value = "Flags made"
    ws.Cells(C_BLANK_ROWS, 1).Value = "Rows with a blank field"
    ws.Cells(C_DUP_KEYS, 1).Value = "Key values appearing more than once"
    ws.Cells(C_KEY, 2).Interior.Color = RGB(255, 247, 214)
    ws.Cells(C_KEY, 2).NumberFormat = "@"
    ws.Cells(LOG_FIRST - 1, 1).Value = "Log"
    ws.Cells(LOG_FIRST - 1, 1).Font.Bold = True
    ws.Columns(1).ColumnWidth = 34
    ws.Columns(2).ColumnWidth = 18
    ws.Columns(3).ColumnWidth = 90
    Set ControlSheet = ws
End Function

' A message box, also written to the log, so a screenshot of the Hygiene sheet shows what was said. kind defaults
' to 64, vbInformation: a named constant as an Optional default does not compile in LibreOffice, which the tests run on.
Private Sub Say(msg As String, Optional kind As Long = 64, Optional heading As String = "Hygiene")
    AddLog heading & " said", Replace(msg, vbLf, " ")
    If Not HygieneQuiet Then MsgBox msg, kind, heading
End Sub

Public Sub HygieneSetQuiet()
    HygieneQuiet = True
End Sub

' Proves the error path: freezes the screen and the status bar as a long run does, then fails. The log must show the
' error, and the screen must come back. The tests run it; it changes nothing but the log.
Public Sub HygieneSelfTest()
    On Error GoTo failed
    Application.ScreenUpdating = False
    Application.StatusBar = "Self test: running"
    Err.Raise 1004, "Hygiene", "a planted error"
    Exit Sub
failed:
    Recover "Self test"
End Sub

' An error part-way through: the screen and status bar put back, the error logged and shown.
Private Sub Recover(action As String)
    Dim num As Long, what As String
    num = Err.Number
    what = Err.Description
    On Error Resume Next
    Application.StatusBar = False
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Say action & " stopped on an error and did not finish: " & what & " (error " & num & "). Nothing on the " & _
        "source sheet was changed.", vbCritical, action
End Sub

Private Sub AddLog(action As String, what As String)
    Dim ws As Worksheet, r As Long
    Set ws = ControlSheet()
    r = LOG_FIRST
    Do While ws.Cells(r, 1).Value <> ""
        r = r + 1
    Loop
    ws.Cells(r, 1).Value = Format(Now, "yyyy-mm-dd hh:mm:ss")
    WriteCell ws.Cells(r, 2), action
    WriteCell ws.Cells(r, 3), Left(what, 32000)
End Sub

' Excel reads text written to a cell as if it were typed: "00123" becomes the number 123, "2024-01" and "Jan-24"
' dates, "- (812)" a formula's arithmetic. Such text goes into a cell formatted as Text first, so it stays exactly as
' it was. Deliberately broad: text kept as text needlessly costs nothing, text converted is a wrong value. LibreOffice
' does not re-read, and its IsDate rejects "2024-01", so the tests check the format, not the conversion.
Private Function Reparsed(s As String) As Boolean
    Dim t As String, i As Long, ch As String, digits As Long, other As Boolean
    t = Trim(s)
    If t = "" Then Exit Function
    If IsNumeric(t) Or IsDate(t) Then
        Reparsed = True
        Exit Function
    End If
    Select Case Left(t, 1)
        Case "=", "+", "-", "@", "'"
            Reparsed = True
            Exit Function
    End Select
    If UCase(t) = "TRUE" Or UCase(t) = "FALSE" Or Right(t, 1) = "%" Then
        Reparsed = True
        Exit Function
    End If
    ' digits with a date or time separator anywhere: "2024-01", "1/2", "12:30", "Jan-24", "5 Mar"
    For i = 1 To Len(t)
        ch = Mid(t, i, 1)
        If ch >= "0" And ch <= "9" Then
            digits = digits + 1
        ElseIf ch = "-" Or ch = "/" Or ch = ":" Or ch = " " Or ch = "." Then
            other = True
        End If
    Next i
    Reparsed = digits > 0 And other
End Function

' One value into one cell, text kept as text: a single cell's format costs nothing, so all text goes in as Text.
Private Sub WriteCell(cell As Range, x As Variant)
    If VarType(x) = vbString Then cell.NumberFormat = "@"
    cell.Value = x
End Sub

' A column of values into column k from row 2, in one write; then each text value Excel would re-read is written
' again into a cell formatted as Text.
Private Sub WriteColumn(ws As Worksheet, k As Long, v As Variant)
    Dim n As Long, i As Long
    n = UBound(v, 1) - LBound(v, 1) + 1
    If n = 1 Then
        WriteCell ws.Cells(2, k), v(LBound(v, 1), 1)
        Exit Sub
    End If
    ' a column of nothing but text (and blanks) is formatted as Text whole, in one call, before it is written
    Dim allText As Boolean
    allText = True
    For i = LBound(v, 1) To UBound(v, 1)
        If Not IsEmpty(v(i, 1)) And VarType(v(i, 1)) <> vbString Then
            allText = False
            Exit For
        End If
    Next i
    If allText Then ws.Range(ws.Cells(2, k), ws.Cells(n + 1, k)).NumberFormat = "@"
    ws.Range(ws.Cells(2, k), ws.Cells(n + 1, k)).Value = v
    If allText Then Exit Sub
    For i = LBound(v, 1) To UBound(v, 1)
        If VarType(v(i, 1)) = vbString Then
            If Reparsed(CStr(v(i, 1))) Then
                ws.Cells(i - LBound(v, 1) + 2, k).NumberFormat = "@"
                ws.Cells(i - LBound(v, 1) + 2, k).Value = v(i, 1)
            End If
        End If
    Next i
End Sub

' A sheet emptied for writing: cleared when it exists, added after `after` when it does not.
Private Function FreshSheet(nm As String, after As Worksheet) As Worksheet
    Dim ws As Worksheet
    If SheetExists(nm) Then
        Set ws = ThisBook().Worksheets(nm)
        ' the Keep? dropdown goes with its column; nothing else on these sheets carries validation
        If nm = AUDIT Then ws.Columns(A_KEEP).Validation.Delete
        ws.Cells.Clear
        If ws.AutoFilterMode Then ws.AutoFilterMode = False
    Else
        Set ws = ThisBook().Worksheets.Add(After:=after)
        ws.Name = nm
    End If
    Set FreshSheet = ws
End Function

Private Function SheetExists(nm As String) As Boolean
    Dim ws As Worksheet
    For Each ws In ThisBook().Worksheets
        If ws.Name = nm Then
            SheetExists = True
            Exit Function
        End If
    Next ws
End Function

' Column c's values from row 2 to nRows, as a two-dimensional array (1 To n, 1 To 1) even for one row.
Private Function ColumnValues(ws As Worksheet, c As Long, nRows As Long) As Variant
    ColumnValues = BlockValues(ws, 2, c, nRows, c)
End Function

' A block's values as a two-dimensional array, even when the block is one cell (whose .Value is not an array).
Private Function BlockValues(ws As Worksheet, r1 As Long, c1 As Long, r2 As Long, c2 As Long) As Variant
    Dim one(1 To 1, 1 To 1) As Variant
    If r1 = r2 And c1 = c2 Then
        one(1, 1) = ws.Cells(r1, c1).Value
        BlockValues = one
    Else
        BlockValues = ws.Range(ws.Cells(r1, c1), ws.Cells(r2, c2)).Value
    End If
End Function

Private Function LastRow(ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If f Is Nothing Then LastRow = 0 Else LastRow = f.Row
End Function

' The last column holding anything on any row, so data under a blank heading is profiled too, as "(no name, ...)".
Private Function LastCol(ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    If f Is Nothing Then LastCol = 0 Else LastCol = f.Column
End Function
