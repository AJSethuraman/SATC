from __future__ import annotations

import json
from pathlib import Path

from .models import AgentManifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENT_DIR = PROJECT_ROOT / "examples" / "agents"


DEFAULT_TALKER_DIR = Path(__file__).resolve().parent.parent / "brains" / "talkers"


def load_talkers(directory: str | Path = DEFAULT_TALKER_DIR) -> list[AgentManifest]:
    """The house talkers (PRD §5.25): JSON manifests of kind talker, at most
    three, in file-name order."""
    paths = sorted(Path(directory).glob("*.json"))
    talkers = [AgentManifest.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if any(t.kind != "talker" for t in talkers):
        raise ValueError(f"every manifest in {directory} must be a talker")
    if len(talkers) > 3:
        raise ValueError(f"at most three talkers in {directory}")
    return talkers


def load_manifests(directory: str | Path = DEFAULT_AGENT_DIR) -> list[AgentManifest]:
    paths = sorted(Path(directory).glob("*.json"))
    manifests = [
        AgentManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if not 4 <= len(manifests) <= 8:
        raise ValueError(f"expected 4..8 agent JSON files in {directory}")
    return manifests
