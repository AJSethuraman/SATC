# Walkthrough defects — the desk test, 22 September 2026

Written for whoever fixes the product. The procedure the walk followed is
`PROCEDURE-desk-test.md` (delivered as one PDF under
`walkthrough/desk-test-2026-09-22/`); this is what the walk found on the way,
ranked by what each would cost a real person at a desk, not by how
interesting it is.

**Status, 22 September 2026, later the same day.** The firm: *"we need to
patch anything wrong prior to shipping. Especially math issues."* Defects 1
to 10 were fixed the same day, each pinned by a test in
`tests/test_walk_defects.py`, and the walk was run again on the patched
script; every step's screen was re-captured and the procedure re-issued.
Defect 11 stands, by the firm's own ruling. Each defect below ends with a
**Fixed** line saying what the screen says now. Later the same day the firm asked
for a picker instead of a file to fill in (*"no editing at the desk"*), then
chose a form in Excel over a prompt (*"Actually excel version is fine"*), and
Part E of the procedure became `--setup` writing `question.xlsx`, the picks
made from dropdowns, and the same command building; the keyboard picker stays
under `--ask`, and the fill-in path the walk found defect 1 on remains for
scripts. On the math: the walk
cross-checked every number on every screen against the counts and found no
arithmetic defect; the section at the end lists what was checked.

**The denominator.** At the time of the walk the project's suite was **99
tests, all passing**, with **9 of 9 mutations caught** and **48 of 48 checks
agreeing** in the exercise harness that runs the same script on eleven
made-up books. **None of the eleven defects below was caught by any of them.**
Every one is a thing a screen says, or does not say, to the person holding
it. Two are outright false sentences on the cover; the rest are screens that
show the person something they were not meant to read, or hide something
they were.

The walk was done as the person would do it: the emailed file saved into an
empty folder, each command typed, each screen read, the workbook opened tab
by tab, then a question file written for the extract and the pack built from
it. Thirty screens, all kept. Two deviations, stated here rather than hidden:
the terminal screens are rendered from the captured text, and the spreadsheet
screens come from LibreOffice, because Excel is not on this machine. The one
knob change (step 16) was made by a script writing the cell, standing in for
typing in it. Nothing was fixed during the walk; every screen is as the
product showed it.

## 1 · Fill in the question file exactly as the tool wrote it, and the cover says step 4 is "not built in this version"

**What I did.** Ran `--init` on the made-up extract, replaced the twenty
`[CONFIRM: …]` slots with answers and nothing else, validated (accepted),
built, opened the cover. Steps 22 to 30.

**What the screen said.** *"Survives or collapses (step 4): not built in this
version."* And beside it: *"the flag's odds ratio is 3.72 [2.84, 4.88] with
the controls (M1) and 3.72 [2.84, 4.88] with the confounders added (M2)"*.
The build's own summary printed no step-4 line at all and said nothing about
why.

**What was actually true.** Step 4 is built; it ran on the same extract four
screens earlier and said *survives* three times. The skeleton ships
`confounders: []`, with the examples in comments, and marks it with no
`[CONFIRM: …]`. So a person who does what the file's header tells them —
fill in every marked value — gets a pack that answers *"is that real or
something else in disguise?"* with a sentence saying the software cannot,
and a model line claiming confounders were added when none were named.

**Cost.** The highest of anything here. The question the pack exists to
answer goes unanswered, and the screen blames the product rather than the
file, so the person has no way to know the fix is theirs. `not_built` in
`wording.yaml` is the sentence reserved for a step that does not exist; it
is being used for a step that was given nothing to do.

**The fix.** Three parts. The skeleton marks `confounders` as a slot to fill
(or the validator says *"no confounders listed: step 4 will have nothing to
compare"* and the build's summary repeats it). The cover says what happened:
*"Survives or collapses (step 4): the question file lists nothing to compare
within."* And M2 says *"no confounders to add"* instead of quoting M1 again.

**Fixed.** All three. The skeleton's line now reads `confounders: "[CONFIRM:
what the effect might be hiding in: list columns as the examples below show,
or write [] for none]"` and the loader refuses the file until it is answered
(21 slots, not 20). A file that answers `[]` gets, on validate, *"note: no
confounders listed: step 4 will have nothing to compare within"*; on build,
*"step 4: nothing to compare within — the question file lists no
confounders"*; on the cover, *"Survives or collapses (step 4): the question
file lists nothing to compare within, so the flag was not tested against
anything. List confounders and build again."* and *"There is no M2: the
question file lists no confounders to add."*; and on the model tab, *"M2: M1
again — the question file lists no confounders to add"*. The sentence *"not
built in this version"* is left for the one thing it is true of, a rule type
the tool does not build.

## 2 · Every command dumps a block of builder-facing JSON onto the person's screen

**What I did.** Typed `python build_pack.py --synth demo`, then the build.
Steps 3, 5, 20, 22, 25, 28, 29.

**What the screen said.** After the plain line *"wrote demo/loans.csv,
config.yaml, planted.json (effect, seed 20260918, 40,000 loans)"*, fourteen
more lines: `{ "ok": true, "out": "demo", "seed": 20260918, …
"true_marginal_flag_odds_ratio": 4.317157028211426, "note": "true_marginal_
flag_odds_ratio is the odds ratio of flagged (ratio > 1) against unflagged
loans computed from the probabilities the generator drew with, …" }`. The
build printed its own block after its summary; the refusal at step 25
printed twenty lines of reasons and then the same twenty again as JSON.

**What was actually true.** That block is the machine-readable status the
tool writes for scripts; the plain summary above it is the part written for
a person. A person typing the command at a desk gets both, and the one
written for them is the shorter half of the screen.

**Cost.** The first thing the tool shows a new user is something they were
not meant to read. It looks like an error dump. A second-time user learns to
ignore the bottom half of every screen, which is exactly where a refusal's
detail also lands.

**The fix.** The bundle keeps the JSON off the screen unless asked (`--json`)
or writes it to a file beside the output. The plain summary is the screen.

**Fixed.** The bundle prints nothing to the screen but the summary; `--json`
on any command prints the status as well, and the harness and the tests ask
for it. The installed `pack` command is unchanged.

## 3 · The one screen that tells the person their next command names a command the desk does not have

**What I did.** Ran `--synth demo`, then `--init demo/loans.csv`. Steps 3
and 22.

**What the screen said.** After `--init`: *"then: pack validate
demo/question.yaml --data demo/loans.csv --asof YYYY-MM-DD"*. After
`--synth`: nothing about a next step.

**What was actually true.** `pack validate` is the installed tool's spelling.
The desk has `python build_pack.py --validate demo/loans.csv --config
demo/question.yaml`, which is a different order of words as well as a
different command. And the make-a-book step, whose whole point is the build
that follows, says nothing about it; the build command is the longest one in
the tool.

**Cost.** A person following the screen types a command that does not exist
on their machine, on the first screen that offered to help.

**The fix.** Every command that writes something says the next command,
spelled the way this script takes it.

**Fixed.** The bundle tells the tool its own file name, and every command
ends with a *then:* line in that spelling: after `--synth demo`, *"then:
python build_pack.py --data demo/loans.csv --asof 2026-06-30 --config
demo/config.yaml -o demo/pack.xlsx"*; after `--init`, *"then: fill in every
[CONFIRM: ...] value, and python build_pack.py --validate … --config …"*;
after a validate that passes, the build; after a build, *"then: open
demo/pack.xlsx in Excel; the cover's last line should say every formula
check agrees"*.

## 4 · Running the emailed file makes a folder appear beside it with a bank's name inside

**What I did.** Ran `--synth demo` and then looked at the folder. Step 4.

**What the screen said.** A new folder `analysis_pack_bundle_src`, holding
sixteen source files including `keybank_style.py`, and a folder `question`
holding `stated_income_vs_sales.yaml`.

**What was actually true.** The script unpacks itself beside itself on every
run and never tidies up. The style module carries the name of a bank the
tool is not for, and the carried question file is named after the pair of
fields the first pack was written for — on 20 September the firm said the
column names would never reach the builder, and here the builder's example
names sit on the desk of whoever runs the file.

**Cost.** Someone at another bank opens the folder that appeared and reads
another bank's name. Someone who was told the tool is not about any
particular field finds a file that says which field it was about.

**The fix.** Unpack to a temporary folder and remove it, or to a folder whose
name says what it is (`build_pack_internals`). Rename the style module for
what it does. Carry no question file at all: `--init` writes one, and a build
without `--config` should say so rather than silently use the carried one.

**Fixed, two of three.** The package unpacks into a temporary folder that is
removed when the command ends, so nothing appears beside the emailed file (a
test lists the folder after every command). The style module is
`workbook_style.py`, with no bank in its name or its first line. The carried
question file stays: it is what the first pack is built from when no
`--config` is given, and it never touches the desk now that nothing is
unpacked there.

## 5 · The labels that explain the numbers are cut off in exactly the rows the cover points to

**What I did.** Read the gradient, stratified and decomposition tabs. Steps
9, 11, 12.

**What the screen said.** Gradient, heading row: *"Multiple t above with
loans:lear of that bucket"*. Decomposition: *"Gap (pts)agged events"*.
Stratified, the four verdict rows under every block: *"Crude odds ratio,
whole population — ratio, lower"* followed by three numbers, and *"Pooled
odds ratio across bands (Mantel-Haenszel"* with no closing bracket.

**What was actually true.** Two headings share the space of one column
(*"Bucket above with loans"* and *"Clear of that bucket"*; *"Gap (pts)"* and
*"Share of flagged events"*), and the stratified labels are longer than
column A and are cut where column B's number starts. Excel does the same:
text stops at the next non-empty cell.

**Cost.** The three numbers on the crude row are ratio, lower, upper; the
label says *"ratio, lower"*. The person cannot name the third number from
the screen. These are the rows the cover's second line summarises.

**The fix.** Widen the label columns to the longest label the tool can
write, or wrap the heading rows. A test that measures every heading against
its column width would hold it.

**Fixed.** Every header row wraps, and the row grows to hold its longest
heading; the two long gradient headings got wider columns; the stratified
tab's label column is wide enough for *"Pooled odds ratio across bands
(Mantel-Haenszel) — ratio, lower, upper"*. The test walks every sheet and
fails on any header that needs more lines than its row has, or any bold
label in column A with a number beside it that is longer than the column.

## 6 · The chart's helper columns are shown as if they were results

**What I did.** Read the gradient tab to the right of the table. Step 9.

**What the screen said.** Five more columns after *"Clear of that bucket"*:
*"Bar up · Bar down · Last rate seen · Last lower · Last upper"*, holding
numbers like 0.0011 and 0.0579 with no explanation on the tab or in the
method notes. The stratified tab has the same to the right of every block.

**What was actually true.** They feed the chart's error bars and carry a
bucket's rate forward over an empty bucket (the adversarial fix of 20
September). They are plumbing.

**Cost.** Unlabelled numbers in a results table are read as results. A person
comparing *"Last upper 0.1110"* with *"Upper 11.10%"* sees the same number
in two formats and does not know why.

**The fix.** Move them under a heading that says *"chart helpers — not
results"*, grey them, or hide the columns; the chart reads them either way.

**Fixed.** The headings now read *"chart: bar up"*, *"chart: last rate
seen"*, and on the stratified tab *"working: P"* … *"chart: flagged bar
up"*, in a quieter italic face, and each tab's note ends *"Columns headed
chart: feed the chart … and are not results."* Not hidden: Excel leaves
hidden columns out of a chart by default, and the chart would have gone
blank.

## 7 · The build's summary uses two terms it never explains

**What the screen said.** *"step 6 M1: flag odds ratio 3.73 [2.84, 4.89],
211 events, 11 coefficients, EPP 19.2"* and *"formula check: not run here
(no engine); Excel verifies on open"*. Steps 5, 20, 29.

**What was actually true.** EPP is events per parameter, the thin-data
warning the model tab explains in a sentence (the tab spells it out; the
screen does not); "no engine" means the desk has no spreadsheet program that
recalculates formulas from Python, so Excel does that when the file is
opened.

**Cost.** The firm's standing rule for this project is plain words. A number
with a three-letter label beside it reads as a warning the person cannot act
on.

**The fix.** Say it: *"211 events over 11 coefficients: about 19 events per
coefficient, comfortably above the ten the model needs"*, and *"the formula
check runs when Excel opens the file"*.

**Fixed.** The build's summary now reads *"step 6 M1: flag odds ratio 3.73
[2.84, 4.89] on 211 events over 11 coefficients, about 19 events per
coefficient"* (with *"(thin: the model wants at least ten)"* when it is) and
*"formula check: runs when Excel opens the file (this machine has no
spreadsheet engine) — 1389 checks written to _check"*.

## 8 · The cover says the pack was run on the as-of date

**What the screen said.** *"synthetic_effect · run 2026-06-30 · as-of
2026-06-30"* on every cover and every tab's header band. Step 6. The walk
was run on 22 September 2026.

**What was actually true.** The tool reads no clock (so that the same inputs
give the same bytes), and when `--run-date` is not given it writes the as-of
date in its place. Nobody at a desk passes `--run-date`; the procedure does
not either.

**Cost.** The one date a reviewer uses to ask *"which run is this?"* is
wrong on every pack built the ordinary way, and wrong in a way that looks
right. *Never invent a value* is the first design principle; this value is
invented.

**The fix.** With no `--run-date`, write *"run date not given"* on the cover
and in the file's properties, or make the flag required and say so in the
usage lines at the top of the script.

**Fixed.** With no `--run-date` the cover and every tab's header band read
*"run date not given"*, `_provenance` says *"not given (pass --run-date to
stamp it); the file's own timestamp is the as-of date"*, the build's summary
says *"run date: not given, so the pack says so"*, and the script's usage
lines say the same. The file's properties carry the as-of date, because a
file must carry some date and that one is true. Same inputs still give the
same bytes.

## 9 · The first sentence on the cover uses the outcome's name as a verb, and the second line is missing a space

**What the screen said.** *"Loans where field_a divided by field_b is > 1:
do they event more often than loans where it is not …"* and *"Survives or
collapses (step 4), for event:size_band (edges) — survives; …"*. Steps 6, 21,
30.

**What was actually true.** The question sentence in `wording.yaml` reads
*"do they {outcome_label} more often"*, which works for a label like
*default* and breaks for any label that is a noun — *event*, *charge-off*,
*loss* — which is most of them. The second line joins the label to the first
confounder with a colon and no space.

**Cost.** It is the first sentence of the deliverable, on every pack. It
reads as broken English to the person the pack is written for.

**The fix.** *"do they go on to {outcome_label} more often"* does not work
either; the label needs to be a noun everywhere: *"Loans where … > 1: is
{outcome_label} more common among them than among loans where it is not,
and is that real or something else in disguise?"*. And *"for event: size_band
(edges)"*.

**Fixed.** Both sentences read as above. The missing space was the wording
filler stripping the template's trailing space; the cover puts it back in
both the live formula and its Python twin, and the test reads the formula.

## 10 · A knob's note says the step it drives is not in this version, and the outcome line shows a builder's word as if it were a column

**What the screen said.** `_config`, live knobs: *"Survives threshold 0.50 —
Step 4 (not in this version): the share of the crude effect that must remain
for 'survives'."* Rebuild knobs: *"Outcome — event (event_date)"*. Step 15.

**What was actually true.** Step 4 has been in this version since slice 5
and the knob does drive its word (the cover proved it at step 17). The
outcome's date column is `outcome_date`; `event_date` is the tool's name
for the *kind* of outcome, which the person never chose and cannot find in
their file.

**Cost.** A person deciding whether to touch the knob reads that it does
nothing. A person checking the outcome against their extract finds a column
that is not there.

**The fix.** Delete *"(not in this version)"*. Show the outcome as *"event,
from outcome_date"* and keep the kind out of it.

**Fixed.** The knob's note reads *"Step 4's word: the share of the crude
effect that must remain for 'survives'. 0.50 means half."* The outcome line
reads *"event, from outcome_date"*; a flag outcome names its column and cut,
a measure outcome its two columns and the as-of date.

## 11 · The question file the tool writes quotes three real values of every column

**What the screen said.** Step 23: every field line ends with a comment
such as *"# text, blank 0%, e.g. L000001, L000002, L000003"*.

**What was actually true.** The samples are what makes the file fillable
without opening the extract, and the firm declined a PII guard for this
project on 19 September. Recorded, not ranked above anything: on a real
extract with a name column, the file a person is most likely to email for
help carries three names.

**The fix, if the firm wants one.** Show samples only for columns that read
as numbers or dates; for text columns say *"text, blank 0%"* and stop.

**Not fixed**, by the firm's ruling of 18 September (*"stop worrying about
PII. It is all on Key's desk"*). Recorded so the ruling is a choice and not
an oversight.

## The math, checked by hand from the screens

The firm asked for math issues first. The walk found none; this is what was
checked, each from the numbers on the screens and nothing else:

- **Capture, 2019Q1:** 610 of 1,370 loans with `field_b` blank is 44.5%;
  1,370 − 64 − 610 leaves 696, and *both present* reads 728, so 32 loans are
  blank in both fields, which is what two independent blank rates of 4.7%
  and 44.5% would give (about 29). Share 728 of 1,370 is 53.1%.
- **Prevalence, 2019Q1:** 155 flagged of 728 with both present is 21.3%.
- **Gradient:** the multiples 0.59, 1.73, 2.88, 5.37, 10.07 are each
  bucket's rate over the base rate 0.527% (0.31 ÷ 0.527 = 0.59; 5.31 ÷ 0.527
  = 10.07). Five rates rising is *monotonic increasing*.
- **Stratified, crude odds ratio:** flagged events are 211 − 103 = 108 on
  5,575 flagged loans; unflagged 103 on 19,531. The odds ratio (108 ÷ 5,467)
  ÷ (103 ÷ 19,428) = 3.726, and its log-scale standard error √(1/108 + 1/5,467
  + 1/103 + 1/19,428) = 0.1386, so the interval is exp(1.3155 ± 1.96 ×
  0.1386) = [2.84, 4.89]. The screen reads 3.73 [2.84, 4.89]. The pooled
  ratio 3.74 against the crude 3.73 gives *share kept* log 3.74 ÷ log 3.73 =
  1.00.
- **Model:** M1's flag row 3.729 [2.842, 4.894] with standard error 0.1387
  agrees with the crude to the third decimal, as it should on this book,
  where the generator drew the controls independently of the flag. 211
  events over 11 coefficients is 19.2; M2's 21 coefficients are the 11 plus
  five size bands and five category levels; 211 ÷ 21 = 10.0.
- **Control:** 5,575 of 25,106 is 22.2%.
- **Known answers:** the planted odds ratio 4.32 lies inside M1's [2.84,
  4.89]; the book with nothing planted gives 0.82 [0.62, 1.08] with 1 inside
  and *no crude effect* three times.
- **Formula twins:** 1,389 of 1,389 live formulas recomputed by LibreOffice
  agreed with Python's numbers, and 590 of 590 on the pack built from the
  filled-in question file.

## What the walk did not find

The numbers agreed everywhere they could be compared: the build's summary,
the cover, the tabs and the planted answer (4.32, inside M1's 2.84 to 4.89).
The made-up book with nothing planted said *no crude effect* three times and
put 1 inside the model's interval. The knob change at step 16 was picked up
by the cover's last line through the workbook's own formulas, with no code
involved. The unfilled question file was refused naming all twenty slots.
The pack built from the filled file gave the same three lines as the pack
built from the tool's own question file, except for the one this list opens
with.
