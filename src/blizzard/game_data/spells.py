from .base import GameDataService


class SpellService(GameDataService):
    cache_category = "spells"

    def get_spell(self, spell_id):
        return self.get(f"/data/wow/spell/{spell_id}")

    def get_media(self, spell_id):
        return self.get(f"/data/wow/media/spell/{spell_id}")

    def search(self, **criteria):
        return self.client.get(
            "/data/wow/search/spell",
            namespace_type=self.namespace_type,
            params=criteria,
        )

