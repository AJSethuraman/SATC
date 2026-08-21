# Website disclosures — draft

Drafted for the `website/` footer and intake form. **Not legal advice.** Two of
the three items below are statements about your own process, which is why they
are drafted rather than deferred. The third is the one that is actually a legal
question, and it is left open.

---

## What we are actually disclosing

Four candidates were on the table. Only one of them is a lawyer's question.

| # | Candidate | Verdict |
|---|---|---|
| 1 | What the firm is and is not | **Open.** The only real legal question. See below. |
| 2 | No advice from the website | **Drafted.** Standard, low-risk. |
| 3 | What the intake form does with their data | **Drafted.** A promise about your process, not law. |
| 4 | Circular 230 legend | **Dropped.** Largely obsolete since 2014. Adding it back signals a firm working from a decade-old template. |

---

## 2 · No advice from the website — DRAFT

Footer, below the copyright line, at 12–13px in `--ink-2`.

> The information on this site is general and is not tax, accounting, or legal
> advice for your situation. Reading it, or sending us your details through the
> form, does not create a client relationship — that begins when we both sign an
> engagement letter.

**Why it is worded that way.** The second sentence is the one that does the work:
it names the exact moment the relationship starts, which is a fact you control
and can prove. The common version — "does not constitute the formation of an
attorney-client or accountant-client relationship" — says less and sounds
borrowed.

**Shorter variant** if the footer is tight:

> General information, not advice for your situation. A client relationship
> begins when we both sign an engagement letter.

---

## 3 · What the intake form does — DRAFT

Directly under the submit button, or as the final step's helper text. This is
not a disclaimer; it is the answer to "what happens after I press this."

> **What happens next.** Your answers come to us by email. We reply within one
> business day — usually with questions, sometimes with a time to talk. Nothing
> is filed, charged, or shared with anyone on the strength of this form.
>
> **Don't attach documents here.** When we start work you will get a secure
> upload link. A tax return holds your Social Security number, your income, and
> your bank details, and email is not the place for it.

**Why it is worded that way.** The second paragraph is the same promise the
client portal screen makes and the same one the onboarding letter makes. Three
surfaces, one message: documents go through the secure channel, never email.
That consistency is worth more than any single wording.

**Two things to confirm before this ships** — both are yours, not counsel's:

- **"within one business day"** — is that the promise you want to make in
  writing? It is the strongest line on the page if true, and the most damaging
  if not. `AckWindow` in the onboarding letter should carry the same value.
- **"by email"** — accurate as long as `SATC_CONFIG` mails the submission and
  stores nothing. If a submission is ever persisted to a database or a
  third-party form service, this sentence has to change and a privacy policy
  becomes a real requirement rather than an optional one.

---

## 1 · What the firm is — STILL OPEN

**Do not draft this one.** It is the only item where a wrong sentence has a
regulator on the other end of it.

The facts, as supplied:

- SAT-C is a **limited liability partnership registered in Ohio**.
- Arjun is an **individually licensed Ohio CPA**.
- The firm is **not registered with the Accountancy Board of Ohio**.
- The firm **does not perform audits, reviews, or any attest work**.

Ohio generally requires a firm practising public accounting to register with the
Accountancy Board separately from the individual licence, and an unregistered
firm generally may not hold itself out as a "CPA firm". The site currently says
**"led by a licensed CPA"** — a statement about a person — which is the
conservative form and is very likely fine. The question is whether offering
paid tax and accounting services under a firm name requires registration
regardless of how the firm describes itself.

**The cheap way to close this:** call the Accountancy Board of Ohio and ask
directly. Fifteen minutes, no fee. Their answer settles this item, the firm's
self-description across the whole site, and the footer wording below.

**Placeholder until then** — factual, claims nothing:

> Sethuraman Accounting, Tax, and Consulting LLP is a limited liability
> partnership registered in Ohio. We do not perform audits, reviews, or other
> attest services.

That sentence is already what the document footers carry, minus the attest line.
It is safe because every word in it is a fact you can evidence. **Do not add to
it** — not "CPA firm", not "Certified Public Accountants", not a licence number
— until item 1 is answered.

---

## Where each one goes

| Text | Location | File |
|---|---|---|
| No advice from the website | Footer, under copyright | `website/index.html` |
| Firm status placeholder | Footer small print | `website/index.html` |
| What happens next | Under the intake submit button | intake markup — **not** `intake.js` logic |

None of these touch `intake.js`, `intake-config.js`, or `SATC_CONFIG`.
