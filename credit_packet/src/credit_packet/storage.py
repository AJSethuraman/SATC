import hashlib, json
from pathlib import Path

class CacheStore:
    def __init__(self, root: Path = Path('.cache/credit_packet')):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / (hashlib.sha256(key.encode()).hexdigest() + '.json')

    def get(self, key: str):
        p = self._path(key)
        if p.exists():
            return json.loads(p.read_text())
        return None

    def set(self, key: str, value):
        self._path(key).write_text(json.dumps(value))
