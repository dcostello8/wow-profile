from .base import GameDataService


class RealmService(GameDataService):
    cache_category = "realms"

    def get_region_index(self):
        return self.get("/data/wow/region/index")

    def get_region(self, region_id):
        return self.get(f"/data/wow/region/{region_id}")

    def get_realm_index(self):
        return self.get("/data/wow/realm/index")

    def get_realm(self, realm_slug):
        return self.get(f"/data/wow/realm/{realm_slug}")

    def search_realms(self, **criteria):
        return self.client.get(
            "/data/wow/search/realm",
            namespace_type=self.namespace_type,
            params=criteria,
        )

    def get_connected_realm_index(self):
        return self.get("/data/wow/connected-realm/index")

    def get_connected_realm(self, connected_realm_id):
        return self.get(f"/data/wow/connected-realm/{connected_realm_id}")

    def search_connected_realms(self, **criteria):
        return self.client.get(
            "/data/wow/search/connected-realm",
            namespace_type=self.namespace_type,
            params=criteria,
        )

