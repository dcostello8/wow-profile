"""Normalize and compare account mount and Battle Pet collections."""


FACTION_ALLIANCE = "Alliance"
FACTION_HORDE = "Horde"
FACTION_NEUTRAL = "Neutral"
DEFAULT_MOUNT_FACTIONS = (FACTION_ALLIANCE, FACTION_NEUTRAL)


def _records(source, collection_key):
    if isinstance(source, dict):
        source = source.get(collection_key) or []
    if not isinstance(source, list):
        return []
    return [record for record in source if isinstance(record, dict)]


def _nested_record(record, keys):
    for key in keys:
        nested = record.get(key)
        if isinstance(nested, dict):
            return nested
    return {}


def _value(record, nested, key):
    value = record.get(key)
    if value is not None:
        return value
    return nested.get(key)


def _record_id(record, nested):
    value = _value(record, nested, "id")
    if value is not None:
        return value
    key = nested.get("key") or record.get("key")
    if isinstance(key, dict):
        return key.get("id")
    return None


def _faction_value(value):
    if isinstance(value, dict):
        value = value.get("name") or value.get("type")
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold().replace("_", " ")
    if normalized == "alliance":
        return FACTION_ALLIANCE
    if normalized == "horde":
        return FACTION_HORDE
    if normalized == "neutral":
        return FACTION_NEUTRAL
    return value


def _faction(record, nested):
    for source in (record, nested):
        if "faction" in source:
            return _faction_value(source.get("faction"))
    return None


def _normalize_record(record, nested_keys):
    nested = _nested_record(record, nested_keys)
    normalized = {"raw": record}
    record_id = _record_id(record, nested)
    name = _value(record, nested, "name")
    faction = _faction(record, nested)
    if record_id is not None:
        normalized["id"] = record_id
    if name is not None:
        normalized["name"] = name
    if faction is not None:
        normalized["faction"] = faction
    return normalized


def normalize_owned_mounts(source):
    return [
        _normalize_record(record, ("mount",))
        for record in _records(source, "mounts")
    ]


def normalize_mount_catalog(source):
    return [
        _normalize_record(record, ("mount",))
        for record in _records(source, "mounts")
    ]


def normalize_owned_pets(source):
    return [
        _normalize_record(record, ("pet", "species"))
        for record in _records(source, "pets")
    ]


def normalize_pet_catalog(source):
    return [
        _normalize_record(record, ("pet", "species"))
        for record in _records(source, "pets")
    ]


def filter_by_faction(records, factions=DEFAULT_MOUNT_FACTIONS):
    allowed = {_faction_value(faction) for faction in factions}
    known = {FACTION_ALLIANCE, FACTION_HORDE, FACTION_NEUTRAL}
    return [
        record
        for record in records
        if (
            record.get("faction") is None
            or record.get("faction") not in known
            or record.get("faction") in allowed
        )
    ]


def calculate_owned_missing(owned, catalog, factions=None):
    filtered_owned = filter_by_faction(owned, factions) if factions else list(owned)
    filtered_catalog = filter_by_faction(catalog, factions) if factions else list(catalog)
    catalog_ids = {
        record.get("id")
        for record in filtered_catalog
        if record.get("id") is not None
    }
    owned_ids = {
        record.get("id")
        for record in filtered_owned
        if record.get("id") is not None
    }
    missing = [record for record in filtered_catalog if record.get("id") not in owned_ids]
    unknown_owned = [
        record
        for record in filtered_owned
        if record.get("id") is None or record.get("id") not in catalog_ids
    ]
    return {
        "owned": filtered_owned,
        "missing": missing,
        "catalog": filtered_catalog,
        "unknown_owned": unknown_owned,
    }


def calculate_mounts(owned_source, catalog_source, factions=None):
    return calculate_owned_missing(
        normalize_owned_mounts(owned_source),
        normalize_mount_catalog(catalog_source),
        factions,
    )


def calculate_pets(owned_source, catalog_source, factions=None):
    return calculate_owned_missing(
        normalize_owned_pets(owned_source),
        normalize_pet_catalog(catalog_source),
        factions,
    )