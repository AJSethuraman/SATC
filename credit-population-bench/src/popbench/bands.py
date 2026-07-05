"""Configurable band schemes — never hard-coded edges.

Band edges are configuration, not constants (the research doc is emphatic:
there is no single FICO/DTI/LTV standard). This module ships the defaults —
CFPB six-tier FICO and the 36/43 DTI edges — plus an FR Y-14Q preset
(≤620/>620) and an LTV default, and lets a reviewer supply fully custom edges.
A scheme maps a numeric column to an ordered categorical label used as a
group-by dimension.

A scheme is edges + labels: ``edges`` are the internal cut points and
``labels`` name the ``len(edges)+1`` resulting bands, low to high. Binning is
right-closed, so an edge value falls in the *lower* band (FICO 619 -> subprime,
620 -> near-prime), matching how these tiers are written.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BandScheme:
    name: str
    field: str                       # canonical field id this scheme bands
    edges: tuple[float, ...]         # internal cut points, ascending
    labels: tuple[str, ...]          # len == len(edges) + 1

    def __post_init__(self):
        if len(self.labels) != len(self.edges) + 1:
            raise ValueError(
                f"scheme {self.name!r}: {len(self.labels)} labels for "
                f"{len(self.edges)} edges (need {len(self.edges)+1})")
        if list(self.edges) != sorted(self.edges):
            raise ValueError(f"scheme {self.name!r}: edges must be ascending")

    def assign(self, series: pd.Series) -> pd.Series:
        """Label each value; NaN stays NaN (a distinct 'unbanded' cell)."""
        bins = [-math.inf, *self.edges, math.inf]
        return pd.cut(series.astype("float64"), bins=bins, labels=list(self.labels),
                      right=True, ordered=True)


# --- shipped presets (edges live here as defaults; overridable via _config) --

PRESETS: dict[str, dict[str, BandScheme]] = {
    "fico_orig": {
        "cfpb": BandScheme(
            "cfpb", "fico_orig", (579, 619, 659, 719, 799),
            ("deep subprime (<=579)", "subprime (580-619)", "near-prime (620-659)",
             "prime (660-719)", "prime-plus (720-799)", "superprime (800+)")),
        "y14q": BandScheme(
            "y14q", "fico_orig", (620,), ("<=620", ">620")),
    },
    "dti": {
        "default": BandScheme(
            "default", "dti", (0.36, 0.43, 0.49),
            ("<=36%", "37-43%", "44-49%", "50%+")),
    },
    "ltv": {
        "default": BandScheme(
            "default", "ltv", (0.60, 0.80, 0.90, 1.00),
            ("<=60%", "61-80%", "81-90%", "91-100%", "100%+")),
    },
}


def get_preset(field: str, scheme: str) -> BandScheme:
    try:
        return PRESETS[field][scheme]
    except KeyError as exc:
        avail = {f: list(s) for f, s in PRESETS.items()}
        raise KeyError(f"no band preset {field!r}/{scheme!r}; available: {avail}") from exc


def custom(field: str, edges, labels, name: str = "custom") -> BandScheme:
    return BandScheme(name, field, tuple(float(e) for e in edges), tuple(labels))
