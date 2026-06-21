# SATC — Marketing Website

A single-file, fully responsive landing site for **Sethuraman Accounting, Tax &
Consulting**. It's the public page you share with people so they can learn what
you do and **book a consultation** with you.

- **One file:** [`index.html`](./index.html). No build step, no framework, no
  dependencies. Open it in a browser to preview; drop it on any static host to
  publish.
- **Mobile-first:** works on phones, tablets, and desktop (the original mockup
  was desktop-only — this rebuild fixes that).
- **Honest content:** no fake testimonials, metrics, or blog posts — only true
  claims you can stand behind.

---

## ✅ Go live in 2 steps

Everything you'll ever need to edit lives in **one block** at the very bottom of
`index.html`, labelled `⚙️ SATC_CONFIG`.

### 1. Add your booking link (the whole point of the site)

Set up a free scheduler, then paste its link into the config:

```js
const SATC_CONFIG = {
  booking: {
    provider: "calendly",                               // "calendly" | "cal" | "iframe"
    url: "https://calendly.com/your-handle/30min"       // ← paste your link here
  },
  ...
```

You don't have an account yet? Pick one (both free, ~5 minutes):

| Option | Link | In the config |
|---|---|---|
| **Calendly** | <https://calendly.com> → create a 30-min event type → copy its share link | `provider: "calendly"`, `url: "https://calendly.com/you/30min"` |
| **Cal.com** (open-source) | <https://cal.com> → create an event type → copy its link | `provider: "cal"`, `url: "https://cal.com/you/consultation"` |

Until you add a link, the booking section automatically shows a tidy
**"Email to Book"** fallback — so the page is never broken in the meantime.

### 2. Set your contact details

```js
  contact: {
    email:    "you@yourbusiness.com",   // change from the gmail default when ready
    phone:    "",                       // optional — leave "" to hide
    location: "By appointment · Remote & in-person",
    linkedin: ""                        // optional — leave "" to hide
  }
```

Any field left as `""` is hidden automatically.

That's it. Commit, and the site updates.

---

## 🚀 Hosting (GitHub Pages)

A deploy workflow is already included at
[`.github/workflows/pages.yml`](../.github/workflows/pages.yml). To turn it on:

1. **Merge this to `main`** (the workflow deploys from `main`).
2. The workflow **auto-enables** Pages (Source = GitHub Actions), so there's
   normally no toggle to flip. If your org blocks that, set it once by hand:
   **Settings → Pages → Build and deployment → Source → "GitHub Actions"**.
3. Wait for the **Deploy website to GitHub Pages** action to finish (Actions
   tab). It's live first at `https://ajsethuraman.github.io/satc/`, then at
   **https://satcllp.com** once the custom-domain DNS below is set.

After that, any push to `main` that changes `website/` redeploys automatically.
You can also trigger it manually from the Actions tab ("Run workflow").

### Custom domain — `satcllp.com` (Squarespace-managed DNS)

The domain is registered/managed in Squarespace. We're pointing the **website**
records at GitHub Pages while leaving **email** untouched. A `website/CNAME` file
(containing `satcllp.com`) is already committed, so the domain survives every
redeploy.

> ⚠️ **Do NOT delete the `MX` records** (or any `TXT`/SPF/DKIM records). Those
> route `arjun_sethuraman@satcllp.com` email and are **independent** of the
> website. Changing the `A`/`CNAME` records below moves the *site* only — email
> keeps working as long as the `MX` records stay.

**1. In GitHub:** Settings → Pages → **Custom domain** → enter `satcllp.com` →
Save. After it verifies, tick **Enforce HTTPS** (may take a few minutes for the
certificate).

**2. In Squarespace** (Domains → `satcllp.com` → **DNS / DNS Settings**):

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

Or serve it (so the scheduler embed behaves exactly like production):

```bash
cd website && python -m http.server 8000   # then visit http://localhost:8000
```

---

## What's on the page

`Nav → Hero → Services (3) → The Occam Platform → Why SATC (4) → How We Work
(3 steps) → Book a Consultation → Footer / Contact`

The **Occam Platform** section ties into the in-house tools already in this repo
(`invoice-generator`, `drake-entry-assistant`) — it's real, not marketing fluff.

## Editing copy / colours

- **Text:** edit the HTML directly — it reads top to bottom, section by section.
- **Colours & fonts:** the palette is a set of CSS variables in `:root` near the
  top of the `<style>` block (navy `#0B1F3A`, gold `#B08D57`, cream `#F7F5F0`).
- **Logo:** the "S" seal is inline SVG (search for `class="seal"`); swap in your
  own SVG/logo if you have one.
