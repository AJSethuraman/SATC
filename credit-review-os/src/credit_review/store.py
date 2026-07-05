"""The Review Room's engagement store — the working surface.

One encrypted file per engagement (AES-256-GCM through the existing crypto
layer; plaintext never touches disk). It holds what the reviewer has keyed so
far: file entries, pool buckets, and finding tracking. **The workbook remains
the source of truth**: the store feeds the existing deterministic builder and
holds nothing the built workbook won't contain.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from credit_review import crypto
from credit_review.config import ConfigError, Engagement, Program
from credit_review.config_mode_b import ProductSample, validate_samples_data

STORE_VERSION = 1


def default_store_dir() -> Path:
    return Path.home() / ".credit-review" / "engagements"


class EngagementStore:
    """Load-modify-save document store for one engagement."""

    def __init__(self, program: Program, engagement: Engagement,
                 store_dir: Path | None = None, key_dir: Path | None = None) -> None:
        self.program = program
        self.engagement = engagement
        self.store_dir = Path(store_dir) if store_dir else default_store_dir()
        self.key_dir = key_dir
        self.path = self.store_dir / f"{engagement.engagement_id}.store"
        self._doc = self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> dict:
        if self.path.exists():
            key = crypto.load_or_create_key(self.key_dir)
            doc = json.loads(crypto.decrypt_bytes(self.path.read_bytes(), key))
            if doc.get("v") != STORE_VERSION:
                raise ConfigError(f"store version {doc.get('v')!r} not supported")
            return doc
        return {
            "v": STORE_VERSION,
            "engagement_id": self.engagement.engagement_id,
            "lob": self.program.lob,
            "products": {p["id"]: {"files": [], "pool": {}, "tracking": {}}
                         for p in self.program.products},
        }

    def save(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.store_dir, 0o700)
        except OSError:
            pass
        key = crypto.load_or_create_key(self.key_dir)
        blob = crypto.encrypt_bytes(
            json.dumps(self._doc, separators=(",", ":"), sort_keys=True).encode(),
            key)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)

    # -- product helpers -----------------------------------------------------
    def product(self, product_id: str) -> dict:
        by_id = {p["id"]: p for p in self.program.products}
        if product_id not in by_id:
            raise ConfigError(f"unknown product {product_id!r}")
        return by_id[product_id]

    def block(self, product_id: str) -> dict:
        self.product(product_id)
        return self._doc["products"][product_id]

    def files(self, product_id: str) -> list[dict]:
        return list(self.block(product_id)["files"])

    def get_file(self, product_id: str, loan_number: str) -> dict | None:
        for entry in self.block(product_id)["files"]:
            if entry["loan_number"] == loan_number:
                return dict(entry)
        return None

    # -- mutations (each validates through the samples-loader rules) ---------
    def upsert_file(self, product_id: str, entry: dict) -> None:
        block = self.block(product_id)
        files = [f for f in block["files"]
                 if f["loan_number"] != entry.get("loan_number")]
        candidate = files + [entry]
        self._validate({**self._samples_doc(), "products": {
            **self._samples_doc()["products"],
            product_id: {**self._samples_doc()["products"][product_id],
                         "files": candidate}}})
        block["files"] = candidate
        self.save()

    def delete_file(self, product_id: str, loan_number: str) -> None:
        block = self.block(product_id)
        block["files"] = [f for f in block["files"]
                          if f["loan_number"] != loan_number]
        self.save()

    def set_pool(self, product_id: str, pool: dict) -> None:
        block = self.block(product_id)
        self._validate({**self._samples_doc(), "products": {
            **self._samples_doc()["products"],
            product_id: {**self._samples_doc()["products"][product_id],
                         "pool": pool}}}, require_pools=True,
            only_product=product_id)
        block["pool"] = pool
        self.save()

    def set_tracking(self, product_id: str, test_id: str, fields: dict) -> None:
        valid = {t["id"] for t in self.product(product_id)["tests"]}
        if test_id not in valid:
            raise ConfigError(f"unknown test {test_id!r} for {product_id}")
        status = fields.get("status", "open")
        if status not in ("open", "cleared", "waived"):
            raise ConfigError(f"status must be open/cleared/waived, got {status!r}")
        tracking = self.block(product_id)["tracking"]
        tracking[test_id] = {k: v for k, v in fields.items()
                             if k in ("status", "owner", "due", "cleared") and v}
        self.save()

    # -- outputs ---------------------------------------------------------------
    def _samples_doc(self) -> dict:
        return {"products": {pid: {"files": block["files"], "pool": block["pool"]}
                             for pid, block in self._doc["products"].items()}}

    def _validate(self, doc: dict, require_pools: bool = False,
                  only_product: str | None = None) -> None:
        """Run the samples-loader validation over the in-progress document.

        While an engagement is in flight, pools may be missing — validate
        files strictly always, pools only when present/required.
        """
        products = {}
        for pid, block in doc["products"].items():
            pool = block.get("pool") or {}
            if pool or (require_pools and (only_product in (None, pid))):
                products[pid] = block
            else:
                products[pid] = {**block, "pool": _placeholder_pool(
                    self.product(pid)["classification_type"])}
        validate_samples_data({"products": products}, self.program.products,
                              self.engagement.overlay_products, where="store")

    def to_samples(self) -> dict[str, ProductSample]:
        """The build handoff: identical validation to the fixture path, so the
        store can never produce a workbook the loader would refuse."""
        for pid, block in self._doc["products"].items():
            if not block["pool"]:
                raise ConfigError(f"product {pid!r} has no pool buckets keyed yet")
        return validate_samples_data(self._samples_doc(), self.program.products,
                                     self.engagement.overlay_products,
                                     where="store")

    def progress(self) -> dict:
        """Per product, per segment: planned vs entered (the board's numbers)."""
        out = {}
        for pid, block in self._doc["products"].items():
            plan = self.engagement.overlay_products[pid]["sample_plan"]["segments"]
            done = {}
            for f in block["files"]:
                done[f["segment"]] = done.get(f["segment"], 0) + 1
            out[pid] = {
                "segments": [{**seg, "done": done.get(seg["id"], 0)} for seg in plan],
                "files": len(block["files"]),
                "pool_keyed": bool(block["pool"]),
            }
        return out


def _placeholder_pool(classification_type: str) -> dict:
    pool = {b: {"count": 0, "dollars": 0} for b in
            ("current", "dpd_30_59", "dpd_60_89", "dpd_90_119", "dpd_120_179",
             "dpd_180_plus")}
    if classification_type == "residential_secured":
        pool["qualifying_90_ltv60"] = {"count": 0, "dollars": 0}
        pool["writedown_loss"] = {"count": 0, "dollars": 0}
    return pool
