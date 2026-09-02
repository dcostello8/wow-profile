from .base import GameDataService


class MythicPlusService(GameDataService):
    cache_category = "mythic-plus"

    def get_dungeon_index(self):
        return self.get("/data/wow/mythic-keystone/dungeon/index")

    def get_dungeon(self, dungeon_id):
        return self.get(f"/data/wow/mythic-keystone/dungeon/{dungeon_id}")

    def get_period_index(self):
        return self.get("/data/wow/mythic-keystone/period/index")

    def get_period(self, period_id):
        return self.get(f"/data/wow/mythic-keystone/period/{period_id}")

    def get_season_index(self):
        return self.get("/data/wow/mythic-keystone/season/index")

    def get_season(self, season_id):
        return self.get(f"/data/wow/mythic-keystone/season/{season_id}")

    def get_affix_index(self):
        return self.get("/data/wow/keystone-affix/index")

    def get_affix(self, affix_id):
        return self.get(f"/data/wow/keystone-affix/{affix_id}")

    def get_affix_media(self, affix_id):
        return self.get(f"/data/wow/media/keystone-affix/{affix_id}")

