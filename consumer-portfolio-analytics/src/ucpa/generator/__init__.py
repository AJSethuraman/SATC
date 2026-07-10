"""Synthetic data generation (seeded, deterministic) and tape degradation."""

from ucpa.generator.card_generator import CardGeneratorConfig, generate_card_portfolio
from ucpa.generator.degrade import degrade_to_tier

__all__ = ["CardGeneratorConfig", "generate_card_portfolio", "degrade_to_tier"]
