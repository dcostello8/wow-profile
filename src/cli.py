import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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
from .local_wow import import_saved_variables
from .oauth import (
    exchange_code_for_token,
    get_client_credentials_token,
    wait_for_authorization_code,
)
from .output import (
    ACCOUNT_SUMMARY_MARKDOWN_FILE,
    FULL_ROSTER_MARKDOWN_FILE,
    ROSTER_MARKDOWN_FILE,
    ROSTER_INDEX_FILE,
    character_output_path,
    equipment_sets_summary,
    local_specs_summary,
    roster_index_entry,
    write_json,
    write_account_summary_markdown,
    write_full_roster_markdown,
    write_roster_markdown,
)
from .roster_ui import run_roster_ui


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

    total_selected = len(selected)
    for position, character in enumerate(selected, start=1):
        display_name = f"{character.get('name')} - {character.get('realm')}"
        try:
            print(f"Updating [{position}/{total_selected}] {display_name}...", flush=True)
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
            existing_document = load_json_file(output_path) or {}
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
            if existing_document.get("local_client_data"):
                document["local_client_data"] = existing_document["local_client_data"]
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
    refresh_local_output_summaries()

    print(f"Wrote {ROSTER_INDEX_FILE}.")
    print(f"Wrote {ROSTER_MARKDOWN_FILE}.")
    print(f"Wrote {ACCOUNT_SUMMARY_MARKDOWN_FILE}.")
    print(
        f"Updated {success_count} characters; "
        f"{partial_count} partial; {failure_count} failed."
    )
    return 0 if failure_count == 0 else 1


def load_json_file(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_character_documents(index):
    documents = []
    for character in (index or {}).get("characters", []):
        profile_path = character.get("profile_path")
        if not profile_path:
            continue
        document = load_json_file(Path(profile_path))
        if document:
            documents.append(document)
    return documents


def write_account_summary():
    generated_at = datetime.now(timezone.utc).isoformat()
    roster, _ = load_character_roster()
    index = load_json_file(ROSTER_INDEX_FILE) or {}
    character_documents = load_character_documents(index)
    write_account_summary_markdown(
        ACCOUNT_SUMMARY_MARKDOWN_FILE,
        generated_at,
        roster,
        index,
        character_documents,
    )


def refresh_local_output_summaries():
    index = load_json_file(ROSTER_INDEX_FILE) or {}
    if not index:
        write_account_summary()
        return

    for character in index.get("characters", []):
        profile_path = character.get("profile_path")
        if not profile_path:
            continue
        document = load_json_file(Path(profile_path))
        if document:
            spec_summary = local_specs_summary(document)
            equipment_summary = equipment_sets_summary(document)
            if spec_summary:
                character["local_specs"] = spec_summary
            if equipment_summary:
                character["local_equipment_sets"] = equipment_summary

    write_json(ROSTER_INDEX_FILE, index)
    write_roster_markdown(ROSTER_MARKDOWN_FILE, index)
    write_account_summary()


def account_summary():
    write_account_summary()
    print(f"Wrote {ACCOUNT_SUMMARY_MARKDOWN_FILE}.")
    return 0


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


def import_local(saved_variables):
    result = import_saved_variables(Path(saved_variables))
    refresh_local_output_summaries()
    print(f"Imported local WoW data for {result.matched} characters.")
    print(f"Refreshed {ROSTER_INDEX_FILE}.")
    print(f"Refreshed {ROSTER_MARKDOWN_FILE}.")
    print(f"Refreshed {ACCOUNT_SUMMARY_MARKDOWN_FILE}.")
    if result.missing_output:
        print(
            f"Skipped {result.missing_output} matched characters without generated JSON. "
            "Run update for those characters first."
        )
    if result.unmatched:
        print(f"SavedVariables contained {result.unmatched} characters not found in characters.yaml.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Discover and update World of Warcraft character data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Authenticate and write characters.yaml.")
    subparsers.add_parser("update", help="Fetch data for enabled characters.")
    subparsers.add_parser("fullroster", help="Write basic info for all discovered characters.")
    subparsers.add_parser("summary", help="Write account_summary.html from existing output.")
    roster_ui_parser = subparsers.add_parser(
        "roster-ui",
        help="Open a local UI for enabling and disabling discovered characters.",
    )
    roster_ui_parser.add_argument("--host", default="127.0.0.1", help="Host for the local UI.")
    roster_ui_parser.add_argument("--port", default=8765, type=int, help="Port for the local UI.")
    import_local_parser = subparsers.add_parser(
        "import-local",
        help="Merge WowProfileCollector SavedVariables into generated character JSON.",
    )
    import_local_parser.add_argument(
        "--saved-variables",
        required=True,
        help="Path to WTF\\Account\\<account>\\SavedVariables\\WowProfileCollector.lua.",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "discover":
            discover()
            return 0
        if args.command == "update":
            return update()
        if args.command == "fullroster":
            return fullroster()
        if args.command == "summary":
            return account_summary()
        if args.command == "roster-ui":
            return run_roster_ui(args.host, args.port)
        if args.command == "import-local":
            return import_local(args.saved_variables)
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
