import json
import re
from pathlib import Path

from .config import require_character_field


OUTPUT_DIR = Path("output")
CHARACTER_OUTPUT_DIR = OUTPUT_DIR / "characters"
ROSTER_INDEX_FILE = OUTPUT_DIR / "roster.json"
ROSTER_MARKDOWN_FILE = OUTPUT_DIR / "roster.md"
FULL_ROSTER_MARKDOWN_FILE = OUTPUT_DIR / "fullroster.md"


def safe_output_stem(character):
    name = require_character_field(character, "name")
    realm_slug = require_character_field(character, "realm_slug")
    character_id = require_character_field(character, "id")
    stem = f"{name}-{realm_slug}-{character_id}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", stem).strip("-")


def character_output_path(character):
    return CHARACTER_OUTPUT_DIR / f"{safe_output_stem(character)}.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_roster_markdown(path, index):
    lines = [
        "# World of Warcraft Roster",
        "",
        f"Generated: {index.get('generated_at')}",
        "",
        "| Character | Realm | Level | Class | Spec | Status | Sections |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]

    for character in index.get("characters", []):
        sections = character.get("sections") or {}
        updated_sections = sum(
            1
            for result in sections.values()
            if result.get("status") == "updated"
        )
        section_count = len(sections)
        section_text = f"{updated_sections}/{section_count}" if section_count else ""
        lines.append(
            "| {name} | {realm} | {level} | {character_class} | {active_spec} | {status} | {sections} |".format(
                name=character.get("name") or "",
                realm=character.get("realm") or "",
                level=character.get("level") or "",
                character_class=character.get("character_class") or "",
                active_spec=character.get("active_spec") or "",
                status=character.get("status") or "",
                sections=section_text,
            )
        )

    lines.extend([
        "",
        f"Updated: {index.get('updated_count', 0)}",
        f"Partial: {index.get('partial_count', 0)}",
        f"Failed: {index.get('failed_count', 0)}",
        "",
    ])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def markdown_cell(value):
    return str(value if value is not None else "").replace("|", "\\|")


def write_full_roster_markdown(path, generated_at, entries):
    grouped = {}
    for entry in entries:
        realm = entry.get("realm") or "Unknown Realm"
        grouped.setdefault(realm, []).append(entry)

    lines = [
        "# Full World of Warcraft Roster",
        "",
        f"Generated: {generated_at}",
        "",
    ]

    for realm in sorted(grouped):
        lines.extend([
            f"## {realm}",
            "",
            "| Character | Level | Class | Last Updated |",
            "| --- | ---: | --- | --- |",
        ])
        for entry in sorted(grouped[realm], key=lambda item: (item.get("name") or "").lower()):
            lines.append(
                "| {name} | {level} | {character_class} | {last_updated} |".format(
                    name=markdown_cell(entry.get("name")),
                    level=markdown_cell(entry.get("level")),
                    character_class=markdown_cell(entry.get("character_class")),
                    last_updated=markdown_cell(entry.get("last_updated")),
                )
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_profile(profile):
    if not profile:
        return {}
    return {
        "level": profile.get("level"),
        "faction": (profile.get("faction") or {}).get("name"),
        "race": (profile.get("race") or {}).get("name"),
        "character_class": (profile.get("character_class") or {}).get("name"),
        "active_spec": (profile.get("active_spec") or {}).get("name"),
        "guild": (profile.get("guild") or {}).get("name"),
        "last_login_timestamp": profile.get("last_login_timestamp"),
    }


def roster_index_entry(character, status, profile_path=None, profile=None, error=None):
    entry = {
        "key": character.get("key"),
        "name": character.get("name"),
        "realm": character.get("realm"),
        "realm_slug": character.get("realm_slug"),
        "region": character.get("region"),
        "id": character.get("id"),
        "enabled": bool(character.get("enabled")),
        "stale": bool(character.get("stale", False)),
        "status": status,
    }
    if profile_path:
        entry["profile_path"] = str(profile_path).replace("\\", "/")
    entry.update(summarize_profile(profile))
    if error:
        entry["error"] = error
    return entry
