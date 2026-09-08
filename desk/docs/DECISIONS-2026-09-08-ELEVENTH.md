# What the desktop found — 8 September 2026, 02:04 UTC

**The first run on the firm's own machine**, after a session spent an hour
testing against cloud containers it had NAMED "Forge · Desk" and then reasoned
about as though the name made them the Forge. The firm stopped it. Everything
below is from `Forge - Desk`, `environment_kind: bridge`, desk 0.9.3, HEAD
`2e3b8e12`, working from the checkout and deliberately NOT through the Skill
tool.

---

## 1 · ecfr.gov is not egress-blocked. It is USER-AGENT blocked.

This session reported, from a cloud container, that ecfr.gov was blocked at the
proxy — and concluded that *"the desk can go and look"* might be false for
primary authority everywhere. **That conclusion was wrong.** From the desktop:

| user agent | bytes | what came back |
|---|---|---|
| `satc-desk-tieout` — **the shipped one**, `tools/tieout.py:106` | 10,596 | an interstitial |
| `python-urllib/3.13` | 10,596 | an interstitial |
| `curl/8.0` | 10,596 | an interstitial |
| `Chrome/140` | **584,798** | **the regulation** |

The same URL, the same machine, the same minute. ecfr.gov redirects
non-browser clients to `unblock.federalregister.gov`.

### The dangerous part is that the interstitial returns 200

`proving.prove` turns a network **exception** into `COULD_NOT` — correct, and
already tested: a network that is down says nothing about whether the text
moved. A clean **200 carrying the wrong document** fell straight through to
`DIFFERS`, and `ask.answer` reads `DIFFERS` as `authority_has_moved` and
**withdraws the answer**. The desk that found it:

> *"Run a tie-out over the desks today and every primary-authority citation is
> withdrawn as 'the publisher no longer carries it' when nothing has moved."*

**Fixed in 0.9.5, honestly rather than away.** `fetch.Response` carries the URL
it landed on; `prove` compares hosts before comparing text, and a landing on
another host is `COULD_NOT` with a note naming both. `authority_has_moved` is a
claim about the PUBLISHER; being bounced by a bot filter is a claim about US.
A redirect *within* the publisher still ties out, and a real rewrite still
`DIFFERS` — both pinned by tests, four mutations caught.

### WHAT IS NOT FIXED, AND IS THE FIRM'S TO DECIDE

**What does this desk call itself to a publisher?** The tie-out still cannot
read ecfr.gov. The one-line change is a browser user agent, and the desk that
found the problem declined to make it:

> *"That is a one-line change, and you should not make it on my say-so without
> deciding what this desk calls itself to a publisher."*

Right. Three options, and this is a decision about honesty, not a bug:

1. **Announce as a browser.** One line, works today. It is also a false
   statement to the publisher about what is asking, which is the thing this
   whole repository refuses to do to its own readers.
2. **Use an actual browser.** `record.ACCESS` has declared a `headless_browser`
   rung since the beginning and **has never been walked** — all 36 sources sit
   on `public_fetch`. A real browser reporting a real browser UA is true. It is
   also the rung the ladder was built for, and eCFR would be the first source
   to earn it.
3. **Ask eCFR.** They publish federal regulations and there may be an API or a
   declared-agent path. Slowest, most correct, and nobody has looked.

**Recommendation: 2.** It is honest, it walks a ladder that has been decorative
for a week, and it needs no permission from anyone.

---

## 2 · The lease question closes, on FASB's own free publication

`ask.consult` routes it to `capitalization-and-de-minimis` and
`vehicle-expense`, both refusing `wrong_body_of_authority` with the right
follow-up. **The gate works.**

Then the desk went and looked, and hit the licence wall exactly where expected —
**and did not cross it**:

> *"asc.fasb.org returns HTTP 403 to any non-browser client; in real Chrome it
> serves /Login gated by a reCAPTCHA AND an Access button reading 'By clicking
> on Access below, you agree to our terms and conditions', labelled 'For
> Personal and Non-Commercial Use'. I clicked neither."*

**But a free, FASB-published route works.** `storage.fasb.org`, ASU 2016-02
Section A — 877,554 bytes, 191 pages, `842-20-25-1` occurring exactly once:

> *"At the commencement date, a lessee shall recognize a right-of-use asset and
> a lease liability."*

**FOR THE FIRM, AND NOT DECIDED HERE:** is FASB's own free Accounting Standards
Update acceptable authority where the Codification is licensed? It is published
by the standard-setter, it is free, and it is not the Codification. Admitting
`fasb.org` closes the lease question and stops `us-gaap` being a domain the gate
can name and no desk can answer. Nothing has been written to any desk.

---

## 3 · Three defects in how this session drives the desk

- **`python3` is not on PATH on that Windows machine — only `python`.** Every
  script sent has failed on it. **Third report.** Nothing was changed after the
  first two.
- **The tie-out script sent for verification hard-coded the exact UA class
  ecfr.gov bounces.** It could not have succeeded as written.
- **`cd <your SATC checkout>` is ambiguous — there are two clean clones on that
  machine.** Name the path.

And the one that keeps costing releases: **the Skill tool served
`desk/0.4.0/skills/ask-desk` — five releases back, not the 0.8.3 predicted.**
The version warning added in 0.7.3 lives in the SKILL.md that does not load. It
cannot reach the agent that needs it. **That check has to live in `ask.py` /
`relay.py`, which are current, or in the harness — not in the file whose
staleness is the problem.**
