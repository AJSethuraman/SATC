# Setting up the macros (once per computer)

The macros live in your **Personal Macro Workbook**, PERSONAL.XLSB: a hidden workbook Excel opens every time it
starts, under your Windows login. Macros kept there work in any workbook you open on that computer. They are not in
the workbooks themselves, so a file you send to someone carries no macro, and nobody else has them unless they set
them up.

## 1. Check that your Excel allows your own macros

1. In Excel: **File → Options → Trust Center → Trust Center Settings… → Macro Settings**.
2. Read which option is selected:
   - **Disable all macros without notification**: macros are blocked. Stop here. These macros will not run on this
     machine; ask IT or use the by-hand route.
   - **Disable VBA macros with notification**, or anything that enables them: carry on.
3. Click **Cancel**; nothing needs changing.

## 2. Create the Personal Macro Workbook (skip if you already have one)

PERSONAL.XLSB does not exist until something is stored in it. The usual way is to record a throwaway macro:

1. **View → Macros → Record Macro…**
2. In **Store macro in**, choose **Personal Macro Workbook**. Click **OK**.
3. Click any cell, then **View → Macros → Stop Recording**.

## 3. Import the macro file

1. Press **Alt+F11**. The Visual Basic window opens.
2. In the **Project** pane on the left, click **VBAProject (PERSONAL.XLSB)**. If the pane is missing, press **Ctrl+R**.
3. **File → Import File…** and pick **Hygiene.bas**. A module named **Hygiene** appears under PERSONAL.XLSB → Modules.
4. Optional: right-click the throwaway **Module1** from step 2 → **Remove Module1** → **No** (don't export).
5. Close the Visual Basic window.
6. When you next close Excel, it asks whether to save changes to the Personal Macro Workbook: click **Save**.

**If you already imported an older Hygiene.bas:** remove the old **Hygiene** module first (step 4, on Hygiene), then
import the new one. Two modules with the same macros confuse Excel.

## 4. Run them

**View → Macros → View Macros**, choose the macro, click **Run**:

| Macro | Run it on | What it does |
|---|---|---|
| `PERSONAL.XLSB!HygieneProfile` | the sheet holding the population (column names in row 1) | Writes **Column Audit**: one row per column, with what it found. Decisions you typed earlier are kept. |
| `PERSONAL.XLSB!HygieneBuild` | any sheet | Reads your decisions on Column Audit and writes **Final Population** (values) and **Row Audit**. Refuses, and says why, while any column has no decision. |
| `PERSONAL.XLSB!HygieneSaveCopy` | any sheet | Saves Final Population alone, values only, as a new workbook in the same folder. |

**A shortcut key:** in View Macros, select the macro → **Options…** → type a letter with Shift held, e.g. **Shift+P**
makes it **Ctrl+Shift+P**.

## 5. If something goes wrong

Every run writes a line to the log at the bottom of the **Hygiene** sheet, including every message it showed you.
A screenshot of that sheet is what to send back.
