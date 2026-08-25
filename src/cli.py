import argparse
import sys
from datetime import datetime, timezone

import requests

from .blizzard_api import (
    error_summary,
    fetch_account_profile,
    fetch_character_profile,
    fetch_enabled_character_sections,
    region_hosts,
)
from .config import (
    CHARACTERS_FILE,
    DEFAULT_UPDATE_SETTINGS,
    enabled_characters,
    load_character_roster,
    load_config,
    merge_roster,
    require_character_field,
    save_roster,
    selected_update_sections,
    update_settings_for_character,
)
from .oauth import (
    exchange_code_for_token,
    get_client_credentials_token,
    wait_for_authorization_code,
)
from .output import (
    FULL_ROSTER_MARKDOWN_FILE,
    ROSTER_MARKDOWN_FILE,
    ROSTER_INDEX_FILE,
    character_output_path,
    roster_index_entry,
    write_json,
    write_full_roster_markdown,
    write_roster_markdown,
)


def discover():
    config = load_config()
    hosts = region_hosts(config["region"])
    code = wait_for_authorization_code(config, hosts)
    access_token = exchange_code_for_token(config, hosts, code)
    account_profile = fetch_account_profile(config, hosts, access_token)
    roster = merge_roster(config, account_profile)
    save_roster(roster)

    total = len(roster["characters"])
    enabled = sum(1 for character in roster["characters"] if character.get("enabled"))
    print(f"Wrote {total} characters to {CHARACTERS_FILE}.")
    print(f"Enabled characters preserved: {enabled}. Newly discovered characters default to disabled.")


def update():
    config = load_config()
    hosts = region_hosts(config["region"])
    roster, characters = load_character_roster()
    selected = enabled_characters(characters)

    if not selected:
        print("No enabled characters found in characters.yaml.")
        print("Set enabled: true for at least one character, then run update again.")
        return 0

    access_token = get_client_credentials_token(config, hosts)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    index = {
        "generated_at": retrieved_at,
        "source": "Battle.net World of Warcraft Profile API",
        "character_count": len(selected),
        "default_update": dict(DEFAULT_UPDATE_SETTINGS),
        "characters": [],
    }

    print(f"Updating {len(selected)} enabled characters...")
    success_count = 0
    failure_count = 0
    partial_count = 0

    for character in selected:
        display_name = f"{character.get('name')} - {character.get('realm')}"
        try:
            require_character_field(character, "name")
            require_character_field(character, "realm_slug")
            settings = update_settings_for_character(roster, character)
            sections = selected_update_sections(settings)
            if not sections:
                raise RuntimeError("No update sections are enabled for this character.")

            data, section_status = fetch_enabled_character_sections(
                config, hosts, access_token, character, sections
            )
            failed_sections = [
                section
                for section, result in section_status.items()
                if result.get("status") != "updated"
            ]
            status = "updated" if not failed_sections else "partial"
            if len(failed_sections) == len(sections):
                status = "failed"

            profile = data.get("profile")
            output_path = character_output_path(character)
            document = {
                "retrieved_at": retrieved_at,
                "source": "Battle.net World of Warcraft Profile API",
                "character": {
                    "key": character.get("key"),
                    "name": character.get("name"),
                    "realm": character.get("realm"),
                    "realm_slug": character.get("realm_slug"),
                    "region": character.get("region"),
                    "id": character.get("id"),
                },
                "update_settings": settings,
                "sections": data,
                "section_status": section_status,
            }
            write_json(output_path, document)
            index["characters"].append(
                {
                    **roster_index_entry(
                        character, status, output_path, profile=profile
                    ),
                    "sections": section_status,
                }
            )
            if status == "updated":
                success_count += 1
            elif status == "partial":
                partial_count += 1
            else:
                failure_count += 1
            print(
                f"Updated {display_name}: "
                f"{len(sections) - len(failed_sections)}/{len(sections)} sections."
            )
        except requests.HTTPError as exc:
            failure_count += 1
            index["characters"].append(
                roster_index_entry(character, "failed", error=error_summary(exc))
            )
            response = exc.response
            status_code = response.status_code if response is not None else "unknown"
            print(f"Failed {display_name}: HTTP {status_code}.", file=sys.stderr)
        except Exception as exc:
            failure_count += 1
            index["characters"].append(
                roster_index_entry(character, "failed", error=str(exc))
            )
            print(f"Failed {display_name}: {exc}", file=sys.stderr)

    index["updated_count"] = success_count
    index["partial_count"] = partial_count
    index["failed_count"] = failure_count
    write_json(ROSTER_INDEX_FILE, index)
    write_roster_markdown(ROSTER_MARKDOWN_FILE, index)

    print(f"Wrote {ROSTER_INDEX_FILE}.")
    print(f"Wrote {ROSTER_MARKDOWN_FILE}.")
    print(
        f"Updated {success_count} characters; "
        f"{partial_count} partial; {failure_count} failed."
    )
    return 0 if failure_count == 0 else 1


def fullroster():
    config = load_config()
    hosts = region_hosts(config["region"])
    _, characters = load_character_roster()

    if not characters:
        print("No characters found in characters.yaml.")
        print("Run discover first, then run fullroster again.")
        return 0

    access_token = get_client_credentials_token(config, hosts)
    generated_at = datetime.now(timezone.utc).isoformat()
    updated_date = generated_at[:10]
    entries = []
    failure_count = 0

    print(f"Building full roster for {len(characters)} characters...", flush=True)
    for character in characters:
        display_name = f"{character.get('name')} - {character.get('realm')}"
        entry = {
            "name": character.get("name"),
            "realm": character.get("realm"),
            "level": "",
            "character_class": "",
            "last_updated": "",
        }
        try:
            require_character_field(character, "name")
            require_character_field(character, "realm_slug")
            profile = fetch_character_profile(config, hosts, access_token, character)
            entry["level"] = profile.get("level")
            entry["character_class"] = (profile.get("character_class") or {}).get("name")
            entry["last_updated"] = updated_date
            print(f"Fetched {display_name}.")
        except requests.HTTPError as exc:
            failure_count += 1
            response = exc.response
            status_code = response.status_code if response is not None else "unknown"
            print(f"Failed {display_name}: HTTP {status_code}.", file=sys.stderr)
        except Exception as exc:
            failure_count += 1
            print(f"Failed {display_name}: {exc}", file=sys.stderr)
        entries.append(entry)

    write_full_roster_markdown(FULL_ROSTER_MARKDOWN_FILE, generated_at, entries)
    print(f"Wrote {FULL_ROSTER_MARKDOWN_FILE}.")
    print(
        f"Fetched profile details for {len(characters) - failure_count} characters; "
        f"{failure_count} unavailable."
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Discover and update World of Warcraft character data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Authenticate and write characters.yaml.")
    subparsers.add_parser("update", help="Fetch data for enabled characters.")
    subparsers.add_parser("fullroster", help="Write basic info for all discovered characters.")
    args = parser.parse_args(argv)

    try:
        if args.command == "discover":
            discover()
            return 0
        if args.command == "update":
            return update()
        if args.command == "fullroster":
            return fullroster()
    except requests.HTTPError as exc:
        response = exc.response
        details = response.text if response is not None else str(exc)
        print(f"HTTP error from Battle.net: {exc}", file=sys.stderr)
        print(details, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 1
