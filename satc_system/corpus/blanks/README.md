# Real blank forms — the part that actually proves something

Empty on purpose. `irs.gov` is blocked from the build environment, so these have
to be fetched once, by hand, from an unblocked machine.

**What to put here:** the IRS's own fillable PDFs — `fw2.pdf`, `f1099int.pdf`,
`f1099div.pdf`, `f1099nec.pdf`, `f1099r.pdf`, `f1099g.pdf`, `f1098.pdf`,
`f1095a.pdf`, `f1040.pdf`. Public documents. No client data ever goes in here.

**Why it matters more than the rest of the corpus.** A generated page that says
"Form W-2" classifies as a W-2 and proves nothing. A real blank carries the real
AcroForm field names, the real layout, and the real text-layer reading order —
which is what the classifier is actually up against, and what it got wrong in the
field while the synthetic tests stayed green.

Filled with obviously-synthetic values (invalid SSN/EIN ranges), these become the
only cases in the corpus that test the thing that broke.
