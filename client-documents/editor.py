"""Open a template, open a section, edit the wording. Save.

The firm's ask, 26 August 2026, and their own framing of the cost:

    "for editing these this may be overkill but i do not care. i want it to be
     very straightforward and simple. like i can just click a template, open a
     section, edit it"

The templates are hand-authored HTML and will stay that way -- the layout, the
merge markers and the print stylesheet are not things anyone should be editing
through a form. What a person actually wants to change is a SENTENCE. So this
module exposes exactly that: every paragraph and list item in a template, as
plain text, grouped under the numbered section it sits in.

THE ROUND TRIP IS THE SAFETY. A block is editable only if `to_html(to_text(x))`
returns `x` byte for byte. Anything this module cannot take apart and put back
together identically is shown read-only rather than mangled, and
`test_editor.py` checks that property against every block in all ten templates.
A block that stops round-tripping becomes read-only on its own; it never
becomes a corrupted document.

The little markup a person types:

    **bold**        <strong>bold</strong>
    *emphasis*      <em>emphasis</em>
    <<FieldName>>   the merge field, in the span the stylesheet expects

Everything else is refused at save time, because a template is not a place to
invent HTML.
"""

from __future__ import annotations

import html as H
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"

# The on-screen crib at the bottom of every template. It is stripped before a
# client sees the page and is documentation for whoever wires the software, so
# it is not offered for editing.
REF = '<div class="ref">'

EDITABLE_TAGS = ("p", "li")

# What the little markup can express, and therefore all a block may contain if
# a person is going to edit it as text. A WHITELIST rather than a list of
# things to avoid: the first version listed the nesting tags it knew about, and
# happily offered a `<li>` holding nothing but `[[EACH ScopeItems]]`, and the
# checkbox scaffolding, and anything with a `<br/>` in it.
_KNOWN = re.compile(r"</?(?:strong|b|em|i)>|<span class=\"f\">|</span>")


class EditError(Exception):
    """The edit would damage the document, so it was not saved."""


# ── the little markup ─────────────────────────────────────────────────────

_FIELD_SPAN = re.compile(r'<span class="f">&lt;&lt;([A-Za-z][\w.]*)&gt;&gt;</span>')
_STRONG = re.compile(r"<(strong|b)>(.*?)</\1>", re.S)
_EM = re.compile(r"<(em|i)>(.*?)</\1>", re.S)


def to_text(inner: str) -> str:
    """A block's inner HTML -> what a person types."""
    t = _FIELD_SPAN.sub(lambda m: f"<<{m.group(1)}>>", inner)
    t = _STRONG.sub(lambda m: f"**{m.group(2)}**", t)
    t = _EM.sub(lambda m: f"*{m.group(2)}*", t)
    return H.unescape(t)


def _tag_used(inner: str, pair: tuple[str, str]) -> str:
    """Which of two equivalent tags this block already uses.

    `<b>` and `<strong>` mean the same thing to a reader, and the templates
    use both. The editor keeps whichever the block was written with rather
    than normalising, so an edit never restyles the sentence it edits; where a
    block mixes them it takes the one that comes first.

    That mixing is why `.body b` was given `.body strong`'s rule on 26 August
    2026. Measured in a browser, `<strong>` was resolving to weight 600 in
    navy and `<b>` to the browser default 700 in body ink -- two visibly
    different bolds inside one paragraph of a client's letter.
    """
    short, long = pair
    hits = [(m.start(), m.group(1))
            for m in re.finditer(rf"<({short}|{long})>", inner)]
    return hits[0][1] if hits else long


def to_html(text: str, like: str = "") -> str:
    """What a person types -> a block's inner HTML.

    Escaping happens FIRST so that a stray `<` or `&` in someone's sentence
    cannot open a tag; the markup is then re-expanded from the escaped text.
    `like` is the block being replaced, and only decides `<b>` vs `<strong>`
    and `<i>` vs `<em>`.
    """
    strong = _tag_used(like, ("b", "strong"))
    em = _tag_used(like, ("i", "em"))
    t = H.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<{strong}>{m.group(1)}</{strong}>", t, flags=re.S)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
               lambda m: f"<{em}>{m.group(1)}</{em}>", t, flags=re.S)
    t = re.sub(r"&lt;&lt;([A-Za-z][\w.]*)&gt;&gt;",
               lambda m: f'<span class="f">&lt;&lt;{m.group(1)}&gt;&gt;</span>', t)
    return t


def round_trips(inner: str) -> bool:
    """Can the editor take this block apart and put it back, byte for byte?

    BYTE FOR BYTE, not "near enough". The first version accepted a block that
    came back normalised, on the reasoning that `<b>` and `<strong>` render
    the same. `test_editor.py` immediately caught what that means in practice:
    open a section, change nothing, save it, and three sentences of the
    delivery letter get rewritten. Opening a document must never modify it.

    Five blocks mixed the two tags in one sentence and were normalised in the
    templates instead, once, by hand -- which is also what surfaced the
    stylesheet bug where the two rendered at different weights.
    """
    try:
        return to_html(to_text(inner), like=inner) == inner
    except Exception:
        return False


# ── finding the blocks ────────────────────────────────────────────────────

def _spans(html: str, tag: str) -> list[tuple[int, int]]:
    """(start, end) of every `<tag>`'s INNER html, nesting handled."""
    open_re = re.compile(rf"<{tag}\b[^>]*>", re.I)
    close = f"</{tag}>"
    out, i = [], 0
    while True:
        m = open_re.search(html, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth:
            nxt_open = open_re.search(html, j)
            nxt_close = html.find(close, j)
            if nxt_close == -1:
                return out              # malformed; stop rather than guess
            if nxt_open and nxt_open.start() < nxt_close:
                depth += 1
                j = nxt_open.end()
            else:
                depth -= 1
                j = nxt_close + len(close)
        out.append((m.end(), j - len(close)))
        i = j


_HEADING = re.compile(r'<h2>(?:<span class="n">(\d+)</span>)?(.*?)</h2>', re.S)


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def _editable(inner: str) -> tuple[bool, str]:
    """May a person edit this block as a sentence, and if not, why not."""
    if "[[" in inner or "]]" in inner:
        return False, "carries a conditional or a repeat — that is structure"
    left = _KNOWN.sub("", inner)
    if "<" in left or ">" in left:
        stray = re.search(r"<[^>]*>?", left)
        return False, f"carries markup the editor cannot rebuild: {stray.group(0)[:40]}"
    if not round_trips(inner):
        return False, "cannot be taken apart and put back exactly"
    return True, ""


@dataclass
class Block:
    id: str
    start: int
    end: int
    tag: str
    html: str
    text: str
    editable: bool
    reason: str = ""
    fields: tuple[str, ...] = ()


@dataclass
class Section:
    id: str
    number: str
    title: str
    blocks: list[Block] = field(default_factory=list)


def body_of(html: str) -> str:
    return html.split(REF)[0]


def sections(html: str) -> list[Section]:
    """Every editable sentence in a template, under the section it lives in."""
    body = body_of(html)

    heads = [(m.start(), m.group(1) or "", _strip(m.group(2)))
             for m in _HEADING.finditer(body)]

    found: list[tuple[int, int, str]] = []
    for tag in EDITABLE_TAGS:
        found += [(a, b, tag) for a, b in _spans(body, tag)]
    found.sort()

    # A block inside another editable block is that block's business.
    top: list[tuple[int, int, str]] = []
    for a, b, tag in found:
        if any(a2 <= a and b <= b2 for a2, b2, _ in top):
            continue
        top.append((a, b, tag))

    out = [Section("top", "", "Top of the document")]
    seen = {"top": 0}
    hi = 0
    for a, b, tag in top:
        while hi < len(heads) and heads[hi][0] < a:
            num, title = heads[hi][1], heads[hi][2]
            sid = f"s{num or len(out)}"
            out.append(Section(sid, num, title))
            seen[sid] = 0
            hi += 1
        sec = out[-1]
        inner = body[a:b]
        editable, reason = _editable(inner)
        seen[sec.id] += 1
        sec.blocks.append(Block(
            id=f"{sec.id}.{seen[sec.id]}", start=a, end=b, tag=tag,
            html=inner, text=to_text(inner), editable=editable, reason=reason,
            fields=tuple(sorted(set(_FIELD_SPAN.findall(inner)))),
        ))
    return [s for s in out if s.blocks]


def find(html: str, block_id: str) -> Block:
    for s in sections(html):
        for b in s.blocks:
            if b.id == block_id:
                return b
    raise EditError(f"no block {block_id!r} in this template")


# ── saving ────────────────────────────────────────────────────────────────

_BANNED = (("[[", "a conditional or a repeat"),
           ("]]", "a conditional or a repeat"),
           ("[CONFIRM:", "an open decision"))


def check(before: Block, text: str) -> str:
    """The proposed replacement's inner HTML, or raise.

    Every rule here is one way an edit could produce a document that still
    renders and is quietly wrong.
    """
    if not before.editable:
        raise EditError(
            f"{before.id} is shown read-only: {before.reason}. Edit the "
            f"template file itself if this really has to change."
        )
    if not text.strip():
        raise EditError(
            "an empty block would leave a gap in the document. Delete it in "
            "the template file if it should not be there at all."
        )
    for token, what in _BANNED:
        if token in text:
            raise EditError(
                f"{token!r} is {what}, which decides whether whole blocks "
                f"appear. That is structure, not wording, and it belongs in "
                f"the template file."
            )
    after = to_html(text, like=before.html)
    was = set(before.fields)
    now = set(_FIELD_SPAN.findall(after))
    if was - now:
        raise EditError(
            "this would drop " + ", ".join(f"<<{f}>>" for f in sorted(was - now))
            + ". A merge field carries a real value onto the document; losing "
              "one loses the value silently."
        )
    if now - was:
        raise EditError(
            "this adds " + ", ".join(f"<<{f}>>" for f in sorted(now - was))
            + ", which the registry does not record for this template. A new "
              "field has to be registered before it can be used, or the "
              "render fails at the client's document."
        )
    if to_html(to_text(after), like=after) != after:
        raise EditError(
            "the result cannot be read back as text, so the editor would not "
            "be able to show you what it saved."
        )
    return after


def apply(html: str, edits: dict[str, str]) -> tuple[str, list[str]]:
    """The template with some blocks' wording replaced, and which changed.

    EVERY EDIT IS CHECKED BEFORE ANY IS WRITTEN. A section saved as a whole
    must not leave half its sentences changed and half refused: that is a
    document nobody can reason about, and the person would have to work out
    which half landed.

    Applied back to front so an earlier block's new length cannot move a later
    block's offsets out from under it.
    """
    body = body_of(html)
    tail = html[len(body):]
    blocks = {b.id: b for s in sections(html) for b in s.blocks}

    planned = []
    for bid, text in edits.items():
        before = blocks.get(bid)
        if before is None:
            raise EditError(f"no block {bid!r} in this template")
        after = check(before, text)
        if after != before.html:
            planned.append((before, after))

    for before, after in sorted(planned, key=lambda x: -x[0].start):
        body = body[:before.start] + after + body[before.end:]
    return body + tail, [b.id for b, _ in planned]


def save(name: str, edits: dict[str, str], template_dir: Path | None = None) -> list[str]:
    """Write the edits, or write nothing. Returns the ids that changed."""
    d = Path(template_dir) if template_dir else TEMPLATE_DIR
    path = d / name
    if path.parent != d or not path.exists():
        raise EditError(f"no template {name!r}")
    html, changed = apply(path.read_text(encoding="utf-8"), edits)
    if changed:
        path.write_text(html, encoding="utf-8")
    return changed
