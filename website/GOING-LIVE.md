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
