"""Sort + re-label a folder of client documents.

Given a messy folder (``IMG_4471.pdf``, ``scan0012.pdf``, ``Untitled (3).pdf``),
this classifies each file by *reading* it (see :mod:`satc.ingest.classify`), then
proposes a clean name and a by-type destination:

    _SATC_Sorted/W-2/W-2 - Buckeye Manufacturing LLC.pdf
    _SATC_Sorted/1099-INT/1099-INT - Heartland Bank.pdf
    _SATC_Sorted/Engagement letter/Engagement.pdf
    _SATC_Sorted/Unclassified/IMG_4471.pdf

It is **non-destructive**: it never moves or deletes an original. With
``apply=False`` (the default) it only returns the plan so it can be previewed;
with ``apply=True`` it *copies* each original to its clean home. The same
classification drives intake, so a sorted folder is also a ready-to-read folder.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from satc.config import load_extraction_map
from satc.ingest.classify import Classification, DocumentClassifier, load_classifier

DEFAULT_DEST_NAME = "_SATC_Sorted"
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(text: str) -> str:
    """Filesystem-safe, trimmed component."""
    return _UNSAFE.sub("", str(text)).strip().strip(".") or "DOC"


@dataclass(slots=True)
class SortItem:
    original: str          # absolute source path
    original_name: str
    label: str
    code: str
    confidence: str
    method: str            # how it was classified (form fields / text / filename / vision)
    new_relpath: str       # destination, relative to the dest root
    entity: str = ""       # employer/payer name pulled for the clean name (if any)
    extractable: bool = False
    copied: bool = False


@dataclass(slots=True)
class SortPlan:
    src: str
    dest: str
    items: list[SortItem] = field(default_factory=list)
    applied: bool = False

    def by_type(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for it in self.items:
            out[it.label] = out.get(it.label, 0) + 1
        return out

    @property
    def classified(self) -> int:
        return sum(1 for it in self.items if it.method != "unclassified")


def _entity_for(path: Path, c: Classification) -> str:
    """Best-effort employer/payer name for the clean filename (fillable PDFs only)."""
    if not c.extractable or path.suffix.lower() != ".pdf":
        return ""
    try:
        from satc.ingest.readers import PdfFormReader

        cfg = load_extraction_map(c.key)
        labeled = PdfFormReader(cfg).read(str(path)).labeled_fields
    except Exception:  # noqa: BLE001 - naming is a nicety, never fatal
        return ""
    for label, value in labeled.items():
        low = label.lower()
        if ("employer name" in low or "payer name" in low) and str(value).strip():
            return str(value).strip()
    return ""


def _clean_name(c: Classification, entity: str, suffix: str) -> str:
    base = _safe(c.code)
    if entity:
        base = f"{base} - {_safe(entity)}"
    return base + suffix.lower()


def sort_folder(src: str | Path, dest: str | Path | None = None, *, apply: bool = False,
                classifier: DocumentClassifier | None = None) -> SortPlan:
    """Classify and (optionally) copy every file in ``src`` into a clean tree."""
    src_path = Path(src)
    dest_path = Path(dest) if dest else src_path / DEFAULT_DEST_NAME
    classifier = classifier or load_classifier()

    plan = SortPlan(src=str(src_path), dest=str(dest_path))
    if not src_path.is_dir():
        return plan

    used: set[str] = set()
    dest_resolved = dest_path.resolve()
    for path in sorted(p for p in src_path.iterdir() if p.is_file()):
        # Don't re-sort our own output if dest lives under src.
        try:
            if dest_resolved in path.resolve().parents:
                continue
        except OSError:
            pass

        c = classifier.classify_path(path)
        entity = _entity_for(path, c)
        bucket = _safe(c.label)
        name = _clean_name(c, entity, path.suffix) if c.classified else _safe(path.name)

        relpath = f"{bucket}/{name}"
        if relpath in used:                       # de-dupe collisions within the plan
            stem, dot, ext = name.rpartition(".")
            n = 2
            while relpath in used:
                name = f"{stem} ({n}).{ext}" if dot else f"{name} ({n})"
                relpath = f"{bucket}/{name}"
                n += 1
        used.add(relpath)

        plan.items.append(SortItem(
            original=str(path), original_name=path.name, label=c.label, code=c.code,
            confidence=c.confidence, method=c.method, new_relpath=relpath,
            entity=entity, extractable=c.extractable,
        ))

    if apply:
        for it in plan.items:
            target = dest_path / it.new_relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(it.original, target)     # copy, never move — originals untouched
            it.copied = True
        plan.applied = True

    return plan
