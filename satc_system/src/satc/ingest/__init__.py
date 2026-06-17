"""Ingestion: document reading + extraction + the staging/confirmation gate."""

from __future__ import annotations

from typing import Any

from satc.ingest.extractors.mapping import MapExtractor
from satc.ingest.readers.base import DocumentReader, ReadResult
from satc.ingest.staging_gate import MAPPING_1040, LineMapping, StagingGate
from satc.models.staging import StagedDocument


def read_and_stage(reader: DocumentReader, source: str, *, config: dict[str, Any],
                   document_id: str, client_id: str, tax_year: int,
                   sharepoint_link: str | None = None) -> StagedDocument:
    """Read a raw document, then extract + stage it (front-to-gate in one call)."""
    result: ReadResult = reader.read(source)
    return MapExtractor(config).extract(
        document_id=document_id, client_id=client_id, tax_year=tax_year,
        labeled_fields=result.labeled_fields, sharepoint_link=sharepoint_link,
        confidences=result.confidence_map())


__all__ = ["MapExtractor", "StagingGate", "LineMapping", "MAPPING_1040",
           "DocumentReader", "ReadResult", "read_and_stage"]
