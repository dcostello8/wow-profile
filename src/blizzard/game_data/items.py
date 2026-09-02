from .base import GameDataService


class ItemService(GameDataService):
    cache_category = "items"

    def get_item(self, item_id):
        return self.get(f"/data/wow/item/{item_id}")

    def get_media(self, item_id):
        return self.get(f"/data/wow/media/item/{item_id}")

    def search(self, **criteria):
        return self.client.get(
            "/data/wow/search/item",
            namespace_type=self.namespace_type,
            params=criteria,
        )

