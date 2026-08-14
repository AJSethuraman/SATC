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
| `.lockup .seal` | Square mark; `.divider` set to `display:none` |
| `.lockup .name` | Sans 700, tracking `-0.03em` (was serif, `+0.18em`) |
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

### 1 · The mark — "the Notch" (nav + footer, 2 places)

Replaces the circular `S` seal. Same `.seal` class, same size slot. The outer
**path** is a square with an 8×8 notch removed at the bottom-right; the inner
rect is that removed piece, the same 8×8, set beside it. Outer uses
`currentColor` so `.on-dark` inverts automatically.

Full specification — construction grid, colour variants, size range, lockups,
misuse — is in **`SATC Mark - Notch Spec.html`**.

```html
<svg class="seal" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path class="s-o" d="M3 3 H19 V11 H11 V19 H3 Z"/>
  <rect class="s-i" x="22" y="22" width="8" height="8"/>
</svg>
```

> **The notch and the piece must both stay 8×8** — the piece fits the hole it
> came from, and that equality is the entire concept. Don't resize either one,
> don't fill the outline, and don't rotate the mark.

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
- Wordmark → sans (tries IBM Plex Sans, falls back to DejaVu), mono for tracked lines
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

## Deploy caution

`website/` auto-deploys to GitHub Pages on push to `main`. Per repo convention:
**feature branch → draft PR**, not a direct push. This restyle is a visible
change to a live page — the warm→cool shift is the most noticeable part.
