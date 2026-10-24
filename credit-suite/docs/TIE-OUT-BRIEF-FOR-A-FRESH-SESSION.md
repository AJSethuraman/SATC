# Tie this out. Form your own view first.

**You are the second pair of eyes, and the first pair built the thing.**

A session assembled this feed between 4 and 7 September 2026 and then audited
its own work — which is the preparer verifying themselves, and the reason you
exist. That session found five real faults. **Three of them were sentences it
had written itself**, which is exactly the class of thing a self-review is worst
at and a stranger is best at.

So the order below is deliberate. Do not skip to the findings.

---

## 1 · Read only this much, then decide what to attack

- `docs/tie-out/SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-2026-09-07.pdf` —
  what the feed claims about itself
- `verified-data/SATC-verified-credit-data.xlsx` — the delivered workbook
- `verified-data/*.csv` — the same data, checkable with a script

That is the deliverable. It is what a reader gets, and it is what you are
auditing.

**Now write down what you are going to check, and why, before reading anything
else.** Put it in `docs/tie-out/SECOND-PASS-<date>.md`. Not a plan of how you
will check — a list of the claims you doubt. The value of this pass is entirely
in the targets you pick that the first session did not.

Some ground it has NOT covered, offered as a floor rather than a list to work
through — your own targets matter more than these:

- The **macro side is the weak half** and the covering document says so. 11,237
  observations have no obtainable source, and the sources that were checked
  were checked once, by the session that chose them.
- **Nothing was checked by a second person, anywhere.** Every "verified" in
  this feed traces back to one session's judgement about what counts.
- Four of the eight FDIC-computed ratios (`ROAQ`, `NIMY`, `NTLNLSQR`, `EEFFR`)
  are checked against nothing at all.
- The **177 "not on this filing" rows** were taken on the verifier's word.
- The exhibits photograph the row a citation names. Nobody has asked whether the
  citation names the right row for a field whose *meaning* is contested.

---

## 2 · Then read what the first session found, and say where you differ

`BACKLOG.md`, the entries dated 7 September 2026. They carry five provenance
faults, what each one caused, and the three "not checked" items it measured
afterwards.

Say plainly: what you found that it did not, what it found that you would not
have, and anything you think it got wrong. **Disagreement is the output.** If
you agree with everything, say that too — but say it after looking, not
instead of.

---

## 3 · Running it

Everything below is copy-pastable and the paths are real.

Install what it needs:

```
cd C:\Users\ajish\SATC-cs\credit-suite && python -m pip install -e ".[test]" pymupdf
```

The tests. Pytest's default temp folder is not writable in some sandboxes, so
point it somewhere you own:

```
cd C:\Users\ajish\SATC-cs\credit-suite && python -m pytest -q --basetemp=C:\Users\ajish\SATC-evidence\pytest-tmp
```

Build the feed and tie it out in one go — build, three checks, then the
workbook, with a failed stage stopping the run. About a minute:

```
cd C:\Users\ajish\SATC-cs\credit-suite && python tools\tieout\run_and_tie_out.py
```

The tie-out on its own, against a different random sample each time:

```
cd C:\Users\ajish\SATC-cs\credit-suite && python tools\tieout\tieout_on_run.py
```

---

## 4 · Where things are

| | |
|---|---|
| The working data | `C:\Users\ajish\SATC-evidence\credit-suite-workdir` — 760 filed Call Reports, the strips, the intermediates. Its own README says which half cannot be rebuilt. |
| The exhibits | `C:\Users\ajish\SATC-evidence\banks-10y-2026-09-05` — 209 PDFs, one per bank per year |
| The path setting | `src/credit_suite/workdir.py`. `$CREDIT_SUITE_WORKDIR` overrides it for one run. |
| The one comparison | `src/credit_suite/sources/fdic/tieout.py` — every check calls this; nothing reimplements it |
| The peer group | `config/peers.json` |

**A term you will meet everywhere.** An **MDRM code** — `RCFD2170`, `RCONJ454` —
is the Federal Reserve's permanent identifier for one line on one schedule of
the Call Report. The four-letter prefix says which column (`RCFD` consolidated,
`RCON` domestic, `RIAD` income statement); the four characters after it are the
line. Quote one to a bank's finance team and they know exactly which number you
mean. A **facsimile** is the FFIEC's exact copy of the filled-in form — the
document itself, not a database rendered to look like one.

---

## 5 · Two things that will mislead you if nobody says them

**The `ours` side must come out of the delivered file.** Several checks here
read an intermediate instead, and one hop — from what was verified to what the
firm opens — was described in a docstring for weeks and never executed. It is
executed now (`prove_delivered_is_what_was_checked.py`, 143,201 of 143,201
identical), but the shape of that mistake is everywhere in this codebase's
history and it is the one worth watching for.

**A value can be right and its citation wrong**, and only following the citation
to the page shows it. Nine values once matched to within exactly one thousand
dollars across three unrelated banks because the citation pointed at the bank's
own single-line total while the FDIC published the sum of two separately
rounded halves. Both numbers were correct as published.

---

## 6 · What you are not being asked to do

Not to make it green. The feed carries one difference the first session could
not explain, twenty-four series with no obtainable source, and four ratios
checked against nothing. **Those are the honest state, not a backlog.** A second
pass that quietly closes them is worth less than one that finds a sixth thing
wrong.
