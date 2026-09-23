"""Write the pinned JSON Schemas from the models module. Run after any change to
arena/models.py; tests/test_contract.py fails until the pinned copy matches."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena.models import action_json_schema, manifest_json_schema  # noqa: E402

TARGETS = {
    "agent-action.schema.json": action_json_schema,
    "agent-manifest.schema.json": manifest_json_schema,
}


def main() -> int:
    for name, fn in TARGETS.items():
        path = ROOT / "schemas" / name
        path.write_text(json.dumps(fn(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
