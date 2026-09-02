from ..client import NAMESPACE_PROFILE


CHARACTER_PROFILE_SECTIONS = {
    "profile": "",
    "equipment": "equipment",
    "specializations": "specializations",
    "statistics": "statistics",
    "professions": "professions",
    "mythic_plus": "mythic-keystone-profile",
    "media": "character-media",
    "reputations": "reputations",
    "titles": "titles",
    "achievements": "achievements",
    "achievement_statistics": "achievements/statistics",
    "appearance": "appearance",
    "collections": "collections",
    "encounters": "encounters",
    "encounter_dungeons": "encounters/dungeons",
    "encounter_raids": "encounters/raids",
    "hunter_pets": "hunter-pets",
    "pvp_summary": "pvp-summary",
    "quests": "quests",
    "completed_quests": "quests/completed",
    "soulbinds": "soulbinds",
}


class CharacterProfileService:
    def __init__(self, client):
        self.client = client

    def get_section(self, character, section):
        endpoint = CHARACTER_PROFILE_SECTIONS[section]
        return self.client.get(
            self.character_path(character, endpoint),
            namespace_type=NAMESPACE_PROFILE,
        )

    def get_profile(self, character):
        return self.get_section(character, "profile")

    def get_equipment(self, character):
        return self.get_section(character, "equipment")

    def get_specializations(self, character):
        return self.get_section(character, "specializations")

    def get_statistics(self, character):
        return self.get_section(character, "statistics")

    def get_professions(self, character):
        return self.get_section(character, "professions")

    def get_mythic_keystone_profile(self, character):
        return self.get_section(character, "mythic_plus")

    def get_mythic_keystone_profile_season(self, character, season_id):
        return self.client.get(
            self.character_path(character, f"mythic-keystone-profile/season/{season_id}"),
            namespace_type=NAMESPACE_PROFILE,
        )

    def get_media(self, character):
        return self.get_section(character, "media")

    def get_reputations(self, character):
        return self.get_section(character, "reputations")

    def get_titles(self, character):
        return self.get_section(character, "titles")

    def get_pvp_bracket(self, character, bracket):
        return self.client.get(
            self.character_path(character, f"pvp-bracket/{bracket}"),
            namespace_type=NAMESPACE_PROFILE,
        )

    def character_path(self, character, endpoint=""):
        suffix = f"/{endpoint}" if endpoint else ""
        return (
            "/profile/wow/character/"
            f"{character['realm_slug']}/{character['name'].lower()}{suffix}"
        )

