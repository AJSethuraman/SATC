# Real blank IRS forms — the part that actually proves something

Two ways to fill this folder. Either is fine; you only need one.

## The easy way — PowerShell

**From the root of the SATC repo** (the folder with `client-documents`,
`satc_system` and `website` in it):

```
powershell -ExecutionPolicy Bypass -File .\satc_system\corpus\blanks\fetch.ps1
```

The path matters and the working directory does not: the script downloads into
its own folder wherever you run it from. An earlier version of this line read
`.\fetch.ps1`, which only worked if you were already standing in this directory —
and produced *"The argument '.\fetch.ps1' to the -File parameter does not exist"*
if you were anywhere else. That was a bad instruction, not a broken script.

Fifteen forms, one command. It names anything it could not fetch instead of
failing quietly, so a form the IRS has moved is something you can see.

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
| K-1 (1120-S) | Shareholder's Share | https://www.irs.gov/pub/irs-pdf/f1120ssk1.pdf |

## ⚠ I could not test any of this

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
