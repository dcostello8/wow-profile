from os import getenv
from pathlib import Path

import yaml
from dotenv import load_dotenv


DEFAULT_REDIRECT_URI = "http://localhost:8000/callback"
DEFAULT_LOCALE = "en_US"
DEFAULT_UPDATE_SETTINGS = {
    "profile": True,
    "equipment": True,
    "specializations": True,
    "statistics": True,
    "professions": True,
    "mythic_plus": True,
    "media": True,
    "reputations": True,
    "titles": True,
}
UPDATE_SECTIONS = (
    "profile",
    "equipment",
    "specializations",
    "statistics",
    "professions",
    "mythic_plus",
    "media",
    "reputations",
    "titles",
)
CHARACTERS_FILE = Path("characters.yaml")
CHARACTER_FIELD_ORDER = [
    "key",
    "name",
    "enabled",
    "region",
    "id",
    "realm",
    "realm_id",
    "realm_slug",
    "stale",
    "wow_account_id",
    "protected_character_href",
]


def require_env(name):
    value = getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config():
    load_dotenv()
    return {
        "client_id": require_env("BLIZZARD_CLIENT_ID"),
        "client_secret": require_env("BLIZZARD_CLIENT_SECRET"),
        "redirect_uri": getenv("BLIZZARD_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        "region": getenv("BLIZZARD_REGION", "us").lower(),
        "locale": getenv("BLIZZARD_LOCALE", DEFAULT_LOCALE),
    }


def load_existing_roster(path=CHARACTERS_FILE):
    if not path.exists():
        return {"characters": []}

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if isinstance(data, list):
        return {"characters": data}
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a YAML mapping or list.")

    characters = data.get("characters")
    if characters is None:
        data["characters"] = []
    elif not isinstance(characters, list):
        raise RuntimeError(f"{path} field 'characters' must be a list.")
    return data


def save_roster(roster, path=CHARACTERS_FILE):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(roster, handle, sort_keys=False, allow_unicode=True)


def character_key(region, character):
    realm = character.get("realm") or {}
    realm_slug = (
        realm.get("slug")
        or character.get("realm_slug")
        or str(realm.get("id") or "").lower()
    )
    name = character.get("name") or str(character.get("id") or "")
    character_id = character.get("id")
    if character_id:
        return f"{region}:id:{character_id}"
    return f"{region}:{realm_slug}:{name.lower()}"


def existing_character_key(character):
    region = character.get("region")
    character_id = character.get("id")
    if region and character_id:
        return f"{region}:id:{character_id}"
    if character.get("key"):
        return character["key"]
    realm_slug = character.get("realm_slug") or character.get("realm")
    name = character.get("name")
    if region and realm_slug and name:
        return f"{region}:{str(realm_slug).lower()}:{name.lower()}"
    return None


def flatten_characters(account_profile):
    characters = []
    for account in account_profile.get("wow_accounts", []):
        account_id = account.get("id")
        for character in account.get("characters", []):
            item = dict(character)
            if account_id is not None:
                item["wow_account_id"] = account_id
            characters.append(item)
    return characters


def order_character_fields(character):
    ordered = {
        field: character[field]
        for field in CHARACTER_FIELD_ORDER
        if field in character
    }
    for field, value in character.items():
        if field not in ordered:
            ordered[field] = value
    return ordered


def simplify_character(region, character, existing=None):
    existing = existing or {}
    realm = character.get("realm") or {}
    protected_character = character.get("protected_character") or {}
    key = character_key(region, character)

    item = dict(existing)
    item.update({
        "key": key,
        "enabled": bool(existing.get("enabled", False)),
        "region": region,
        "name": character.get("name"),
        "id": character.get("id"),
        "realm": realm.get("name"),
        "realm_id": realm.get("id"),
        "realm_slug": realm.get("slug"),
        "stale": False,
    })

    if character.get("wow_account_id") is not None:
        item["wow_account_id"] = character["wow_account_id"]
    if protected_character.get("href"):
        item["protected_character_href"] = protected_character["href"]

    return order_character_fields(item)


def merge_roster(app_config, account_profile, path=CHARACTERS_FILE):
    roster = load_existing_roster(path)
    existing_by_key = {}
    existing_order = []
    for character in roster["characters"]:
        if not isinstance(character, dict):
            continue
        key = existing_character_key(character)
        if not key:
            continue
        existing_by_key[key] = character
        existing_order.append(key)

    discovered = flatten_characters(account_profile)
    merged_by_key = {}
    discovered_order = []

    for character in discovered:
        key = character_key(app_config["region"], character)
        merged_by_key[key] = simplify_character(
            app_config["region"], character, existing_by_key.get(key)
        )
        discovered_order.append(key)

    merged = []
    seen = set()
    for key in existing_order:
        if key in merged_by_key:
            merged.append(merged_by_key[key])
        else:
            stale_character = dict(existing_by_key[key])
            stale_character["stale"] = True
            stale_character["enabled"] = False
            merged.append(order_character_fields(stale_character))
        seen.add(key)

    for key in discovered_order:
        if key not in seen:
            merged.append(merged_by_key[key])
            seen.add(key)

    roster["characters"] = merged
    return roster


def load_character_roster(path=CHARACTERS_FILE):
    roster = load_existing_roster(path)
    return roster, [
        character
        for character in roster["characters"]
        if isinstance(character, dict)
    ]


def enabled_characters(characters):
    return [
        character
        for character in characters
        if character.get("enabled") is True and not character.get("stale")
    ]


def update_settings_for_character(roster, character):
    settings = dict(DEFAULT_UPDATE_SETTINGS)
    defaults = roster.get("defaults") or {}
    default_update = defaults.get("update") or {}
    if isinstance(default_update, dict):
        settings.update({
            key: bool(value)
            for key, value in default_update.items()
            if key in UPDATE_SECTIONS
        })

    character_update = character.get("update") or {}
    if isinstance(character_update, dict):
        settings.update({
            key: bool(value)
            for key, value in character_update.items()
            if key in UPDATE_SECTIONS
        })

    return settings


def selected_update_sections(settings):
    return [
        section
        for section in UPDATE_SECTIONS
        if settings.get(section, False)
    ]


def require_character_field(character, field):
    value = character.get(field)
    if value in (None, ""):
        name = character.get("name") or character.get("key") or "unknown character"
        raise RuntimeError(f"Active character {name} is missing required field: {field}")
    return value
