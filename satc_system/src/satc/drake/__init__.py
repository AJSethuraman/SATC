"""Drake preparer-set parser, communication generator, and data-mart seed.

The preparer copy is an OUTPUT used to reconcile, communicate, and seed the data
mart — never to populate intake fields.
"""

from __future__ import annotations

from satc.drake.comms import (
    DeliverySummary,
    build_delivery_summary,
    render_cover_letter,
    render_delivery_email,
    summary_lines,
)
from satc.drake.preparer_set_parser import PreparerSet, parse_preparer_set
from satc.drake.seed import seed_data_mart, seed_records

__all__ = [
    "PreparerSet",
    "parse_preparer_set",
    "DeliverySummary",
    "build_delivery_summary",
    "render_delivery_email",
    "render_cover_letter",
    "summary_lines",
    "seed_data_mart",
    "seed_records",
]
