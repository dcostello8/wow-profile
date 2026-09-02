from .base import GameDataService


class ProfessionService(GameDataService):
    cache_category = "professions"

    def get_index(self):
        return self.get("/data/wow/profession/index")

    def get_profession(self, profession_id):
        return self.get(f"/data/wow/profession/{profession_id}")

    def get_skill_tier(self, profession_id, skill_tier_id):
        return self.get(
            f"/data/wow/profession/{profession_id}/skill-tier/{skill_tier_id}"
        )

    def get_media(self, profession_id):
        return self.get(f"/data/wow/media/profession/{profession_id}")

    def get_recipe(self, recipe_id):
        return self.get(f"/data/wow/recipe/{recipe_id}")

    def get_recipe_media(self, recipe_id):
        return self.get(f"/data/wow/media/recipe/{recipe_id}")

