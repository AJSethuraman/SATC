"""How well does document reading actually work? — measured, not assumed.

Every test of the reader ladder up to now used fixtures written by the same
hand that wrote the reader. That proves the PLUMBING (a read flows through
classification, extraction, staging, confirmation) and proves nothing about
whether a real ADP W-2 is read correctly. A W-2 from ADP, Paychex and Gusto are
three different layouts; a phone photo of one is a fourth problem.

So this measures against a CORPUS of real documents with known-correct values,
and reports the one number that has to be perfect.

**Precision at HIGH confidence is the only metric that must be zero-defect.**
The staging gate auto-accepts HIGH-confidence deterministic reads without a
human looking. A missed read costs the owner thirty seconds of typing. A
confidently-WRONG read puts a bad number on a tax return, unseen. Those are not
the same failure and must not share a number:

    silent_errors      MUST be 0      — auto-accepted and wrong
    caught_errors      tolerable      — wrong, but flagged for review
    misses             tolerable      — nothing extracted; the owner types it

Recall is a convenience metric. Precision-at-HIGH is a correctness one.

The corpus lives OUTSIDE git (``corpus/`` is ignored) because real client
documents are real PII. Each document sits beside a ``.expected.yaml`` naming
the values a human verified by eye. Absent a corpus this module reports that
honestly rather than passing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from satc.config import read_yaml

CORPUS_ENV = "SATC_CORPUS_DIR"

# Confidence at which the staging gate accepts a value with no human review.
AUTO_CONFIRM_AT = "HIGH"


def corpus_dir() -> Path:
    """Where the document corpus lives. Never inside the repo."""
    import os

    env = os.environ.get(CORPUS_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "corpus"


@dataclass(slots=True)
class Expectation:
    """What a human verified a document actually says."""

    path: Path
    doc_type: str = ""
    """The type a human confirmed. Empty means "don't score classification"."""

    fields: dict[str, str] = field(default_factory=dict)
    """label -> the value a human read off the document, verbatim."""

    note: str = ""

    @classmethod
    def load(cls, expected_path: Path) -> "Expectation":
        data = read_yaml(expected_path) or {}
        # foo.expected.yaml describes foo.pdf (or foo.png, foo.jpg...).
        stem = expected_path.name[: -len(".expected.yaml")]
        matches = [p for p in expected_path.parent.iterdir()
                   if p.is_file() and p.stem == stem
                   and not p.name.endswith(".expected.yaml")]
        document = matches[0] if matches else expected_path.parent / stem
        return cls(path=document, doc_type=str(data.get("doc_type", "")),
                   fields={str(k): str(v) for k, v in (data.get("fields") or {}).items()},
                   note=str(data.get("note", "")))


def load_corpus(directory: Path | None = None) -> list[Expectation]:
    """Every document in the corpus that has verified expectations beside it."""
    root = directory or corpus_dir()
    if not root.is_dir():
        return []
    return [Expectation.load(p) for p in sorted(root.rglob("*.expected.yaml"))]


def _normalise(value: str) -> str:
    """Compare what a human would call the same value.

    ``$145,000.00`` and ``145000`` are the same number read off the same box;
    scoring them as a mismatch would drown the signal that matters.
    """
    text = str(value or "").strip().lower()
    for junk in ("$", ",", " "):
        text = text.replace(junk, "")
    if text.endswith(".00"):
        text = text[:-3]
    return text


@dataclass(slots=True)
class FieldResult:
    label: str
    expected: str
    got: str
    confidence: str
    extractor: str = ""

    @property
    def is_missing(self) -> bool:
        return not str(self.got).strip()

    @property
    def is_correct(self) -> bool:
        return not self.is_missing and _normalise(self.got) == _normalise(self.expected)

    @property
    def auto_confirmed(self) -> bool:
        return self.confidence == AUTO_CONFIRM_AT

    @property
    def is_silent_error(self) -> bool:
        """Wrong AND accepted without a human looking. The number that must be 0."""
        return not self.is_missing and not self.is_correct and self.auto_confirmed


@dataclass(slots=True)
class Scoreboard:
    """What the corpus says about how well reading actually works."""

    documents: int = 0
    classified_correctly: int = 0
    classified_wrongly: int = 0
    unclassified: int = 0
    fields: list[FieldResult] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)

    @property
    def silent_errors(self) -> list[FieldResult]:
        """Auto-accepted and wrong. MUST be empty."""
        return [f for f in self.fields if f.is_silent_error]

    @property
    def caught_errors(self) -> list[FieldResult]:
        """Wrong, but flagged for review — the owner sees these."""
        return [f for f in self.fields
                if not f.is_missing and not f.is_correct and not f.auto_confirmed]

    @property
    def misses(self) -> list[FieldResult]:
        return [f for f in self.fields if f.is_missing]

    @property
    def correct(self) -> list[FieldResult]:
        return [f for f in self.fields if f.is_correct]

    @property
    def precision_at_high(self) -> float | None:
        """Of the values accepted with no human looking, how many were right?

        ``None`` when nothing was auto-accepted — reported as unknown rather
        than as a perfect score, because a metric with no denominator is not
        evidence (doctrine rule 10).
        """
        auto = [f for f in self.fields if f.auto_confirmed and not f.is_missing]
        if not auto:
            return None
        return sum(1 for f in auto if f.is_correct) / len(auto)

    @property
    def recall(self) -> float | None:
        if not self.fields:
            return None
        return len(self.correct) / len(self.fields)

    @property
    def is_acceptable(self) -> bool:
        """The bar: nothing wrong was accepted unseen."""
        return not self.silent_errors

    def report(self) -> str:
        if not self.documents:
            return (f"No corpus found at {corpus_dir()}.\n"
                    f"Reading accuracy is UNMEASURED — the existing tests prove the "
                    f"plumbing, not that a real W-2 is read correctly.\n"
                    f"Add documents plus a <name>.expected.yaml beside each.")
        lines = [
            f"Corpus: {self.documents} documents, {len(self.fields)} verified values",
            "",
            f"  classified right      {self.classified_correctly}",
            f"  classified WRONG      {self.classified_wrongly}",
            f"  not classified        {self.unclassified}",
            "",
            f"  values correct        {len(self.correct)}",
            f"  values missed         {len(self.misses)}        (owner types them)",
            f"  errors CAUGHT         {len(self.caught_errors)}        (flagged for review)",
            f"  errors SILENT         {len(self.silent_errors)}        <- must be 0",
        ]
        precision = self.precision_at_high
        lines.append("")
        lines.append(f"  precision at HIGH     "
                     f"{'unmeasured (nothing auto-accepted)' if precision is None else f'{precision:.1%}'}")
        recall = self.recall
        lines.append(f"  recall                "
                     f"{'n/a' if recall is None else f'{recall:.1%}'}")
        if self.unreadable:
            lines += ["", "  unreadable:"] + [f"    {u}" for u in self.unreadable]
        if self.silent_errors:
            lines += ["", "  SILENT ERRORS (accepted without review, and wrong):"]
            lines += [f"    {f.label}: expected {f.expected!r}, read {f.got!r}"
                      for f in self.silent_errors]
        return "\n".join(lines)


def score(expectations=None, *, directory: Path | None = None) -> Scoreboard:
    """Run the real reader ladder over the corpus and score what came back."""
    from satc.config import load_extraction_map
    from satc.ingest import load_classifier
    from satc.settings import cloud_vision_enabled

    items = expectations if expectations is not None else load_corpus(directory)
    board = Scoreboard()
    if not items:
        return board

    classifier = load_classifier(has_key=cloud_vision_enabled())
    for expectation in items:
        if not expectation.path.exists():
            board.unreadable.append(f"{expectation.path.name} (file missing)")
            continue
        board.documents += 1

        classification = classifier.classify_path(expectation.path)
        if expectation.doc_type:
            if not classification.classified:
                board.unclassified += 1
            elif classification.code == expectation.doc_type:
                board.classified_correctly += 1
            else:
                board.classified_wrongly += 1

        if not expectation.fields or not classification.key:
            continue
        try:
            cfg = load_extraction_map(classification.key)
        except Exception:  # noqa: BLE001 - no map for this type; nothing to score
            continue

        result, problem = _read(expectation.path, cfg)
        if result is None:
            board.unreadable.append(f"{expectation.path.name} ({problem})")
            continue

        confidences = result.confidence_map()
        found = _by_any_name(result.labeled_fields, confidences, cfg)
        for name, want in expectation.fields.items():
            got, confidence = found.get(_key(name), ("", "UNCERTAIN"))
            board.fields.append(FieldResult(
                label=f"{expectation.path.name}:{name}",
                expected=want, got=got, confidence=confidence,
                extractor=result.backend))
    return board


def _key(name: str) -> str:
    """Loosely normalise a field name so expectations are writable by hand."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _by_any_name(labeled: dict, confidences: dict, cfg: dict) -> dict:
    """Index a read by EVERY name a human might use for the same field.

    Expectations are written by a person looking at a document, not by someone
    reading configs/extraction/*.yaml. So "Box 1 wages", "wages", and
    "w2.box1_wages" all have to find the same value — otherwise the scoreboard
    reports a reading failure when the only thing that failed was the label the
    owner happened to type, which would make it worse than useless.
    """
    out: dict[str, tuple[str, str]] = {}
    for label, value in labeled.items():
        out[_key(label)] = (value, confidences.get(label, "UNCERTAIN"))

    for spec in cfg.get("fields", []) or []:
        label = spec.get("label", "")
        entry = out.get(_key(label))
        if entry is None:
            continue
        for alias in [spec.get("field_path", ""), *(spec.get("aliases") or [])]:
            if alias:
                out.setdefault(_key(alias), entry)
        # "Box 1 - Wages, tips, other comp" should also answer to "box1" and to
        # the words after the dash.
        if " - " in label:
            box, _, rest = label.partition(" - ")
            out.setdefault(_key(box), entry)
            out.setdefault(_key(rest), entry)
    return out


def _read(path: Path, cfg: dict):
    """The same ladder AppState.run_intake uses — measured, not a copy of it."""
    from satc.app.state import AppState

    return AppState._read_document(path, cfg, allow_cloud=False)
