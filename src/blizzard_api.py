import requests

from .blizzard.client import BlizzardClient, region_hosts
from .blizzard.profile.account import AccountProfileService
from .blizzard.profile.character import (
    CHARACTER_PROFILE_SECTIONS,
    CharacterProfileService,
)

UPDATE_ENDPOINTS = CHARACTER_PROFILE_SECTIONS


def fetch_account_profile(config, hosts, access_token):
    client = BlizzardClient(config, access_token, hosts=hosts)
    return AccountProfileService(client).get_wow_profile()


def fetch_character_resource(config, hosts, access_token, character, section):
    service_config = {
        **config,
        "region": character.get("region") or config["region"],
    }
    client = BlizzardClient(service_config, access_token, hosts=hosts)
    return CharacterProfileService(client).get_section(character, section)


def fetch_character_profile(config, hosts, access_token, character):
    return fetch_character_resource(config, hosts, access_token, character, "profile")


def error_summary(exc):
    if isinstance(exc, requests.HTTPError):
        response = exc.response
        if response is None:
            return str(exc)
        text = response.text.strip()
        if len(text) > 500:
            text = f"{text[:500]}..."
        return f"HTTP {response.status_code}: {text}"
    return str(exc)


def fetch_enabled_character_sections(config, hosts, access_token, character, sections):
    data = {}
    section_status = {}

    for section in sections:
        try:
            data[section] = fetch_character_resource(
                config, hosts, access_token, character, section
            )
            section_status[section] = {"status": "updated"}
        except requests.HTTPError as exc:
            response = exc.response
            section_status[section] = {
                "status": "failed",
                "error": error_summary(exc),
            }
            if response is not None:
                section_status[section]["status_code"] = response.status_code
        except Exception as exc:
            section_status[section] = {
                "status": "failed",
                "error": str(exc),
            }

    return data, section_status
