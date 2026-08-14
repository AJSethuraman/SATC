# Putting the site on satcllp.com

A checklist for moving the site from `ajsethuraman.github.io/SATC/` onto the
real domain. Two paths — do **A** now if you want it live quickly with your
email never at risk, and **B** later when there's no deadline pressure.

**The domain is registered and DNS-managed at Squarespace. Email
(`arjun_sethuraman@satcllp.com`) runs on it.** That is the thing to protect.

---

## Before anything — the restore point

- [ ] Open Squarespace → Domains → `satcllp.com` → **DNS Settings**
- [ ] **Screenshot the entire record list.** Every row: type, host, value, priority.
      Scroll and capture all of it.
- [ ] Save the screenshot somewhere you'll find it in a hurry

Thirty seconds, and it is the difference between "undo it" and "reconstruct it
from memory at 11pm".

---

## What DNS actually is, so the risk is clear

DNS is the **address book**. Your email provider is the **destination**.

| Record | Controls | Touch it? |
|---|---|---|
| `A` / `CNAME` | where the **website** lives | yes — this is the whole job |
| `MX` | where **mail** is delivered | **never, except to copy it verbatim** |
| `TXT` (SPF, DKIM, DMARC) | whether your mail is **trusted** rather than filtered | same — copy verbatim |

Changing `A` records moves the website only. Mailboxes never move, and nothing
about Microsoft 365 changes.

---

## Path A — GitHub Pages + Squarespace DNS

**Lowest risk: you only add website records. `MX` and `TXT` are never edited,
so email is not in the blast radius.** Accepts GitHub's commercial-use grey
area (see §"Which host" below).

### A1 · Squarespace DNS

- [ ] Remove the **A** records on host `@` that point at Squarespace
- [ ] Remove the `www` **CNAME** if it points at Squarespace
- [ ] **Leave every `MX` and `TXT` record exactly as it is**
- [ ] Add four **A** records, host `@`:
      `185.199.108.153` · `185.199.109.153` · `185.199.110.153` · `185.199.111.153`
- [ ] Add a **CNAME**: host `www` → `ajsethuraman.github.io`

> If a published Squarespace **site** is attached to the domain, disconnect it
> first or Squarespace will keep overwriting these records.

### A2 · GitHub

- [ ] Repo → **Settings → Pages → Custom domain** → `satcllp.com` → Save
      (GitHub commits a `CNAME` file to the repo automatically)
- [ ] Wait for the green check, then tick **Enforce HTTPS**
      (certificate issue can take minutes to an hour)

### A3 · Confirm

- [ ] `https://satcllp.com` loads the site
- [ ] `https://www.satcllp.com` reaches it too
- [ ] **Send yourself an email and reply to it** — proves mail still flows
- [ ] Then do §"Repo-side URL switch" below

---

## Path B — Cloudflare Pages + Cloudflare DNS

Better hosting terms and unlimited bandwidth, but the apex domain requires DNS
to live at Cloudflare — **so your `MX` records move house.** They still point at
the same mail provider; they just have to be recreated at the new DNS host.

### B1 · Add the domain to Cloudflare

- [ ] Create a Cloudflare account, **Add a site** → `satcllp.com`
- [ ] Choose the **Free** plan
- [ ] Let Cloudflare scan and import the existing records

### ⛔ B2 · THE MX GATE — do not pass this without checking

**Cloudflare's scan usually imports `MX` and `TXT` correctly. Usually is not
always, and SPF/DKIM/DMARC are the ones that scan least reliably.**

Open the imported record list beside your screenshot and fill this in:

| Record | On the screenshot | Imported at Cloudflare | Match? |
|---|---|---|---|
| MX (priority + host) | | | ☐ |
| MX (any additional) | | | ☐ |
| TXT — SPF (`v=spf1 …`) | | | ☐ |
| TXT — DKIM (often `selector._domainkey`) | | | ☐ |
| TXT — DMARC (`_dmarc`) | | | ☐ |
| TXT — domain verification (Microsoft `MS=…`) | | | ☐ |
| Any other record on the screenshot | | | ☐ |

- [ ] Every row above ticked, values matching **character for character**
- [ ] Anything missing has been **added by hand** at Cloudflare
- [ ] `MX` records are set to **DNS only** (grey cloud, not orange) — proxying
      mail records breaks delivery

**Only when every row matches:**

- [ ] Change the nameservers at Squarespace to the two Cloudflare gives you

> Until you change nameservers, Squarespace is still answering — so everything
> above is rehearsal, and mail keeps flowing while you check.

### B3 · Cloudflare Pages

- [ ] Workers & Pages → **Create → Pages → Connect to Git** → this repo
- [ ] Build command: **none**. Output directory: `website`
- [ ] Add the custom domain `satcllp.com` in the Pages project

> ⚠️ **`website/` contains files the public site should not serve** —
> `INTAKE.md`, `README.md`, this file, `intake.spec.py`, `assets/make-images.py`.
> The GitHub Actions deploy strips `.md` and `.py` before publishing
> (`.github/workflows/pages.yml`, "Stage site files"). Cloudflare pointed
> straight at `website/` would publish all of them. Either give the Pages
> project a build command that does the same strip, or move those files out of
> `website/` first.

### B4 · Confirm

- [ ] `https://satcllp.com` loads the site
- [ ] **Send yourself an email and reply to it**
- [ ] Send a test from an *outside* address (a personal Gmail) and confirm it
      arrives — this is what catches a broken SPF record
- [ ] Turn off the GitHub Pages custom domain so two hosts aren't claiming it
- [ ] Then do §"Repo-side URL switch" below

---

## Repo-side URL switch — after DNS resolves, not before

The site has the current URL baked into several files. Switching them **before**
the domain works points link previews and the canonical tag at a dead address,
which is worse than the mismatch you have now.

Ask Claude to do this in one commit, or do it by hand:

- [ ] `website/index.html` — `og:url`, `og:image`, `twitter:image`, `canonical`,
      and the JSON-LD `url` / `image`
- [ ] `website/sitemap.xml` — the `<loc>`
- [ ] `website/robots.txt` — the sitemap line
- [ ] `website/assets/make-images.py` — already says `SATCLLP.COM`, so nothing
      to change, but **re-run it** if anything else moved
- [ ] `website/README.md` and `website/INTAKE.md` — the live-URL references
- [ ] Re-share a link somewhere to confirm the preview card renders

---

## Which host — the short version

| | GitHub Pages | Cloudflare Pages |
|---|---|---|
| Commercial use | grey area — terms discourage running a business on it | explicitly allowed |
| Bandwidth | 100 GB/month soft | unlimited |
| Builds | 10/hour | 500/month |
| Email risk during setup | **none** — `MX` never touched | `MX` migrates with DNS |
| Cost | $0 | $0 |

Both are free and neither locks you in: the site is seven static files, so
switching later is a folder copy and a DNS change.

---

## If something breaks

- **Website down, email fine** → revert the `A` records to the screenshot. Low stakes.
- **Email stopped** → compare live records against the screenshot and restore any
  missing `MX`/`TXT` immediately. Sending servers retry for **24–72 hours**, so a
  fast fix usually means delayed mail rather than lost mail.
- **Mail arrives but lands in spam** → an SPF/DKIM/DMARC `TXT` record is missing
  or altered. Check those three against the screenshot first.

---

## Recorded DNS — Squarespace panel, 14 August 2026

> ✅ **Verified live on 14 August 2026.** Squarespace's DNS page shows a banner
> saying *"You're using custom nameservers… to activate the DNS records below,
> switch to Squarespace nameservers."* **Ignore it.** A direct lookup shows every
> record below resolving publicly with matching values, and `squarespacedns.com`
> among the domain's nameservers. Squarespace **is** serving this zone, and
> edits made on that page **do** take effect.
>
> (The delegation also lists `dns1–4.p08.nsone.net` alongside the four
> `ns01–04.squarespacedns.com`, which is probably what makes Squarespace's own
> check report "custom". It does not stop the records working.)

Everything here is public information — DNS is queryable by anyone — so it is
safe to keep in the repo.

### Squarespace Defaults (website — these are the ones that get replaced)

| Type | Name | Priority | TTL | Data |
|---|---|---|---|---|
| A | @ | — | 4 hrs | `198.185.159.145` |
| A | @ | — | 4 hrs | `198.49.23.144` |
| A | @ | — | 4 hrs | `198.49.23.145` |
| A | @ | — | 4 hrs | `198.185.159.144` |
| CNAME | www | — | 4 hrs | `ext-sq.squarespace.com` |

### Squarespace Domain Connect

| Type | Name | Priority | TTL | Data |
|---|---|---|---|---|
| CNAME | _domainconnect | — | 4 hrs | `_domainconnect.domains.squarespace.com` |

### Google Workspace verification

| Type | Name | Priority | TTL | Data |
|---|---|---|---|---|
| TXT | @ | — | 4 hrs | `google-site-verification=JcikLSQNLDrhc9bRYX78ZriBlPXjiI9VwTFFJGVJT0k` |

### Custom records — **THIS IS THE EMAIL. DO NOT TOUCH.**

| Type | Name | Priority | TTL | Data |
|---|---|---|---|---|
| MX | @ | **0** | 4 hrs | `satcllp-com.mail.protection.outlook.com` |
| TXT | @ | — | 4 hrs | `MS=ms36114642` |
| CNAME | autodiscover | — | 4 hrs | `autodiscover.outlook.com` |
| TXT | @ | — | 4 hrs | `v=spf1 include:spf.protection.outlook.com -all` |

Mail is **Microsoft 365**. The four rows above are the whole of it: `MX` routes
delivery, `MS=` proves the domain to Microsoft, `autodiscover` is what Outlook
uses to configure clients, and the `v=spf1` line says Microsoft is the only
server allowed to send as `satcllp.com`.

---

## Where things actually stand

- **The four `A` records are the Squarespace preset**, never pointed at a real
  site — no Squarespace site was ever published. They are exactly what Path A
  replaces, and nothing depends on them.
- **The custom records are the email**, added by hand for Microsoft 365. All
  four resolve correctly, which is why mail flows.
- **`satcllp.com` currently answers with Squarespace's IPs**, so the domain
  shows a Squarespace placeholder rather than anything of ours.

So **Path A is the job**: swap the four `A` records and the `www` CNAME, leave
every `MX` and `TXT` alone.

---

## Two gaps worth closing while you are in here

Neither breaks anything today. Both affect whether **your** mail reaches other
people's inboxes — worth attention given mail from the site has already been
filtered as spam once.

**No DKIM records** — confirmed by lookup: `selector1._domainkey.satcllp.com`
does not resolve. Microsoft 365 signs outbound mail with DKIM, but only once
two CNAMEs exist — `selector1._domainkey` and `selector2._domainkey`, pointing
at `…onmicrosoft.com` targets Microsoft gives you. Neither is in the list above.
Enable DKIM in the Microsoft 365 admin centre (Defender → Policies → Email
authentication) and it will tell you the exact two records to add.

**No DMARC record** — confirmed by lookup: `_dmarc.satcllp.com` does not
resolve. Without one, receiving
servers have no instruction about what to do with mail that fails checks, and
some treat that as a reason to filter. A monitoring-only policy is safe to start
with and changes nothing about delivery:

```
Name: _dmarc     Type: TXT
Data: v=DMARC1; p=none; rua=mailto:arjun_sethuraman@satcllp.com
```

Add DKIM first, then DMARC at `p=none`, and leave it there until you have seen
a few reports.

**One oddity:** there is a Google Workspace verification TXT alongside the
Microsoft records. Probably left over from an earlier setup. Harmless, but if
Google Workspace is not in use it can go — after confirming nothing depends on
it.
