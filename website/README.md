# SATC — Marketing Website

A single-file, fully responsive site for **Sethuraman Accounting, Tax &
Consulting**. Right now it works as a **glorified intake form**: the page you
send a lead to so they can tell you about their situation before you ever get
on a call.

- **One file:** [`index.html`](./index.html). No build step, no framework, no
  dependencies. Open it in a browser to preview; drop it on any static host to
  publish.
- **Mobile-first:** works on phones, tablets, and desktop.
- **Honest content:** no fake testimonials, metrics, or blog posts — only true
  claims you can stand behind.

**The page is:** `Nav → Hero → Services (3) → Intake form → Footer`.

> **Working on the intake?** [`INTAKE.md`](./INTAKE.md) is the living log — what
> we're building, the architecture audit, decisions made, and open questions.
> Read it before changing the form, and update it as you go.

> **Looking for the full marketing site?** The longer version (About, Occam
> platform, Why SATC, How We Work, FAQ, booking embed) is preserved at
> [`docs/website-archive/index-full-marketing-2026-08-13.html`](../docs/website-archive/index-full-marketing-2026-08-13.html)
> and in git history. It lives outside `website/`, so it is **not** published.

---

## ✅ Go live in 2 steps

Everything you'll ever need to edit lives in **one block** at the very bottom of
`index.html`, labelled `⚙️ SATC_CONFIG`.

### 1. Point the form at your inbox (the whole point of the site)

The form posts to **[Formspree](https://formspree.io)** — free, no backend, and
submissions land in your email. Sign up, create a form, copy the ID out of the
URL it gives you (the last part, like `xkgwabcd`), and paste it in:

```js
const SATC_CONFIG = {
  contact: {
    email:      "arjun_sethuraman@satcllp.com",
    formspreeId: "xkgwabcd"      // ← paste your Formspree form ID here
  },
  ...
```

Until you set this, the form **falls back to opening the visitor's email app**
with every answer pre-filled. It works, but far fewer people finish — so set the
Formspree ID before you start sending the link around.

The free tier is 50 submissions/month. Each email arrives as a readable
`Label: value` list; blank answers are stripped out, so you only see what they
actually filled in.

### 2. Set your contact details

```js
  contact: {
    email:    "you@yourbusiness.com",
    phone:    "",                       // optional — leave "" to hide
    location: "By appointment · Remote & in-person",
    linkedin: ""                        // optional — leave "" to hide
  }
```

Any field left as `""` is hidden automatically.

### Optional: add a booking link

You have Calendly through your Microsoft account. Paste the link and a
"book a time" line appears beside the form; leave it blank and it stays hidden.

```js
  booking: { url: "https://calendly.com/your-handle/30min" }
```

That's it. Commit, and the site updates.

---

## 🔒 What the form does and does not collect

This is a static page on GitHub Pages. There is **no backend** — submissions
travel to Formspree and then to your inbox. That shapes what it may ask for.

**It collects:** name, email, phone, city/state, referral source, which services
are needed, tax years, urgency, filing status, dependents, states worked in,
prior preparer, business/rental details (entity type, headcount, bookkeeping,
revenue band), notable events for the year, and free-text notes.

**It never collects:** SSNs, ITINs, EINs, dates of birth, bank account numbers,
or document uploads. The page says so explicitly, in a callout above the first
field.

Instead, the **"What you'll need"** section lists the documents a first
engagement needs — photo ID, last year's return, W-2s/1099s, business books,
and so on — as checkboxes the visitor *ticks to confirm they have*. Nothing is
required. That tells you where to start without moving a single sensitive value
across the open internet.

**The handoff:** your reply email carries a secure upload link for the actual
documents. The page promises this in three places, so keep that promise — and
don't collect tax documents over email or text. Anything touching real TINs
belongs in `satc_system`'s encrypted identity vault, not here.

---

## 🚀 Hosting (GitHub Pages)

A deploy workflow is already included at
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml). Any push to
`main` that changes `website/` redeploys automatically — **treat edits here as
production changes.** You can also trigger it manually from the Actions tab
("Run workflow").

The site is live at **https://ajsethuraman.github.io/satc/**.

> **Current setup:** served from the GitHub URL above. There is no `CNAME` file,
> so nothing is pinned to a custom domain. If GitHub still shows a **Custom
> domain** under Settings → Pages, clear that field and Save.

### Later: connect the `satcllp.com` domain (Squarespace-managed DNS)

When you're ready to use the real domain, do these three things. The domain is
registered/managed in Squarespace; we point the **website** records at GitHub
while leaving **email** untouched.

> ⚠️ **Do NOT delete the `MX` records** (or any `TXT`/SPF/DKIM records). Those
> route `arjun_sethuraman@satcllp.com` email and are **independent** of the
> website. Changing the `A`/`CNAME` records below moves the *site* only — email
> keeps working as long as the `MX` records stay.

**1. Re-add the domain pin:** create a file `website/CNAME` containing one line,
`satcllp.com`, and update the absolute URLs in `index.html` (`og:url`,
`og:image`, `canonical`, and the JSON-LD `url`/`image`) plus `robots.txt` /
`sitemap.xml` from `ajsethuraman.github.io/satc` back to `satcllp.com`.

**2. In GitHub:** Settings → Pages → **Custom domain** → enter `satcllp.com` →
Save. After it verifies, tick **Enforce HTTPS** (may take a few minutes for the
certificate).

**3. In Squarespace** (Domains → `satcllp.com` → **DNS / DNS Settings**):

- Remove the existing **A** records on host `@` that point to Squarespace, and
  the `www` **CNAME** if it points to Squarespace. (Leave `MX`/`TXT` alone.)
- Add these **A** records (host `@`):

  ```
  185.199.108.153
  185.199.109.153
  185.199.110.153
  185.199.111.153
  ```

- Add a **CNAME**: host `www` → value `ajsethuraman.github.io`
- *(Optional, IPv6)* add **AAAA** records on host `@`:
  `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`,
  `2606:50c0:8003::153`

DNS usually propagates within an hour (can take up to 24–48h). Once it resolves,
the site is live at **https://satcllp.com** (and `www.` redirects to it).

> If `satcllp.com` is currently connected to a published **Squarespace site**,
> you may need to disconnect that site from the domain first so Squarespace stops
> overriding these records. This replaces whatever Squarespace was serving — which
> is the point.

---

## Preview locally

Just open the file — no server required:

```bash
# from the repo root
open website/index.html        # macOS
xdg-open website/index.html    # Linux
start website/index.html       # Windows
```

Or serve it:

```bash
cd website && python -m http.server 8000   # then visit http://localhost:8000
```

To test the form without a Formspree account, submit it and check that your mail
client opens with every answer pre-filled — that's the fallback path working.

## Editing copy / colours

- **Text:** edit the HTML directly — it reads top to bottom, section by section.
- **Form fields:** each input's `name` attribute is the label you'll see in the
  email, so keep them human-readable (`name="Filing status"`, not `name="fs"`).
- **Colours & fonts:** the palette is a set of CSS variables in `:root` near the
  top of the `<style>` block (navy `#0B1F3A`, gold `#B08D57`, cream `#F7F5F0`).
- **Logo:** the "S" seal is inline SVG (search for `class="seal"`); swap in your
  own SVG/logo if you have one.
