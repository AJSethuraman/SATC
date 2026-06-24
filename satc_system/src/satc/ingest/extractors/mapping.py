"""Config-driven extractor: map a document's labeled fields to canonical paths.

Real source PDFs (W-2, 1099, K-1, a prior-year 1040) are first reduced to
labeled key/value pairs — by a form-field read, an OCR/extraction service, or
``pdftotext`` + the label patterns in the extraction config. This extractor then
maps those source labels to the system's canonical ``field_path`` values and
stages each one with provenance and confidence. It does not interpret the tax
result; it only normalizes and stages for the confirmation gate.

Extraction config (``configs/extraction/<doc>.yaml``)::

    doc_type: "W-2"
    fields:
      - {field_path: w2.box1_wages, label: "Box 1 - Wages", aliases: ["wages"], money: true}
      - {field_path: w2.employer_ein, label: "Employer EIN", money: false, sensitive: true}

``sensitive: true`` fields (SSN/EIN) are staged masked — the full value stays in
the vault, never the workbook.
"""

from __future__ import annotations

from typing import Any

from satc.ingest.extractors.base import make_staged_field
from satc.masking import mask_value
from satc.models.staging import StagedDocument
from datetime import datetime


def _normalize(label: str) -> str:
    return "".join(ch for ch in label.lower() if ch.isalnum())


class MapExtractor:
    """Maps labeled source fields to canonical staged fields using a config."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.doc_type = config.get("doc_type", "OTHER")
        self.field_specs = config.get("fields", [])
        # Build a lookup from every label/alias (normalized) to its spec.
        self._index: dict[str, dict] = {}
        for spec in self.field_specs:
            for key in [spec.get("label", "")] + list(spec.get("aliases", [])):
                if key:
                    self._index[_normalize(key)] = spec
            self._index[_normalize(spec["field_path"])] = spec

    def extract(self, *, document_id: str, client_id: str, tax_year: int,
                labeled_fields: dict[str, Any], page: int | None = None,
                sharepoint_link: str | None = None,
                confidences: dict[str, str] | None = None) -> StagedDocument:
        """Map ``{source_label: value}`` to a staged document.

        ``confidences`` (optional, keyed by source label) lets a reader downgrade
        fields it was unsure about — e.g. a vision backend flags blurry values LOW
        so they never auto-confirm.
        """
        confidences = confidences or {}
        staged = StagedDocument(
            document_id=document_id, client_id=client_id, tax_year=tax_year,
            doc_type=self.doc_type, extracted_at=datetime.now(),
        )
        seen: set[str] = set()
        for source_label, raw_value in labeled_fields.items():
            spec = self._index.get(_normalize(source_label))
            if spec is None:
                continue  # unmapped source label — ignored (conservative)
            field_path = spec["field_path"]
            if field_path in seen:
                continue
            seen.add(field_path)
            is_money = bool(spec.get("money", False))
            value = raw_value
            base_conf = confidences.get(source_label, "HIGH")
            if spec.get("sensitive"):
                # Never stage a full SSN/EIN; mask to last-4. Vault holds the full value.
                value = mask_value(field_path, raw_value)
                is_money = False
            field = make_staged_field(
                field_id=f"{document_id}:{field_path}",
                document_id=document_id, client_id=client_id, tax_year=tax_year,
                field_path=field_path, label=spec.get("label", field_path),
                raw_value=value, is_money=is_money, extractor=f"MapExtractor[{self.doc_type}]",
                page=page, sharepoint_link=sharepoint_link, base_confidence=base_conf,
            )
            staged.fields.append(field)
        return staged
