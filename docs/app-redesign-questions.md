# The practice app's redesign — what needs an answer from the firm

A design for the app you use to run the practice arrived on 2 September 2026
(`satc-handoff/06-APP/`). Most of it is how things look, and that is being
applied without asking. Some of it would change how the software behaves, or
would put a number on screen that the software does not actually know, or would
delete a page you currently use. Those are below.

**Questions 1 to 5 are not built and are waiting on you.** Questions 6 and 7
are already done and are here so you can see them and object. Each says what is
being asked, what happens either way, and what I would do. Answer in a line
each.

---

## 1 · The bar that says "4 of 9"

**The design puts a nine-step progress bar on every client.** The nine steps
are: interviewed, priced, pack built, sent, signed, filed, billed, paid, closed.

**The software can only tell seven of the nine apart, and two of those seven it
cannot see at all from the browser.**

* "Interviewed" and "priced" happen in the same instant — the price is worked
  out when you press *Create the engagement*. Nothing is ever interviewed and
  not priced, so those are one step, not two.
* "Filed" and "closed" are also one thing: the only record of either is the
  close-out you answer at the end of the cycle, and that can only be done from
  the terminal today, not from a screen.
* The other five — pack built, sent, signed, billed, paid — the software knows
  exactly.

Drawing nine ticks when the software can distinguish seven is a number nobody
can check. This repository has a long record of exactly that going wrong.

**Either way:** a seven-step bar is honest today and is the same object; a
nine-step bar needs the close-out brought onto a screen and the filing recorded
as its own act, which is real work and worth doing on its own merits.

**My recommendation:** draw seven, named as the software knows them — *sitting
done · pack built · sent · signed · billed · paid · closed*. Add the eighth and
ninth when filing is recorded separately from closing.

**The question:** seven now, or wait and do nine properly?

---

## 2 · Do you bill before you file, or after?

The bar in question 1 only works if the steps happen in one order. **Yours do
not, and your own letter says so.**

* Every engagement letter promises: *we will not e-file a return before the
  invoice for it is settled.* That says **bill, get paid, then file**.
* The software's own note beside that check says most engagements **bill after
  filing**, and it deliberately does not block those.

Both are true of different clients. A bar counting one-two-three would run
backwards for whichever kind is not the one it was drawn for.

**Either way:** if there is one house order, the bar counts and is useful. If
there genuinely are two, the bar has to show which steps are done rather than
how far along, and that reads differently.

**My recommendation:** show the steps that are done, with no running count, so
it is right for both. It loses "how far along" and keeps the truth.

**The question:** is there one order you want every engagement to follow, or do
you want the screen to accept both?

---

## 3 · The line at the top: "4 clients due before 15 September"

The design adds a standing line to the top of every screen: today's date, the
next tax deadline, and how many of your clients are due before it.

**The date half is safe.** The software already works the calendar out from the
statute — 15 September 2026 for partnerships and S corporations on extension is
right, and it is derived, not typed.

**The count half is not.** The software's season board only counts two kinds of
date — when papers are due in, and the ordinary filing deadline. It does not
count extension deadlines, so "4 clients due before it" would be counting
nothing on the very date the line names.

**Either way:** the line goes up with the date only, and gains the count when
the board is taught about extensions (small, and worth doing). Or the count goes
up now, and is wrong.

**My recommendation:** put the date up now, leave the count off until the board
counts extensions. A wrong count at the top of every screen is worse than no
count.

**The question:** happy with the date alone to start?

---

## 4 · Three pages the design would delete

Each of these is a page you land on after pressing something. The design would
remove them and put you straight on the client's file instead.

| Page | What it says now | What you would get instead |
|---|---|---|
| **"Engagement 2026-0001 created"** | Three buttons, one of which you always press | The client's file, with a line at the top saying it was just made |
| **"The pack, and every check that passed"** | The eleven checks, and nothing to press | A line on the page you came from: built this morning, eleven checks, all fine |
| **"The new quote is recorded"** | One sentence confirming it | The client's file with the new figure on it |

**Either way:** each deletion is one fewer press and one fewer page to read. The
cost is that the confirmation disappears — you find out it worked by seeing the
result rather than by being told.

**My recommendation:** delete the first and the third; keep the second. The
eleven checks before a pack goes to a client is the one place in the software
where reading the page *is* the work, and folding it into a line invites nobody
to read it.

**The question:** which of the three, if any?

---

## 5 · The thirty-seven "Change" buttons on the last look

The screen before an engagement is created lists every answer with a *Change*
button beside each. The design keeps the screen and removes the buttons: the
row itself becomes clickable, and the word appears only on the row you are
pointing at or have tabbed to.

**Either way:** the page gets much easier to read a wrong answer off. Nothing
is lost for the keyboard — tab order is unchanged and the word appears when you
land on a row. Someone using a touchscreen loses the visible target until they
touch it.

**My recommendation:** do it. Do you use this on a tablet or only on a laptop?

---

## 6 · A third colour, for "waiting on you"

`[CONFIRM: ...]` is what a document prints where a sentence is yours to write
and the software refuses to invent one. Today it looks like an error.

The design gives it its own colour — burnt orange, `#A8571C` — used for nothing
else, ever. Navy means the firm acting; oxblood means a refusal; orange means
the software is waiting on you.

I have checked it: it is legible on the page and as a white-on-orange chip, and
in black and white it is further from oxblood than oxblood is from navy — so it
does not rely on colour alone. It is being applied now, because it states no new
fact.

**The question, and it is only a check:** any objection to a third colour
entering the brand for this one meaning?

---

## 7 · Words on your screens the design would change

None of these is a sentence a client reads. All are labels you read.

| Now | Would become |
|---|---|
| `11 check(s), and what each one actually looked at.` | `11 checks. What each one read is on the right.` |
| `ok` / `FAIL` / `NONE` | `fine` / `stops it` / `nothing to look at` |
| `Built and checked. 4 document(s) in /tmp/.../pack` | `4 documents, built and checked. Nothing has been sent.` |
| `plain — SAT-C Engagement Letter - Reyes - 2026.html` | `no banned legalese and no British spelling — Engagement Letter` |
| `1 of 1 bill(s) outstanding, as of the last time the card processor was asked.` | `1 of 1 bill unpaid, as of the last time the card processor was asked.` |
| `Send it anyway, and record that` | `Send it past these checks` |
| `Prices` | `What the firm charges` |
| `HARD NO` in red inside an ordinary box | a red edge on the row, and `the firm says no` beside the tick |

**All of these are applied.** The filename and the file path were already wrong
by your own rule — they are the same thing you objected to on 2 September.

Two things the design asked for that were **not** done, and why:

* It wanted the payments line to read *"Last checked with the card processor at
  08:14 today."* Nothing in the software records when it last asked, so that
  time would have been made up. The existing, vaguer sentence is the true one.
* It wanted the pack's folder taken off the screen. It stays, moved out of the
  headline: nothing in the browser actually sends a pack, so that line is the
  only thing telling you where the files you have to attach are. It comes off
  the day there is a send button.

**The one question here:** `ok` / `FAIL` / `NONE` is also what the terminal
prints, and the terminal has not been changed — so the same check now reads
`FAIL` in one place and `stops it` in the other. Should the terminal follow the
screen, or keep its own shorter words?

---

## What is being applied without asking

Everything that is only how it looks and states no new fact: the stylesheet, the
spacing and type, a visible outline wherever the keyboard is, the five state
marks on the checks before a pack goes out, the burnt orange for
`[CONFIRM: ...]`, the counts written as `11 checks` rather than `11 check(s)`,
and the wording fixes in the table above.

**Not applied, and waiting on this page:** the stage bar, the count in the
season line, every deletion, and the change to the *Change* buttons.

Two more the design assumed and the software does not have, so they are not
oversights either. The document shelf would say *"built this morning, 08:52 ·
eleven checks, all fine"* on each document — nothing records when a document was
built or how many checks it passed on its own. And the interview would gain a
running summary of what the client has said so far, pinned beside the question —
there is no such summary today; it would be new. Both are worth building. Say if
either is worth building first.
