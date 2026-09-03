# SATC Website — Style Spec

Restyle spec for `website/index.html`. Direction: **modern practice** — cool
ground, IBM Plex superfamily, navy dominant, **oxblood as the single action
colour**, gold demoted to hairlines.

Companion files: **`satc-restyle.css`** (drop-in) · **`reference.html`** (every
component built correctly).

---

## How to apply this — 7 steps

1. **Swap the fonts.** Replace the Google Fonts `<link>` in `<head>`:
   ```html
   <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
   ```
2. **Replace the `<style>` block** contents with `satc-restyle.css`. Every class
   name and selector in the original is preserved, including the
   `.intake-form .wiz-*` specificity hacks — do not simplify those.
3. **Swap the seal** in the nav and footer (2 places) — markup below.
4. **Add the "Who this is for" section** between Services and Intake — markup below.
5. **Promote the credential** into `.section-head .right` — markup below.
6. **Update `theme-color` and the favicon** data-URI — values below.
7. **Regenerate the two brand rasters** — `og-image.png` and `apple-touch-icon.png`
   still carry the old circular gold seal. See below.

Nothing in `intake.js`, `intake-config.js`, or `SATC_CONFIG` changes. All JS
hooks (`data-email`, `data-phone-row`, `#intakeMount`, `#year`, `#navToggle`)
are untouched.

---

## Why the diff is small

**Every token name in `:root` is kept and re-pointed.** Swapping the `:root`
block restyles ~70% of the page on its own; the rest of the stylesheet handles
the places that need a real change.

Two names are now misnomers, kept deliberately so no other rule has to change:

| Token | Was | Now | Note |
|---|---|---|---|
| `--cream` | `#F7F5F0` warm | `#F7F7F5` **cool** | page shell |
| `--paper` | `#FBF9F4` warm | `#FFFFFF` | raised surfaces |

Rename later if you like; it's a find-and-replace, not a redesign.

---

## Tokens

### Brand & text
| Token | Value | Use |
|---|---|---|
| `--navy` | `#132437` | headings, dark surfaces, chip-selected |
| `--navy-deep` | `#0D1926` | footer |
| `--navy-soft` | `#22374F` | navy hover |
| `--charcoal` | `#242C36` | body copy |
| `--charcoal-2` | `#4A5360` | secondary copy |
| `--mute` | `#82817C` | **NEW** — labels, eyebrows, anything formerly gold text |
| `--ink` | `#131A22` | form input text |

### Action — the important change
| Token | Value | Use |
|---|---|---|
| `--oxblood` | `#6A2833` | **the only fill you click.** Primary buttons, progress bar, focus rings |
| `--oxblood-lt` | `#83323F` | hover |

`#fff` on `--oxblood` = **8.9:1** — passes AA and AAA.

### Gold — hairlines only
| Token | Value | Use |
|---|---|---|
| `--gold` | `#C0A265` | 1px rules, list bullets, dark-surface accents |
| `--gold-light` | `#D6BE8C` | dark-surface text accents |
| `--gold-deep` | `#8A7433` | the *only* gold approved for text on light (4.6:1) |

### Ground
| Token | Value | Use |
|---|---|---|
| `--cream` | `#F7F7F5` | page shell |
| `--cream-2` | `#EFEFEC` | intake band |
| `--paper` | `#FFFFFF` | cards, form, service tiles |
| `--hairline` | `#E6E5E0` | default divider |
| `--hairline-2` | `#D8D7D1` | **NEW** — stronger divider, input borders |

### Type
```
--serif: "IBM Plex Serif"   /* reserved — currently unused on the page */
--sans:  "IBM Plex Sans"    /* everything */
--mono:  "IBM Plex Mono"    /* eyebrows, micro-labels, step numerals, figures */
```

One superfamily means the site, the invoice app, and any future document are
provably one system rather than coincidentally compatible.

---

## The five rules that make this work

**1 · Gold never fills.** Hairlines, 1px rules, 4px bullets. The moment gold
covers area it reads as cheap simulated metal. This was the main reason the old
palette felt generic.

**2 · Oxblood is scarce and means one thing.** It is *the button you press* —
plus the progress bar and focus rings. If you reach for it a third time, use
`--navy` or `--mute` instead. Roughly: navy ~88% of ink, oxblood ~9%, gold ~1%.

**3 · Headings are sans, 600 weight, negative tracking.** Cormorant → Plex Sans
is most of the shift. Every heading carries `letter-spacing: -0.03em` or tighter;
display sizes go to `-0.045em`.

**4 · No italic ornament.** `<em>` inside a heading was gold serif italic. It is
now upright and simply *quieter* (`--mute`, or 50% white on navy). Emphasis by
tone, not decoration.

**5 · Tracking came down hard.** Eyebrows moved `0.32em → 0.18em` and to mono;
buttons moved from `11px uppercase / 0.28em` to `14px sentence case / -0.005em`.
Wide-tracked uppercase is the most "heritage" signal in the old page.

---

## Do / don't

| Do | Don't |
|---|---|
| `--gold` on 1px borders and rules | Fill any area with gold |
| `--oxblood` on the primary button | Use oxblood for headings or body text |
| `--gold-deep` if gold text is unavoidable | `--gold` or `--gold-light` as text on light |
| `--mute` for labels and eyebrows | Gold for labels (the old pattern) |
| Mono for eyebrows, numerals, micro-labels | Mono for body copy or headings |
| `-0.03em` tracking on headings | Positive tracking on anything but eyebrows |
| Navy for chip-selected state | Oxblood for form states |
| Squares and rules as ornament | Circles — they read traditional here |
| Sentence case on buttons | `text-transform: uppercase` on buttons |

---

## Component changes

| Component | Change |
|---|---|
| `.btn.gold` | Now **oxblood**, 14px, sentence case, radius 2px. Class name kept so HTML doesn't change |
| `.btn` / `.btn-link` | Tracking `0.28em → -0.005em`; uppercase removed; `→` kept |
| `.nav-cta` | Navy fill, sentence case, 13.5px |
| `.eyebrow` | Mono, 10.5px, `0.18em`, `--mute` |
| `.h2` / `.hero h1` | Sans 600, tracking `-0.038em` / `-0.045em` |
| `.h2 em` | Upright, `--mute` — no gold, no italic |
| `.lead` / `.hero p.lede` | Sans upright (was serif italic) |
| `.lockup .name` | **SAT‑C wordmark**, solid square as hyphen, 21px, tracking `-0.04em` (was serif SETHURAMAN, `+0.18em`) |
| `.lockup .seal` / `.divider` | `display: none` — the symbol is now favicon/OG only |
| `.hero::before/::after` | Concentric gold **circles → offset squares**, echoing the mark |
| `.service .num` | Mono, oxblood (was serif italic gold) |
| `.service ul li` | Now rule-separated rows |
| `.steps li .n` | Solid navy square, mono numeral (was gold-bordered serif italic) |
| `.chip.on` | **Navy**, not gold — form state, so oxblood stays scarce |
| `.wiz-bar span` | Oxblood progress |
| `.credential` | Promoted from footnote to statement — see below |
| `.callout` | Left border oxblood, tinted oxblood at 5% |
| Inputs | `--hairline-2` border, radius 2px, navy focus ring |

---

## New markup — 3 places

### 1 · The lockup — SAT‑C wordmark (nav + footer, 2 places)

Two parts to the identity:

- **Symbol** — the Notch (notched square + removed piece, oxblood on light,
  **gold on navy**). Favicon, app icon, OG image. Unchanged.
- **Wordmark** — what appears on the page: **a small solid square stands in for
  the hyphen** in SAT‑C (oxblood on light, gold on navy), `LLP` following
  lighter and untracked, with the full firm name beneath as the descriptor. The
  Notch symbol is not used in the lockup.

This replaces both the circular `S` seal *and* the SETHURAMAN wordmark. The full
legal name stays in the footer small print, where it already appears.

Full specification is in **`SATC Mark - Notch Spec.html`**.

```html
<a class="lockup" href="#top" aria-label="SAT-C LLP — home">
  <span class="text">
    <span class="name">SAT<span class="hy"></span>C<i>LLP</i></span>
    <span class="tag">Sethuraman Accounting, Tax &amp; Consulting</span>
  </span>
</a>
```

> **The one trap.** The square is sized in `em`, so `font-size` must sit on
> `.name` — the same element that contains the `<svg>`. Put it on a sibling and
> the square silently collapses to the inherited 16px while the letters stay
> large. The CSS ships correctly; don't "tidy" the size onto `.lockup`.

The old `.seal` and `.divider` rules are set to `display: none` rather than
deleted, so leftover markup in either place degrades quietly.

Keep the empty `<div class="divider"></div>` in place — the CSS hides it, so no
markup change is needed there.

**Favicon** (replace the data-URI in `<head>`). A navy **tile** — at 16px an
outline on white loses its stroke, a tile never does:
```html
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20fill='%23132437'/%3E%3Cpath%20d='M6%206%20H20%20V13%20H13%20V20%20H6%20Z'%20fill='none'%20stroke='%23fff'%20stroke-width='3'/%3E%3Crect%20x='21'%20y='21'%20width='6'%20height='6'%20fill='%23C0A265'/%3E%3C/svg%3E" />
```

**Theme colour:** `<meta name="theme-color" content="#132437" />`

### 2 · The credential — promoted

Goes in the empty `.section-head .right` slot in `#services`. It was a 13px
footnote; the CPA licence is the most persuasive fact on the page. Understated
on purpose — no badge, no seal, no adjectives.

```html
<div class="right">
  <p class="credential">
    <span class="lic">Certified Public Accountant · Ohio</span>
    Led by a <b>licensed CPA</b> with a background in large&#8209;bank credit risk and internal audit.
  </p>
</div>
```

> Keep this factual. Don't add years-of-experience claims, and don't imply audit
> registration — the "Who this is for" section explicitly says you don't do audit
> work, which is both accurate and a trust signal.

### 3 · "Who this is for" — new section

Insert **between** `#services` and `#intake`. Purpose is qualification: a
wrong-fit visitor leaves before spending five minutes on the form, and a
right-fit visitor recognises themselves. **The "probably not" column is the
point** — it's the most trust-building block on the page.

Full markup is in `reference.html` (`section.band.tight.fit#fit`). Structure:

```
section.band.tight.fit#fit
└ .wrap
  ├ .section-head  → .eyebrow + h2.h2 + .right>.lead
  ├ .fit-grid
  │ ├ .fit-col.yes → h3 + p.sub + ul>li   (oxblood square bullets)
  │ └ .fit-col.no  → h3 + p.sub + ul>li   (grey rule bullets)
  └ p.fit-note
```

Consider adding `<a class="nav-cta ghost" href="#fit">Who it's for</a>` to
`.nav-links`, and a matching footer link.

---

## Brand rasters — regenerate (don't skip this)

Two **binary** assets in `website/` still show the old circular gold "S" seal on
warm cream, and both are referenced from `<head>`:

| File | Size | Referenced by |
|---|---|---|
| `website/apple-touch-icon.png` | 180×180 | `<link rel="apple-touch-icon">` |
| `website/og-image.png` | **1200×630** | `og:image`, `twitter:image` |

CSS cannot fix these. If you apply everything else and stop, the page restyles
but **every iOS home-screen icon and every link preview still shows the old
brand** — the two surfaces seen *outside* the page.

They're generated by `website/assets/make-images.py` (Pillow). An updated
generator ships alongside this spec as **`make-images.py`** — replace the repo
copy with it and run:

```bash
pip install Pillow
python3 website/assets/make-images.py
```

What changed in it:

- Palette → `NAVY #132437`, `GOLD #C0A265`, `OXBLOOD #6A2833`, white/`#F7F7F5`
- `seal()` (circle + ring + serif "S") → `mark()` drawing **the Notch**, with
  proportions normalised from the SVG so raster and vector agree exactly
- Decorative concentric **circles → offset squares**, matching `.hero::before/::after`
- Wordmark → `SAT[square]C LLP` drawn in three parts, with a **gold square in
  place of the hyphen** at the same 0.3em / 0.18em / 0.2em geometry as `.wm .hy`,
  so the OG image matches the HTML instead of shipping a literal `-`
- Descriptor → the full firm name, `SETHURAMAN ACCOUNTING, TAX & CONSULTING`
  (mono 17px, tracking 2, so it stays inside the 1200px canvas)
- OG tagline → "Everything you need, from one desk." (the page's actual H1)

> The script prefers IBM Plex Sans if installed and falls back to DejaVu, so it
> runs anywhere. For pixel-exact Plex output, install the family or point the
> `PLEX_*` constants at your `.ttf` files.

Keep `og:image:width` / `og:image:height` at `1200` / `630`.

---

## Accessibility

All checked against the new tokens:

| Pair | Ratio | |
|---|---|---|
| `--charcoal` on `--cream` | 12.9:1 | AAA |
| `--charcoal-2` on `--cream` | 7.4:1 | AAA |
| `--mute` on `--cream` | 3.6:1 | AA large / non-text only — **never body copy** |
| `#fff` on `--oxblood` | 8.9:1 | AAA |
| `#fff` on `--navy` | 14.6:1 | AAA |
| `--gold-deep` on `--cream` | 4.6:1 | AA |
| `--gold` on `--cream` | 2.3:1 | **fails — decorative only** |

Also preserved from the original: `:focus-visible` rings (now oxblood), the
`.chip:has(input:focus-visible)` ring, 44px minimum tap targets on choice rows,
`.sr-only`, and `prefers-reduced-motion`.

---

## Imagery policy

**There is no photography on this site.** That's a decision, not a gap — and it
should be written down so it isn't quietly reversed later.

For a firm positioning on precision, stock photography is the visual equivalent
of the generic palette we moved away from: handshakes, skylines, glass towers,
and calculators on desks all signal "we couldn't think of anything." They also
cost money and date badly.

**What carries the visual load instead:**

| Instead of a photo | Use |
|---|---|
| Hero image | The headline itself, set large. Type is the image. |
| Decorative graphics | The offset squares from the mark, at large scale, low contrast (`.hero::before/::after`) |
| "Trust" imagery | A well-set figures table. For an accounting firm a correctly typeset statement *is* the credential |
| Section breaks | Rules and whitespace — `--hairline` and generous `section.band` padding |
| Icons | The three existing line icons in `.service-icon`. Don't add more |

**Rules**

- No stock photography, ever. No AI-generated imagery, ever.
- Don't add icons beyond the three service marks. An icon per list item turns a
  professional page into a brochure.
- No illustration, no isometric graphics, no abstract 3D shapes.
- The grey striped placeholder boxes used in design mockups are **for design
  only** — they must never reach production. If a slot has no real content, the
  slot shouldn't exist.
- **The one exception worth planning for:** a real portrait of Arjun, if you ever
  want one. If so — plain mid-grey or navy backdrop, natural light, no office
  props, square crop, and one treatment used consistently. One honest portrait
  beats any amount of stock.

---

## Compliance — what to confirm before this goes live

> **Not legal advice.** These are the questions the design raises; the answers
> come from the Accountancy Board of Ohio, the Ohio Secretary of State, and your
> counsel. Placeholders in the templates are marked `[LIKE THIS]`.

The firm is an **Ohio LLP**, Arjun is an **individually licensed Ohio CPA**, and
the firm does **not** perform audits. That combination sits close to a line, so
three things need checking:

**1 · Firm registration.** Ohio generally requires firms practising public
accounting to register with the Accountancy Board of Ohio, separately from the
individual licence. Whether SAT-C needs firm registration depends on the exact
services offered. **Confirm this first** — it governs the two items below.

**2 · How the firm may describe itself.** There's a meaningful difference between:

- *"Led by a licensed CPA"* — a statement about a **person**. This is what the
  site says, and it's the more conservative claim.
- *"CPA firm"* / *"Certified Public Accountants"* — a statement about the
  **firm**, which typically requires firm registration.

The templates deliberately use the first form. Don't upgrade the language to the
second without confirming item 1.

**3 · No assurance language.** Since there's no audit practice, these words must
not appear anywhere in copy, templates, or proposals: *audit, audited, auditing,
assurance, opinion, review engagement, attest, examination.* The "Who this is
for" section states this positively — "we don't do audit work" — which is both
accurate and a trust signal, and the engagement letter repeats it.

**Also confirm:**

- Ohio Secretary of State **registration number**, and whether it must appear on
  correspondence.
- Arjun's **Ohio licence number** — the letterhead has `[NUMBER]` reserved.
- **Peer review** enrolment, if any service offered triggers it.
- The **website disclosure** wording (the general-information disclaimer in the
  footer). The templates carry a bracketed placeholder rather than invented text.
- The full legal name — **"Sethuraman Accounting, Tax, and Consulting LLP"** —
  appears in the footer of every document, with `SAT-C LLP` used only as a short
  form after the full name is established.

---

## Deploy caution

`website/` auto-deploys to GitHub Pages on push to `main`. Per repo convention:
**feature branch → draft PR**, not a direct push. This restyle is a visible
change to a live page — the warm→cool shift is the most noticeable part.
