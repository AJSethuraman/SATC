"""Document extractors (config-driven label mapping + conservative parsing)."""

from __future__ import annotations

from satc.ingest.extractors.base import make_staged_field, parse_money
from satc.ingest.extractors.mapping import MapExtractor

__all__ = ["MapExtractor", "parse_money", "make_staged_field"]
