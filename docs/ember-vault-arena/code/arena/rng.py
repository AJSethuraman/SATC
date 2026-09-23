from __future__ import annotations

import hashlib


class HashRNG:
    """Version-stable deterministic random stream.

    Each result is derived from SHA-256(seed:counter:label), so a replay can
    independently reproduce every roll without relying on Python's PRNG.
    """

    def __init__(self, seed: int):
        self.seed = int(seed)
        self.counter = 0

    def roll(self, sides: int, label: str) -> tuple[int, dict[str, int | str]]:
        if sides < 2:
            raise ValueError("sides must be >= 2")
        counter = self.counter
        material = f"{self.seed}:{counter}:{label}".encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()
        value = int(digest[:16], 16) % sides + 1
        self.counter += 1
        return value, {
            "seed": self.seed,
            "counter": counter,
            "label": label,
            "sides": sides,
            "digest_prefix": digest[:16],
            "result": value,
        }

