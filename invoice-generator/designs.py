"""Invoice designs — the gallery a sender picks a look from.

A design is **presentation only**. It changes colours, type and the shape of
the masthead; it never changes a number, a field, or which fields exist. That
line is load-bearing: the same invoice rendered in any of these must total the
same, and ``tests/test_designs.py`` proves it by rendering one invoice through
every design and comparing the money.

## Two axes, multiplied

A *family* is a layout treatment (where the accent sits, whether the table
header is filled, how heavy the type is). A *palette* is a colour pairing.
Every family works with every palette, so the gallery is the product of the
two rather than a hand-maintained list of near-duplicates.

The count is therefore ``len(FAMILIES) * len(PALETTES)`` and is asserted in the
tests rather than written down in prose, because a number in a docstring is a
number that goes stale. (`docs/SOFTWARE-TENETS.md` — report the denominator,
and let the software report it.)

## Why the CSS lives here and not in the template

Both front doors render the *same* document markup: the PDF template and the
on-screen editor include ``_invoice_document.html``. If the two carried
separate stylesheets the on-screen "live preview" would be a lookalike rather
than a preview, and the first time they drifted we would be showing a client
one thing and sending them another. One token table, one CSS emitter, two
callers.

## The PDF engines constrain what a design may do

``pdf.py`` renders through WeasyPrint *or* xhtml2pdf, and the latter supports
no flexbox, no grid and no absolute positioning. Every design here is
expressible in table-safe CSS — background colours, borders, padding, type.
A family that needed real layout primitives would render correctly in the
browser and silently differently in the PDF, which is the exact failure the
shared-template decision above exists to prevent.
"""

# --- palettes ---------------------------------------------------------
#
# ``ink`` is body/heading text, ``accent`` the brand colour, ``soft`` a tint
# of the accent light enough to carry ``accent`` text on top of it. The pairs
# are chosen so accent-on-soft and white-on-accent both clear WCAG AA at the
# sizes the document uses them.
PALETTES = {
    "navy":     {"label": "Navy",     "ink": "#1f2a44", "accent": "#2563eb", "soft": "#eff4ff"},
    "slate":    {"label": "Slate",    "ink": "#0f172a", "accent": "#475569", "soft": "#f1f5f9"},
    "emerald":  {"label": "Emerald",  "ink": "#0b2e22", "accent": "#059669", "soft": "#ecfdf5"},
    "plum":     {"label": "Plum",     "ink": "#2e1065", "accent": "#7c3aed", "soft": "#f5f3ff"},
    "crimson":  {"label": "Crimson",  "ink": "#450a0a", "accent": "#dc2626", "soft": "#fef2f2"},
    "amber":    {"label": "Amber",    "ink": "#431407", "accent": "#b45309", "soft": "#fffbeb"},
    "teal":     {"label": "Teal",     "ink": "#042f2e", "accent": "#0d9488", "soft": "#f0fdfa"},
    "graphite": {"label": "Graphite", "ink": "#18181b", "accent": "#52525b", "soft": "#f4f4f5"},
}

# Two stacks, both resolvable without shipping a font file. WeasyPrint and
# xhtml2pdf each fall back to their own built-in faces for anything they
# cannot find, and a webfont that resolves in the browser but not in the PDF
# would reflow the document between the preview and the artifact.
SANS = '"Helvetica Neue", Helvetica, Arial, sans-serif'
SERIF = 'Georgia, "Times New Roman", Times, serif'

# --- families ---------------------------------------------------------
#
# ``head``  — how the masthead is treated: rule | band | plain | stripe
# ``thead`` — the line-item header fill: ink | accent | none
# ``title`` — the size/weight of the word INVOICE
FAMILIES = {
    "classic": {
        "label": "Classic",
        "blurb": "A dark rule under the masthead and a solid header row.",
        "font": SANS, "head": "rule", "thead": "ink",
        "title_size": "26pt", "title_weight": "bold", "title_spacing": "1pt",
        "radius": "10px",
    },
    "band": {
        "label": "Band",
        "blurb": "A full-width colour band across the top of the page.",
        "font": SANS, "head": "band", "thead": "accent",
        "title_size": "24pt", "title_weight": "bold", "title_spacing": "1.5pt",
        "radius": "8px",
    },
    "minimal": {
        "label": "Minimal",
        "blurb": "Hairlines and white space. No filled blocks anywhere.",
        "font": SANS, "head": "plain", "thead": "none",
        "title_size": "20pt", "title_weight": "normal", "title_spacing": "3pt",
        "radius": "4px",
    },
    "bold": {
        "label": "Bold",
        "blurb": "An oversized title and heavy type throughout.",
        "font": SANS, "head": "plain", "thead": "ink",
        "title_size": "38pt", "title_weight": "bold", "title_spacing": "-1pt",
        "radius": "2px",
    },
    "stripe": {
        "label": "Stripe",
        "blurb": "A colour bar down the left edge, set in a serif.",
        "font": SERIF, "head": "stripe", "thead": "none",
        "title_size": "24pt", "title_weight": "normal", "title_spacing": "2pt",
        "radius": "6px",
    },
    "modern": {
        "label": "Modern",
        "blurb": "Tinted header row and a soft totals block.",
        "font": SANS, "head": "rule", "thead": "accent",
        "title_size": "28pt", "title_weight": "bold", "title_spacing": "0pt",
        "radius": "14px",
    },
}

# The design used when none is chosen. It reproduces the look the app shipped
# with before the gallery existed, so an invoice saved by the old form and
# re-rendered by the new code comes out of the printer unchanged.
DEFAULT_DESIGN = "classic-navy"


def design_id(family, palette):
    return f"{family}-{palette}"


def all_designs():
    """Every design in gallery order, as a list of resolved token dicts."""
    return [
        resolve(design_id(family, palette))
        for family in FAMILIES
        for palette in PALETTES
    ]


def is_design(value):
    return isinstance(value, str) and value in {
        design_id(f, p) for f in FAMILIES for p in PALETTES
    }


def resolve(value):
    """Return the token dict for ``value``, falling back to the default.

    **This function defaults where most of this codebase refuses**, and the
    distinction is deliberate rather than an exception being carved out.
    ``helpers.parse_money`` refuses an unparseable rate because the
    alternative is billing a number nobody typed. A design id is not a fact
    about the engagement — it is a skin. An invoice that will not render
    because a stale bookmark carries a retired design id is a worse outcome
    than the same invoice rendering in the default look, and nothing about
    the money moves either way.

    The invariant that keeps this honest is tested: every design totals the
    same invoice identically, so a wrong skin cannot become a wrong amount.
    """
    if not is_design(value):
        value = DEFAULT_DESIGN
    family_key, palette_key = value.split("-", 1)
    family = FAMILIES[family_key]
    palette = PALETTES[palette_key]
    return {
        "id": value,
        "family": family_key,
        "palette": palette_key,
        "label": f"{family['label']} {palette['label']}",
        "blurb": family["blurb"],
        "ink": palette["ink"],
        "accent": palette["accent"],
        "soft": palette["soft"],
        "font": family["font"],
        "head": family["head"],
        "thead": family["thead"],
        "title_size": family["title_size"],
        "title_weight": family["title_weight"],
        "title_spacing": family["title_spacing"],
        "radius": family["radius"],
        # Fixed neutrals. They sit outside the palette because a muted
        # caption tinted with the brand colour reads as a mistake rather
        # than as a choice at 8pt.
        "muted": "#64748b",
        "body": "#475569",
        "line": "#e2e8f0",
        "zebra": "#f8fafc",
    }
