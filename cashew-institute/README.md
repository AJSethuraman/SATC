# cashew-institute

A single-page satirical website for the **Global Cashew Integrity Council** — a
fictional standards body that has spent forty-seven years failing to
authenticate a cashew. The design plays it completely straight (annual-report
typography, hairline rules, small-caps labels); the copy carries the joke.

Nothing here is real. The footer says so plainly, and so does the form's
confirmation message.

## Layout

```
cashew-institute/
└── index.html    the entire site — markup, styles and one small script
```

No build step, no framework, no dependencies beyond the Google Fonts link in
`<head>`. Edit `index.html` directly, the same way `website/` is maintained.

## Run it locally

```bash
cd cashew-institute
python -m http.server 8000
# → http://localhost:8000
```

There is no test suite. Verify a change by driving a real browser: check the
layout at 1400px, ~900px and ~400px, open every FAQ item, and submit the
registration form both empty-ish and with a valid address.

## Hosting on GitHub Pages

The site is a plain static file, so any Pages source will serve it. **A repo can
only publish one Pages site**, and this repo's slot is already taken by
`website/` (the real SATC marketing site, deployed by
`.github/workflows/pages.yml` on push to `main`). Pick one of:

1. **Its own repo (recommended).** Create a new public repo, copy `index.html`
   into it, push to `main`, then set *Settings → Pages → Source* to
   *Deploy from a branch → main / (root)*. Live at
   `https://<user>.github.io/<repo>/`. This keeps a joke site off the
   accounting practice's domain.

2. **A subpath of the existing Pages site.** Add a step to
   `.github/workflows/pages.yml` that copies this folder into
   `_site/cashews/`, publishing it at
   `https://ajsethuraman.github.io/SATC/cashews/`. That workflow deploys
   production for a real business — don't change it without sign-off.

Option 1 is untouched-production and takes about a minute in the GitHub UI.
