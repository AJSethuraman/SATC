# Runbook — live acceptance on the build PC

The last mile of M1 (issue #169). Everything else in this repository runs on the
deterministic offline demo provider, which is what makes the verification bar
fast and airtight — and also what makes it possible for the whole suite to be
green while the live adapters, or Excel itself, are broken.

This is the check that closes that gap. It needs a Windows machine with Excel
installed, a network, and a FRED key. It is **not** part of CI.

## Before you start

| | |
|---|---|
| Excel | any recent desktop Excel (verified on 16.0) |
| `FRED_API_KEY` | free from <https://fredaccount.stlouisfed.org/apikeys> |
| FDIC | nothing — the BankFind API is **keyless** |
| Python | `pip install openpyxl pandas fredapi pywin32` |

Check the machine first; it takes ten seconds and saves a confusing failure later:

```powershell
python -c "import os;print('FRED key:', bool(os.environ.get('FRED_API_KEY')))"
python -c "import win32com.client as w;x=w.DispatchEx('Excel.Application');print('Excel',x.Version);x.Quit()"
```

## 1 · Live data reaching a flag

```powershell
cd credit-suite
python tools/live_acceptance.py                 # both monitors
python tools/live_acceptance.py fdic            # just one
python tools/live_acceptance.py --keep .\live   # keep the workbooks to open
```

It builds each monitor exactly as it ships, pulls **real** data, and prints a
verdict. A pass means all of: the run was in `live` mode, real observations
landed in the raw block, and at least one of them **reached a flag**. The last
part is the point — a pull that lands data nothing reads proves very little.

FDIC takes seconds (one bulk request). FRED takes about 90 seconds: it makes one
request per series, paced to stay under the published rate limit, and says so.

**What a good result looks like** (2026-09-04):

```
fdic  12/12 banks landed, vintage from the API's own index timestamp
      JPMorgan Chase Bank NA   P3CONOTHR  8.35   ALERT
      Wells Fargo Bank NA      NTCONOTQR  4.13   ALERT
      Bank of America NA       UNRLZCAPR 33.15   WATCH
fred  135/146 series pulled, 6 alerts
      DRSFRMOBS  zscore 1.44 vs band 1.00
      DRSFRMACBS zscore 1.33 vs band 1.00
```

**Known: FRED reports 11 failures**, all metro house-price series
(`ATNHPIUS…Q`). Those ids are wrong in the seed — see issue #181. Everything
else pulling is the expected state until that is fixed; a *twelfth* failure
would be new and worth reading.

## 2 · Real Excel

Excel is the only thing that can answer two questions: does the embedded VBA
project actually load, and do the formulas compute what we think they do.
openpyxl, olevba and the OPC audit all prove the *bytes* are right, and all
three pass on a workbook Excel refuses to load.

```powershell
# formulas: open, force a full rebuild, read cells back
python tools/excel_acceptance.py --workbook .\live\Bank_Peer_Monitor.xlsm `
    --recalc "Watchlist!A5" --recalc "Watchlist!H5" `
    --recalc "Dashboard_AssetQuality!D8"

# the button
python tools/excel_acceptance.py --workbook .\live\Bank_Peer_Monitor.xlsm
```

**The harness will not hang.** Every COM call runs on a worker thread under a
deadline; a dialog responder records each dialog's text before answering it; and
`finally` kills any `EXCEL.EXE` the script started, measured against a PID
baseline so a copy you already had open is never touched. That is all there
because the first attempt hung for ten minutes on an invisible modal dialog and
left a stray process behind. `DisplayAlerts = False` does **not** suppress a VBA
`MsgBox`.

Add `--visible` to watch it happen.

### What passes today

Recalc **passes**, against live data:

```
Watchlist!A5                 JPMorgan Chase Bank NA
Watchlist!H5                 ALERT
Dashboard_AssetQuality!D8    0.7792763341160891
```

That last figure is the `NCLNLSR` the FDIC API returned for CERT 628 in the same
session. API → raw block → Excel formula → lit flag, end to end.

### What fails today

**The ExtractFiles button does not work** — issue #180. Excel raises

> An error occurred while loading 'PeerMonitor'. Do you want to continue loading
> the project?

and after clicking Yes the macro is unavailable. This is **pre-existing**: the
committed, legacy-built workbook from before the consolidation fails identically,
and the VBA writer moved into the engine byte-identically.

**The working path meanwhile** is the fallback the contract already ships for
this exact case (§11). It opens with no dialogs at all:

1. open `<Workbook>_fallback.xlsx`
2. `Alt+F11`, paste `macro.bas` into a new module
3. save as `.xlsm`

or skip the button entirely — extract `runner.py` yourself and run it, which is
all the button does:

```powershell
python tools/../src/credit_suite/... # or simply:
python runner.py --workbook ".\Bank_Peer_Monitor.xlsm" --demo
```

## 3 · What to record

The point of a desk run is the evidence, so keep it:

- the JSON from each tool (both print one object)
- which values reached which flags, with the entity and metric named
- the data vintage each source reported
- anything that failed, **including the two known failures above** — a run that
  reports them is a run that examined them; a run that reports nothing has not
  been shown to have looked

## Cleaning up

The tools kill their own Excel. If a run is interrupted at the wrong moment:

```powershell
Get-Process EXCEL -ErrorAction SilentlyContinue | Stop-Process -Force
```

Nothing here writes into the repository. `live_acceptance.py` builds into a
temp directory unless you pass `--keep`.

## Before you start: the red banner

If the `.xlsm` arrived by email, download, or chat, Excel will open it with a
**red** bar — *Microsoft has blocked macros from running because the source of
this file is untrusted* — and there is no button through it. The ExtractFiles
button does nothing until this is dealt with. Every recipient hits it; it is
not a fault in the workbook.

**Mark of the Web** — a hidden tag Windows attaches to any file that arrived
from the internet. Since 2022 Excel refuses to run macros in a tagged file.
The tag is a hidden stream on the file called `Zone.Identifier`.

Two fixes. The first is per file; the second is permanent.

### Once, for one file

Right-click the file → **Properties** → tick **Unblock** at the bottom → OK.
Or in PowerShell, with the real path:

```powershell
Unblock-File "$env:USERPROFILE\Downloads\Bank_Peer_Monitor.xlsm"
```

### Permanently: a Trusted Location

**Trusted Location** — a folder you tell Excel to treat as safe. Files opened
from it skip the macro block entirely, tag or not. Use a folder that holds
*only* these workbooks — never Downloads or Documents, because everything that
lands there would be trusted too.

1. Make the folder:

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\SATC-Monitors"
   ```

2. Register it with Excel (Command Prompt, your own account):

   ```
   reg add "HKCU\Software\Microsoft\Office\16.0\Excel\Security\Trusted Locations\LocationSATC" /v Path /t REG_SZ /d "%USERPROFILE%\SATC-Monitors\" /f
   ```

3. Label it so you recognise it later:

   ```
   reg add "HKCU\Software\Microsoft\Office\16.0\Excel\Security\Trusted Locations\LocationSATC" /v Description /t REG_SZ /d "SATC credit monitors" /f
   ```

4. Restart Excel. Move the workbooks into `SATC-Monitors` and open them from
   there.

Or by hand: **File → Options → Trust Center → Trust Center Settings → Trusted
Locations → Add new location**.

The chart workbook (`<Monitor>_Charts.xlsx`, from `tools/chartbook.py`) has no
macros and opens with no banner anywhere. Only the `.xlsm` needs this.
