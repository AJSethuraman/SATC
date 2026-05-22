"""Adapter implementations for system-specific entry backends.

Only this package (plus config files) should contain Drake-specific behavior.
"""

from dea.adapters.fake import FakeDrakeAdapter
from dea.adapters.real import RealDrakeAdapter

__all__ = ["FakeDrakeAdapter", "RealDrakeAdapter"]
