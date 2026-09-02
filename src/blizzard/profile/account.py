from ..client import NAMESPACE_PROFILE


class AccountProfileService:
    def __init__(self, client):
        self.client = client

    def get_wow_profile(self):
        return self.client.get("/profile/user/wow", namespace_type=NAMESPACE_PROFILE)

    def get_collections(self):
        return self.client.get("/profile/user/wow/collections", namespace_type=NAMESPACE_PROFILE)

    def get_mounts(self):
        return self.client.get("/profile/user/wow/collections/mounts", namespace_type=NAMESPACE_PROFILE)

    def get_pets(self):
        return self.client.get("/profile/user/wow/collections/pets", namespace_type=NAMESPACE_PROFILE)

