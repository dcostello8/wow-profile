import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config_analysis import compare_specs, presentation_data, shared_spell_consistency
from .config import load_character_roster
from .output import character_output_path, write_json


SAVED_VARIABLE_NAME = "WowProfileCollectorDB"
SUPPORTED_SCHEMA_VERSIONS = {1, 2}


class LuaParseError(RuntimeError):
    pass


@dataclass
class LocalImportResult:
    matched: int
    missing_output: int
    unmatched: int


TOKEN_RE = re.compile(
    r"""
    (?P<space>\s+)
    |(?P<comment>--[^\n]*)
    |(?P<brace>[{}\[\]=,])
    |(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
    |(?P<number>-?\d+(?:\.\d+)?)
    |(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


class LuaTokenizer:
    def __init__(self, text: str):
        self.tokens = []
        position = 0
        while position < len(text):
            match = TOKEN_RE.match(text, position)
            if not match:
                raise LuaParseError(f"Unexpected Lua token near offset {position}.")
            position = match.end()
            kind = match.lastgroup
            value = match.group()
            if kind not in {"space", "comment"}:
                self.tokens.append((kind, value))
        self.index = 0

    def peek(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self, expected=None):
        token = self.peek()
        if token is None:
            raise LuaParseError("Unexpected end of Lua input.")
        if expected is not None and token[1] != expected:
            raise LuaParseError(f"Expected {expected!r}, found {token[1]!r}.")
        self.index += 1
        return token


def parse_saved_variables(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"\b{SAVED_VARIABLE_NAME}\b\s*=", text)
    if not match:
        raise LuaParseError(f"{path} does not assign {SAVED_VARIABLE_NAME}.")

    tokenizer = LuaTokenizer(text[match.end():])
    saved_variables = parse_value(tokenizer)
    if not isinstance(saved_variables, dict):
        raise LuaParseError(f"{SAVED_VARIABLE_NAME} must be a Lua table.")
    schema_version = saved_variables.get("schema_version")
    if schema_version is not None and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise LuaParseError(
            f"Unsupported {SAVED_VARIABLE_NAME} schema version {schema_version!r}; "
            f"supported versions are {sorted(SUPPORTED_SCHEMA_VERSIONS)}."
        )
    return saved_variables


def parse_value(tokenizer: LuaTokenizer):
    token = tokenizer.peek()
    if token is None:
        raise LuaParseError("Expected Lua value.")
    kind, value = token

    if value == "{":
        return parse_table(tokenizer)
    if kind == "string":
        tokenizer.pop()
        return json.loads(value) if value.startswith('"') else value[1:-1]
    if kind == "number":
        tokenizer.pop()
        return float(value) if "." in value else int(value)
    if kind == "identifier":
        tokenizer.pop()
        if value == "true":
            return True
        if value == "false":
            return False
        if value == "nil":
            return None
        return value
    raise LuaParseError(f"Expected Lua value, found {value!r}.")


def parse_table(tokenizer: LuaTokenizer):
    tokenizer.pop("{")
    array_items = []
    keyed_items = {}

    while tokenizer.peek() and tokenizer.peek()[1] != "}":
        key = None
        explicit_key = False
        token = tokenizer.peek()

        if token[1] == "[":
            tokenizer.pop("[")
            key = parse_value(tokenizer)
            tokenizer.pop("]")
            tokenizer.pop("=")
            explicit_key = True
        elif token[0] == "identifier":
            next_token = tokenizer.tokens[tokenizer.index + 1] if tokenizer.index + 1 < len(tokenizer.tokens) else None
            if next_token and next_token[1] == "=":
                key = tokenizer.pop()[1]
                tokenizer.pop("=")
                explicit_key = True

        value = parse_value(tokenizer)
        if explicit_key:
            keyed_items[str(key)] = value
        else:
            array_items.append(value)

        if tokenizer.peek() and tokenizer.peek()[1] == ",":
            tokenizer.pop(",")

    tokenizer.pop("}")
    if keyed_items:
        for index, value in enumerate(array_items, start=1):
            keyed_items[str(index)] = value
        return keyed_items
    return array_items


def modifier_list(binding):
    modifiers = binding.get("modifiers")
    if isinstance(modifiers, list):
        return modifiers
    mask = int(binding.get("modifiers_mask") or binding.get("modifiers") or 0)
    result = []
    if mask & 1:
        result.append("SHIFT")
    if mask & 2:
        result.append("CTRL")
    if mask & 4:
        result.append("ALT")
    return result


def modifier_flags(modifiers):
    names = {str(modifier).upper() for modifier in modifiers}
    return {
        "shift": "SHIFT" in names,
        "ctrl": "CTRL" in names,
        "alt": "ALT" in names,
    }


def display_binding(key, modifiers=None):
    modifier_names = [name.title() for name in (modifiers or [])]
    if not key:
        return " + ".join(modifier_names)
    return " + ".join([*modifier_names, str(key)])


def normalize_action(action):
    if not isinstance(action, dict):
        return None

    spell = action.get("spell") if isinstance(action.get("spell"), dict) else {}
    item = action.get("item") if isinstance(action.get("item"), dict) else {}
    macro = action.get("macro") if isinstance(action.get("macro"), dict) else {}
    normalized = {
        "slot": action.get("slot"),
        "type": action.get("type"),
        "id": action.get("id"),
        "sub_type": action.get("sub_type"),
        "text": action.get("text"),
    }
    if spell:
        normalized["spell"] = {
            "id": spell.get("id"),
            "name": spell.get("name"),
            "icon": spell.get("icon"),
        }
    if item:
        normalized["item"] = {
            "id": item.get("id"),
            "name": item.get("name"),
        }
    if macro:
        normalized["macro"] = {
            "id": macro.get("id"),
            "name": macro.get("name"),
            "icon": macro.get("icon"),
            "body": macro.get("body"),
        }
    return normalized


def normalize_click_binding(binding):
    spell = binding.get("spell") if isinstance(binding.get("spell"), dict) else {}
    modifiers = modifier_list(binding)
    button = binding.get("button")
    return {
        "action": binding.get("action") or spell.get("name"),
        "type": binding.get("type"),
        "action_type": binding.get("type"),
        "spell_id": binding.get("spell_id") or spell.get("id"),
        "spell_name": spell.get("name"),
        "button": button,
        "modifiers": modifiers,
        "modifier_flags": modifier_flags(modifiers),
        "display_binding": display_binding(button, modifiers),
    }


def normalize_key_binding(binding):
    action = binding.get("action") if isinstance(binding.get("action"), dict) else {}
    spell = action.get("spell") if isinstance(action.get("spell"), dict) else {}
    item = action.get("item") if isinstance(action.get("item"), dict) else {}
    macro = action.get("macro") if isinstance(action.get("macro"), dict) else {}
    keys = binding.get("keys") or []
    normalized_action = normalize_action(action)

    return {
        "keys": keys,
        "display_keys": [display_binding(key) for key in keys],
        "command": binding.get("command"),
        "category": binding.get("category"),
        "action_bar_slot": binding.get("action_bar_slot"),
        "action_type": action.get("type"),
        "action_sub_type": action.get("sub_type"),
        "spell_id": spell.get("id") or (action.get("id") if action.get("type") == "spell" else None),
        "spell_name": spell.get("name"),
        "item_id": item.get("id") or (action.get("id") if action.get("type") == "item" else None),
        "item_name": item.get("name"),
        "macro_id": macro.get("id") or (action.get("id") if action.get("type") == "macro" else None),
        "macro_name": macro.get("name"),
        "macro_body": macro.get("body"),
        "action": normalized_action,
    }


def normalize_macro(macro):
    if not isinstance(macro, dict):
        return None
    return {
        "id": macro.get("id"),
        "name": macro.get("name"),
        "icon": macro.get("icon"),
        "body": macro.get("body"),
    }


def normalize_action_bar(action):
    return normalize_action(action)


def normalize_spec_capture(capture):
    click_bindings = [
        normalize_click_binding(binding)
        for binding in capture.get("click_bindings", [])
        if isinstance(binding, dict)
    ]
    key_bindings = [
        normalize_key_binding(binding)
        for binding in capture.get("key_bindings", [])
        if isinstance(binding, dict)
    ]
    action_bars = [
        normalize_action_bar(action)
        for action in capture.get("action_bars", [])
        if isinstance(action, dict)
    ]
    macros = [
        normalize_macro(macro)
        for macro in capture.get("macros", [])
        if isinstance(macro, dict)
    ]
    configuration = {
        "click_bindings": click_bindings,
        "key_bindings": key_bindings,
        "action_bars": action_bars,
        "macros": macros,
    }
    return {
        "captured_at": capture.get("captured_at"),
        "character": capture.get("character"),
        "realm": capture.get("realm"),
        "class": capture.get("class"),
        "class_file": capture.get("class_file"),
        "spec_id": capture.get("spec_id"),
        "spec_name": capture.get("spec_name"),
        "item_level": capture.get("item_level"),
        "click_bindings": click_bindings,
        "key_bindings": key_bindings,
        "action_bars": action_bars,
        "macros": macros,
        "client_configuration": configuration,
    }


def normalized_characters(saved_variables):
    characters = []
    for realm, realm_data in (saved_variables.get("characters") or {}).items():
        if not isinstance(realm_data, dict):
            continue
        for name, specs in realm_data.items():
            if not isinstance(specs, dict):
                continue
            normalized_specs = {}
            equipment_sets = specs.get("equipment_sets") if isinstance(specs.get("equipment_sets"), list) else []
            for spec_key, capture in specs.items():
                if str(spec_key) in {"0", "equipment_sets"}:
                    continue
                if isinstance(capture, dict):
                    normalized_specs[str(spec_key)] = normalize_spec_capture(capture)
            characters.append({
                "name": name,
                "realm": realm,
                "specs": normalized_specs,
                "equipment_sets": equipment_sets,
            })
    return characters


def character_match_key(name, realm):
    return (name or "").casefold(), (realm or "").casefold()


def merge_local_character_data(document, local_character, imported_at):
    client_data = document.get("local_client_data") or {}
    existing_specs = client_data.get("specs") or {}
    merged_specs = dict(existing_specs)
    merged_specs.update(local_character.get("specs") or {})
    for spec in merged_specs.values():
        if isinstance(spec, dict):
            spec["configuration_presentation"] = presentation_data(spec)

    document["local_client_data"] = {
        "source": "WowProfileCollector SavedVariables",
        "imported_at": imported_at,
        "character": {
            "name": local_character.get("name"),
            "realm": local_character.get("realm"),
        },
        "specs": merged_specs,
        "configuration_comparison": compare_specs(merged_specs),
        "shared_spell_consistency": shared_spell_consistency(merged_specs),
        "equipment_sets": local_character.get("equipment_sets") or [],
    }
    return document


def import_saved_variables(saved_variables_path: Path):
    roster, characters = load_character_roster()
    del roster

    saved_variables = parse_saved_variables(saved_variables_path)
    local_by_key = {
        character_match_key(character.get("name"), character.get("realm")): character
        for character in normalized_characters(saved_variables)
    }
    imported_at = datetime.now(timezone.utc).isoformat()
    matched = 0
    missing_output = 0

    for character in characters:
        local_character = local_by_key.get(character_match_key(character.get("name"), character.get("realm")))
        if not local_character:
            continue

        output_path = character_output_path(character)
        if not output_path.exists():
            missing_output += 1
            continue

        document = json.loads(output_path.read_text(encoding="utf-8"))
        write_json(output_path, merge_local_character_data(document, local_character, imported_at))
        matched += 1

    return LocalImportResult(
        matched=matched,
        missing_output=missing_output,
        unmatched=max(0, len(local_by_key) - matched - missing_output),
    )
