# Walkthrough defects — satcllp.com, 7 September 2026

**What was walked.** The six published pages of the live public site, in Chrome,
as a prospective client landing cold: a single-member LLC doing contract work,
wondering whether to elect S corporation and what a return costs. Home →
Pricing → the guides → the intake form, to the last step.

**This is a separate register from `docs/WALKTHROUGH-DEFECTS.md`**, which covers
the internal apps (`satc_system`, `client-documents`) walked on 5 September. Two
different products; merging them would give whoever fixes one a list about the
other.

**The live site, not a branch.** Everything below is what a client sees at
satcllp.com right now.

**Nothing was submitted.** The walk stopped at the "Send to SATC" button. Pressing
it puts a real lead in the firm's inbox, so the last click was not made and the
final step's behaviour after submission is unproven.

---

## The denominator

| Check | Result | Caught any of the five below? |
|---|---|---|
| `pricing.spec.py` | 66 / 66 pass | no |
| `copy.spec.py` | 36 / 36 pass | no |
| `build-guides.py --check` | 4 files match | no |
| `tenets.spec.py` | 0 failing | no |
| `build-guides.py --publish-ready` | 0 open, exit 0 | no |
| `intake.spec.py` | **never ran on this machine** | — |

**Roughly 106 passing checks. They caught none of these.** That is not a
criticism of them; it is the shape of the problem. Four of the five defects below
sit in files no check opens, and the fifth is a navigation fact no test asserts.

**Read D1 with that table.** It is not that the linter failed. It is that the
linter cannot see the place the copy lives.

---

## D1 · The one phrase the firm banned by name is live on the home page, and the linter that bans it cannot see it

**Severity: highest.** Every visitor who reaches the last step of the intake form
reads it.

**What I did.** Walked the intake form to the final step, "How do we reach you?",
and read the consent checkbox.

**What the screen says:**

> I understand that sending this does not create a client engagement. SATC is
> engaged only when we both sign an **engagement letter**.

**What is actually true.** `"engagement letter"` is a banned phrase. It is in
`website/copy.spec.py` line 67, in `CONTRACT_WORDS`, alongside `governs` and
`pursuant`. It is there because of this, recorded in `CLAUDE.md`:

> i would never expect a client to understand what an engagement letter is
> inherently. 'governs the work' come on.

The price page was corrected in August. **The home page was not, because nothing
looked at it.**

**Why the check passes anyway.** Three facts, each verified:

| | |
|---|---|
| `grep -c "engagement letter" website/index.html` | **0** |
| Where the string actually lives | `website/intake.js:236`, inside a template literal that builds the checkbox |
| What `copy.spec.py` scans | `PAGES` — six `.html` files. It never opens a `.js` file. |

The copy is injected by JavaScript at render time, so the page source the linter
reads does not contain it. **The rule and the text are in two places with nothing
comparing them.**

**How much else is hiding there.** I ran the firm's own three word lists over
every client-visible string in the files `copy.spec.py` does not open:

```
website/intake.js          37 prose strings   1 hit   CONTRACT_WORDS "engagement letter"
website/intake-config.js   29 prose strings   0 hits
website/site-config.js      0 prose strings   0 hits
website/build-pricing-config.py  51 strings   2 hits — BOTH FALSE POSITIVES
```

The two in `build-pricing-config.py` are the **comment explaining this exact
failure** (lines 90–97), and the string reaches the generated
`pricing-config.js` **0** times. Correctly excluded rather than counted.

**So: one real hit, and it is the sentence the firm named.**

**The fix is two things, and only one of them is mine.**

1. *The wording* is client-facing copy and therefore the firm's. Not changed here.
2. *The structure* is the actual defect: `copy.spec.py` must cover the strings in
   `intake.js`, or the intake copy must move into a file that is already linted.
   Until one of those happens, any future sentence added to the form is unchecked
   — which is how this one got there.

---

## D2 · `sitemap.xml` dates the three guides twelve days before they existed

**Severity: high, and invisible.** It costs the firm the thing today's work was for.

**What I did.** Fetched `https://satcllp.com/sitemap.xml` and compared its
`lastmod` values against `git log --diff-filter=A`.

**What the file says.** All three guides: `<lastmod>2026-08-26</lastmod>`.

**What is actually true.** The three guide pages were created on **2026-09-07**,
in commit `061ac96` — *the same commit that added those sitemap rows*. Whoever
added them copied the date from the rows above.

**Why it matters.** The file's own comment states the rule it broke:

> `lastmod` is a real date per page, not the date this file was touched; a
> sitemap that claims everything changed today is a sitemap a crawler stops
> believing.

The rule was kept for `/` and `/pricing.html`, which really were 26 August. It
was broken for the three new rows. A crawler is now told these pages have not
changed since twelve days *before they were published* — so the wording the firm
approved today, and the em-dash fix, are the changes least likely to be
re-crawled promptly.

**Nothing checks this file.** `grep -rln "sitemap"` across every spec and the CI
workflows returns nothing. `sitemap.xml` and `robots.txt` are the two published
files with no test of any kind.

---

## D3 · The home page links to no guide, and two of the three are unreachable except from inside the guides

**Severity: medium-high.** It undercuts the reason the guides were written.

**What I did.** Fetched all six pages and built the internal link graph.

**Inbound links, from outside the page's own folder:**

| Page | Linked from |
|---|---|
| `/` | pricing, privacy, all three guides |
| `/pricing.html` | home, all three guides |
| `/privacy.html` | home |
| `/guides/records.html` | **pricing only** |
| `/guides/business-records.html` | **nothing outside `/guides/`** |
| `/guides/s-corp.html` | **nothing outside `/guides/`** |

`grep -c "guides/" website/index.html` → **0**.

**The only route to the S-corp guide** is: home → *Pricing* → *"here is what that
means"* → records.html → the small **ALSO HERE** nav at the foot → S corp. Four
hops, the last from a footer nav on a different guide.

**Why it matters.** `docs/guides/PLAN.md` justifies that page on the grounds that
*"an S corp owner searching the phrase is exactly who would find the page."* That
premise is about **search**, and search is fine — all three are in `sitemap.xml`
and return 200. But a visitor who arrives at the front door and does not click
*Pricing* will never learn the guides exist.

**Not fixed here.** Adding a link to the home page is a change to the front door
and therefore the firm's.

---

## D4 · The intake form has no progress indicator

**Severity: medium.** Abandonment risk on the only lead path the site has.

**What I did.** Walked the wizard from the first question to the final step,
looking for any affordance showing position or length.

**What is actually true.** There is none. No "step 3 of 6", no bar, no dots. I
searched for `[class*=progress]`, `[role=progressbar]`, `[aria-valuenow]`,
`[class*=dot]`, `[class*=crumb]` inside the form: the only match is the
`fieldset.wiz-step` class name, which renders nothing a person can see.

The wizard also renders **one step at a time** — only a single `fieldset` exists
in the DOM — so a client cannot scroll ahead to judge the length either.

**Why it matters.** The home page promises, in its own panel:

> **Five minutes now,** a conversation next.

The form is the thing that has to keep that promise, and it gives the person
filling it in no way to tell whether they are near the end.

---

## D5 · `privacy.html` is the only page of six with no Open Graph tags

**Severity: low.**

Every other page carries `og:title`, `og:description` and `og:image`. Privacy
carries none, so when the firm sends that link — to a client asking what the form
collects, which is exactly when it gets sent — the preview is bare.

Its `<title>` and `<meta name="description">` are both present and good, so this
is an inconsistency rather than an omission of substance.

---

## Not defects — decisions the firm may not know they have made

**`robots.txt` blocks the AI crawlers.** Under a *"BEGIN Cloudflare Managed
content"* block, `ClaudeBot`, `GPTBot`, `Google-Extended`, `Applebot-Extended`,
`CCBot`, `Bytespider`, `meta-externalagent` and `Amazonbot` are all
`Disallow: /`. Ordinary search is explicitly allowed
(`Content-Signal: search=yes`).

This is Cloudflare's default, not something anyone here wrote. It is a real
business choice — a small firm hoping to be surfaced by an AI assistant is opted
out of exactly that — and it is worth making deliberately rather than inheriting.
**Not changed.**

**The price page carries no prices without JavaScript, and handles it well.** With
JS off the page says: *"The prices on this page need JavaScript to load. Turn it
on, or send us your situation and you'll get the numbers that apply to it."* That
is a correct, plainly-written fallback. Noted because it means no price is in the
HTML source, so anything that does not execute JavaScript sees a page with no
figures on it.

---

## What I got wrong

Three times my own probe reported a defect that was not one. **Each time the site
was right and my instrument was wrong**, which is worth more than the findings
above, because a sweep that reported all three would have had somebody "fix"
things that were correct.

1. **The spam-trap field looked visible.** `_gotcha` passed my
   `display/visibility/zero-size` test. Inspected properly it is at
   `left:-9999px`, `opacity:0`, `tabindex:-1`, `aria-hidden="true"`,
   `autocomplete="off"` — a textbook correctly-hidden honeypot. My check did not
   look for off-screen positioning.
2. **A question appeared to be printed twice.** The second copy is a
   `class="sr-only"` span at `clip:rect(0,0,0,0)`, 1×1px — a screen-reader label.
   The form's accessibility is *better* than my probe assumed, not worse.
3. **A step appeared to refuse to advance with no message.** It shows
   *"Please fill this in to continue."* My earlier read was taken from a stale
   render and missed it. The form's validation is consistent across the steps I
   tested — the first step says *"Pick at least one to continue."*

**The lesson for the next sweep:** a visibility heuristic built from
`display`/`visibility`/size alone over-fires on three common and correct
patterns. Check `clip`, `opacity`, and off-screen position before reporting
anything as visible-but-shouldn't-be.

---

## What was not walked

- **Desktop width.** The browser's display in this environment is **736px wide**
  (`screen.width`), and part-way through the walk the window wedged at 640×311
  with `outerWidth` reporting `0`; `resize_window` returned success without
  applying. **Everything above was found at narrow width.** Layout at a normal
  desktop size is unproven by this walk.
- **The procedure document.** The walk skill requires two documents and this is
  one of them. A step-by-step procedure needs a readable screenshot per step, and
  a 640×311 viewport cannot produce one. **It is not written, rather than written
  badly.** It needs the Chrome window restored.
- **Submitting the form.** Deliberate — see the top of this file.
- **The email that a submission generates**, the Formspree path, and anything
  after the last click.
- **`intake.spec.py`**, which has still never run on this machine.
- **Any page in a real mobile browser**, as opposed to a narrow desktop viewport.
