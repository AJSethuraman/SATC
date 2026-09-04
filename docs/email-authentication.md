# Making sure our email reaches people

`satcllp.com` sends through **Microsoft 365**. DNS is at **Cloudflare**.

Three records decide whether a receiving server trusts mail claiming to be from
us. As of 14 August 2026 we have one of the three:

| | Status | What it does |
|---|---|---|
| **SPF** | ✅ in place | Says which servers may send as `satcllp.com` |
| **DKIM** | ❌ missing | Cryptographically signs each message so it can't be altered or forged |
| **DMARC** | ❌ missing | Tells receivers what to do when a message fails the first two |

SPF alone is the weakest of the three. Without DKIM, a message that gets
forwarded — which happens constantly, and is exactly what a referral does —
breaks SPF and has nothing to fall back on. That is a common reason a
legitimate small-practice email lands in someone's junk folder.

---

## Step 1 · Turn on DKIM in Microsoft 365

1. Go to **security.microsoft.com**
2. **Email & collaboration** → **Policies & rules** → **Threat policies**
3. Under *Rules*, open **Email authentication settings** → the **DKIM** tab
4. Click **satcllp.com** in the list

The panel will show the toggle switched **off** and give you **two CNAME
records** to create. They look like this — the portal shows the exact targets,
including our tenant's `onmicrosoft.com` name:

```
Host:   selector1._domainkey
Target: selector1-satcllp-com._domainkey.<tenant>.onmicrosoft.com

Host:   selector2._domainkey
Target: selector2-satcllp-com._domainkey.<tenant>.onmicrosoft.com
```

**Copy the targets from the portal — do not type them from this file.** The
`<tenant>` part is specific to our account.

> Leave the toggle **off** for now. Enabling it before the records exist fails
> with an error.

---

## Step 2 · Add both CNAMEs at Cloudflare

Cloudflare → **satcllp.com** → **DNS** → **Add record**, twice:

| Type | Name | Target | Proxy |
|---|---|---|---|
| CNAME | `selector1._domainkey` | *(from the portal)* | **DNS only** |
| CNAME | `selector2._domainkey` | *(from the portal)* | **DNS only** |

- [ ] Both records set to **DNS only** — the grey cloud, not orange.
      Proxying a DKIM record breaks it, the same way it would break `MX`.
- [ ] TTL left on **Auto**

Cloudflare may append the domain to the name automatically — `selector1._domainkey`
becoming `selector1._domainkey.satcllp.com`. That is correct. What is *not*
correct is `selector1._domainkey.satcllp.com.satcllp.com`, which happens if you
paste the full name in. Check the saved record reads the way you expect.

---

## Step 3 · Switch DKIM on

Back at **security.microsoft.com** → DKIM tab → `satcllp.com` → set
**Sign messages for this domain with DKIM signatures** to **Enabled**.

If it errors saying the CNAMEs are not found, DNS has not caught up yet. Wait a
few minutes and try again — this is normal and harmless.

---

## Step 4 · Add DMARC

Cloudflare → **DNS** → **Add record**:

| Type | Name | Content |
|---|---|---|
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:arjun_sethuraman@satcllp.com` |

What the parts mean:

- `p=none` — **monitor only.** Receivers report what they see but change
  nothing about delivery. This is deliberately the safe setting: it cannot make
  our mail worse, and it is where every DMARC rollout should start.
- `rua=` — where the daily aggregate reports go. They arrive as XML
  attachments, and are ugly but informative: they show every server sending as
  `satcllp.com`, which is how you find out about anything unexpected.

**Do not start at `p=reject`.** If any legitimate sender is missing from SPF,
reject silently destroys that mail with no bounce. `p=none` first, read the
reports for a few weeks, then tighten.

---

## Step 5 · Verify

Ask Claude to check, or look them up yourself:

- `selector1._domainkey.satcllp.com` should resolve as a CNAME
- `_dmarc.satcllp.com` should return the TXT record
- Send a message to a Gmail address, open it, **Show original** — SPF, DKIM and
  DMARC should all read **PASS**

---

## Later, once the reports are boring

Tighten in two moves, weeks apart, reading reports in between:

1. `p=quarantine` — failures go to junk rather than the inbox
2. `p=reject` — failures are refused outright

There is no hurry. `p=none` plus working DKIM already fixes the deliverability
problem; the stricter policies protect the *domain* from being forged by
someone else.

---

## One thing to remember for the future

Our SPF ends in `-all`, a **hard fail**: it says Microsoft 365 is the *only*
system allowed to send as `satcllp.com`.

That is the right setting, but it means **any new service that sends email on
our behalf must be added to the SPF record first** — a newsletter tool, a CRM,
a scheduling system that emails clients as us. Miss that step and its mail is
rejected outright.

This does **not** apply to Formspree or Calendly. They send from their own
domains and merely set the reply-to, so our SPF does not govern them.
