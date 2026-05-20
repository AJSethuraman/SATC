import hashlib
from pathlib import Path

class CacheStore:
    def __init__(self, root: Path = Path('.cache/sec')):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_key(self, key: str, suffix: str) -> Path:
        digest = hashlib.sha256(key.encode('utf-8')).hexdigest()
        return self.root / f"{digest}.{suffix}"

    def get_bytes(self, key: str) -> bytes | None:
        for sfx in ("json","txt","bin"):
            p=self.path_for_key(key,sfx)
            if p.exists():
                return p.read_bytes()
        return None

    def set_bytes(self, key: str, data: bytes, suffix: str):
        self.path_for_key(key, suffix).write_bytes(data)
