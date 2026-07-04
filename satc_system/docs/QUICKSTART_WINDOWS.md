# SATC — Windows Quickstart

A start-to-finish guide for a preparer setting SATC up on a Windows PC. No
developer knowledge needed.

---

## 1. Install

**Option A — the app (no Python).** Download **`SATC.exe`** from the
[Releases](../../../releases) page. Double-click it.

- Windows SmartScreen may show *"Windows protected your PC."* This is expected for
  an unsigned app — click **More info → Run anyway**.
- Your antivirus may briefly quarantine it (a known false positive for this kind of
  packaged Python app). If so, restore it / add an exclusion for `SATC.exe`.

**Option B — from source.** On the repo page click **Code → Download ZIP**, unzip,
open the **`satc_system`** folder, and double-click **`install.bat`**. It creates a
private environment and installs everything. When it finishes, double-click
**`SATC.bat`** to start.

Either way, SATC opens in your web browser automatically. Leave the little black
window open while you use it; closing it stops SATC.

## 2. First run

- SATC opens at `http://127.0.0.1:5050`. It comes pre-loaded with **sample data** so
  you can look around. Every page shows a banner reminding you it's sample data.
- When you're ready to use it for real, go to the **Setup** screen and click
  **Start clean** to clear the sample clients. (This is the only way it clears —
  once cleared, it stays cleared.)

## 3. Check your setup

Open the **Setup** screen (or run `satc doctor` from a terminal). It gives a
plain-English readiness report — Python, optional OCR, data location — with a
"do this" fix next to anything that needs attention.

- To read **scanned or photographed** documents, install
  [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki). SATC finds
  it automatically at the default install location; if you put it elsewhere, set the
  `SATC_TESSERACT` environment variable to the full path of `tesseract.exe`.

## 4. Add your first client

Go to **Clients → New client**, enter the name and SSN/EIN, and save. The identity
(name + SSN) goes into the encrypted vault; the app works from a de-identified
record everywhere else.

## 5. Collect & track documents (the core loop)

1. Start an **engagement** for the client (pick the workflow — 1040, Schedule C,
   S-corp, etc.). SATC builds a document-request checklist for that engagement.
2. Send/print the client's **document request** or organizer from the engagement
   screen.
3. As documents come in, drop the client's files in a folder and point **Intake** at
   it. SATC classifies each file *by its content*, splits combined PDFs, and stages
   the figures it reads.
4. Review the staged values in **Staging** and confirm them (nothing is trusted
   until you confirm). Confirmed figures post to the client's record and can be
   exported to a Drake-ready workbook from **Export**.

## 6. Small services — withholding checkup

**Withholding** projects a household's full-year federal withholding from their
paystubs (typed, pasted, or uploaded) and recommends a W-4 line-4c adjustment.
Nothing is stored — it's a quick service you can run any time.

## Your Data & Security

**Where it lives:** `%USERPROFILE%\.satc\data` when you run `SATC.exe`, or
`satc_system\build\data\` when you run from source. **These are two separate
stores** — clients you add in one mode won't appear in the other. Pick one mode and
stick with it.

**Encryption:** the identity vault (`satc_vault.db`) encrypts names and SSNs/EINs at
rest with AES-256. On Windows the encryption key is sealed to your Windows user
account, so a copied vault file can't be read on another machine or by another user.

**Backups & moving machines:** back up by **copying the whole data folder** (both
the `.db` files and `vault.key`). To move machines, copy the folder — but note the
DPAPI-sealed key only unseals on the original Windows account, so for a machine move,
keep BitLocker on and treat the copy as sensitive.

**Do:** keep **BitLocker** (full-disk encryption) on; keep the data folder out of
OneDrive/Dropbox/shared drives unless you intend it. **Don't:** email the `.db`
files; put the data folder on a shared drive.

**Uninstalling** the app does **not** delete your data folder — delete it by hand if
you want it gone (`satc reset` wipes the databases and asks you to confirm first).

**Your obligations:** as a paid preparer holding client SSNs you're subject to the
**FTC Safeguards Rule** and IRS Pub 4557 — you need a written information security
plan (WISP). SATC's encryption + local-only design supports this, but the WISP is
yours to maintain. IRS **Pub 5708** is a fill-in-the-blank WISP template.

## Using SATC with an AI assistant (optional)

SATC can be driven from Claude Desktop / Cowork in plain English. By default the
agent is **read-only** (look things up, run withholding) and cannot change client
records. Setup is a one-click extension install — see
**[Using SATC with an agent](MCP.md)**.

## Troubleshooting

| Symptom | Fix |
|---|---|
| SmartScreen "Windows protected your PC" | **More info → Run anyway** (expected for an unsigned app). |
| Antivirus quarantines `SATC.exe` | Restore / add an exclusion; it's a known false positive for packaged Python apps. |
| `install.bat`: "Python is not installed" | Install Python from [python.org](https://www.python.org/downloads/) with **Add to PATH** checked, then re-run. |
| `install.bat` ends without "Installed" | The pip step failed (check the messages / your internet). Re-run after fixing. |
| `'satc' is not recognized` after starting `SATC.bat` | The install didn't finish — re-run `install.bat`. |
| Scanned PDF won't read / "cannot find the file" | Install Tesseract (see step 3); SATC auto-detects it, or set `SATC_TESSERACT`. |
| "Setup" says Tesseract not found but it's installed | It's not at the default path — set `SATC_TESSERACT` to your `tesseract.exe`. |
| Browser didn't open | Open `http://127.0.0.1:5050` yourself (or the port shown in the black window). |
| Port already in use | SATC auto-picks a free port; use the URL printed in the black window, or set `SATC_PORT`. |
| My clients disappeared after switching to the .exe | You're now on the `~/.satc/data` store, not the source `build/data` one — see *Where it lives* above. |
