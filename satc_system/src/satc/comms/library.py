"""The communication-template LIBRARY — loading ``configs/comms/`` into objects.

This is the config-reading half of the comms area. It knows where templates live
and what shape they have; it knows nothing about clients, Flask, or rendering
(see :mod:`satc.comms.render` and :mod:`satc.comms.context`).

A template is two things on disk: an entry in ``configs/comms/templates.yaml``
and a plain-text body file beside it. Growing the library is a config edit — add
a body file, add its entry, declare any new merge fields. No code changes.

One compatibility note: ``delivery_email.txt`` carries its own ``Subject:`` first
line because :mod:`satc.drake.comms` renders that file directly. When a template
declares no ``subject``, the loader lifts that leading line off instead, so the
file stays byte-identical for its original consumer.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from satc.config import CONFIG_ROOT, ConfigError

# Who fills a merge field. See the header of ``configs/comms/templates.yaml``.
PlaceholderSource = Literal["state", "config", "firm", "drafted", "preparer"]

TEMPLATE_REGISTRY = "templates.yaml"


def comms_dir(config_root: Path | None = None) -> Path:
    return (config_root or CONFIG_ROOT) / "comms"


@dataclass(frozen=True, slots=True)
class Placeholder:
    """One declared merge field."""

    name: str
    label: str
    source: PlaceholderSource = "state"
    note: str = ""

    @property
    def preparer_filled(self) -> bool:
        """Whether the OWNER must type this — a fact nothing else can supply.

        Only ``preparer`` now. Standing firm wording comes from config and
        judgement wording is drafted by the model, so what is left here is a
        genuine unknown fact (an invoice number), not homework.
        """
        return self.source == "preparer"

    @property
    def model_drafted(self) -> bool:
        """Wording the local model writes so the draft arrives finished."""
        return self.source == "drafted"

    @property
    def from_firm_standing_text(self) -> bool:
        return self.source == "firm"


@dataclass(frozen=True, slots=True)
class CommsTemplate:
    """A draftable communication: metadata + the text to merge into."""

    key: str
    name: str
    kind: Literal["email", "letter"]
    description: str
    body: str
    subject: str = ""
    stage: str = ""
    body_file: str = ""

    @property
    def is_email(self) -> bool:
        return self.kind == "email"


@dataclass(frozen=True, slots=True)
class CommsLibrary:
    """Everything ``configs/comms/`` declares, loaded and validated."""

    firm: dict[str, str]
    placeholders: dict[str, Placeholder]
    templates: tuple[CommsTemplate, ...]

    def template(self, key: str) -> CommsTemplate:
        for tpl in self.templates:
            if tpl.key == key:
                return tpl
        raise ConfigError(f"No comms template named {key!r}")

    def keys(self) -> list[str]:
        return [t.key for t in self.templates]

    def by_stage(self) -> list[tuple[str, list[CommsTemplate]]]:
        """Templates grouped by workflow stage, in registry order."""
        groups: list[tuple[str, list[CommsTemplate]]] = []
        index: dict[str, int] = {}
        for tpl in self.templates:
            stage = tpl.stage or "Other"
            if stage not in index:
                index[stage] = len(groups)
                groups.append((stage, []))
            groups[index[stage]][1].append(tpl)
        return groups

    def placeholder(self, name: str) -> Placeholder | None:
        return self.placeholders.get(name)

    def preparer_fields(self, template: CommsTemplate) -> list[Placeholder]:
        """The declared merge fields in ``template`` a human has to type."""
        from satc.comms.render import placeholder_names

        return [p for name in placeholder_names(template)
                if (p := self.placeholders.get(name)) is not None and p.preparer_filled]

    def firm_values(self) -> dict[str, str]:
        """The firm block as merge values (``firm_name``, ``preparer_name``, ...)."""
        out = {"preparer_name": self.firm.get("preparer_name", "")}
        for key in ("name", "short_name", "tagline", "email"):
            out[f"firm_{key}"] = self.firm.get(key, "")
        return {k: v for k, v in out.items() if v}


def _split_subject(body: str) -> tuple[str, str]:
    """Lift a leading ``Subject:`` line off a body. Returns ``(subject, body)``."""
    head, sep, rest = body.partition("\n")
    if sep and head.lower().startswith("subject:"):
        return head.split(":", 1)[1].strip(), rest.lstrip("\n")
    return "", body


def _load_template(entry: dict, folder: Path) -> CommsTemplate:
    key = str(entry.get("key", "")).strip()
    if not key:
        raise ConfigError(f"A comms template entry has no key: {entry!r}")
    body_file = str(entry.get("body_file", "")).strip()
    if not body_file:
        raise ConfigError(f"Comms template {key!r} declares no body_file")
    path = folder / body_file
    if not path.exists():
        raise ConfigError(f"Comms template {key!r} points at a missing file: {path}")

    body = path.read_text(encoding="utf-8")
    subject = str(entry.get("subject", "") or "").strip()
    if not subject:
        subject, body = _split_subject(body)

    kind = str(entry.get("kind", "email")).strip().lower()
    if kind not in ("email", "letter"):
        raise ConfigError(f"Comms template {key!r} has an unknown kind: {kind!r}")

    return CommsTemplate(
        key=key, name=str(entry.get("name", key)), kind=kind,
        description=" ".join(str(entry.get("description", "")).split()),
        body=body, subject=subject, stage=str(entry.get("stage", "")),
        body_file=body_file)


def load_library(config_root: Path | None = None) -> CommsLibrary:
    """Read ``configs/comms/templates.yaml`` and every body file it names."""
    folder = comms_dir(config_root)
    registry = folder / TEMPLATE_REGISTRY
    if not registry.exists():
        raise ConfigError(f"Comms template registry not found: {registry}")
    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"Comms registry must be a mapping: {registry}")

    placeholders = {
        name: Placeholder(name=name, label=str(spec.get("label", name)),
                          source=str(spec.get("source", "state")),  # type: ignore[arg-type]
                          note=str(spec.get("note", "")))
        for name, spec in (data.get("placeholders") or {}).items()
    }
    templates = tuple(_load_template(e, folder) for e in (data.get("templates") or []))
    if not templates:
        raise ConfigError(f"Comms registry declares no templates: {registry}")

    keys = [t.key for t in templates]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ConfigError(f"Duplicate comms template keys: {sorted(dupes)}")

    firm = {k: str(v) for k, v in (data.get("firm") or {}).items()}
    return CommsLibrary(firm=firm, placeholders=placeholders, templates=templates)


@lru_cache(maxsize=1)
def _cached_library() -> CommsLibrary:
    return load_library()


def library() -> CommsLibrary:
    """The installed library (cached — configs don't change while running)."""
    return _cached_library()
