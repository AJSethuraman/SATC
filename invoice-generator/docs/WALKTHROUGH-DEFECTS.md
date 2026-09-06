# Walking Invoicer: fourteen defects a green suite did not catch

**Job walked:** raise an invoice for a client, send it, and record the payment.
**When:** 6 September 2026. **Where:** a real Chromium, clicking the real interface,
against `claude/invoice-generator-snfbjk` at `445eee1` with a fresh database.
**The route is written up separately** in `docs/walkthrough/invoice-and-get-paid-2026-09-06/`
— that half is for whoever does the job; this half is for whoever fixes it.

This is the second walk in two days and the first of Invoicer. The desk and the
engagement browser were walked on 5 September; that write-up is at the repository
root, in `../../docs/WALKTHROUGH-DEFECTS.md`.

## The denominator

| | |
|---|---|
| `pytest` in `invoice-generator/` | **325 passed, 1 skipped** |
| `exercise.py` | **289 checks · 278 ok · 0 FAILED · 608 compared · 53 PDFs opened** |
| Of the fourteen below, caught by either | **none** |

Not one of these is a wrong *number*. The arithmetic held everywhere I checked it —
2,935.00 less a 100.00 discount, 8.25% of the 2,835.00 that leaves, 3,068.89 —
in the editor, in the PDF, in the email and on the client's page. What a suite
cannot be surprised by is a document that is correct and still unusable, a
promise on one screen that no code path can keep, and a feature nobody signed in
can reach.

---

## 1 · Every invoice emailed to a client is stamped DRAFT

**Cost: the client's accounts department bounces it, and we chase a payment that was never going to be made.**

**What I did.** Saved the invoice, pressed **Send invoice**, opened the attachment
on the mail that arrived.

**What the screen said.** *Invoice sent — to ap@northwind.example.* Status: **Sent**.

**What was actually true.** The attached PDF carries a **DRAFT** badge. Downloading
the same invoice from the same page a minute later gives a PDF that reads **SENT** —
so it is not the invoice, it is the moment. `email_invoice` renders the PDF at
`app.py:1573` and only then flips the status at `app.py:1605`. The file the client
receives is always one state behind. Reproduced on a clean database.

**The fix.** Move the status change ahead of the render, inside the same
transaction as the send, and roll it back if the send raises — the flip must not
outlive a failed send. A test that asserts the *attachment* has no DRAFT badge,
not merely that a PDF was attached.

---

## 2 · The signed-out generator can only ever produce a DRAFT PDF

**Cost: the product's front door hands a first-time visitor a document they cannot send.**

**What I did.** Filled in the generator with no account and pressed **Download PDF** —
the exact path the landing page advertises (*"No account. Nothing to install. Type
it, pick a look, download the PDF."*).

**What the screen said.** The editor shows no status anywhere. The right-hand panel
says only that the file is made and no copy is kept.

**What was actually true.** `_generator_invoice` sets `invoice.status = "Draft"` on
the transient invoice and the page offers no control to change it, so **DRAFT is the
only output this door can produce**. The one thing an anonymous visitor came to do,
they cannot do.

**The fix.** Decide what an unsaved invoice's status *is*, and it is probably
nothing: suppress the badge when the invoice has no owner, or give the generator a
document-status control. Either is a five-line change; the choice is the firm's.

**Whose it is.** The badge itself is older than this branch — `main` stamps
`display_status` on the PDF too (`invoice_pdf.html:150`), so defect 1 has been live
for as long as sending has. What is new here is a door that can produce *nothing
else*, and that arrived with the generator.

---

## 3 · The plain-text half of the email says "Pay online here" when nobody can pay online

**Cost: the AP mailbox that reads text-only is sent to a page with no payment on it.**

**What I did.** Read both halves of the multipart email the product sent.

**What the screen said.** The HTML half is correct — *"you can review it"*, and the
button reads **View invoice →**, because round four taught it to ask whether payment
is possible.

**What was actually true.** The text half is unconditional:

```
Please find attached invoice SATC-2026-0184.

Pay online here: http://…/i/MQ.apze0w…
```

Stripe is not connected. `email_invoice` passes `payment_url=public_url` to
`send_invoice_email` (`app.py:1590`), and `email_utils.py:189` prints the pay line
whenever that argument is non-empty. **The two halves of one email disagree**, and
the round-five fix reached the half people look at.

**The fix.** Pass `_pay_url(invoice)` rather than `public_url` — the helper that
already exists for exactly this — and keep the view link separately. While in there:
the text body carries no amount and no due date, which `exercise.py` has recorded as
known since before this branch.

---

## 4 · The 48 designs are unreachable the moment you sign in

**Cost: the headline feature of this branch is available only to people who do not have an account.**

**What I did.** Signed up, then looked for the editor I had just been using.

**What the screen said.** The signed-in bar offers **Invoices**, **Account** and
**New invoice**.

**What was actually true.** There is no link to `/generator` anywhere in the
signed-in app — I checked every anchor on the page, not just the chrome, and the
count is zero. **New invoice** goes to `/new`, which is the older form: no live
document, no design gallery, a different layout for the same job. So an owner can
never choose a design for an invoice they raise the normal way, and cannot change
the design on one they already have.

**The fix.** Point **New invoice** at `/generator`, or add the editor to the
navigation. The two front doors already share `_populate_invoice_from_form`, so this
is routing, not a rewrite. What to do with `/new` afterwards is a separate decision.

---

## 5 · The design you choose is honoured by the PDF and by nothing else

**Cost: the owner picks a look, and every screen they and their client actually read shows a different one.**

**What I did.** Chose `band-emerald`, saved, then compared the three surfaces.

**What the screen said.** *"Switching a design keeps everything you have typed."*
The PDF is emerald.

**What was actually true.** The owner's invoice page and the client's public page
both render the default navy — computed `background-color` `rgb(39, 52, 80)` on the
table header of each — and the string `band-emerald` does not appear in either
page's HTML at all. One of three surfaces obeys the choice.

**The fix.** `invoice_detail.html` and `public_invoice.html` need the same
`resolve(invoice.design)` and stylesheet include the PDF template already uses. The
markup is identical across all 48 designs by construction, so this is a stylesheet
link, not a re-layout.

---

## 6 · The client's page leads with our branding, not the sender's

**Cost: it contradicts a decision the firm has already recorded.**

**What I did.** Opened the public link in a browser that had never seen the app.

**What the screen said.** *Invoicer* — logo and wordmark — centred above everything,
and *Powered by Invoicer* in the footer. The sender's name is further down, inside
the document.

**What was actually true.** D-5, answered by the firm and recorded as conviction
**C15**: **"Client's branding only."** The one page built specifically for a client
to look at opens with ours.

**The fix.** Drop the masthead from `public_invoice.html` and let the invoice's own
letterhead be the first thing. Whether any attribution survives in the footer is the
firm's call, not a developer's.

---

## 7 · Signing up from the editor drops you somewhere else, with no way back

**Cost: a first-time user reaches the point of committing and is put in a settings screen.**

**What I did.** Pressed **Save & send it** with a finished invoice on the page.

**What the screen said.** The link goes to `/signup?next=/generator`. After
submitting: *Welcome! Your account is ready.*, on `/account`.

**What was actually true.** The `next` parameter is ignored — the landing page is
`/account` — and, per defect 4, nothing in the signed-in navigation leads back to
the editor. The only reason this is not data loss is that the draft is held in
`localStorage` and is still there when you type the URL yourself. That is a
consolation, not a design: it is per-browser and per-machine, so the same journey on
a phone after signing up on a laptop starts from an empty page.

**The fix.** Honour `next` on signup. It makes defect 4 less sharp but does not
replace it.

---

## 8 · Notes and Terms are shown on the document for the whole session and print nothing

**Cost: the sender believes their payment terms are on the invoice. They are not.**

**What I did.** Left the Notes and Terms blocks alone — they read *"Thank you for
your business."* and *"Payment due within 14 days."* — and downloaded the PDF.

**What the screen said.** Both lines, in place, in the document, in grey, in every
screenshot from step 2 onwards.

**What was actually true.** They are `placeholder` attributes. The PDF has no notes
block and no terms block at all. Grey is doing the whole job of distinguishing
"example" from "content", on a page whose entire premise is that what you see is
what prints.

**The fix.** Either print the defaults when the fields are empty, or render the
prompts somewhere that is visibly not the document — a hint under the block rather
than inside it. The first is friendlier and matches what the sender already believes.

---

## 9 · The new-invoice form promises a pay-online link the site cannot send

**Cost: the same false promise as defect 3, on the screen where the owner is deciding what to send.**

**What I did.** Opened **New invoice** while Stripe was not configured.

**What the screen said.** A blue panel: *"This invoice will be sent from
billing@satcllp.example with a secure pay-online link."* On the Account page, at the
same time: *"Stripe isn't configured on this site yet, so online payments are
unavailable."*

**What was actually true.** The second one. The panel is unconditional.

**The fix.** Gate the panel on `current_user.can_accept_payments`, and say what will
happen instead when it is false.

---

## 10 · An account can default to 6 currencies; an invoice can be raised in 157

**Cost: an owner who bills in one of the other 151 re-picks the currency on every invoice.**

**What I did.** Compared the Account page's **Default currency** dropdown with the
generator's.

**What was actually true.** Six options against `currencies.py`'s full table. The
account settings predate the currency work on this branch and were not brought along.

**The fix.** One shared choice list. Worth pairing with the payment allowlist, so the
list can say which of them can be paid online.

---

## 11 · A workspace bringing its own SMTP cannot turn TLS off

**Cost: an internal relay on port 25 cannot be used, with no explanation on screen.**

**What I did.** Read the **Bring your own SMTP** block: host, port, username,
password. No TLS control.

**What was actually true.** `email_utils.py:72` sets `"use_tls": True` for the
custom-SMTP path, and `_deliver` calls `starttls()` whenever that is set and the port
is not 465. A server that does not advertise STARTTLS fails, and the owner has
nothing to change.

**The fix.** A checkbox, defaulting to on. Off is a real configuration, not a
mistake, and the field is beside three others that are already free text.

---

## 12 · No favicon

**Cost: small, and it is on the tab the client has open while deciding to pay.**

`GET /favicon.ico` returns 404 on every page load, so the client's invoice tab shows
the browser's blank-page icon. For a product whose pitch is that the invoice looks
professional, the tab is part of the invoice.

---

## 13 · The editor prints figures the document never would

**Cost: cosmetic, on the surface whose whole claim is that it is the document.**

Two of them, both visible in step 5 of the procedure:

* **Amount paid** reads **−$0.00** when nothing has been paid. The PDF correctly
  omits the row entirely.
* **Unit price** shows the raw typed value — `1450` — while the AMOUNT cell beside it
  reads `$1,450.00` and the PDF renders both as money.

**The fix.** Suppress the amount-paid row at zero, as the PDF does, and format the
unit-price input on blur.

---

## 14 · One Activity entry has no date

**Cost: trivial, and it is the entry somebody will one day need to date.**

*Invoice created* and *Marked paid* each carry a date. *Invoice sent* carries the
recipient instead. When a client says they never received it, the send is the entry
you go looking for.

---

## What this run says about the suite

The suite is not weak — 325 tests and a 289-check harness caught the arithmetic,
the ledger, the currency conversion and the refusals, and every one of those held up
under a real browser. What it could not do is notice that:

* a correct document is stamped with the wrong word (1, 2);
* one half of an email contradicts the other (3);
* a feature exists and cannot be reached (4);
* a choice is honoured on one surface out of three (5);
* a page contradicts a decision the firm recorded in writing (6).

Each needs somebody to know what the thing is *for*. The nearest a test could get is
defect 1 — assert the attachment carries no DRAFT badge — and it is worth writing,
because that one costs real money.

Two of these are mine from this branch and recent: defect 3 is the round-five
payment-invitation fix reaching the HTML body and not the text one, and defect 5 is
the design system stopping at the PDF. Both were introduced by work that was reviewed
five times, by a reviewer that reads diffs — which is an argument for walking *as well
as* reviewing, not against either.

Defects 1, 8, 9, 11 and 12 are older than this branch and were simply never looked at
from the client's side of the screen.
