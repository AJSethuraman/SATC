"""Synthetic, masked fixtures (never real PII)."""

from __future__ import annotations

from satc.fixtures.synthetic import (
    synthetic_1040_values,
    synthetic_carryforwards,
    synthetic_documents,
    synthetic_drake_intake,
    synthetic_entity_values,
    synthetic_identities,
    synthetic_mart,
    synthetic_preparer_set_text,
)
from satc.fixtures.sample_docs import create_sample_folder

__all__ = [
    "create_sample_folder",
    "synthetic_1040_values",
    "synthetic_carryforwards",
    "synthetic_documents",
    "synthetic_drake_intake",
    "synthetic_entity_values",
    "synthetic_identities",
    "synthetic_mart",
    "synthetic_preparer_set_text",
]
