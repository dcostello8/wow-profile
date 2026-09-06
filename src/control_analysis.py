"""Functional-role analysis for normalized local client controls."""

from pathlib import Path

import yaml

from .config_analysis import presentation_data

DEFAULT_ROLE_FILE = Path("data/ability_roles.yaml")


def _spell_id(value):
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Ability spell ID must be an integer: {value!r}")
    if normalized <= 0:
        raise ValueError(f"Ability spell ID must be positive: {value!r}")
    return normalized


def load_ability_roles(path=DEFAULT_ROLE_FILE):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Ability role data must be a mapping.")
    abilities = data.get("abilities")
    if not isinstance(abilities, dict):
        raise ValueError("Ability role data must contain an 'abilities' mapping.")

    roles = {}
    for raw_spell_id, definition in abilities.items():
        spell_id = _spell_id(raw_spell_id)
        if not isinstance(definition, dict):
            raise ValueError(f"Ability {spell_id} must be a mapping.")
        role_names = definition.get("roles")
        if not isinstance(role_names, list) or not role_names:
            raise ValueError(f"Ability {spell_id} must define a non-empty roles list.")
        if any(not isinstance(role, str) or not role.strip() for role in role_names):
            raise ValueError(f"Ability {spell_id} roles must be non-empty strings.")
        roles[spell_id] = {
            "name": definition.get("name") or "",
            "roles": [role.strip() for role in role_names],
        }
    return roles


def _assignment_rows(spec, role_map):
    for row in presentation_data(spec)["key_bindings"] + presentation_data(spec)["click_bindings"]:
        spell_id = row.get("spell_id")
        try:
            definition = role_map.get(int(spell_id))
        except (TypeError, ValueError):
            definition = None
        roles = definition["roles"] if definition else [None]
        for role in roles:
            yield {
                "role": role,
                "spell_id": int(spell_id),
                "ability": row.get("label") or (definition or {}).get("name") or str(spell_id),
                "binding": row.get("binding"),
                "source": row.get("source"),
                "spec_id": spec.get("spec_id"),
                "spec_name": spec.get("spec_name") or str(spec.get("spec_id") or ""),
            }


def classify_spec_controls(spec, role_map=None):
    role_map = load_ability_roles() if role_map is None else role_map
    return list(_assignment_rows(spec, role_map))


def aggregate_role_bindings(documents, role_map=None):
    role_map = load_ability_roles() if role_map is None else role_map
    assignments = []
    for document in documents or []:
        character = document.get("character") or {}
        local_data = document.get("local_client_data") or {}
        for spec in (local_data.get("specs") or {}).values():
            if not isinstance(spec, dict):
                continue
            for assignment in _assignment_rows(spec, role_map):
                assignments.append({
                    **assignment,
                    "character": character.get("name") or "Unknown",
                    "character_key": character.get("key"),
                })
    return assignments


def analyze_active_controls(documents, role_map=None):
    role_map = load_ability_roles() if role_map is None else role_map
    assignments = aggregate_role_bindings(documents, role_map)
    configured_roles = sorted({role for definition in role_map.values() for role in definition["roles"]})
    results = []
    for role in configured_roles:
        role_assignments = [item for item in assignments if item["role"] == role]
        binding_sets = {
            (item.get("source"), item.get("binding"))
            for item in role_assignments
        }
        if not role_assignments:
            status = "unused"
        elif len(binding_sets) == 1:
            status = "consistent"
        else:
            status = "varied"
        results.append({
            "role": role,
            "status": status,
            "assignments": role_assignments,
        })
    return results
