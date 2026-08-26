# Website tenets

Read this before drafting anything on satcllp.com — copy or layout. Every rule
is here because the firm rejected a real draft and said why. The quotes are
theirs; they are blunter than any paraphrase, and that is the point.

Ordered by how often each would have caught something during the pricing page
build (26 Aug 2026), not by conceptual tidiness.

## The one-minute version

1. No sentence about how we behave. Not "we're upfront", not "no surprises", not "we fix our own errors free".
2. Nothing may look unfinished — no stranded white space, no card stretched past its content, no half-empty row.
3. If a sentence exists because a slot was empty, delete the sentence and fix the slot.
4. Two things doing the same job look identical. Two things doing different jobs look different.
5. Never say the same thing twice on one page.
6. Never promise a person, a time, or a number we cannot hold.
7. Never transcribe a spec, a schedule label, or a term of art.
8. Use the firm's own words, literally.
9. One line each.

If a draft passes all nine and you still cannot say what a sentence *tells the
reader*, delete it.

---

## 1. Never write a sentence about how we behave

The most-deleted category in the build. Claims about our own character read as
filler at best and as a pitch at worst.

> "literally do not specify stuff like we fix our own errors for free. we don't
> need to say that."

> "delete the rest we dont need to be claiming how upfront we are about stuff"

> "literally AI dribble, why can't you get that?" — on *"The rare one that
> isn't, you'll hear about in advance."*

> "it sounds obviously earnest to say 'anything sensitive comes later, once
> we've spoken' like it sounds literally scammy because it's being said like
> that, just don't have to say it."

> "don't say things like 'honestly' randomly, i can blatantly tell how much the
> latest models have been trained to say they're being honest about stuff and it
> just comes off as annoying"

| Rejected | Survived |
|---|---|
| "We'll walk through what you need and hand you a quote. If it turns out to be more work than it looked, you hear that then — not on the invoice." | "We'll walk through what you need together and tell you what it costs." |
| "Flat, whichever of these applies. The rare one that isn't, you'll hear about in advance." | *(deleted — nothing replaced it)* |
| "If we're not the right firm for the work, we'll say so rather than take the engagement. What we do take on, we do by the book." | "If we're not the right firm for the work, we'll say so." |
| "We publish what we charge" | *(deleted)* |

**The test.** Does it give the reader a fact they can act on, or only an
impression of us? *"You hear which before we start"* survived on the hourly note
because it says which of two things happens. *"You'll hear about it in advance"*
died because it only says we are the kind of firm that tells you things.

**The edge.** Not a ban on standing for anything — the firm kept one affirmative
line about doing work properly, and even then said "maybe it's too poignant."
One sentence, never a hedge, never a paragraph.

**How to check.** Same technique as `pricing.spec.py`'s `CONTRACT_WORDS`: pull
visible text, lowercase, fail on a word list — `no surprises`, `upfront`, `rest
assured`, `honestly`, `we pride`, `we always`, `we never`, `you'll hear`,
`we'll tell you`, `at no charge`, `our promise`, `peace of mind`, `you can trust`.

---

## 2. Nothing may look unfinished

About half of every correction in this build was visual, and most were the same
complaint: a block that looks like it failed to load.

> "too much white space was added - amendments needs moved up to that it isn't
> stranded. that looks so visually unappealing"

> "ok actually just delete Where you start and kind of center the button - i
> don't like the big block of white it looks too contrasting in that area"

> "some way to make it look cleaner - not have 2 options on some lines, 3 on
> others"

Four causes, all now recorded in `pricing.html`'s CSS comments:

- **`auto-fit` strands a card.** It picked three columns at some widths, leaving
  the fourth alone on row two. Fixed with explicit breakpoints — four, then two,
  then one. Every row is always full.
- **A stretched row is a hole inside a border.** When the entity cards lost
  their lists, a `1fr` last row turned the rest of the card into empty space
  *inside* a box, "which reads as a card that failed to load." Fixed with
  `align-content:start`, so the space falls below the cards where it is margin.
- **A panel held to its sibling's height leaves a hole** — ~200px of nothing
  above the navy band. Let each panel size to its own content; a band that moves
  when you press a tab is what a tab does.
- **CSS `columns` balances by height** and stranded the third group. Fixed with
  explicit `nth-child` grid placement.

**How to check.** Drive Chromium and measure. This build did exactly that:
`getBoundingClientRect` on the two menu columns until the bottom delta was
**0px**, and on the two situations blocks until both measured **390px**. Assert
equality, don't eyeball it. Check the phone width too — the firm reviews on a
phone.

---

## 3. If a sentence exists because a slot was empty, delete the sentence

The deepest failure here, and the hardest for a drafter to see: the layout
supplies the motive, and the drafter then supplies a justification.

> "Delete 'One price for any of them'... AI-Coded dribble, again. like either
> don't say anything or say something more human"

> "'Only what the price above doesn't already cover.' this is so AI-coded, you
> should know better. just delete"

> "delete Here are the numbers" / "delete These are hourly because we can't
> price them until we see them:"

> "No, start at 200 except this is stupid. Just let the prices speak"
> — which deleted an entire explanatory box above the prices

The agent's own post-mortem after the final rejection names the mechanism:

> "The sentence was only ever there to fill a slot... I wrote it to match a
> layout, then reasoned backwards to justify it."

**The test.** Before writing a sentence, ask what happens if it isn't there. If
the answer is "there'd be a gap," that is a CSS problem. Empty space is fixed
with spacing, centering or regrouping — never with prose.

**How to check.** Generalize `pricing.spec.py`'s lede rule (`above.count("<p")
<= 1` between the headline and the prices): cap how much prose a *region* may
hold, rather than policing its wording. Regions that earn a cap — above the
prices, under a section heading, under a control.

---

## 4. Two things doing the same job must look identical

> "ok now this looks visually weird because one has bullet points above the
> others - 1 line on these too"

> "why are the bullet points not identical across" ... "why are they dashes
> instead of the literal same bullet points for everywhere el[se]"

> "no 'The' i want it to match Hourly Situations more visually ... i want it to
> look visually similar to hourly situations so it takes up the same amount of
> space in that regard"

> "the service menu is so close to being fully aligned... it's off a little bit
> at the bottom"

The `$50 situations` block was rebuilt part-for-part against `Hourly situations`
beside it — heading, sub-line, ruled list — and lost its "The" so the headings
would scan the same.

**The flip side matters as much.** Asked to merge individual and entity pricing
into one section, the firm reversed: *"actually ou have a point they are fairly
different... instead, can we make it flip back and forth."* So an entity card is
the *same card* with three structural differences that carry meaning — gold rule
instead of navy, `from` as a label above the number, hollow bullets instead of
filled. Same family, different job, difference carried by structure rather than
a color wash.

**How to check.** The spec asserts the modifier class (`tier ent`) and the
rendered `from`, "because dropping it makes a floor a promise." In the browser,
assert shared computed styles and equal section heights between paired blocks.

---

## 5. Never say the same thing twice

> "this is redundant to saying 'From' - what is something more valuable to say?"

> "one full schedule C and actual expenses are very similar to saying the same
> thing. we should maybe just use that space to say something else"

> "that's kind of what the blue banner says anyway, maybe we just make the
> prices and form names and such larger?"

> "the one desk thing happens so quickly back to back, like you scroll from the
> top to the middle and all of a sudden 'x, one desk' again"

Note the instinct in the third quote: when a sentence duplicates something
already on screen, the fix is usually **typographic, not verbal** — delete the
words and make the real content bigger. The `FROM` label went 10px → 13px for
exactly that reason. Three entity cards each repeating the same add-on list
became one prose band saying it once, because "two cards repeated a list and the
third had nothing to say."

**How to check.** No word list is worth its false positives. Read the page top to
bottom in one pass — the firm's own method: "this is all in order of reading it
on the website more or less."

---

## 6. Never promise a person, a time, or a number we cannot hold

> "do not say 'by one person' in general, never promise it is by someone in
> particular. i do not want to pigeon hole myself"

> "do not promise the one business day thing... do not say it is from me
> directly. it will be from the company... like it'll probably be from me but
> why say that."

> "this makes it sound like we can price 100% accurately - we cannot"

> "i dont want it obvious, or to be over promising"

This is exposure, not modesty. A named person constrains hiring. A turnaround
time is a commitment made before the work is seen. A flat-looking number on a
floor price is a quote. The same logic reaches figures: the foreign-account cap
is *soft*, so the page must say the time past it is billed — the spec fails
otherwise, "because naming it without that is a promise the firm is not making."

**Also banned: claims about anyone else.** *"I'm not personally a huge fan of
shifting the blame to others... we don't need to say anything about other tax
places."*

**How to check.** `COMPARATIVE` already exists in the spec. Add a promise list —
`business day`, `within 24`, `turnaround`, `guarantee`, `by Arjun`,
`personally`, `same day`. For figures, the regenerate-and-diff check stops an
invented or stale number outright.

---

## 7. Never transcribe a spec, a schedule label, or a term of art

The original CLAUDE.md rule, still earning its place. The sentence that started
it:

> "These are prices, not a quote. You get an estimate in writing with your own
> lines on it, and the engagement letter governs the work."

> "like this sounds like corporate babble given by AI. because it is. i would
> never expect a client to understand what an engagement letter is inherently.
> 'governs the work' come on"

> "you need to understand that public facing and internal are two different
> things... things should sound way more simple to our clients than it does to
> us - doesn't that just make sense?"

The failure was mechanical. The pricing brief told the *builder* "An estimate is
not a quote. The engagement letter governs; the estimate accompanies it," and
that sentence went onto the page. A requirement says what the page must be *true
about*. It is not the sentence.

The same leak ran through data: the fee schedule's `label` and `detail` are
written for the preparer, and piping them onto the page printed "Per statement
that cannot be summarized" at a visitor. Fixed structurally —
`build-pricing-config.py` holds an `EXTRA_COPY` overlay in the firm's words, and
the spec fails if a newly-published line has no entry.

| Rejected | Survived |
|---|---|
| "Working out what an owner of a business should be paid" — *"this doesn't connect to someone who doesn't understand we're talking like an s corp"* | "Setting what an S corporation owner pays themselves" |
| "A brokerage statement that has to be typed in by hand" | "Keyed brokerage statements" |
| "Not an S corporation or partnership return — those are under Businesses" | "Own an entity? See the Businesses tab." |
| "Schedule C · standard mileage" | "Gig or contract work / Schedule C · rideshare, delivery, freelance and the like" |

Plain is not dumbed down. The firm chose "We don't provide assurance services
yet" over "we don't do audit work," and "coming soon" over "we don't offer that
yet" — the real name of the service, and a door left open. But no jargon the
reader didn't bring: *"nobody knows what a KPI is out side of people who already
know."*

**How to check.** `CONTRACT_WORDS` in `pricing.spec.py`, run over visible text
only so a source comment explaining the rule doesn't trip it. Mutation-tested:
putting "the engagement letter governs the work" back fails the build.

---

## 8. Use the firm's own words, literally

When the firm hands you a sentence, they mean that sentence. Rewriting it into
brand voice costs a round.

> "no, that sounds way too casual. use my words more literally - these represent
> our pricing for the upcoming tax year and are subject to change"

> "Better. I want words tightened up. They sound oddly uncanny"

> "stop saying things like 'a real answer next', the real part just sounds...
> weird"

> "as opposed to couldn't put our name to, go with wouldn't. if i wouldn't i
> wouldn't for you right?"

> "Also, no British spelling this is a totally English American company"

Read each instruction for whether it is a *sentence* or a *direction*. "use my
words more literally" means transcribe. "Don't word it like this but it's my
general idea" means paraphrase. Getting it backwards costs a round either way.
And tone is not a coat of paint: *"you need to apply the tone all over, it's a
design element."*

**How to check.** The `BRITISH` list is mechanical, and the generator re-spells
anything the schedule brings in. The rest is judgment — but diff your version
against the firm's before shipping.

---

## 9. One line each

> "i want these on one line, shorten them to be on one line each instead of
> split into 2. some stuff can be trimmed by just cutting words. for instance
> 'Owners whose books have fallen behind and need catching up before anything
> else' doesn't need the 'and...' part really"

> "just say Pricing is subject to change. - the other one takes up too much
> space"

> "the [extension] tile is too many words but it says what it needs to for the
> most part"

A copy rule and a layout rule at once: uneven wrapping is what makes a row of
cards look ragged, and cutting words is cheaper than adjusting the grid.

Longest surviving sentence on the pricing page: *"Depending on what turns up,
hourly work is either added to a fixed price or replaces it."* Twenty-one words.
That is the practical ceiling.

**How to check.** The spec fails any client-facing sentence over 28 words. 28 is
deliberately generous — a floor on effort, not a style. Aim far lower.

---

## What the six CLAUDE.md rules missed

The register section in `CLAUDE.md` was written *mid-conversation*, at the
firm's request ("ok what kind of instructions do you need to not let slop like
this through"). After it was written, and after two of its clauses were
machine-enforced, the firm rejected copy five more times — including "literally
AI dribble, why can't you get that?"

Run the six rules over the sentence that drew that:

> "Flat, whichever of these applies. The rare one that isn't, you'll hear about
> in advance."

1. Never transcribe a spec — **passes.** Written fresh, not lifted from a brief.
2. No term to look up — **passes.** Every word is common.
3. No contract-desk verbs — **passes.** None present.
4. Cut any sentence whose only job is to protect us — **passes**, by the drafter's own reading. It looks like a warning *to the reader*.
5. Past ~25 words — **passes.** Eight words, then nine.
6. Would you say it across a desk — **passes.** You would.

Six for six, and the firm's read was "AI dribble." Not a close call the rules
narrowly lost — a category they do not cover. Four gaps:

**Gap 1 — every rule takes the sentence as given and asks whether it is worded
right. None asks whether it should exist.** The dominant failure in this build
was existence, not wording: "just delete", "delete the rest", "either don't say
anything or say something more human", "Just let the prices speak." Rule 1 comes
closest and only fires when the sentence came from a document. A sentence
invented on the spot to fill a gap sails through. → **tenet 3.**

**Gap 2 — rule 4 covers sentences that protect us; nothing covers sentences that
flatter us.** "We're upfront", "no surprises", "we fix our own errors free",
"honestly", "we'll say so rather than take the engagement" — the single largest
deleted category in the conversation, and all six rules are silent on it.
→ **tenet 1, with a word list.**

**Gap 3 — the rules say nothing about layout, so layout pressure produces copy
with nothing standing in its way.** Half the corrections were visual, and the
visual system is an active *producer* of bad copy: an empty half of a two-column
block asks for a sentence, and one appears. The agent's own diagnosis — "I wrote
it to match a layout, then reasoned backwards to justify it." A copy standard
that ignores layout cannot catch a copy failure whose cause is layout.
→ **tenets 2, 3 and 4 together.**

**Gap 4 — only two of six are enforced; the other four are self-assessment by
the party whose judgment already failed.** Rules 3 and 5 became `CONTRACT_WORDS`
and the 28-word check, and neither has been violated since. Rules 1, 2, 4 and 6
stayed judgment calls, and every post-CLAUDE.md rejection passed the drafter's
own reading of all four. Rule 6 especially — "read it as if saying it across a
desk" — asks the author to grade a sentence seconds after writing it, the one
moment they are least able to. → **a word list for every tenet that admits one,
and a measured browser check for every layout tenet.**

---

## Enforcement

`website/pricing.spec.py` is the working model — 61 checks, no browser, no
server, seconds in CI. Its four techniques, strongest first:

1. **Regenerate and diff.** `pricing-config.js` is generated from
   `client-documents/registry/fee-schedule.yaml` by `build-pricing-config.py`;
   the spec re-runs the generator and fails if the committed file differs. One
   check subsumes every "is this figure right" question.
2. **Word lists over extracted visible text.** Strip comments, `<script>` and
   `<style>`; convert closing block tags to `". "`; strip remaining tags; append
   every string in the config; then match. This is how `CONTRACT_WORDS`,
   `COMPARATIVE` and `BRITISH` work, and the pattern to copy for the self-claim
   and promise lists above.
3. **Assertions keyed on data, not phrasing.** The spec broke twice because
   checks were keyed on literal words the firm then rewrote. Key on the
   schedule's own fields, or on meaning — "does the foreign-account line say the
   time past the cap is billed" is tested as `("bill" and "time") or "hour"`.
4. **Measured browser checks.** Bounding boxes, computed styles, section
   heights, asserted equal. Chromium is at
   `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.

Still missing: a self-claim word list (tenet 1), a promise word list (tenet 6),
prose caps per region (tenet 3), paired-block equality in the browser (tenets 2
and 4).

Mutation-test every new check the way `CONTRACT_WORDS` was — put the rejected
sentence back and confirm the build goes red. A check nobody has seen fail is a
check nobody should trust.
