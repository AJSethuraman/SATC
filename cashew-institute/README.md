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

## Hosting

Live at **https://ajsethuraman.github.io/SATC/cashews/**, published by
`.github/workflows/pages.yml` on push to `main`. That workflow stages this
folder into `_site/cashews/` alongside the marketing site at the root; the
`.md` sweep drops this README, so `index.html` is the only file published.

**This does not reach satcllp.com.** The practice's live site is served by
Cloudflare Pages, whose build command copies `website/` only:

```
rm -rf _site && mkdir -p _site && cp -r website/. _site/ && find _site \( -name '*.md' -o -name '*.py' \) -delete
```

Nothing outside `website/` can appear on the practice's domain, so the two
sites share a repo and nothing else. If that Cloudflare build command is ever
widened to copy the repo root, this folder would come with it — check here
first.

A repo publishes only one Pages site, which is why this rides as a subpath
rather than getting its own. To move it to a standalone repo instead: create an
empty public repo, copy `index.html` in, push to `main`, set *Settings → Pages
→ Source* to *Deploy from a branch → main / (root)*, and drop the two
`cashew-institute` hunks from `pages.yml`.
