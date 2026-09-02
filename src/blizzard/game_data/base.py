from ..cache import JsonCache
from ..client import NAMESPACE_STATIC


class GameDataService:
    namespace_type = NAMESPACE_STATIC
    cache_category = "game-data"

    def __init__(self, client, cache=None):
        self.client = client
        self.cache = cache or JsonCache()

    def get(self, path, cache_key=None, params=None):
        key = cache_key or path
        return self.cache.get_or_fetch(
            self.cache_category,
            key,
            lambda: self.client.get(path, namespace_type=self.namespace_type, params=params),
        )

