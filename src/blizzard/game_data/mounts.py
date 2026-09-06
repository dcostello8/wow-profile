from .base import GameDataService


class MountService(GameDataService):
    cache_category = "mounts"

    def get_index(self):
        return self.get("/data/wow/mount/index")

    def get_mount(self, mount_id):
        return self.get(f"/data/wow/mount/{mount_id}")