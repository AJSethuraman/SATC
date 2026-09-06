# Schedule C profit and loss — what was decided, and what I would argue with

Written 6 September 2026, alongside the build. This is the memo, not the manual;
`README.md` says how to run it and `YEAR-UPDATE.md` is the January job.

---

## 1 · The premise, questioned

**It mostly holds. One part of it does not.**

### What is right

The portfolio-of-utilities case you were pitched is bad economics for a solo
practice, and your three reasons are the correct three. I would add a fourth: a
tool farm has no defensible position. Twenty thin calculators can each be
rebuilt in an afternoon by anybody, so the only moat is spend. One tool that
carries a licensed name and is maintained against a form that changes every year
is a different asset — the maintenance is the moat, and it is a moat you are
already standing in because you do this work anyway.

The intent argument is right too. A person who fills in twenty-eight expense
lines for their own business has told you more about themselves than any ad
click ever will.

### What is wrong

**The tool will not rank, and the plan quietly assumes it will.**

I looked at who is already there. Two separate markets:

- **Generic P&L generators** — [Novo](https://www.novo.co/small-business-resources/profit-loss-statement),
  [FounderPath](https://founderpath.com/free-tools/profit-and-loss-statement-template),
  [Jupid](https://jupid.com/profit-and-loss-template), Protoolio, Get Figured.
  Free, no signup, PDF and Excel. FounderPath already advertises browser-only
  generation with nothing uploaded. **This half is a commodity and your
  differentiator is already someone else's marketing copy.**
- **Schedule C-line-organised tools** — this exists, but as an Excel download
  ([Ardent Seller](https://www.ardentseller.app/resources/schedule-c-tax-expense-tracker/),
  [Senter CPA](https://sentercpa.com/new-schedule-c-excel-worksheet-for-2025/))
  or bundled inside a paid expense tracker
  ([DeductFlow](https://deductflow.com/guides/schedule-c-expense-tracker-str)).
  **A free, no-signup, in-browser one is a real gap.**

But look at what actually ranks for the audience: line-by-line *guides*
([sdocpa.com](https://www.sdocpa.com/schedule-c-instructions/),
[Taxstra](https://taxstra.com/resources/schedule-c-explained/),
[Jupid](https://jupid.com/blog/schedule-c-instructions-guide-2026),
[Outsourcing Processing](https://outsourcingprocessing.com/full-guide-irs-schedule-c-lines-explained-what-goes-where/)).
The demand is for *what goes on line 24b*, not for *a Schedule C P&L tool*. Nobody
searches for a thing they do not know exists.

**So: the tool is the conversion asset, not the traffic asset.** Shipping it
alone and waiting is the failure mode — six months of nothing, and the wrong
conclusion drawn ("the idea does not work") when what failed was distribution.

### What I would do instead of variants

Before Etsy, eBay, DoorDash and reseller versions, do these two, in this order:

1. **Write one long line-by-line Schedule C page** on satcllp.com, in your voice,
   that answers *what goes where* — and put the tool at the top and bottom of it.
   That page is the thing that ranks. The tool is what converts the reader. One
   page, written once a year, is a smaller maintenance burden than five variants
   and has a far better chance of being found.
2. **Add a second door for the higher-intent query.** The sharpest wedge into
   this audience is not "schedule c calculator" — it is *"my accountant asked me
   for a profit and loss statement and I do not have one."* That person has
   already decided to use a preparer, is mildly embarrassed, and wants to hand
   over something that looks right. Same tool, different heading and first
   paragraph, at its own URL. It costs a page, not a project.

The Etsy and DoorDash variants only make sense after the base has produced at
least one enquiry you can trace. Building five of them first is the tool-farm
mistake wearing different clothes.

### The number, honestly

"Schedule C profit and loss" style queries are low hundreds a month across all
phrasings, and you will not have all of them. Say 30–80 visits a month once the
guide page is indexed, an enquiry rate somewhere between half a percent and two
percent, and you are looking at **a handful of enquiries a year.** One converted
1040 with a Schedule C pays for the whole thing several times over. That is the
actual case for building it, and it is a good one — but it is a case that needs
you to be patient and to have instrumented it, which is section 6.

---

## 2 · The domain model: compute, collect, or refuse

The line that had to hold: **the tool organises figures the filer already has;
it does not decide what is deductible.** Here is where every line landed and why.

### The lines it computes

Pure arithmetic on the form's own instructions, with no judgement in it at all:

| Line | What it does |
|---|---|
| 3 | line 1 − line 2 |
| 4 | copied from line 42 |
| 5 | line 3 − line 4 |
| 7 | line 5 + line 6 |
| 27a or 27b | copied from line 48 — **which one depends on the year, see below** |
| 28 | the twenty-four expense lines added |
| 29 | line 7 − line 28 |
| 31 | line 29 − line 30 |
| 40 | lines 35 to 39 added |
| 42 | line 40 − line 41 |
| 48 | the other-expense rows added |

### The lines it only collects

Everything on Part II. The filer types the figure they are claiming. There is no
category guessing, no "is this advertising or office expense", no suggestion.

### The three calculators, and why only three

A calculator earns its place only if it is (a) arithmetic on a published IRS
figure and (b) something the filer has already chosen to use.

- **Standard mileage.** Business miles × the year's rate. The rate is held in
  tenths of a cent so 65.5 is an integer, and it carries its IRS notice number
  onto the screen and into the PDF. It says, before you use it, that it is only
  for the standard mileage method.
- **Simplified home office.** $5 a square foot, capped at 300 feet. It does *not*
  apply the gross income limit itself — the engine does that, because the limit
  depends on line 29 and the calculator has never seen line 29.
- **Half of meals.** Because line 24b says *"Deductible meals"*, and people type
  what they spent. The 80% hours-of-service exception travels with the answer
  every time it is shown, so nobody uses it who should not.

### The four refusals, printed on the page and in the document

| Line | Refused because |
|---|---|
| 9 | Actual vehicle costs need the vehicle's cost, its business-use share and prior depreciation. |
| 13 | Depreciation and §179 need per-asset basis, placed-in-service dates, conventions and prior years. |
| 30 | The Form 8829 method needs mortgage or rent, taxes, insurance, utilities and floor area. |
| 32 | Whether a loss is usable this year depends on at-risk amounts and income outside this form. |

Each refusal names the line, says why, and says what to do instead. They are
printed only when they bear on the return in front of you — four paragraphs of
refusals on a one-line return is noise, and noise is how a real warning gets
skipped.

### Also deliberately absent

Passive activity limits, excess business loss under §461(l), hobby loss, QBI,
and **self-employment tax**.

Self-employment tax is the one worth arguing about. It is deterministic, it is
the first thing a sole trader actually wants to know, and it would make the tool
markedly more useful. I left it out for one reason: getting it right needs their
W-2 wages to apply the Social Security wage base, and a figure that is right for
most people and quietly wrong for anyone with a day job is worse than no figure
on a page with your name on it.

**I argued it was the strongest v2 candidate. On 6 September 2026 the firm
overruled that, and the reason is worth more than the recommendation was:**

> *"It is not my concern to fill out a form for them. This is already helpful
> when free and I would expect them to pay us if they wanted to take it to that
> step themselves through our own work."*

So it is not a gap waiting to be filled in a later version. **The refusal is
the offer.** The free tool sorts a person's own figures; it does not carry them
to the answer they would otherwise pay for. Where the next step is the firm's
work, the tool stops and says so — and saying so is the handoff, not a
shortcoming in it. That reasoning is not about this tool: it applies to
anything free the practice publishes, which is why it went to `bassy` as a
candidate conviction rather than being filed here as a scoping note.

### The thing that would have been a silent bug

For tax years 2023 and 2024, Schedule C line 27a is *"Other expenses (from line
48)"* and 27b is the energy efficient commercial buildings deduction. **For 2025
the IRS swapped them.** Line 48's own wording changes with it: "Enter here and on
line 27a" becomes "line 27b".

A tool that hardcodes either arrangement puts a real figure on the wrong line of
a real return for half the years it supports. So the slot is a per-year
parameter, the labels are extracted from the official PDF for each year rather
than typed from memory (`evidence/`), and `tests/lines.test.mjs` re-reads that
evidence and reports its denominator: **52 of 55 labels verified word-for-word
against the IRS PDF per year, 3 reworded** (44a/b/c, which the form asks as one
sentence with three boxes).

I mutation-tested that check three ways before trusting it.

---

## 3 · Your open questions, answered

### Persist a draft locally?

**Yes, but off by default, and say why in the same breath.**

A tick-box that reads *"Keep what I have typed on this device"*, unticked, with
the sentence *"Do not tick it on a shared or library computer"* immediately
under it, and a "Clear everything" button beside it. Nothing is written to the
browser until it is ticked — the browser walk asserts `localStorage.length === 0`
before and `1` after, and asserts clearing really clears.

The alternative — remembering by default with a warning — trades a real risk
against a small convenience, on a page whose entire pitch is that it is careful
with your figures. Not worth it.

### Gross figures with statutory limits, or already-limited figures?

**Already-limited. You lean safer and you are right, and the form agrees with
you.**

This is not a close call once you read the form's own wording. Line 24b is
*"Deductible meals"*, not "meals". Line 9 is *"Car and truck expenses"* meaning
the deduction, not what the vehicle cost to run. Line 30 is *"Expenses for
business use of your home"* meaning the amount from Form 8829 or the simplified
worksheet. **Schedule C is already a limited-figures form.** Building a
gross-figures tool would mean building a different form and hoping it maps.

The friendliness that would have been lost is recovered by the three
calculators, each opt-in and each showing its working. That is the whole
difference between "we halved your meals" and "here is half of what you spent,
and here is when half is the wrong number".

### Clean P&L, Schedule C worksheet, or both?

**Both, from one computation, because they have two readers.**

- The **profit and loss statement** reads like a statement. A bank, a landlord
  or a lender can look at it. Line numbers are there but small and to one side.
- The **Schedule C worksheet** is the form's order and the form's wording, every
  line including the empty ones, plus the Part IV vehicle answers and the Part V
  list. A preparer copies figures off it without having to work out where
  anything goes.

They come from one `compute()`, so they cannot disagree — and a test asserts the
net profit appears in both. The PDF can be either or both; the spreadsheet
always carries both plus a detail sheet.

Blank stays blank on both. A line nobody filled in prints nothing, never `0.00`,
because on a worksheet those two things mean different things to whoever reads it
next.

### How should the handoff to SATC work?

**After the download, never before it, and never as a gate.**

There are exactly three mentions:

1. One quiet line in the summary panel: *"Would rather not do this again next
   year?"*
2. A panel that is `hidden` until a file has actually been downloaded, and then
   says you take on sole traders and that nothing starts until they have seen a
   price and said yes.
3. The footer, saying plainly that using the tool does not make anyone a client,
   with a link if they would like it to.

What keeps it from cheapening the tool is that the tool works completely without
any of them. No email wall, no "enter your email to download", no modal. The
browser walk asserts the invitation is invisible until a file has been produced.

### Which tax years, and how does January not become a burden?

**2023, 2024 and 2025 ship.** 2025 is the year being filed; 2024 and 2023 cover
amended and late returns, which is a real and underserved case.

January is one file and one line:

1. Copy `years/2025.mjs` to `years/2026.mjs`, change the four figures and their
   sources.
2. Add one import and one entry in `src/years.mjs`.
3. Run `npm test`. It fails if a parameter has no irs.gov source, if a rate is
   outside a sane range, or if a label has drifted from the form.
4. `npm run build`, `python3 copy.spec.py`, `npm run walk`.

`YEAR-UPDATE.md` is that list with the commands in it.

**One warning, already handled.** The IRS split the 2026 business mileage rate
mid-year — 72.5 cents through June, 76 cents from July. A tool holding one rate
per year would silently produce a wrong number for every 2026 filer. The rate is
therefore stored as a list of periods, and the mileage calculator **refuses**
rather than averaging when a year has more than one, telling the filer to split
the miles. A test builds a fake split year and asserts the refusal.

---

## 4 · How it is built, and why it looks like that

**One HTML file, no dependencies, no build framework.** 101 KB.

The privacy claim is the tool's main asset, and a claim is only as good as a
reader's ability to check it. So: one file, view source, no script tags pointing
anywhere, no analytics, no web fonts. `build.mjs` **refuses to write the page**
if it contains a `fetch(`, an `XMLHttpRequest`, a `sendBeacon`, an external
script, stylesheet, image or preload, or a dynamic import. `tests/build.test.mjs`
asserts the same thing about the committed file.

The proof a person can run themselves is on the page: *turn your internet off and
it still works.* The browser walk runs the whole scenario with the network cut
off and every outbound request blocked and recorded, and asserts zero were
attempted.

### Why the PDF and spreadsheet writers are written out rather than pulled in

Three reasons, in order of weight:

1. **Auditability.** A megabyte of minified third-party script makes the privacy
   claim uncheckable by exactly the people it is aimed at.
2. **Testability.** The PDF's content streams are uncompressed, so the figures
   are greppable in the file. The spreadsheet's zip is stored, not deflated, and
   timestamped to a fixed date, so building twice gives identical bytes and a
   test can assert it.
3. **Distribution risk.** The spreadsheet library everyone reaches for was pulled
   from npm. A free tool with a CPA's name on it should not have a dependency
   whose distribution can move.

The cost is about 500 lines I now own. The check on that cost is that neither
writer is trusted by its own reader: the PDF is read back by **pdf.js**, the
engine Firefox uses, and the spreadsheet by **openpyxl**, which has never heard
of this project.

### Money

Integer cents everywhere. No float touches a total. `roundToDollars` follows the
1040 instruction literally — *include the cents when adding, round only the
total* — which is deliberately **not** the same as rounding each figure and
adding the rounded ones, and means a printed whole-dollar column can be a dollar
short of its own total. Rather than hide that, the documents print a line
explaining it, and only when it has actually happened.

A property test caught `roundToDollars(-1)` returning `-0`. That is the sort of
thing property tests are for.

---

## 5 · Deployment

`satcllp.com` is served by Cloudflare Pages, whose build copies `./website` and
nothing else. So the page has to live in `website/` — but the source, the tests,
the 60-odd fixtures and the IRS evidence files should not be sitting on a public
web server.

So this folder holds the source and **generates** the page into
`website/tools/schedule-c-profit-and-loss/index.html`. That is the same shape
`pricing-config.js` already has in this repo: generated from the fee schedule,
committed, and checked by a spec that regenerates and fails on any difference.
`npm run check` and `tests/build.test.mjs` are that check here.

Deploy is therefore: merge to `main`, Cloudflare copies `website/`, done. No
build step on their side, no runtime, nothing to keep alive. The page is static
and will still work in five years if nobody touches it — which is the right
property for something whose only moving part is one file a year.

**Two things I did not do, because they are your call and they touch a live
page:**

- **No link from the main site to the tool.** Adding one to `website/index.html`
  is a production change to a page I was not asked to touch. It is one `<a>`, and
  the tool gets no traffic until it exists.
- **`sitemap.xml` is not updated** for the same reason.

---

## 6 · Measurement: did this produce a paying client?

The minimum chain that answers that question, collecting nothing about anyone's
figures:

1. **Pageviews.** Cloudflare Pages counts requests server-side. No script, no
   cookie, no code on the page. This is why the tool ships with no analytics at
   all — anything client-side would be a request to somebody else's server on a
   page that promises not to make any.
2. **The handoff link carries its source.** Every link from the tool to the
   practice is `https://satcllp.com/?from=schedule-c#intake`. That is already in
   the built page.
3. **The enquiry arrives tagged.** This needs **one line in `website/intake.js`**:
   read `?from=` off the URL and include it in the submitted payload, the way
   the other fields are. I have not made that change — it is a live page and
   it is your call — but without it, step 2 tells you nothing once someone lands
   on the intake form.
4. **Your own records answer the rest.** Did that enquiry become an engagement,
   and did the engagement get paid. That is a question for the practice's books,
   not for the website, and it is the only step that actually answers the
   question you asked.

So the whole instrumentation is: a link parameter, a one-line intake change, and
a column in your own records. Nothing that would be uncomfortable to hold,
because nothing about anyone's business is collected at any point.

**The decision rule, set now rather than later:** if the tool plus the guide page
have not produced one traceable enquiry in twelve months, do not build variants.
If they produce one that converts, the whole line of work has paid for itself and
the variants are worth an afternoon each.

---

## 7 · What a reviewer should be sceptical of

Written down so it is not discovered later.

- **The line labels for 2023 and 2024 came from prior-year PDFs I extracted, not
  from a form you have filed.** The extraction script and its raw output are in
  `evidence/` so you can check any of them in a minute.
- **The 2026 mid-year mileage split is recorded from an IRS listing page, not
  from the notices themselves.** 2026 is not a supported year yet, so nothing
  depends on it — but do not carry that figure into `years/2026.mjs` without
  reading the notice.
- **The spreadsheet only puts a formula on a line that has a figure.** A blank
  computed line has no formula, so if someone opens the file and fills in a
  previously blank Part III, line 4 will not update itself. That is the price of
  blank meaning blank, and I think it is the right side of the trade, but it is
  a real limitation.
- **The whole-dollar rounding note will appear on most real returns.** That is
  the IRS rule working as written, not a defect — but it will look like one to
  someone who has not read this paragraph.
- **Nothing here has been used by a person who is not me.** The browser walk is
  thorough and it is still not the same thing.
