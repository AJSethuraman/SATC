# Decisions, in the firm's own words

Every answer given through an interview question: what was asked and
what was chosen. Answers the firm TYPED rather than picked are marked
— those are the ones that rejected the framing, and they carry the
reasoning. Seed corpus for the convictions.

**44 decisions, 17 of them typed, 446 words** — counting what the firm chose,
not the questions they were asked. (This said 483 until the miner counted it.)

---

### 2026-08-25 18:10:48

**Asked:** The estimate engine is ~10 numbers and 6 settings from working end to end. What is v1 here?

**Chose:** Unblock the estimate first (Recommended)

### 2026-08-25 18:15:40

**Asked:** The registry has one flat base fee per return type. Your sheet has a four-package ladder. How should a client's package get chosen?

**Chose:** Engine derives it, and prints why (Recommended)

### 2026-08-25 18:18:31

**Asked:** How should the package appear on the estimate the client reads?

**Chose:** Package name + what it covers, then extras (Recommended)

### 2026-08-25 18:19:27  · TYPED

**Asked:** What's explicitly OUT of v1? (Pick everything you want excluded — this is the fence that stops the build ballooning.)

**Chose:** we can do one thing at a time correctly and use that as our kind of blueprint for the next step,The invoice bridge (Recommended out),Square vs Stripe (Recommended out),The 2026 materials deadlines (Recommended out),Entity returns — individual 1040 only in v1

### 2026-08-25 18:20:28

**Asked:** What counts as done and verified for the 1040 estimate?

**Chose:** Tests + demo + one real estimate you'd send (Recommended)

### 2026-08-25 18:21:50  · TYPED

**Asked:** A Starter client ($100, W-2 only) turns up with an HSA — one extra form. What should the engine do?

**Chose:** engine has to accomplish all of this - not sure what you're asking here

### 2026-08-25 18:26:39

**Asked:** I'd test this at four seams that already exist, and invent none. Does that match what you expect?

**Chose:** Yes — those four (Recommended)

### 2026-08-25 18:31:25

**Asked:** Does that breakdown look right before I publish it to AJSethuraman/SATC?

**Chose:** Publish as-is (Recommended)

### 2026-08-26 22:04:55  · TYPED

**Asked:** Deleting the notice assumption from the estimate also took "A letter from the IRS or the state you would like us to handle" off the price page's public hourly list — `assumed:` feeds both. Should that line stay on the page?

**Chose:** Let it drop

### 2026-08-26 22:04:55  · TYPED

**Asked:** Who applies the `website/` half of the fix?

**Chose:** the website half is unnecessary - when we are said and done i will have you give me the fee schedule and we will ensure it's right

### 2026-08-26 23:01:22

**Asked:** The pricing check will keep firing on every push. How do you want it handled?

**Chose:** Just fix it (Recommended)

### 2026-08-27 01:13:09

**Asked:** You asked whether you need a separate session to test this overnight. You don't need a separate session — I can run it from here. What do you want the overnight run to actually do?

**Chose:** Open, read and assess every document (Recommended)

### 2026-08-27 18:00:50

**Asked:** The leads page hides its main action, "Accept the claim" needs a gloss, and the home screen shows a raw id like "resume 56509a234d60". Fix those before writing the walkthrough, or document the interface as it stands?

**Chose:** Fix the cheap ones first (Recommended)

### 2026-08-27 18:00:50

**Asked:** The browser covers leads, the interview, prices and templates. Packaging is terminal-only — so a guided walkthrough ends with "now open a terminal and type python cli.py package". Which way?

**Chose:** Extend the browser to packaging (Recommended)

### 2026-08-30 01:05:21  · TYPED

**Asked:** Merging #155 also publishes a live pricing page to satcllp.com — a new pricing.html plus a rewritten index.html, via Cloudflare Pages. That's the lane you told me to leave to the other agent, and they have four website PRs still open (#156, #158, #159, #160). How do you want the website handled?

**Chose:** You shouldn’t ever touch the website itself. That is another agents job. Merge whatever else

### 2026-09-02 22:56:34  · TYPED

**Asked:** A client pays MORE than the bill — say $745 against a $645 invoice. What should happen?

**Chose:** obviously 1 makes sense - except i am not eating a fee for them doing it... right?

### 2026-09-02 22:56:34  · TYPED

**Asked:** The production Square location id is still a [CONFIRM:]. When do you want to do the real $1 charge that proves you actually get paid?

**Chose:** here is the prod ID sq0idp-kaxxfnVnOVaRMxB0U2gj4w

### 2026-09-03 00:17:15

**Asked:** The design wants a progress bar on every client. It drew nine steps; the software can only tell seven apart, and your own process runs two different orders (your letters promise bill-then-file, but most engagements bill after filing). What should the bar do?

**Chose:** Show which steps are done, no count (Recommended)

### 2026-09-03 00:17:15

**Asked:** The design adds a standing line at the top of every screen: today's date, the next tax deadline, and how many clients are due before it. The date is derived from statute and correct. The count isn't — the season board doesn't count extension deadlines, so it would read zero on the very date the line names.

**Chose:** Date only for now (Recommended)

### 2026-09-03 00:17:15

**Asked:** Three pages exist only to confirm something worked. The design would delete them and put you straight on the client's file instead. Which would you drop?

**Chose:** the pack one - so like, i think i get what you are saying but is it mean to be a call to read it all or a call to ensure anything it flags is resolved,"Engagement created" (Recommended),"The new quote is recorded" (Recommended)

### 2026-09-03 00:17:15

**Asked:** The last screen before an engagement is created lists every answer with a "Change" button beside it — thirty-seven of the same word down one page. The design makes the row itself clickable and shows the word only on the row you're pointing at or have tabbed to. Nothing changes for the keyboard; a touchscreen loses the visible target until you touch it.

**Chose:** Do it — I use a laptop (Recommended)

### 2026-09-03 00:19:34

**Asked:** The screens now say `fine` / `stops it` / `nothing to look at` where they used to say `ok` / `FAIL` / `NONE`. The terminal still says the old words — so the same check reads `FAIL` in one place and `stops it` in the other. Which wins?

**Chose:** Terminal follows the screen (Recommended)

### 2026-09-03 00:19:34

**Asked:** The design assumed the document shelf could say "built this morning, 08:52 · eleven checks, all fine" under each document. Nothing records when a document was built or what it passed, so that line would be invented. Worth building?

**Chose:** Yes — build it (Recommended)

### 2026-09-03 00:19:34

**Asked:** The design also wanted the interview to show a running summary of what the client has said so far, pinned beside the question. There's no such summary today — it would be new work. Worth building?

**Chose:** Yes, but after the build record (Recommended)

### 2026-09-03 12:21:04

**Asked:** Does real client data live on the forge — the actual leads workbook and real engagements — or does the forge run on synthetic data only?

**Chose:** Yes — the forge is where the practice runs

### 2026-09-03 12:21:04  · TYPED

**Asked:** Git backs up the code. What backs up the client data — the leads workbook, the engagements, the vault — which is deliberately NOT in git?

**Chose:** nothing yet - you know this based on our standing interview items

### 2026-09-03 12:21:04  · TYPED

**Asked:** What should I prove first once I'm on the forge?

**Chose:** Does the whole suite even run there

### 2026-09-03 21:19:54  · TYPED

**Asked:** With the forge session doing the hands-on building on the real machine, what do you want me to be?

**Chose:** i'll tell you

### 2026-09-03 21:26:39

**Asked:** What is this repo's PRIMARY job? Everything else — the naming, the mining, the new-project prompt — hangs off this answer, so I want to get it right before descending.

**Chose:** It installs itself into every project (Recommended)

### 2026-09-03 21:32:45

**Asked:** A tenet's power is its evidence — "if this rule had been in force, would that bug have shipped?" But the evidence is SATC's: commits, your own words, test docstrings. When a tenet installs into a brand-new project, what comes with it?

**Chose:** Evidence travels and accumulates (Recommended)

### 2026-09-03 21:35:59

**Asked:** When should the brain push back on you? This is the design decision that separates "keeps me in check" from "nags until I ignore it".

**Chose:** Only when you contradict yourself (Recommended)

### 2026-09-03 21:37:01

**Asked:** What does this brain govern? You have at least two lines running — the accounting practice, and the credit/macro analytics consulting work — and CLAUDE.md keeps them deliberately separate.

**Chose:** Everything you build, forever (Recommended)

### 2026-09-03 21:39:10

**Asked:** How does a conviction get onto the record — and stay accurate enough that being challenged with it doesn't feel like being misquoted?

**Chose:** It proposes, you confirm — in your own words (Recommended)

### 2026-09-03 21:41:08  · TYPED

**Asked:** What do you want to call it? You said you'd pick, so these are proposals to react to — tell me if none of them land and I'll go again.

**Chose:** it being... you?

### 2026-09-03 21:42:15  · TYPED

**Asked:** Given that — the name lands on a role any session steps into, and the plugin is that role — do the proposals still work, or do you want to name it yourself?

**Chose:** Different names for the role and the repo

### 2026-09-03 21:43:07

**Asked:** The REPO name — plain, searchable, ages well. Note it shouldn't be SATC-prefixed, since you scoped this to everything you build, forever.

**Chose:** canon (Recommended)

### 2026-09-03 21:43:07  · TYPED

**Asked:** The ROLE name — what you say out loud. Your Jarvis. Say the word if none of these sound right and I'll come back with a wider spread, sound-first with my reasoning stripped out.

**Chose:** Give me a wider spread

### 2026-09-03 21:45:08  · TYPED

**Asked:** Which one? Pick on sound — any name from the list above works, type it into Other if it's not one of these four.

**Chose:** no i just... want something more me. this is like the only thing i want to be more me than my disciplines. this sounds dumb but a deep cut reference to dance gavin dance, i love jon mess

### 2026-09-03 21:48:23  · TYPED

**Asked:** Which one? Any word from the table works — Other takes it. And if I've picked the obvious ones and missed the real deep cut, name it and it's done.

**Chose:** my love for DGD comes later. it starts with acceptance speech. instant gratification. i have evaporate tattooed onto my arm. i also like everything to date

### 2026-09-03 21:49:54  · TYPED

**Asked:** Which one? Any title from that era works — Other takes it.

**Chose:** the ones you had earlier sounded more like names

### 2026-09-03 21:56:49  · TYPED

**Asked:** Name-shaped, DGD where possible. Say it in a sentence: "—, what did I say about student pricing?"

**Chose:** not tilian for sure

gavin makes some sense though it's not quite a deep cut. is there something from the lore that makes sense? the robot with human hair if it rolled off the tongue. Count Bassy is kind of cute

### 2026-09-03 22:03:37

**Asked:** Landing it. "—, what did I say about student pricing?"

**Chose:** Count Bassy — called Bassy (Recommended)

### 2026-09-03 22:05:39

**Asked:** The raw material for the first mine is perishable. What do you want done about it?

**Chose:** Extract your own words now, mine later (Recommended)

### 2026-09-03 22:08:04

**Asked:** What is v1? Everything not in it still happens — it just happens second, once the first version has proved it survives contact with a real project.

**Chose:** The record and the challenge, installable (Recommended)

