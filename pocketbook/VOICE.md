# PocketBook voice

How everything PocketBook writes should read: tab headings and notes, the Glossary, the audit workbook, the
launcher's messages, refusals, and the docs.

## Why this file exists

The firm, 3 Oct 2026, on the audit workbook's line *"Loans — Every loan whose band and segment are the ones
picked."*:

> *"it just sounds weird. it does not sound like something a human would type. maybe it isn't perfect but I'd want
> this explained like: Loans — Records from the population in the applicable band and/or category."*

And:

> *"it just surprises me that you write like this when the copilot at work is generally better at writing
> 'professionally' in the sense that it sounds reasonably human and i don't generally need to edit it for tone as
> so much as content."*

The cause: the repo's copy rules (root `CLAUDE.md`, *Client-facing copy*, and `website/TENETS.md`) were written for
tax clients reading the public website. They ban any term a first-time reader would look up, and ask for short,
literal sentences. Applied to a tool for bank analysts, they strip out the profession's normal vocabulary and
produce sentences that read like a specification.

## Who reads PocketBook

- **Credit risk analysts**, who run it and work from the tabs.
- **Credit risk managers**, who read the results and the summary.
- **Model validators**, who check the method and the statistics.
- **Internal auditors**, who trace a figure back to the loans.

All of them are professionals. They know what a population, a charge-off, a vintage and a basis point are, and they
expect to see those words.

## The register

Write as a competent analyst writes a workpaper or an internal memo: conventional business English, in full
sentences, using the industry's vocabulary. Terms such as *population, records, applicable, excluded, reconciles,
charge-off, utilization, vintage, basis points, percentage points, denominator, threshold* are expected, not
avoided.

The test is simple: it should read as though a person typed it, and that person knows the subject.

## What applies, and what does not

**Does not apply to PocketBook:** root `CLAUDE.md`'s client-facing copy rules and `website/TENETS.md`. In
particular, there is no ban on terms a reader might look up, and no rule to "say the thing" in everyday words.

**Still applies:**

- **No filler.** A sentence that tells the reader nothing comes out.
- **No self-protective sentences.** Say what the figure is; don't hedge to protect the tool.
- **`pocketbook/TENETS.md` binds.** T1: the method is described once, in one place, never beside every row. T2: a
  check figure appears only where it can fail.
- **A test that already enforces a rule on a surface still holds there.** The Glossary's test keeps the
  contract-word list and a 28-word sentence cap; meet them in that tab.

## Patterns

Each pair is a before and after. The first is the firm's own.

### 1. Define with a noun phrase, not "Every X whose Y…"

- Before: *Loans — Every loan whose band and segment are the ones picked.*
- The firm's version: *Loans — Records from the population in the applicable band and/or category.*
- As written in the audit workbook: *Records from the population in the selected band and segment.*

More:

- Before: *Loans whose outcome is 0 or 1. Any other is left out of the rate.*
- After: *Loans in the pocket with an outcome of 0 or 1. Loans with any other value are excluded from the rate.*

### 2. Full sentences, not clipped fragments or telegraphic colons

- Before: *Ties?: ✓ when they agree to a billionth of the figure.*
- After: *Ties? shows ✓ when the two agree to within one billionth of the figure.*

- Before: *Set at 30: a pocket of 20 loans is grey on Grids.*
- After: *With the minimum set at 30, a pocket of 20 loans is grey on Grids.*

A colon is fine after a label in a list (*Run stamp — identifies the input file…*) and before a formula. It is not a
substitute for a verb.

### 3. Normal articles and connectives

- Before: *The rest's GCOs ÷ its booked.*
- After: *GCOs for the rest of the book as a share of its booked dollars.*

- Before: *Nothing here changes the main workbook. Change what you like.*
- After: *This workbook is independent of the main workbook, so it can be edited freely without affecting it.*

### 4. Use the industry's term, not an invented one

- Before: *the bottom of the GCO rate* → After: *the denominator of the GCO rate*
- Before: *Shuffles as big, either way* → After: *shuffles with a gap at least as large, in either direction*
- Before: *the real labelling* → After: *the actual assignment*
- Before: *under the bar on Control* → After: *below the threshold on Control*
- Before: *filter the words out of the GCO column* → After: *exclude text entries from the GCO column*

Where the workbook has named a thing (*Dollars above share*, *× book*, *Judged against*, *GCOs ($)*, *RANR*), keep
the name. Those are the firm's terms and the tabs use them; this rule is about the words around them.

### 5. No stacked qualifiers

- Before: *Booked dollars of the loans that have both a booked amount and a GCO amount: the bottom of the GCO rate.*
- After: *Booked dollars for loans in the pocket that have both a booked amount and a GCO amount. This is the
  denominator of the GCO rate.*

Split a sentence when a second clause qualifies the first. One idea per sentence.

### 6. Numbers formatted as a report would

- Thousands separated: *185,000 loans*, *$1,780,000*.
- Rates as percentages to the precision the tab shows: *2.20%*.
- Gaps between rates in percentage points, written *-3.00 pts* on the tabs and "percentage points" in prose. Basis
  points where the analyst would say them.
- Multiples with the sign the tabs use: *1.24×*.
- Dollars per $100 booked where the firm uses it: *the book keeps $4.45 per $100 booked*.

### 7. Instructions phrased as a person would give them

- Before: *On Loans, filter In this pocket to 1. The status bar's Count, on the loan column.*
- After: *Filter the Loans sheet to the selected pocket (In this pocket = 1); the status bar shows the count of the
  loan number column.*

- Before: *Divide on a calculator.*
- After: *Divide the pocket's GCO rate by the book's.*

Say what to do, to what, and where to read the answer.

## Spelling

Match what the tabs already use (*grey*, *coloured*) until the firm says otherwise. Sheet and column names are
written exactly as they appear in the workbook.

## How to check a sentence

1. **Would an analyst type this in an email to their manager?** If it would read oddly in an email, it reads oddly
   in a cell.
2. **Does it use the term the industry uses?** Not a coinage, not a paraphrase of a term the reader already knows.
3. **Is it a complete sentence**, with a subject, a verb, articles and connectives? Labels and list headings are the
   exception, not the norm.
4. **Does it say one thing?** If it qualifies itself twice, split it.
5. **Does it carry information?** If it would be true of any pocket, any Run, or any book, it is filler or method,
   and method belongs in the one note (T1).
