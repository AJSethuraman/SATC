"""Adding a template should be a sentence, not a YAML expedition.

The library is config, which was already the right call — rewording a letter is
a text edit, not a code change. But *adding* one still meant writing a body
file, adding a registry entry, and knowing which merge fields exist and what
they are spelled. That is a small expedition for something the owner should be
able to do the moment they think of it.

So: describe the letter in a sentence, and the local model drafts it using
**only merge fields that already exist**. The draft lands on disk as an ordinary
template — same folder, same format, editable by hand forever after. Nothing
here is a special kind of template; it is a faster way to write the same file.

The guard that makes this safe: a body may only reference DECLARED placeholders.
A model inventing ``{client_phone}`` would produce a template that renders a
permanent "fill in" marker nobody can ever satisfy, so unknown fields are
stripped before the file is written and reported to the owner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from satc.comms.library import comms_dir, library

_SLOT = re.compile(r"\{([a-z][a-z0-9_]*)\}")

_SYSTEM = """You write short, warm, plain client letters for a small US tax firm.
British-plain, never corporate, never salesy.

You will be given a list of MERGE FIELDS. Use them by writing {field_name} in the
text. You may ONLY use fields from that list — a field you invent will be deleted.

Absolute rules:
- NEVER write a specific number, amount, date or deadline. If one belongs in the
  letter, use a merge field for it.
- Start with "Dear {salutation}," and end with the sign-off block:
      {preparer_name}
      {firm_name}
- Keep it under 200 words. Nobody reads more.
- Output ONLY the letter. No subject line, no commentary, no markdown."""

_DRAFT_NOTICE = "— DRAFT for preparer review. Not sent automatically. —"


@dataclass(slots=True)
class AuthoredTemplate:
    """A template the model drafted, ready to write to disk."""

    key: str
    name: str
    kind: str
    stage: str
    description: str
    subject: str
    body: str
    unknown_fields: list[str] = field(default_factory=list)
    """Merge fields the model invented, which were stripped. Reported, not hidden."""

    @property
    def body_file(self) -> str:
        return f"{self.key}.txt"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return slug or "untitled"


def available_fields() -> dict[str, str]:
    """Every merge field a new template may use, with what it means."""
    lib = library()
    return {name: (p.label + (f" — {p.note}" if p.note else ""))
            for name, p in sorted(lib.placeholders.items())}


def strip_unknown_fields(body: str) -> tuple[str, list[str]]:
    """Remove merge fields that do not exist, so a template cannot be born broken.

    A model writing ``{client_phone}`` would produce a letter with a permanent
    "fill in" marker nobody can satisfy — the template would be unusable and the
    reason would not be obvious. Better to lose the phrase than ship that.
    """
    known = set(available_fields())
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in known:
            return match.group(0)
        if name not in unknown:
            unknown.append(name)
        return ""

    cleaned = _SLOT.sub(replace, body)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n", unknown


def author(description: str, *, name: str = "", kind: str = "email",
           stage: str = "5 · Relationship", subject: str = "",
           model: str = "", host: str = "", timeout: float = 120.0) -> AuthoredTemplate:
    """Draft a new template from a one-line description of what it is for.

    Raises if the model is unreachable or produces nothing usable — an empty
    template written to disk is worse than none, because it looks like a
    feature that exists.
    """
    import json
    import urllib.request

    from satc import settings
    from satc.agent.runner import DEFAULT_MODEL

    display = (name or description).strip()
    fields = available_fields()
    catalogue = "\n".join(f"  {{{n}}} — {meaning}" for n, meaning in fields.items())
    prompt = (f"Write a client {kind} for a tax practice. Its purpose: {description}\n\n"
              f"MERGE FIELDS you may use:\n{catalogue}")

    base = (host or settings.ollama_host()).rstrip("/")
    payload = json.dumps({
        "model": model or DEFAULT_MODEL, "stream": False,
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}],
        "options": {"temperature": 0.5},
    }).encode("utf-8")
    request = urllib.request.Request(f"{base}/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body_text = ((json.loads(response.read().decode("utf-8")).get("message") or {})
                     .get("content") or "").strip()

    if len(body_text) < 60:
        raise ValueError(
            f"The model returned nothing usable for {display!r}. Try describing "
            f"the letter's purpose in a full sentence — what it is for, and to whom.")

    body, unknown = strip_unknown_fields(body_text)
    if _DRAFT_NOTICE not in body:
        # Every template in the library says it is a draft. A new one must too,
        # or the first thing this feature does is create the one letter that
        # does not admit it needs reading.
        body = body.rstrip() + f"\n\n{_DRAFT_NOTICE}\n"

    key = slugify(name or description)[:40]
    return AuthoredTemplate(
        key=key, name=display[:60], kind=kind, stage=stage,
        description=" ".join(description.split()),
        subject=subject or (f"{display}" if kind == "email" else ""),
        body=body, unknown_fields=unknown)


def install(template: AuthoredTemplate, *, config_root: Path | None = None) -> Path:
    """Write an authored template into the library as an ordinary template.

    Deliberately plain: a body file and a registry entry, identical in every way
    to the hand-written ones. There is no such thing as a "generated template"
    once it lands — it is a text file the owner owns and edits.
    """
    from satc.comms.library import _cached_library

    folder = comms_dir(config_root)
    if any(t.key == template.key for t in library().templates):
        raise ValueError(
            f"A template called {template.key!r} already exists. Pick another "
            f"name, or edit configs/comms/{template.key}.txt directly.")

    (folder / template.body_file).write_text(template.body, encoding="utf-8")

    registry = folder / "templates.yaml"
    text = registry.read_text(encoding="utf-8").rstrip() + "\n"
    entry = [
        "",
        f"  - key: {template.key}",
        f"    name: \"{template.name}\"",
        f"    kind: {template.kind}",
        f"    stage: \"{template.stage}\"",
        f"    description: >-",
        f"      {template.description}",
    ]
    if template.subject:
        entry.append(f"    subject: \"{template.subject}\"")
    entry.append(f"    body_file: {template.body_file}")
    registry.write_text(text + "\n".join(entry) + "\n", encoding="utf-8")

    _cached_library.cache_clear()      # the library is cached per process
    return folder / template.body_file
