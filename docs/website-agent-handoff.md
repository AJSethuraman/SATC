# For the website agent — two edits, both verified

**From:** the practice-ops side (`client-documents`, `satc_system`).
**Date:** 30 August 2026.
**Why you're getting this:** the `published prices match the fee schedule` check
has been red on every branch for days. It is not any one branch's fault — it
fails on `main` too. Nothing outside `website/` can fix it, and the practice-ops
side is not permitted to touch `website/`.

I reproduced it, fixed it locally, confirmed the fix, and reverted — so
`website/` in this repo is untouched by me. Below is exactly what I did.

---

## The state, measured

```
$ cd website && python3 pricing.spec.py
58/61 checks passed

  FAIL  pricing-config.js is what the schedule generates today
        — pricing-config.js is out of date — run: python3 build-pricing-config.py
  FAIL  every hourly trigger in the schedule is on the page
  FAIL  every hourly trigger has client wording
```

**Root cause, one thing.** The fee schedule
(`client-documents/registry/fee-schedule.yaml`) dropped its `notice_response`
item. The website still advertises it in two places, and they are different
kinds of place, which is why it takes two edits rather than one.

---

## Edit 1 — regenerate the config

```
cd website && python3 build-pricing-config.py
```

The only change it makes:

```diff
- 'A letter from the IRS or the state you would like us to handle',
```

**58 → 60 of 61.** This is a generated file; do not hand-edit it.

## Edit 2 — drop `notice_response` from the generator

Regenerating is not enough, because the stale item is *also* named in the
generator's own copy table.

In `website/build-pricing-config.py`, `HOURLY_COPY` has five keys. The schedule
has four:

```
schedule's hourly triggers : brokerage_keying, cleanup, foreign_company, officer_compensation
page has client wording for: brokerage_keying, cleanup, foreign_company, officer_compensation,
                             notice_response          <-- this one
```

Delete the `notice_response` entry from `HOURLY_COPY`, then re-run edit 1.

**60 → 61 of 61.**

---

## What I am NOT asking you to do

Nothing about wording. Both edits remove an item the firm's fee schedule no
longer carries; neither writes a new sentence. If removing it leaves a gap a
client would notice, that is a question for the firm, not for either of us.

## One separate thing, not a bug

An earlier note of mine claimed `website/` still prints `billing@satcllp.com`
where the documents use `arjun_sethuraman@satcllp.com`. **That was wrong** —
`site-config.js` already uses `arjun_sethuraman@satcllp.com`, and `billing@`
appears nowhere under `website/`. The firm has since confirmed `billing@satcllp.com`
exists as a real mailbox anyway. Nothing to do; recorded so nobody re-opens it.

## How to know you're done

```
cd website && python3 pricing.spec.py
61/61 checks passed
```
