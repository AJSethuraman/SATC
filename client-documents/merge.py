"""Merge a client record into a SATC document template.

The templates in ``satc-handoff/04-TEMPLATES`` carry three kinds of marker:

    &lt;&lt;Field&gt;&gt;          substitute a value
    [[IF Flag]] … [[END IF]]      keep or drop the block
    [[EACH List]] … [[END EACH]]  repeat the block once per item

Fields are HTML-escaped in the source (they sit inside ``<span class="f">``);
flags and lists are literal, wrapped in a marker element that exists only so an
unfilled proof is obvious.

Three rules, taken from the templates' own field docs, are enforced here rather
than left to whoever calls this:

1. **Values are escaped.** A client named "Ross & Sons" would otherwise break
   the page.
2. **An unresolved token is a hard failure.** A letter reaching a client with
   ``<<ClientFullName>>`` still in it is, in the templates' words, the one bug
   that actually costs you a client. Never render past it.
3. **A surviving ``[CONFIRM:`` is a hard failure too.** Firm settings carry
   placeholders for decisions not yet made; they must not reach a client
   either, and they fail for the same reason and by the same mechanism.

Nothing here writes a PDF. It produces client-ready HTML; printing is the
caller's problem.
"""

from __future__ import annotations

import decimal
import html
import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path

# --- marker patterns -------------------------------------------------------
# Every marker sits alone inside its wrapper, so the wrapper can be swallowed
# whole. Ordered most-specific first: a table row, then a list item, then a
# bare span. The span form also covers the invoice's inline EstimateReference.
_WRAPPERS = [
    r'<tr class="mark">\s*<td[^>]*>\s*<span class="cond[^"]*">\[\[{tok}\]\]</span>\s*</td>\s*</tr>',
    r'<li class="mark">\s*<span class="cond[^"]*">\[\[{tok}\]\]</span>\s*</li>',
    r'<span class="cond[^"]*">\[\[{tok}\]\]</span>',
]

_FIELD_IN_SPAN = re.compile(r'<span class="f">\s*&lt;&lt;([A-Za-z0-9_.]+)&gt;&gt;\s*</span>')
_FIELD_BARE = re.compile(r'&lt;&lt;([A-Za-z0-9_.]+)&gt;&gt;')
_REF_BLOCK = re.compile(r'<div class="ref">.*?</div>\s*(?=<script|</body)', re.S)

_UNRESOLVED_FIELD = re.compile(r'&lt;&lt;[^&]*&gt;&gt;|<<[A-Za-z0-9_.]+>>')
_UNRESOLVED_BLOCK = re.compile(r'\[\[[^\]]*\]\]')
_CONFIRM = re.compile(r'\[CONFIRM:[^\]]*\]')


class MergeError(RuntimeError):
    """Raised rather than shipping a document with a hole in it."""


@dataclass
class MergeResult:
    html: str
    fields_used: set = dc_field(default_factory=set)
    blocks_kept: set = dc_field(default_factory=set)
    blocks_dropped: set = dc_field(default_factory=set)
    # old -> new section numbers, empty when the document numbered correctly
    # on its own. Carried out so a caller can SAY that a document was
    # renumbered: a silent renumber and no renumber look identical from here,
    # and one of them means a condition dropped a section.
    renumbered: dict = dc_field(default_factory=dict)


def _sentinel(name: str) -> str:
    return f"\x00{name}\x00"


def _swallow_marker(text: str, token: str, replacement: str) -> str:
    """Replace a marker and the wrapper element that exists only to hold it."""
    for pat in _WRAPPERS:
        rx = re.compile(pat.format(tok=re.escape(token)))
        if rx.search(text):
            return rx.sub(replacement, text, count=1)
    # Bare, unwrapped — still valid.
    return text.replace(f"[[{token}]]", replacement, 1)


def _render_each(text: str, record: dict) -> str:
    """Expand [[EACH List]] … [[END EACH]] once per item."""
    while True:
        m = re.search(r"\[\[EACH ([A-Za-z0-9_]+)\]\]", text)
        if not m:
            return text
        name = m.group(1)
        text = _swallow_marker(text, f"EACH {name}", _sentinel("EACH"))
        text = _swallow_marker(text, "END EACH", _sentinel("ENDEACH"))

        start = text.index(_sentinel("EACH"))
        end = text.index(_sentinel("ENDEACH"))
        if end < start:
            raise MergeError(f"[[END EACH]] precedes [[EACH {name}]]")
        chunk = text[start + len(_sentinel("EACH")):end]

        items = record.get(name) or []
        if not isinstance(items, list):
            raise MergeError(f"{name} must be a list, got {type(items).__name__}")

        rendered = []
        for n, item in enumerate(items, 1):
            if not isinstance(item, dict):
                raise MergeError(
                    f"row {n} of {name} is a {type(item).__name__}, not a set "
                    f"of fields — a list of strings cannot fill a table whose "
                    f"columns have names")
            piece = chunk
            for key, value in item.items():
                piece = _substitute_one(piece, f"Item.{key}", value)
            rendered.append(piece)

        text = text[:start] + "".join(rendered) + text[end + len(_sentinel("ENDEACH")):]


def _render_if(text: str, record: dict, kept: set, dropped: set) -> str:
    """Keep or drop [[IF Flag]] … [[END IF]] blocks."""
    while True:
        m = re.search(r"\[\[IF ([A-Za-z0-9_]+)\]\]", text)
        if not m:
            return text
        name = m.group(1)
        text = _swallow_marker(text, f"IF {name}", _sentinel("IF"))
        text = _swallow_marker(text, "END IF", _sentinel("ENDIF"))

        start = text.index(_sentinel("IF"))
        end = text.index(_sentinel("ENDIF"))
        if end < start:
            raise MergeError(f"[[END IF]] precedes [[IF {name}]]")
        chunk = text[start + len(_sentinel("IF")):end]

        if record.get(name):
            kept.add(name)
            replacement = chunk
        else:
            dropped.add(name)
            replacement = ""
        text = text[:start] + replacement + text[end + len(_sentinel("ENDIF")):]


# What a sentence can be given. Anything else is a category error: the record
# handed a TABLE to a slot that holds a phrase.
SCALARS = (str, int, float, bool, decimal.Decimal)


def _substitute_one(text: str, name: str, value) -> str:
    """Replace one field. The .f span goes with it — that chrome is proof-only."""
    safe = html.escape("" if value is None else str(value))
    esc = re.escape(name)
    text = re.sub(rf'<span class="f">\s*&lt;&lt;{esc}&gt;&gt;\s*</span>', lambda _: safe, text)
    text = re.sub(rf'&lt;&lt;{esc}&gt;&gt;', lambda _: safe, text)
    return text


# ── section numbering ─────────────────────────────────────────────────────
#
# A dropped `[[IF]]` section leaves a HOLE IN THE NUMBERING and nothing put it
# right. Every onboarding letter for a client with no previous accountant went
# out reading 01, 02, 04, 05 -- 26 of the 27 packs the harness produces -- and
# the delivery letter jumped 03 to 05 in all 27. The template's own FIELDS spec
# asked for this in so many words ("Renumber the remaining sections in code --
# 05 and 06 must not follow 03") and it was never built.
#
# It belongs HERE, after `_render_if`, and nowhere else. `editor.renumber()`
# renumbers the TEMPLATE, where there is no gap: the gap only exists once a
# condition has been resolved, so a renumbering that reads the template is
# renumbering the one version of the document that was already correct.
_SECTION_N = re.compile(r'(<h2[^>]*><span class="n">)(\d+)(</span>)')
_SECTION_REF = re.compile(r'\b(sections?)(\s+)(\d{1,2})\b', re.I)


def _renumber_sections(text: str) -> tuple[str, dict[str, str]]:
    """Make the numbers on the page read 01..N with no gaps.

    Returns the text and the old->new map, which is empty when nothing moved.
    Prose that cites a section by number is remapped with it: renumbering the
    headings alone would leave "section 04 tells you what to do" pointing at
    whatever now occupies 04, which is worse than the gap it fixed.
    """
    found = _SECTION_N.findall(text)
    if not found:
        return text, {}
    old = [n for _, n, _ in found]
    new = [f"{i:02d}" for i in range(1, len(old) + 1)]
    if old == new:
        return text, {}

    mapping = dict(zip(old, new))

    seq = iter(new)
    text = _SECTION_N.sub(lambda m: f"{m.group(1)}{next(seq)}{m.group(3)}", text)

    def _ref(m):
        n = m.group(3)
        moved = mapping.get(n) or mapping.get(n.zfill(2))
        return f"{m.group(1)}{m.group(2)}{moved}" if moved else m.group(0)

    return _SECTION_REF.sub(_ref, text), mapping


def _dangling_section_refs(text: str) -> set[str]:
    """Numbers the prose cites that the document does not have.

    A client reading "section 03 explains what to do" and finding no section 03
    is the same failure as an unresolved token: the document says something
    that is not true of itself.
    """
    have = {n for _, n, _ in _SECTION_N.findall(text)}
    if not have:
        return set()
    cited = {m.group(3).zfill(2) for m in _SECTION_REF.finditer(text)}
    return cited - have


def render(template_html: str, record: dict, *, strict: bool = True,
           required_lists: "tuple[str, ...] | list[str]" = (),
           inverse_flags: "tuple[tuple[str, str], ...]" = ()) -> MergeResult:
    """Fill a template. Raises MergeError rather than returning a holed document.

    `inverse_flags` names pairs of flags that are two faces of ONE decision --
    "a payment goes with the extension" and "there is nothing to pay". Exactly
    one must be true. Two independent booleans can both be false, and when
    they were, the extension notice printed a heading that warns the payment
    deadline has not moved, an intro that says "section 02 tells you what to
    do about that", and then NOTHING in section 02. The template's own notes
    call that "the worst possible version of this letter" and asked for the
    two to be derived from one stored value; the relationship was recorded in
    prose that nothing read.

    `required_lists` names the `[[EACH X]]` lists that may not be empty. An
    EACH block over a missing list renders to exactly the same nothing as one
    over an empty list, and nothing is indistinguishable from a list that was
    never supplied -- so a fee estimate rendered a blank services table with a
    total underneath it and this function raised nothing at all. Which lists
    may legitimately be empty is a judgement about the document, so it is
    declared in `registry/fields.yaml` (`required: true`) and passed in here,
    not decided in this module.
    """
    text = _REF_BLOCK.sub("", template_html)     # screen-only docs never ship

    kept: set = set()
    dropped: set = set()
    text = _render_each(text, record)
    text = _render_if(text, record, kept, dropped)
    text, renumbered = _renumber_sections(text)

    used = set()
    for name in sorted(set(_FIELD_IN_SPAN.findall(text)) | set(_FIELD_BARE.findall(text))):
        if name.startswith("Item."):
            continue                              # belongs to an EACH block
        if name not in record:
            continue                              # reported below, not silently blanked
        value = record[name]
        # A LIST HANDED TO A SENTENCE USED TO PRINT AS PYTHON. A disengagement
        # letter went out reading: It covers [{'Item': '2026 federal and Ohio
        # returns', 'Status': 'Complete'}]. `str(value)` will happily render a
        # repr into a client's letter and nothing downstream can tell that
        # apart from a phrase somebody meant to write.
        #
        # `[[EACH]]` has refused a non-list since it was written. This is the
        # same gate facing the other way, and it was the missing half.
        if value is not None and not isinstance(value, SCALARS):
            raise MergeError(
                f"{name} is a {type(value).__name__} and this document uses it "
                f"as a phrase, not a table. Rendering it would print Python "
                f"into a client's letter.")
        text = _substitute_one(text, name, value)
        used.add(name)

    if strict:
        problems = []
        # Checked before the token scan: an empty list leaves no token behind,
        # so it would otherwise pass every check below it.
        for name in required_lists:
            rows = record.get(name)
            if not isinstance(rows, list) or not rows:
                problems.append(
                    f"{name} is required and is "
                    + ("missing" if name not in record else "empty")
                    + " -- this document cannot be honest without it")
        leftover = {m for m in _UNRESOLVED_FIELD.findall(text)}
        if leftover:
            problems.append("unresolved fields: " + ", ".join(sorted(leftover)))
        blocks = {m for m in _UNRESOLVED_BLOCK.findall(text)}
        if blocks:
            problems.append("unresolved blocks: " + ", ".join(sorted(blocks)))
        confirms = {m for m in _CONFIRM.findall(text)}
        if confirms:
            problems.append("undecided placeholders: " + ", ".join(sorted(confirms)))
        for a, b in inverse_flags:
            # Only where the template actually uses them: a pair that does not
            # appear in this document is not this document's problem.
            if f"IF {a}" not in template_html and f"IF {b}" not in template_html:
                continue
            on = [n for n in (a, b) if record.get(n)]
            if len(on) != 1:
                problems.append(
                    f"{a} and {b} are two faces of one decision and "
                    + ("both are set" if len(on) == 2 else "neither is set")
                    + " -- the section they control would "
                    + ("contradict itself" if len(on) == 2 else "come out empty")
                    + ", and the document promises the reader it says something")
        dangling = _dangling_section_refs(text)
        if dangling:
            problems.append(
                "points the reader at section(s) "
                + ", ".join(sorted(dangling))
                + ", which this document does not have")
        if problems:
            raise MergeError("; ".join(problems))

    return MergeResult(html=text, fields_used=used, blocks_kept=kept,
                       blocks_dropped=dropped, renumbered=renumbered)


def render_file(template_path: str | Path, record: dict, **kw) -> MergeResult:
    return render(Path(template_path).read_text(encoding="utf-8"), record, **kw)


def tokens_in(template_html: str) -> dict:
    """Every token a template needs. Used by the reconciliation tests.

    ``item_fields`` is the union across the whole template. ``list_items`` is
    the same information split per list, which is the useful form once a
    template carries more than one: the delivery letter's ``ReturnsDelivered``
    and ``ActionList`` have different sub-fields, and a union cannot say so.
    """
    body = _REF_BLOCK.sub("", template_html)
    fields = set(_FIELD_BARE.findall(body))
    return {
        "fields": {f for f in fields if not f.startswith("Item.")},
        "item_fields": {f.split(".", 1)[1] for f in fields if f.startswith("Item.")},
        "flags": set(re.findall(r"\[\[IF ([A-Za-z0-9_]+)\]\]", body)),
        "lists": set(re.findall(r"\[\[EACH ([A-Za-z0-9_]+)\]\]", body)),
        "list_items": _list_items(body),
    }


def _list_items(body: str) -> dict:
    """{list name: sorted sub-field names} for each EACH block in `body`."""
    out = {}
    for m in re.finditer(r"\[\[EACH ([A-Za-z0-9_]+)\]\]", body):
        end = body.find("[[END EACH]]", m.end())
        span = body[m.end():end if end != -1 else len(body)]
        out[m.group(1)] = sorted(
            f.split(".", 1)[1]
            for f in set(_FIELD_BARE.findall(span))
            if f.startswith("Item.")
        )
    return out
