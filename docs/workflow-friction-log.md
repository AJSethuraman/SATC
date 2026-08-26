# Workflow friction log

Things that make filling out a return slower than it needs to be, and what
would fix them. Started 25 August 2026 at Arjun's request, from a note on the
brokerage pricing question:

> it is not that we can't enter the high level data and attach, it's that the
> process is currently me keying in everything because it seemed easier than
> attaching because that requires manually scanning in sometimes or uploading
> to drake. this is the kind of thing that should be added to a log of ideas we
> can have to make things easier on filling stuff out

**This log is not a backlog.** Nothing here is committed work. It is the list
of frictions worth remembering, so that when there is time to build something,
the choice is made from evidence rather than from whatever was annoying that
week.

One rule, because it is the whole point of writing them down: **a friction is
ours, not the client's.** Where our process costs more than the return needs,
that is a cost to fix, not a cost to bill. See the brokerage entry below for
the case that produced the rule.

---

## Open

### Nobody knows how long anything takes, and nobody is going to type it in

**The friction.** Every price in the fee schedule is also a time budget --
`cd client-documents && python cli.py hours` prints them -- and every one of
those budgets is calibrated to the principal's own estimate of his average
rather than to a measurement. Five numbers per engagement would settle most of
what has been argued about this month: the package, the prep hours, the
**admin** hours, whether an assumption failed, and what that cost.

Admin hours is the one that matters most and the one no survey anywhere
reports. It is the number that decides whether Starter at $100 is profitable
work or a donation.

**Asked and answered, 26 August 2026.** The firm chose to log all five for a
full season, over a sample of twenty, and added the condition that makes it
real:

> this is good - should be formalized and automated. add it to the log

**Why it is in this log rather than in the backlog.** Because the friction is
not the measuring -- it is the typing. A time log that depends on a person
remembering to fill it in during March is a time log with a hole in exactly
the weeks that matter most. Any design that starts with "and then you enter
your hours" has already failed.

**What automation could actually reach, today.** The engagement record already
knows the package, the counts, the date it was created and every answer the
interview collected. What it does not know is when work started, when it
stopped, and whether an assumption broke. Three cheap sources exist before
anyone is asked to type anything:

* **The engagement store's own timestamps.** Created, documents rendered,
  invoice raised. That is elapsed calendar time, not hours, but it bounds them.
* **The review flags.** `Outcome.flags` already records the things a preparer
  was asked to look at. "Did an assumption fail" is a flag away from being
  captured rather than remembered.
* **A single start/stop, not a form.** One command that stamps a file, and one
  that closes it, is a different proposition from a timesheet.

**What it needs from a human anyway, and there is no way around it.** Whether
the assumption that failed was the client's or ours. That is a judgement, it
is one word, and it is the difference between a price that is wrong and a
process that is broken.

**Not started.** This is the entry, not the build.

---

### 1099-B: keying every lot instead of summarising and attaching

**The friction.** Every transaction gets keyed by hand. Attaching the statement
instead would mean scanning it or uploading it to Drake, which has felt like
more work than typing.

**Why it matters.** Where a 1099-B reports covered lots with basis and no
adjustments, the totals can be entered by category with the statement attached,
rather than every transaction listed. On a long statement that is the difference
between typing four lines and four hundred. Only the parts that genuinely
cannot be summarised — noncovered lots, adjustments, wash sales, options,
crypto — need to go in individually.

**What would fix it.** Time the two paths once, on a real statement, and find
out whether the scan-and-attach really is slower. If it is, the fix is upstream
of Drake: a way to get a broker PDF attached without a scanner in the loop.

**Status.** Open. Priced around as of 25 Aug: brokerage is counted, not hourly,
and the higher line keys on what cannot be summarised — deliberately not on how
long our current process takes.

> [CONFIRM: the summary-totals treatment above is the general shape of the
> Form 8949 rule, but confirm it against the current form instructions before
> it changes how a return is actually filed. irs.gov is not reachable from the
> machine these notes were written on.]

### No recorded minutes per line

**The friction.** Every fee argument this month — is $200 too much for a
Schedule C, is $100 a loss on a student return, does automation save us
anything — has run into the same wall: nobody knows how long any of it takes.

**Why it matters.** It is not only a pricing problem. Without minutes per line,
"the new tool saved us time" is unprovable, and so is "this client is
unprofitable". Five figures would settle most of the open questions: the
package, the prep hours, the admin hours, whether an assumption failed, and
what that cost.

**What would fix it.** Recording those five against each engagement, starting
with the next one. Not a system — a habit and a column.

**Status.** Open, and blocking more than it looks like.

### Document reading is where automation lands first

**The friction.** The lines that price document reading — a K-1, a rental
statement, a brokerage summary, a local return — are the ones a reader could
plausibly do first, and they are priced today at what they cost a person today.

**Why it matters.** From Arjun, on holding the K-1 line at $15 rather than
raising it: *"we should really be incorporating levels of automation with this
sort of work when it comes to reading docs for requirements."* If those prices
are set at manual effort and never revisited, the saving quietly becomes margin
by default rather than by decision.

**What would fix it.** Tag the automation-exposed lines on the price sheet, so
that when a reader lands it is obvious which prices are in scope — and the
decision about who gets the saving is made on purpose.

**Status.** Open. Raised as a question in the second pricing round.

---

## Closed

*Nothing yet.*
