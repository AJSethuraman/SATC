# Getting a signature: what the rules are, and what it would cost

Research for the one gap that stops the practice-ops pipeline being usable —
the pack builds, gets checked, and then a human emails it and chases. This is
what would have to be true to automate that.

---

> ## ⚠ READ THIS FIRST — none of the regulatory wording below was read by eye
>
> The session this was gathered in runs behind an egress proxy whose policy
> **denies `irs.gov`, `govinfo.gov`, `uscode.house.gov`, `codes.ohio.gov`,
> `ecfr.gov` and `ftc.gov`** — every request returned `403` on CONNECT. Every
> vendor domain was blocked too.
>
> So the URLs cited here are the real primary sources, and the substance was
> recovered from search indexes **of** those documents, but **nobody has opened
> `p1345.pdf` and confirmed the sentences.**
>
> `docs/SOFTWARE-TENETS.md` S1 exists for precisely this: a proof artifact once
> declared 190 documents fine when every one was unreadable. **Before a line of
> this is built against, or a word of it reaches a client, someone must open the
> PDFs and check.** Each claim below is marked ✓ *cited, unread* or ✗ *could not
> verify at all*.

---

## 1 · These are two different problems, not one

The single most useful finding. The two documents a client signs are governed by
different law and need different machinery.

| | The engagement letter | Form 8879 |
|---|---|---|
| What it is | A private contract | An IRS e-file authorization |
| Governed by | ESIGN Act + Ohio UETA | IRS Publication 1345 |
| Identity proofing | None required | Knowledge-based authentication, every remote signature |
| Who produces it | **This repository** | **Drake** |
| What a click-to-sign needs | A timestamp, an email trail, a stored copy | A six-element record, retained three years |

**Consequence: the 8879 is not a coding problem here.** None of the twelve
templates in `satc-handoff/04-TEMPLATES/` is an 8879 and none ever will be —
Drake makes it. Automating *that* signature is a Drake Portals purchase, not a
change to `client-documents/`. What this codebase can automate is the
engagement letter and the records release.

## 2 · Form 8879, remote signature

✓ *cited, unread.* Governing document: **Publication 1345 (Rev. 12-2025)** —
https://www.irs.gov/pub/irs-pdf/p1345.pdf

- **Remote** = the taxpayer e-signs and the ERO is not physically present. The
  ERO must record the taxpayer's name, SSN, address and date of birth, verify
  those against record checks with the applicable agency, credit bureaus or
  similar databases, and perform identity verification per **NIST SP 800-63
  Level 2 assurance and knowledge-based authentication**, or higher.
- **In person**, the ERO inspects a valid government picture ID and compares it
  to the taxpayer. KBA is not required, and the database checks are optional.
- **There is no remote exception.** Identity verification is required *every
  time* a taxpayer e-signs Form 8878 or 8879. The multi-year-relationship
  exception applies **only** where the taxpayer signs in the ERO's physical
  presence. **A returning client signing from their kitchen still needs KBA.**
- **Three failed KBA attempts → the ERO must obtain a handwritten signature.**
  That is a real branch a workflow has to handle, not an edge case.

**The record that must be retained** (produced on IRS request): the digital
image of the signed form; the date and time of signature; the taxpayer's IP
address *(remote only)*; the taxpayer's login identification *(remote only)*;
the identity-verification result — the KBA passed result remotely, or
confirmation that picture ID was verified in person; and the method used to
sign, or a system log showing the signing process completed.

✗ **Could not verify at all:** that "tamper-evident" is Pub 1345 language.
Vendors assert it. Treat it as a vendor claim until the PDF is read.

**Retention:** three years from the return due date or the date the IRS
received the return, whichever is later. Not sent to the IRS unless requested.
May be kept electronically under **Rev. Proc. 97-22**, which requires an
indexed, retrievable, legible, auditable storage system.
✓ https://www.irs.gov/pub/irs-pdf/f8879.pdf

**Entity returns.** The current forms are **8879-CORP** (Rev. 12-2024 — covers
1120, 1120-F *and* 1120-S; it replaced 8879-C and 8879-S) and **8879-PE**
(Rev. 12-2025 — Form 1065).
✓ https://www.irs.gov/forms-pubs/about-form-8879-corp ·
https://www.irs.gov/forms-pubs/about-form-8879-pe

> ✗ **Genuinely unresolved, and the software must not assert either way.**
> Pub 1345's e-signature section speaks to Forms 8878 and 8879. Business MeF
> returns are governed by **Pub. 4163**, and it could not be confirmed that
> 4163 imports the KBA/NIST regime onto 8879-CORP and 8879-PE. Build so KBA
> *can* be applied to entity forms; get the answer from the PDF or the IRS
> e-Help Desk before shipping any copy that makes a claim.

## 3 · The engagement letter needs none of that

✓ *cited, unread.* **ESIGN Act, 15 U.S.C. § 7001(a)** — a signature or contract
"may not be denied legal effect, validity, or enforceability solely because it
is in electronic form."
https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section7001

**Ohio's UETA is Ohio Revised Code Chapter 1306** (effective 14 Sept 2000).
**§ 1306.06(A)** gives electronic records and signatures legal effect;
**§ 1306.08** makes an electronic signature attributable to a person where it
is shown to be that person's act, provable "from the context and surrounding
circumstances."
https://codes.ohio.gov/ohio-revised-code/section-1306.06 ·
https://codes.ohio.gov/ohio-revised-code/section-1306.08

**Plainly: a click-to-sign with an email audit trail is legally sufficient for
an engagement letter.** No KBA, no photo ID, no NIST level. The audit trail —
email address, timestamp, IP, the version of the document that was shown — *is*
the attribution proof § 1306.08 asks for.

## 4 · Obligations that come with choosing a vendor

- ✓ **FTC Safeguards Rule, 16 C.F.R. Part 314.** A tax preparer is a "financial
  institution" and must keep a written information security program (§ 314.3)
  — Qualified Individual, written risk assessment, encryption, MFA, training,
  incident response, annual report (§ 314.4). Technical requirements mandatory
  since **9 June 2023**. https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314
- ✓ **A signing vendor is a "service provider" under § 314.4(f).** The firm must
  select providers capable of appropriate safeguards, **require those
  safeguards by contract**, and periodically assess them. A real procurement
  step — the vendor contract has to be on file.
- ✓ **IRC § 7216 / 26 C.F.R. § 301.7216-2(d).** Disclosing return information to
  the signing vendor is permitted without taxpayer consent as an auxiliary
  service, but only what is *necessary* to obtain the service. Exceeding that
  is a § 7216 / § 6713 penalty. https://www.law.cornell.edu/cfr/text/26/301.7216-2
- ✓ **Pub. 4557, Safeguarding Taxpayer Data** — the IRS-side companion, same
  service-provider evaluation duty. https://www.irs.gov/pub/irs-pdf/p4557.pdf
- ✗ **No US-storage rule was found.** Rev. Proc. 97-22 governs the system's
  qualities, not its geography. **The software must not imply a residency rule
  exists.**

## 5 · Vendors

All figures fetched 28 Aug 2026 from search summaries; **every vendor domain
was blocked**, so no pricing page was read directly. Confirm before buying.

| Vendor | 8879 + real KBA | Public API | Solo price | Sandbox |
|---|---|---|---|---|
| **Drake E-Sign / Portals** | **Yes** — a separate "KBA E-Signature Event", required for 8878/8879 | No | $2.25 per KBA event, $1.00 basic, 5-event minimum | — |
| **DocuSign** | Yes, via ID Check — **metered add-on, not in Personal/Standard/Business Pro**, ~$2.40–2.50/attempt | **Yes**, strong | Standard $25/user/mo annual, **100 envelopes/user/yr cap** | Yes, free |
| **Dropbox Sign** | **No native KBA** — SMS only | Yes, excellent | API Essentials $75/mo; UI from $15/user/mo | Yes, free test mode |
| **ShareFile / RightSignature** | Yes | Yes | Premium claims KBA at no extra cost; **price unverified** | Unverified |
| **SignNow** | Exists; plan gating unclear | API **only on Site License**, ~$1,000–1,750/yr | ~$30/user/mo | Yes |
| **Adobe Acrobat Sign** | Yes, but **enterprise licence only** | Yes | Sales-quoted | Paid add-on |
| **Encyro** | **See the flag below** | **No public API** | Pro $9.99/mo annual | — |
| **Verifyle** | Claims 8878/8879 compliance; mechanism unverified | No | $108/yr; free to CPA-society members | — |
| PandaDoc / Nitro | No | Yes | — | Yes |

### Encyro — disputed, and the firm is closer to it than this research was

> **The firm, 28 August 2026: "No encyro is cheaper and has kba."**
>
> That is a direct contradiction of the flag below, from somebody who has the
> product in front of them. The flag is kept because it is what was found, not
> because it is believed to outrank that — and the evidence behind it is weak:
> **encyro.com was blocked from this session**, so it rests on a search-index
> summary of the *title* of a help article, not on the article.
>
> **One question settles it, and it should be asked in writing before any
> 8879 goes through:** *does Encyro's 8879 e-signature use knowledge-based
> authentication generated from credit-file or public-record data meeting NIST
> SP 800-63 IAL2, or does it use an SMS access code?* An answer naming the KBA
> data provider closes this permanently. Keep the reply.
>
> If the answer is real KBA, **Encyro wins on price outright** and the rest of
> the vendor table below is moot: it is already paid for, already named in the
> client-facing copy, and covers both documents.

### 🚩 What was found, and why it raised a doubt

**Every engagement letter tells the client: "We send documents for signature
through Encyro."** So this matters more than a vendor comparison normally
would.

Encyro markets e-sign for 8879 "with KBA", but its own help article is titled
*"access codes by text (or knowledge based authentication)"* and the mechanism
it describes is an **SMS access code at 16¢ each**, pitched in its own
marketing as easier than *"traditional KBA (credit report based)"*. That is an
admission that it is not credit-bureau KBA. **An SMS code is a possession
factor; Pub 1345 asks for a knowledge factor drawn from non-public records.**

On that evidence the claim and the documentation did not match. **On the
firm's evidence they do.** The written confirmation above is what decides it;
until then this is an open question, not a finding.

Adobe is the second flag, more honestly disclosed: real KBA, enterprise plans
only. Dead for a one-person firm.

## 5b · How a program could originate an Encyro send

Asked directly: *is there any way to automate sending for signature through
Encyro?* Investigated 28 Aug 2026. **Every `*.encyro.com` host is blocked from
this environment**, so all of the below is recovered from search-engine
snippets of Encyro's own help articles; each names the article so it can be
checked in one click from an unblocked machine.

| Surface | Verdict |
|---|---|
| Public REST API | **No.** `api.encyro.com` is real and appears in Encyro's own allowlist guidance (`help/article/244`), but it is the web app's and the Outlook add-in's own backend — the add-in stores *"a login token (not your password)"* against it (`article/133`). No developer portal, no key, no docs. Review aggregators state flatly that Encyro provides no API |
| Send-by-email / SMTP relay | **No.** Encyro explicitly refuses to issue an inbound secure address — *"You cannot place an encrypted email address … on your business card"* (`article/86`). Inbound is a web upload page. No SMTP host appears anywhere |
| **Outlook add-in keyword** | **Yes, and it is the one hook.** *"Keyword based secure send: Simply type '[Secure]' … in the email subject line to automatically send the email securely"* (`article/212`). It is the add-in intercepting a send **on your own machine** |
| Gmail add-on | **No.** *"The Encyro Addon can never start by itself — you must always click to start it"* (`article/207`) |
| Zapier / Power Automate / Make | **No connector** in any of the three directories |
| Watched folder / SFTP / bulk CSV | **No.** Cloud storage is manual desktop sync (`article/78`) |

**What an e-sign request actually needs** (`article/180`): the file, **signature
fields placed on the page**, signer email addresses, an optional signing order,
and a subject/document title. **Dynamic File E-Sign Templates** save the field
placements so only the file changes between clients — the feature that makes
repeat sending fast, and a web-interface feature.

**KBA is per-request and priced per-request** — SMS access codes *"starting
from 16¢ per request, with the first 25 free"* (`blog/easy-e-sign-for-8879-kba`).
That is the same evidence that raised the doubt in §5; the written question
there is what settles it.

### So: what can and cannot be automated

**Sending the documents securely: yes.** The `.eml` this software writes opens
in Outlook already addressed, attached and written; with `[Secure]` in the
subject the add-in routes it through Encyro on send. One press, no stored
credential, no website driven. `registry/signing.yaml` carries the keyword as a
setting, **off by default** until somebody has sent one to themselves and
checked whether the add-in strips it — Encyro says elsewhere that a subject line
is not encrypted, so an unstripped keyword is something the client reads.

Fully hands-off is possible on Windows: `pywin32` can drive Outlook to build
and send that message. It was **not built** — this environment is Linux and
cannot run it, and shipping Windows-only code nobody has executed is the
failure S28 was written about.

**Asking for the signature: no.** Nothing suggests a keyword or an email can
place signature fields on a page. That is the web interface, made quick by a
saved template. Driving it with a browser script is possible and argued against
here: MFA is a control the Safeguards Rule requires and an RPA login degrades
it, a UI change breaks the script silently on a client-facing send, and portal
terms commonly forbid it.

**A hook worth using.** The request's subject/document title is unencrypted and
**you set it** — so putting the engagement ref in it means the ref echoes back
through the completion email, which is what makes the return leg parseable. The
composed subject already carries it.

### The one email to Encyro

> We are a one-person CPA firm and want our own software to originate Encyro
> e-sign requests without anyone using the web interface. Three questions:
> (1) Is there a documented HTTP API on api.encyro.com — even partner-only or
> under NDA — that can upload a PDF and create an e-sign request against a
> saved template, and how do we apply for a key? (2) Does the `[Secure]`
> subject keyword work anywhere other than the installed Outlook add-in — is
> there an SMTP relay we can authenticate to, or an address we can email or
> BCC, to originate a secure message or an e-sign request? (3) What is the
> exact subject line and body format of the notification email you send when a
> signer completes a request, and does it include a stable request ID we can
> parse?

Add the KBA question from §5 and one email closes every open item here.

## 6 · What this points at

> **Superseded by the firm, 28 August 2026: "Drake can print our 8879."**
> That removes the reason to buy Drake E-Sign. If Drake produces the PDF and
> Encyro carries the signature, there is one vendor, one subscription, and the
> 8879 never touches this codebase — which it never could anyway.

**Form 8879 → Drake E-Sign.** Drake already makes the 8879 and is the system of
record for what gets filed; routing it to a third party adds an integration for
no gain. That Drake sells a *distinct* KBA event type is the strongest evidence
in the survey that its KBA is the real credit-file kind. Having no API does not
matter — this codebase does not produce 8879s. **$2.25 per event.**
✗ Could not verify whether Drake meters per event or per signer; on a joint
return that is the difference between $112 and $225 a year. Ask them.

**Engagement letters → either.** With an API: **DocuSign Standard, ~$300/yr**,
upload → envelope → webhook → signed PDF and certificate, free developer
sandbox, and 50 letters sits comfortably under the 100-envelope cap. Without
one: **keep Encyro at ~$120/yr** and send by hand — it is already in the
client-facing copy, which under this repo's "change nothing a client reads"
rule has real value.

**Realistic total for 50 returns: roughly $230–$415 a year**, plus Drake
Portals itself if not already held. **Square is untouched** — none of these
vendors bundles or requires a payment processor.

## 7 · What was built against this

`client-documents/signing.py` — the register, deliberately vendor-independent:
who must sign what (censused from the templates' own signature blocks, so it
follows the documents), what has been signed, by what means, and what is still
out. `may_file` reports the promises the documents already make, and reports
what it *cannot* see — the 8879 and the invoice — as unknown rather than as
passed.

Nothing in it assumes a vendor, and nothing in it asserts a compliance claim.
