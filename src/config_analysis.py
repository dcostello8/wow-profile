"""Analysis helpers for normalized local client configuration."""


def _action_label(action):
    if not isinstance(action, dict):
        return None
    for key in ("spell_name", "item_name", "macro_name"):
        if action.get(key):
            return action[key]
    nested = action.get("action") if isinstance(action.get("action"), dict) else {}
    for key in ("text", "type", "id"):
        if nested.get(key):
            return nested[key]
    return action.get("action_type") or action.get("action_sub_type")


def presentation_data(spec):
    """Return rows suitable for displaying one normalized specialization."""
    key_rows = []
    for binding in spec.get("key_bindings") or []:
        label = _action_label(binding)
        if not label:
            continue
        for key in binding.get("display_keys") or binding.get("keys") or []:
            key_rows.append({
                "binding": key,
                "source": "key",
                "command": binding.get("command"),
                "action_bar_slot": binding.get("action_bar_slot"),
                "action_type": binding.get("action_type"),
                "spell_id": binding.get("spell_id"),
                "label": label,
            })

    click_rows = []
    for binding in spec.get("click_bindings") or []:
        label = binding.get("spell_name") or binding.get("action")
        if not label or not binding.get("display_binding"):
            continue
        click_rows.append({
            "binding": binding["display_binding"],
            "source": "click",
            "action_type": binding.get("action_type") or binding.get("type"),
            "spell_id": binding.get("spell_id"),
            "label": label,
        })

    return {
        "spec_id": spec.get("spec_id"),
        "spec_name": spec.get("spec_name"),
        "key_bindings": key_rows,
        "click_bindings": click_rows,
    }


def _spell_assignments(spec):
    assignments = {}
    for row in presentation_data(spec)["key_bindings"] + presentation_data(spec)["click_bindings"]:
        spell_id = row.get("spell_id")
        if spell_id is None:
            continue
        assignments.setdefault(str(spell_id), {
            "spell_id": spell_id,
            "name": row.get("label"),
            "bindings": [],
        })["bindings"].append({
            "binding": row["binding"],
            "source": row["source"],
        })
    return assignments


def _spell_sort_key(spell_id):
    return int(spell_id) if spell_id.isdigit() else spell_id


def _spec_sort_key(spec_id):
    return int(spec_id) if spec_id.isdigit() else spec_id


def _compare_ability(spell_id, assignments_by_spec, spec_ids):
    per_spec = {}
    names = []
    for spec_id in spec_ids:
        ability = assignments_by_spec[spec_id].get(spell_id)
        per_spec[spec_id] = ability["bindings"] if ability else []
        if ability and ability.get("name"):
            names.append(ability["name"])

    present = [bindings for bindings in per_spec.values() if bindings]
    binding_values = {
        item["binding"]
        for bindings in present
        for item in bindings
    }
    if len(present) < len(spec_ids):
        status = "missing"
    elif len(binding_values) > 1:
        status = "changed"
    else:
        status = "exact_match"
    return {
        "spell_id": int(spell_id) if spell_id.isdigit() else spell_id,
        "name": names[0] if names else None,
        "bindings_by_spec": per_spec,
        "status": status,
    }


def compare_specs(specs):
    """Compare normalized specs keyed by Blizzard specialization ID."""
    normalized_specs = {
        str(spec_id): spec
        for spec_id, spec in (specs or {}).items()
        if isinstance(spec, dict)
    }
    ability_ids = set()
    assignments_by_spec = {}
    for spec_id, spec in normalized_specs.items():
        assignments_by_spec[spec_id] = _spell_assignments(spec)
        ability_ids.update(assignments_by_spec[spec_id])

    spec_ids = sorted(normalized_specs, key=_spec_sort_key)
    abilities = [
        _compare_ability(spell_id, assignments_by_spec, spec_ids)
        for spell_id in sorted(ability_ids, key=_spell_sort_key)
    ]

    return {
        "spec_ids": spec_ids,
        "abilities": abilities,
    }


def shared_spell_consistency(specs):
    """Return only spells present in more than one spec, with their comparison status."""
    comparison = compare_specs(specs)
    spec_count = len(comparison["spec_ids"])
    return {
        **comparison,
        "abilities": [
            ability for ability in comparison["abilities"]
            if sum(bool(bindings) for bindings in ability["bindings_by_spec"].values()) > 1
        ],
        "spec_count": spec_count,
    }