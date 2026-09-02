from .base import GameDataService


class TalentService(GameDataService):
    cache_category = "talents"

    def get_talent_index(self):
        return self.get("/data/wow/talent/index")

    def get_talent(self, talent_id):
        return self.get(f"/data/wow/talent/{talent_id}")

    def get_pvp_talent_index(self):
        return self.get("/data/wow/pvp-talent/index")

    def get_pvp_talent(self, pvp_talent_id):
        return self.get(f"/data/wow/pvp-talent/{pvp_talent_id}")

    def get_talent_tree_index(self):
        return self.get("/data/wow/talent-tree/index")

    def get_talent_tree(self, talent_tree_id, spec_id=None):
        if spec_id is None:
            return self.get(f"/data/wow/talent-tree/{talent_tree_id}")
        return self.get(f"/data/wow/talent-tree/{talent_tree_id}/playable-specialization/{spec_id}")

