# threshold-engine at the bank: the machine checklist

**Who this is for:** whoever takes threshold-engine to KeyBank's machine for the first time.

**What it proves:** that the bank's machine installs it, builds the practice workbook with the same numbers our own walkthrough read in Excel, and then builds one from an internal file, with nothing internal coming back out.

**Time:** about 30 minutes for Parts 1 to 4. Part 5, the internal file, depends on how long the file takes to prepare.

Tick each box as you go. Where something differs, write down what you saw and carry on: Part 6 says what to send back, and what must not leave the bank.

## Words you'll meet

| Word | What it means |
|---|---|
| **Command Prompt** | Windows' window for typing commands. Start button, type `cmd`, press Enter. Every command below is typed there, then Enter. |
| **`%USERPROFILE%`** | Command Prompt's name for your own folder, such as `C:\Users\jsmith`. Type it as written; Windows fills in yours. |
| **Python** | The free program threshold-engine is written in. The machine needs it once. |
| **`py`** | The Python starter python.org's installer puts on Windows. `py --version` asks which Python is there. |
| **openpyxl** | The one add-on threshold-engine needs: it writes the Excel workbook. It brings **et-xmlfile** with it. Both are in the kit as files, so they install with no internet. |
| **pip** | Python's own installer for add-ons. |
| **Template** | An empty file laid out the way threshold-engine reads an internal measure, with questions at the top for who prepared it and how. Seven exist: WAPD, refreshed credit score, early payment default, and four two-book splits. |
| **Workbook** | The Excel file it writes: the lines where each score begins, live, so they move when you change a setting. |
| **Check column** | The last column of the Thresholds tab. Blank means the lines stand; otherwise it says, in words, why it refuses. |

---

## Part 1 · Before you go (on your own computer)

### 1.1 Make the kit

In the SATC repository folder:

```
cd threshold-engine
python tools/bank_kit.py
```

☐ It prints `Wrote ...\ThresholdEngine-kit\ThresholdEngine.zip`, its size (about 500 KB), its SHA-256, and the version lines that also go in the zip's `VERSION.txt`.

The zip holds the window (`Thresholds.pyw`), the code, this checklist, `WHAT-IT-DOES.md`, the two add-ons as files (`add-ons\`) and five public practice files (`practice\`): Federal Reserve and FDIC charge-off rates, nothing of the bank's.

### 1.2 Which Python the bank machine has

Ask IT, or ask someone to type `py --version` in Command Prompt.

☐ It must say **Python 3.9 or later**. threshold-engine has been run on 3.12 (every test, the walkthrough and this checklist's dry run).

If there is none, IT installs **Python 3.12, 64-bit, from python.org**. Its installer can install for your account only, which needs no admin rights; tick **Add python.exe to PATH** on its first screen.

### 1.3 Pack

☐ `ThresholdEngine.zip`, on whatever the bank lets files in on. Bank email often strips `.zip` and `.pyw` files, and USB sticks are often blocked: ask IT how a file gets onto the machine before you go.

☐ This checklist, printed.

---

## Part 2 · Install (at the bank machine)

### 2.1 Check Python

```
py --version
```

☐ `Python 3.9` or later. If `py` is not recognised, try `python --version`, and wherever this checklist says `py`, type `python`.

### 2.2 Unzip into your own folder

Copy the zip into **Downloads**. Right-click it, **Properties**, and if there is an **Unblock** box, tick it and press **OK**. Then:

```
cd /d "%USERPROFILE%"
tar -xf "Downloads\ThresholdEngine.zip"
dir "%USERPROFILE%\ThresholdEngine"
```

☐ It lists `Thresholds.pyw`, `VERSION.txt`, `README.md`, and the folders `src`, `config`, `docs`, `practice` and `add-ons`.

If `tar` is not recognised, right-click the zip, **Extract All…**, and extract to what `echo %USERPROFILE%` prints.

### 2.3 Install the add-on

With internet through the bank's proxy:

```
py -m pip install --user "openpyxl>=3.1"
```

If that fails (the proxy blocks it), from the files in the kit, with no internet:

```
py -m pip install --user --no-index --find-links "%USERPROFILE%\ThresholdEngine\add-ons" openpyxl
```

☐ It ends `Successfully installed et-xmlfile-... openpyxl-...` (or says they are already there).

### 2.4 The commands answer

```
cd /d "%USERPROFILE%\ThresholdEngine"
set PYTHONPATH=src
py -m threshold_engine --help
```

☐ It lists six commands: `profile, evidence, backtest, workbook, peers, template`.

`set PYTHONPATH=src` lasts until the Command Prompt window closes. In a new window, type the first two lines again.

---

## Part 3 · The practice workbook (public data, known answers)

### 3.1 Build it

In the same window:

```
py -m threshold_engine workbook practice.xlsx --series "Credit card=practice\cards_nco_ttm.csv" --series "Mortgage=practice\mortgage_nco_ttm.csv" --series "Home equity=practice\home_equity_nco_ttm.csv" --series "Other consumer=practice\other_consumer_as_filed_nco_ttm.csv" --name "Net charge-off rate (TTM)" --unit "%" --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41
```

☐ It prints `Wrote practice.xlsx: Credit card, Mortgage, Home equity, Other consumer, 163 quarters`.

### 3.2 Open it and read the Thresholds tab

```
start practice.xlsx
```

☐ Excel opens it with no message about repairing the file.

☐ The Thresholds tab reads (to three decimals), and the Check column is blank on every row:

| Product | Median kept | Typical yearly move | Worst kept | 2 from | 3 from | 4 from | 5 from | Latest | Score |
|---|---|---|---|---|---|---|---|---|---|
| Credit card | 3.978 | 0.767 | 10.425 | 3.211 | 3.595 | 4.361 | 6.684 | 3.978 | 3 Moderate |
| Mortgage | 0.122 | 0.058 | 2.490 | 0.064 | 0.093 | 0.151 | 0.500 | 0.000 | 1 Low |
| Home equity | 0.182 | 0.095 | 3.140 | 0.087 | 0.135 | 0.230 | 0.685 | -0.019 | 1 Low |
| Other consumer | 1.288 | 0.293 | 3.335 | 0.995 | 1.141 | 1.434 | 2.222 | 1.776 | 4 Moderate-High |

### 3.3 One judgement, by hand

The workbook opens on the **Assess** tab (red). Under the chart, in **Periods left out**, fill the first two rows from the lists: Product `Credit card`, From `2007Q4`, To `2012Q4`, Reason `financial crisis`; then Product `Credit card`, From `2021Q3`, To `2023Q1`, Reason `pandemic forbearance`. Each Status reads `Left out: 21 quarters` and `Left out: 7 quarters`.

☐ Thresholds, Credit card now reads: median 3.757, move 0.586, worst 6.603, lines **3.171 / 3.464 / 4.050 / 5.981**, latest 3.978, **3 Moderate**. These are the card rehearsal settings the bank accepted; the lines were first recorded on 7 Oct 2026.

☐ At the top of Assess (Credit card picked in B4), Latest reads `2026Q2: 3.978  ->  3 Moderate`; the quarters kept in each score read 25 / 22 / 29 / 55 / 4; and the chart shades five bands with two dark strips under the periods left out.

☐ In **Your settings**, type `0` as Credit card's How rare High is (z). Check reads `Refused: High's z must be above 0` and Latest says there is no score. Type `2.5` back.

### 3.4 The window

Double-click `Thresholds.pyw` in the `ThresholdEngine` folder.

☐ The **Thresholds** window opens with its steps down the left. Every field starts empty and **Run** names what is missing.

If nothing opens, type `py Thresholds.pyw` in the Command Prompt window; a message there says why. Building from the window gives the same workbook as 3.1 when given the same files and values.

---

## Part 4 · Peers (public FDIC data)

`peers pull` needs `api.fdic.gov`, which the bank's proxy may block. **The peer workbook is public data**: if the pull fails at the bank, build it on your own computer (commands in `docs/WHAT-IT-DOES.md`, "Peers") and bring `peers.xlsx` and its CSVs in with the kit.

☐ Peers pulled at the bank, or brought in.

---

## Part 5 · One internal measure (stays at the bank)

### 5.1 Pick a template and write it

```
py -m threshold_engine template list
py -m threshold_engine template write refreshed-score "%USERPROFILE%\refreshed-score.csv"
```

☐ It writes `refreshed-score.csv` and `refreshed-score.checklist.md` beside it.

### 5.2 Fill it

Follow the `.checklist.md`: answer every `[STATE: ...]` line at the top, then one line per quarter, `YYYY-MM-DD,value`, quarter-end dates, oldest first, at least nine quarters. Use Notepad, not Excel.

### 5.3 Check it

```
py -m threshold_engine template check refreshed-score "%USERPROFILE%\refreshed-score.csv"
```

☐ It says the file is OK, or lists every problem at once. Fix and run it again until it is OK.

### 5.4 Build the workbook

Every setting is yours; none has a default. For the refreshed score, lower is worse and it is not floored at zero. The starting values below are the card rehearsal's; change them in Your settings on the Assess tab after the build.

```
py -m threshold_engine workbook "%USERPROFILE%\refreshed-score.xlsx" --series "Refreshed score=%USERPROFILE%\refreshed-score.csv" --name "Refreshed credit score" --unit "score" --direction lower_is_worse --frequency quarterly --smoothing 1 --floor-at-zero no --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 9
```

☐ It writes the workbook, or refuses with a reason. `--min-history` is the quarters the backtest needs before it scores one; with a short file, lower it, and if it refuses, the message says what it needs.

☐ Opened in Excel, Thresholds' lines **fall** from 2 to 5 (lower is worse), and the Check column is blank or says why not.

---

## Part 6 · What to send back, and what must not leave

**Nothing from the bank's books leaves the bank**: no file, no value, no screenshot of an internal workbook, no line of `template check` output that quotes a value.

Send back, in words:

☐ Python version, and whether the add-on installed from the internet or from the kit.

☐ Part 3: every box ticked, or what differed.

☐ Part 5: whether the template check passed first time, and if not, which **kind** of problem (a date, a gap, a heading), not the line.

☐ Part 5: whether the workbook built; if the Check column refused, its words (they hold no values); anything that was unclear.

Screenshots of the **practice** workbook (Part 3) are fine: it is public data.
