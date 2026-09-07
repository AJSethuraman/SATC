# Real blank IRS forms — the part that actually proves something

Two ways to fill this folder. Either is fine; you only need one.

## One paste, from anywhere

Open PowerShell and paste this. It does not matter where you are standing, and
you do not need to find the repo first — it finds itself.

```powershell
$d=Get-ChildItem $HOME -Recurse -Depth 6 -Directory -Filter blanks -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'fetch.ps1') } | Select-Object -First 1; if (-not $d) { $d = New-Item -ItemType Directory -Force -Path "$HOME\Downloads\satc-irs-blanks"; Write-Host "SATC repo not found under $HOME - saving to $($d.FullName) instead." -ForegroundColor Yellow }; $ProgressPreference='SilentlyContinue'; try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12 } catch {}; $ok=0; 'fw2','f1099int','f1099div','f1099b','f1099nec','f1099msc','f1099r','f1099g','f1098','f1098t','f1095a','f1040','f1040sc','f1065sk1','f1120ssk' | ForEach-Object { $p=Join-Path $d.FullName "$_.pdf"; try { Invoke-WebRequest "https://www.irs.gov/pub/irs-pdf/$_.pdf" -OutFile $p -TimeoutSec 45 -UseBasicParsing } catch {}; if ((Test-Path $p) -and (Get-Item $p).Length -gt 0) { $ok++; Write-Host "  $_ ok" } else { Write-Host "  $_ COULD NOT FETCH" -ForegroundColor Red } }; Write-Host "`n  $ok of 15 saved in $($d.FullName)"
```

It searches your user folder for `corpus\blanks` and puts the forms straight in.
**If it cannot find the repo it does not fail** — it saves them to
`Downloads\satc-irs-blanks` and says so, so the paste always ends with fifteen
PDFs somewhere you can find. No `-ExecutionPolicy`, no `cd`, no repo file needed.

Each form prints `ok` or `COULD NOT FETCH`, then a count and the folder used.

**Two earlier versions of this instruction were wrong**, which is why this one is
built the way it is. The first read `bash fetch.sh` — the firm does not use Git
Bash. The second read `.\fetch.ps1`, a bare relative path that produced *"The
argument '.\fetch.ps1' to the -File parameter does not exist"* unless you were
already standing in this exact directory. Both were instructions written to an
assumption about where the reader was standing. This one makes no assumption.

## The script, if you would rather

`fetch.ps1` here does the same thing, once you are in this folder. `fetch.sh` is
its bash twin. A test holds all three lists of forms together — the two scripts
and the links table below — so they cannot drift apart as forms are added.

The `-ExecutionPolicy Bypass` is there because an unsigned `.ps1` will not run on
a default Windows install, and that refusal reads like the script being broken
rather than Windows doing its job. Nothing here needs admin.

**I could not run this one.** There is no PowerShell in the environment it was
written in, so unlike the bash twin below it has never been executed. The
gotchas it does handle are the ones that bite on Windows PowerShell 5.1: the
progress bar that makes downloads ten times slower, TLS 1.0 being the default
where irs.gov wants 1.2, and `Invoke-WebRequest` throwing on a 404 rather than
returning it. If it still misbehaves, that is why — tell me and it gets fixed
rather than defended.

## Or bash, if you ever want it

```
bash satc_system/corpus/blanks/fetch.sh
```

Same forms, same behaviour. A test holds the two lists together, so they cannot
drift apart as forms are added.

## Or click fifteen links

Same files, if you would rather not run a script. Save each into this folder
keeping its filename.

| Form | What it is | Link |
|---|---|---|
| W-2 | Wage and Tax Statement | https://www.irs.gov/pub/irs-pdf/fw2.pdf |
| 1099-INT | Interest Income | https://www.irs.gov/pub/irs-pdf/f1099int.pdf |
| 1099-DIV | Dividends and Distributions | https://www.irs.gov/pub/irs-pdf/f1099div.pdf |
| 1099-B | Proceeds From Broker Transactions | https://www.irs.gov/pub/irs-pdf/f1099b.pdf |
| 1099-NEC | Nonemployee Compensation | https://www.irs.gov/pub/irs-pdf/f1099nec.pdf |
| 1099-MISC | Miscellaneous Information | https://www.irs.gov/pub/irs-pdf/f1099msc.pdf |
| 1099-R | Distributions From Pensions | https://www.irs.gov/pub/irs-pdf/f1099r.pdf |
| 1099-G | Certain Government Payments | https://www.irs.gov/pub/irs-pdf/f1099g.pdf |
| 1098 | Mortgage Interest Statement | https://www.irs.gov/pub/irs-pdf/f1098.pdf |
| 1098-T | Tuition Statement | https://www.irs.gov/pub/irs-pdf/f1098t.pdf |
| 1095-A | Health Insurance Marketplace Statement | https://www.irs.gov/pub/irs-pdf/f1095a.pdf |
| 1040 | U.S. Individual Income Tax Return | https://www.irs.gov/pub/irs-pdf/f1040.pdf |
| Schedule C | Profit or Loss From Business | https://www.irs.gov/pub/irs-pdf/f1040sc.pdf |
| K-1 (1065) | Partner's Share | https://www.irs.gov/pub/irs-pdf/f1065sk1.pdf |
| K-1 (1120-S) | Shareholder's Share | https://www.irs.gov/pub/irs-pdf/f1120ssk.pdf |

## Measured, 31 August 2026 — 13 of 15

The firm ran the one-liner. It worked, found no local repo (so it saved to
`Downloads\satc-irs-blanks`, as designed), and fetched **13 of 15**. Two URLs are
wrong:

| Form | Guessed | What to use instead |
|---|---|---|
| 1099-B | `f1099b.pdf` | https://www.irs.gov/forms-pubs/about-form-1099-b |
| K-1 (1120-S) | `f1120ssk.pdf` | https://www.irs.gov/forms-pubs/about-schedule-k-1-form-1120-s |

**Use the "About" pages, not another guessed filename.** Each one links the
current PDF, so it survives the IRS renaming a file — which is exactly what went
wrong here. I still cannot reach irs.gov to confirm a replacement filename, and
guessing a second time after guessing wrong once is not a method.

Save each as `f1099b.pdf` and `f1120ssk.pdf` so the corpus finds them under the
names it expects.

**Thirteen is already enough to be useful.** The corpus reads whatever is in this
folder; it does not require all fifteen. W-2, the 1099 series bar the B, 1098,
1098-T, 1095-A, 1040, Schedule C and the 1065 K-1 are the forms most client
packets are made of.

## Getting them into the repo

The one-liner saved them to `Downloads` because there is no clone under
`C:\Users\AJ`. To put them where the corpus reads them, in a browser:

1. Open `satc_system/corpus/blanks` on GitHub.
2. **Add file → Upload files.**
3. Drag all thirteen in at once and commit.

No clone, no git, one drag.

## ⚠ What I could not test

`irs.gov` is blocked from the environment I build in — 403 on CONNECT. So the
script has never been run end to end, and **I have not opened a single one of
those links.** The URL pattern is the IRS's long-standing one and I am confident
in it, but a form revised since could have moved, and I would rather say that
than have you find out.

I did prove the *failure* path works, by pointing the same script at an
unreachable host: it named all fifteen and told you what to do. So a moved form
is visible, not silent.

## Why this folder matters more than the rest of the corpus

Everything else in the corpus is text this repository generated. Generated text
proves almost nothing — a page reading *"Form W-2 / 1 Wages, tips, other
compensation"* classifies as a W-2 and always will.

A real blank carries the **real AcroForm field names**, the **real layout**, and
the **real text-layer reading order**. Those are the three things that decide the
answer, and the three things that were wrong in the field while the synthetic
tests stayed green. Your words: *"the synthetic tests weren't doing it — it was
miscategorising W-2s and stuff."*

## No client data. Ever.

These are public IRS documents and committing them is fine. Nothing a client
sent belongs in this folder or anywhere else in this repository — when a real
document fails, add a synthetic reconstruction of *what made it fail*, never the
document.
