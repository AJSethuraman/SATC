from __future__ import annotations

import json
from pathlib import Path

from .models import AgentManifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENT_DIR = PROJECT_ROOT / "examples" / "agents"


def load_manifests(directory: str | Path = DEFAULT_AGENT_DIR) -> list[AgentManifest]:
    paths = sorted(Path(directory).glob("*.json"))
    manifests = [
        AgentManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if not 4 <= len(manifests) <= 8:
        raise ValueError(f"expected 4..8 agent JSON files in {directory}")
    return manifests
