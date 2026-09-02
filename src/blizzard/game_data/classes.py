from .base import GameDataService


class ClassService(GameDataService):
    cache_category = "classes"

    def get_index(self):
        return self.get("/data/wow/playable-class/index")

    def get_class(self, class_id):
        return self.get(f"/data/wow/playable-class/{class_id}")

    def get_media(self, class_id):
        return self.get(f"/data/wow/media/playable-class/{class_id}")

