import requests


UPDATE_ENDPOINTS = {
    "profile": "",
    "equipment": "equipment",
    "specializations": "specializations",
    "professions": "professions",
    "mythic_plus": "mythic-keystone-profile",
}


def region_hosts(region):
    if region == "cn":
        raise RuntimeError("The China Battle.net region is not supported by this utility.")
    return {
        "oauth": f"https://{region}.battle.net/oauth",
        "api": f"https://{region}.api.blizzard.com",
    }


def fetch_account_profile(config, hosts, access_token):
    response = requests.get(
        f"{hosts['api']}/profile/user/wow",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "namespace": f"profile-{config['region']}",
            "locale": config["locale"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_character_resource(config, hosts, access_token, character, section):
    endpoint = UPDATE_ENDPOINTS[section]
    suffix = f"/{endpoint}" if endpoint else ""
    response = requests.get(
        (
            f"{hosts['api']}/profile/wow/character/"
            f"{character['realm_slug']}/{character['name'].lower()}{suffix}"
        ),
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "namespace": f"profile-{character.get('region') or config['region']}",
            "locale": config["locale"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


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
