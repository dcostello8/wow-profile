from .base import GameDataService


class JournalService(GameDataService):
    cache_category = "journal"

    def get_expansion_index(self):
        return self.get("/data/wow/journal-expansion/index")

    def get_expansion(self, expansion_id):
        return self.get(f"/data/wow/journal-expansion/{expansion_id}")

    def get_instance_index(self):
        return self.get("/data/wow/journal-instance/index")

    def get_instance(self, instance_id):
        return self.get(f"/data/wow/journal-instance/{instance_id}")

    def get_encounter_index(self):
        return self.get("/data/wow/journal-encounter/index")

    def get_encounter(self, encounter_id):
        return self.get(f"/data/wow/journal-encounter/{encounter_id}")

    def search_encounters(self, **criteria):
        return self.client.get(
            "/data/wow/search/journal-encounter",
            namespace_type=self.namespace_type,
            params=criteria,
        )

