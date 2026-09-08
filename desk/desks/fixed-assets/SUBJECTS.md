# Subjects — what brings this desk into play

`Answered from <source id>` is what makes routing deterministic AND what makes a
citation checkable: it names the subjects that bring a desk into play, and which
source answers each of them. Their union is what routing fires on, so there is no
second list to drift. It is canon's own selector, borrowed rather than rewritten, and it
matches **whole words only** — substring matching once made *"extension"* fire on
*"extensive"*.

**It under-fires, and that is worth knowing.** The list matches a question's
subject, not its shape, so an inflected form is missed: `defer` does not fire on
`deferring`. Add the inflections that matter rather than loosening the rule — a
false positive is what teaches somebody to stop reading the output.

---

## fixed-assets · When money spent on property is an improvement rather than a repair

**Answered from S1:** capitalize, capitalise, capitalized, capitalised, capitalization, depreciate, depreciation, depreciable, improvement, improvements, betterment, restoration, repair, repairs, adaptation, basis, useful life, unit of property, placed in service, routine maintenance, 263(a), 1.263(a)-3, building, buildings, building structure, building systems, hvac, escalator, escalators, elevator, elevators, roof, structural, leasehold, machinery

**Answered from S3:** acquire, acquired, acquisition, purchase, purchased, tool, tools, equipment, furniture, fixtures, invoice price, transaction costs, produce tangible property, 1.263(a)-2

**S3 IS THE OTHER HALF OF S1 AND THE SUBJECTS HAD TO SAY SO.** S1 answers what
happens to property the taxpayer already owns; S3 answers what happens when they
buy it. Sharing a subject word between them would make routing ambiguous on
exactly the question that needed S3 — so `acquire` and the words a preparer
writes about a purchase are S3's, and `improvement`, `repair` and `basis` stay
S1's. `capitalize` stays on S1 as well: it is the verb both sections use, and the
one question that needed S3 fired on it and reached a desk that then refused for
want of the acquisition rule, which is the behaviour that found this gap.

**Answered from S2:** materials and supplies, materials or supplies, material or supply, rotable, rotable spare parts, spare part, spare parts, consumable, consumables, 1.162-3

**`materials and supplies` MOVED FROM S1 TO S2, and the move is the point.** It
was registered to § 1.263(a)-3, which uses the phrase only to say what it is NOT
— its examples cite § 1.162-3(c)(1)(i) by name for the definition. Leaving the
subject on S1 would have declared a source the desk could never serve on the
question it answers: `engine.serve` refuses a citation from a source the desk
does not use for THIS subject, which is the defect the 7 September answering run
found twice on other desks. Admitting a publisher and not routing to it is
admitting nothing.

**`materials or supplies` IS THERE BECAUSE THE AUTHORITY USES IT AND I DID NOT.**
I declared the *and* form and the singular, tested the serve path with a question
worded the way § 1.263(a)-3's own examples word it — *"are not materials or
supplies under § 1.162-3(c)(1)(i)"* — and got `checked_subject=False`: served,
but with the subject gate never run. The list under-fires on an inflection, which
this file already says of itself. The form the regulation writes is the form a
preparer will write.

---

**THE SUBJECTS WERE THE REGULATION'S VOCABULARY AND THE QUESTIONS ARE THE
SITUATION'S.** Measured 5 September 2026: **9 of this desk's own 16 problems
touched none of its 23 declared subjects.** Not a near miss — *no* subject at
all, so `serve()` reported `checked_subject=False` on over half the desk and the
gate that exists to catch a wrong citation never ran.

The cause is visible in one line of the list. It declared `betterment`,
`restoration`, `adaptation`, `unit of property` — the words § 1.263(a)-3 uses to
*name its tests* — and none of the words it uses to name the *things the tests
are about*. **`building` appears 117 times in the authority this desk holds and
was not a subject of it.** A preparer asks whether to capitalise the new HVAC
units; nobody asks whether a betterment was made to a unit of property.

Every desk built on 5 September has zero blind problems. This one predates the
routing measurement, and the same defect turned up on the capitalisation desk as
`tool` and `asset` — a desk that fires only on the vocabulary of its own
regulation answers the question nobody asked in those words.

**`plumbing` was a candidate and was dropped, measured.** § 1.263(a)-3 lists it
as a building system, and it pulled in three problems from two other desks —
every one about a plumbing *company*, not a plumbing *system*. A word the
regulation and the world use differently, which is the `$2,500` lesson in
another shape.

    with the fourteen candidates    9 blind -> 0    3 other desks' problems
    with `plumbing` dropped         9 blind -> 0    0

Fires on none of the 43 close questions either way. That is its own finding and
is not fixed here: the oldest desk answers nothing a real close asked.

**Judged:** required

*This desk does not serve an answer no second reader has looked at. The firm, on
the docket, 8 September 2026, asked which desks may not serve unjudged:* "The
judge can look at it all I guess?" *— all seven. It is declared here rather than
in the code so lifting it is one line of this file. The engine checks only that
the words the judge quotes are really in what they read; whether those words
carry the conclusion is the judge's call and is recorded, not recomputed.*
