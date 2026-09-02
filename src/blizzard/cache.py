import hashlib
import json
from pathlib import Path


DEFAULT_CACHE_DIR = Path("output/cache/blizzard")


class JsonCache:
    def __init__(self, root=DEFAULT_CACHE_DIR, version="v1"):
        self.root = Path(root)
        self.version = version

    def get(self, category, key):
        path = self.path(category, key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def set(self, category, key, value):
        path = self.path(category, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return value

    def get_or_fetch(self, category, key, fetch):
        cached = self.get(category, key)
        if cached is not None:
            return cached
        return self.set(category, key, fetch())

    def path(self, category, key):
        digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]
        return self.root / self.version / category / f"{digest}.json"

