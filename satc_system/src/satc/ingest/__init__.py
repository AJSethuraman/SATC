"""Ingestion: document extraction + the staging/confirmation gate."""

from __future__ import annotations

from satc.ingest.extractors.mapping import MapExtractor
from satc.ingest.staging_gate import MAPPING_1040, LineMapping, StagingGate

__all__ = ["MapExtractor", "StagingGate", "LineMapping", "MAPPING_1040"]
