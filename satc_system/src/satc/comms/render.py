"""Merging values into a template — the pure half of the comms area.

Two rules shape everything here:

1. **Never invent a value.** A merge field the practice has no fact for is not
   guessed, not silently blanked, and not left as a bare ``{slot}`` that reads
   like a typo. It is replaced with a loud, obviously-unfinished marker —
   ``[[ Fee: fill in ]]`` — so a draft can never be sent looking complete when it
   isn't. :attr:`RenderedDraft.unfilled` names every one.
2. **Substitution, not ``str.format``.** ``format`` raises on the first missing
   key and would choke on any stray brace in a body. This walks the placeholders
   it finds and leaves anything undeclared alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from satc.comms.library import CommsLibrary, CommsTemplate

# A merge field: `{client_name}`. Deliberately strict (lowercase identifiers) so
# ordinary prose braces in a body are never mistaken for a slot.
_SLOT = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def placeholder_names(template: CommsTemplate) -> list[str]:
    """Every merge field used by a template's subject + body, first-seen order."""
    seen: list[str] = []
    for text in (template.subject, template.body):
        for match in _SLOT.finditer(text or ""):
            if match.group(1) not in seen:
                seen.append(match.group(1))
    return seen


def unfilled_marker(name: str, label: str = "") -> str:
    """The visible stand-in for a slot nothing filled."""
    return f"[[ {label or name}: fill in ]]"


@dataclass(slots=True)
class RenderedDraft:
    """A rendered draft: what to send, and what's still missing from it."""

    key: str
    name: str
    kind: str
    subject: str
    body: str
    filled: list[str] = field(default_factory=list)
    unfilled: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.unfilled

    @property
    def text(self) -> str:
        """Subject line + body, the way the two seed files read on disk."""
        return f"Subject: {self.subject}\n\n{self.body}" if self.subject else self.body


def _merge_text(value) -> str:
    """The text a value contributes — ``""`` when it holds nothing.

    Whitespace handling differs by shape, because the two shapes mean different
    things. A single-line value is a stray fact off a record, so it is stripped.
    A multi-line value is a formatted BLOCK (a bullet list of requested items),
    where leading spaces are the indentation — stripping it would left-align the
    first bullet and leave the rest indented.
    """
    if value is None:
        return ""
    text = str(value)
    if not text.strip():
        return ""
    return text.strip("\n").rstrip() if "\n" in text else text.strip()


def render(template: CommsTemplate, values: dict[str, str], *,
           library: CommsLibrary | None = None) -> RenderedDraft:
    """Merge ``values`` into ``template``; mark every slot they didn't fill.

    A value counts as filled only if it holds non-whitespace text — a blank
    means "we don't hold this fact", which is exactly the case the marker
    exists for.
    """
    filled: list[str] = []
    unfilled: list[str] = []

    def label_for(name: str) -> str:
        p = library.placeholder(name) if library is not None else None
        return p.label if p is not None else name

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        text = _merge_text(values.get(name))
        if text:
            if name not in filled:
                filled.append(name)
            return text
        if name not in unfilled:
            unfilled.append(name)
        return unfilled_marker(name, label_for(name))

    subject = _SLOT.sub(substitute, template.subject or "")
    body = _SLOT.sub(substitute, template.body or "")
    return RenderedDraft(key=template.key, name=template.name, kind=template.kind,
                         subject=subject, body=body, filled=filled, unfilled=unfilled)


def render_key(key: str, values: dict[str, str], *,
               library: CommsLibrary | None = None) -> RenderedDraft:
    """Convenience: look a template up by key in ``library`` and render it."""
    from satc.comms.library import library as installed

    lib = library or installed()
    return render(lib.template(key), values, library=lib)
