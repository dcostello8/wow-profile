from .base import GameDataService


class PetService(GameDataService):
    cache_category = "pets"

    def get_index(self):
        return self.get("/data/wow/pet/index")

    def get_pet(self, pet_id):
        return self.get(f"/data/wow/pet/{pet_id}")