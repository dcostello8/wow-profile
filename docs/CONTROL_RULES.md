# Control Rules

## Purpose

This document defines the durable configuration model for:

1. functional ability classification
2. cross-character control comparison
3. user-defined binding conventions
4. binding audits

It is introduced by Phase 3 of `docs/CLIENT_CONFIGURATION_IMPLEMENTATION.md`.

Before modifying control-role or binding-rule behavior, read:

- `AGENTS.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_LOG.md`
- `docs/CLIENT_CONFIGURATION_IMPLEMENTATION.md`
- this file

The project must distinguish between:

```text
What the ability does
```

and:

```text
Where the user expects that function to be bound
```

These are separate configuration concepts.

---

# Core Model

The intended flow is:

```text
normalized local configuration
        ↓
Blizzard spell ID
        ↓
functional role classification
        ↓
actual character/spec assignment
        ↓
optional expected binding rule
        ↓
audit result
```

The addon does not contain this policy.

The UI does not independently derive this policy.

Python analysis and configuration files are authoritative.

---

# Ability Roles

Functional roles describe gameplay purpose.

Examples:

```text
interrupt
self_heal
offensive_cooldown
defensive_cooldown
resurrection
combat_resurrection
dispel
movement
crowd_control
major_healing_cooldown
```

Role names should:

- use lowercase snake_case
- describe gameplay function
- avoid class-specific wording
- remain stable after introduction where practical

Do not create separate role names merely because different classes use different spell names.

---

# Ability Role File

File:

```text
data/ability_roles.yaml
```

Recommended initial schema:

```yaml
version: 1

abilities:
  57994:
    name: Wind Shear
    roles:
      - interrupt
```

## Canonical Identity

The YAML key is the Blizzard spell ID.

Example:

```yaml
57994:
```

is authoritative.

The `name` field is only:

- human-readable documentation
- debugging context
- maintenance convenience

Do not use the `name` field for runtime identity.

Do not infer role membership from `name`.

## Multiple Roles

One Blizzard spell may support multiple functional roles.

Example schema:

```yaml
abilities:
  123456:
    name: Example Ability
    roles:
      - defensive_cooldown
      - movement
```

Analysis code must support a list of roles.

## Unknown Abilities

Unknown/unmapped spells are valid.

Do not:

- fail imports
- guess from spell names
- automatically assign categories based on heuristics

Unmapped abilities remain unclassified.

They may still appear in the normal Bindings UI.

## Curated Data

`ability_roles.yaml` is intentionally curated.

Do not attempt to populate every World of Warcraft ability before the feature is useful.

Prefer adding mappings as relevant characters/specs are encountered.

Only commit role mappings that have been intentionally verified.

---

# Initial Role Vocabulary

## interrupt

Stops enemy spellcasting.

## self_heal

A direct or primary self-healing control relevant to normal gameplay.

Do not automatically classify every healing spell as `self_heal`.

## offensive_cooldown

A meaningful offensive burst cooldown.

## defensive_cooldown

A meaningful defensive/survival cooldown.

## resurrection

A normal out-of-combat resurrection ability.

## combat_resurrection

An ability that resurrects during combat.

Do not combine normal and combat resurrection unless a rule intentionally targets both.

## dispel

A friendly or hostile dispel/cleanse control when useful for binding consistency.

More specific roles may be added later if needed.

## movement

A deliberate mobility control.

## crowd_control

A significant crowd-control ability.

This may later split into more specific categories if useful.

## major_healing_cooldown

A significant healer cooldown used as a major throughput or survival tool.

---

# Control Analysis

Recommended module:

```text
src/control_analysis.py
```

Responsibilities:

- load and validate `data/ability_roles.yaml`
- classify normalized assignments by spell ID
- preserve character identity
- preserve Blizzard specialization ID
- preserve spell ID
- preserve ability name for display
- preserve binding source
- preserve normalized binding
- aggregate results across active characters/specs
- preserve unknown abilities without classification

This module must consume normalized configuration.

It must not parse Lua SavedVariables.

---

# Binding Assignment Identity

A binding assignment is not just a string.

At minimum, assignment identity is:

```text
source + binding
```

Examples:

```text
source: key
binding: ALT-2
```

```text
source: click
binding: Shift + Left Click
```

These are different assignment types even if text happens to look similar.

---

# Source Values

Use normalized source values:

```text
key
click
```

Additional source values may be added later only if the application starts auditing another input mechanism.

Do not use arbitrary display strings as source identifiers.

Action-bar-only classified abilities may be preserved with source `action_bar` and no binding. They are useful diagnostics for an ability that exists in the captured action bar but is not actually bound to a key or click. Audits treat that case as `MISSING`; it must not be converted into a guessed key binding.

---

# Binding Normalization

Expected binding rules must use the same normalized representation used by actual client configuration.

Examples:

```text
ALT-2
CTRL-5
SHIFT-1
Left Click
Shift + Left Click
Mouse Button 4
```

Before implementing the rule loader, document and test the exact canonical normalization produced by the existing importer/presentation layer.

Do not create one binding normalization convention for actual data and another for expected rules.

If canonicalization changes, provide compatibility or migration where practical.

---

# Cross-Character Controls

Phase 3 should aggregate actual assignments by role.

Example output model:

```json
{
  "role": "interrupt",
  "assignments": [
    {
      "character": "Example",
      "character_id": 123,
      "spec_id": 263,
      "spec_name": "Enhancement",
      "spell_id": 57994,
      "ability": "Wind Shear",
      "source": "key",
      "binding": "ALT-2"
    }
  ]
}
```

Exact field names may follow existing project conventions.

The important requirement is preserving stable IDs and source semantics.

---

# Binding Rules

Binding rules describe user intent.

File:

```text
data/binding_rules.yaml
```

Recommended initial schema:

```yaml
version: 1

rules:
  interrupt:
    expected:
      source: key
      binding: ALT-2
    scope: {}
```

The role name must correspond to a functional role from `ability_roles.yaml`.

---

# Rule Semantics

The rule:

```yaml
interrupt:
  expected:
    source: key
    binding: ALT-2
```

means:

> When an applicable character/spec has an ability classified as `interrupt`, the expected assignment is a key binding of `ALT-2`.

The audit must compare actual normalized assignment identity against the expected normalized assignment identity.

Rule loading validates the schema version, role names, expected source, and non-empty expected binding. The optional `scope` mapping is preserved for future class, specialization, spec-role, or character-specific constraints; it is not applied until a concrete scoped rule is needed.

To add or change a rule, edit `data/binding_rules.yaml` and use a confirmed role from `data/ability_roles.yaml`. Do not derive a convention from current character data.

Audit source values are `key` and `click`, and expected bindings use the same normalized forms as actual presentation data, such as `ALT-2` and `Shift + Left Click`.

---

# Scoping

The rule schema should remain extensible toward optional scope fields.

Potential future examples:

```yaml
rules:
  self_heal:
    expected:
      source: key
      binding: ALT-5
    scope:
      spec_roles:
        - dps
```

or:

```yaml
rules:
  resurrection:
    expected:
      source: click
      binding: Mouse Button 4
    scope:
      class_ids:
        - 2
        - 7
        - 10
```

Do not implement all possible scopes up front.

Only add scope types when the user has a concrete rule that needs them.

---

# Precedence

If rule overrides are later introduced, precedence must be explicit.

Recommended future precedence:

```text
character/spec override
    >
spec/class override
    >
role default
```

Do not implement implicit or order-dependent precedence.

---

# Audit Results

Recommended statuses:

```text
PASS
MISMATCH
MISSING
NOT_APPLICABLE
```

`WARNING` is reserved and is not currently emitted.

## PASS

The applicable functional role exists and at least one actual assignment matches the expected assignment according to the rule's defined semantics.

If multiple bindings exist, the exact policy must be defined.

Recommended initial behavior:

- PASS if expected assignment exists
- preserve additional actual assignments for display
- do not silently discard extras

A future stricter rule may require exact-set equality.

## MISMATCH

The applicable role exists, actual assignment data exists, but the expected assignment is absent.

Example:

```text
Actual: Ctrl-2
Expected: Alt-2
```

## MISSING

The ability/role is applicable and available, but no captured assignment exists.

Do not use `MISSING` merely because the class/spec does not have the role.

## NOT_APPLICABLE

The rule does not apply to this character/spec.

Examples:

- class/spec has no classified ability for the role
- explicit scope excludes it

`NOT_APPLICABLE` is not an error.

---

# Multiple Abilities For One Role

A spec may have multiple abilities classified with the same role.

Example:

```text
defensive_cooldown
```

may have several abilities.

Initial audit behavior must be explicit.

Recommended approach:

- retain every classified ability
- evaluate every actual assignment
- PASS the role if the expected assignment appears among applicable assignments
- expose all abilities in detail output

Do not arbitrarily choose the first spell ID.

Later rule syntax may allow `primary`, `any`, or `all` semantics if needed.

---

# Multiple Assignments For One Ability

A spell may be assigned to more than one key/click.

Preserve all assignments.

Do not flatten:

```text
1
ALT-1
```

into an arbitrary single value.

Audit code should compare assignment sets or membership according to the rule definition.

---

# Missing Capture Data

Distinguish:

```text
ability not applicable
```

from:

```text
client data not captured
```

from:

```text
ability exists but no binding found
```

Do not report false `MISSING` results when the entire local capture is absent.

The UI should show a separate unavailable/not-captured state when appropriate.

---

# UI Requirements

## Account-Level Controls

Account Summary may show:

```text
Controls
```

Example summary:

```text
Role                 Binding Consistency
----------------------------------------
Interrupt            Consistent
Self Heal            Mixed
Defensive Cooldown   Mixed
```

A detail modal can show:

```text
Character | Spec | Ability | Binding | Source
```

This view describes actual state only.

## Audit Summary

After rules exist:

```text
Role                 Pass    Issues
------------------------------------
Interrupt              6       1
Self Heal              4       2
Defensive Cooldown     5       0
```

Detailed results should show:

```text
Character
Spec
Ability
Actual
Expected
Status
```

## Per-Character Bindings

The character Bindings modal may show applicable audit results.

Do not duplicate calculations in JavaScript.

The Python-generated analysis is authoritative.

---

# Configuration Ownership

## Addon

Captures actual WoW client state.

Does not know:

- functional roles
- expected controls
- audit policy

## `ability_roles.yaml`

Defines:

```text
What does this spell do?
```

## `binding_rules.yaml`

Defines:

```text
Where should this function be bound?
```

## Python Analysis

Combines actual state with configured meaning/policy.

## UI

Displays results.

Does not invent role mappings or audit conclusions.

---

# Data Validation

Role/rule configuration loaders should fail with actionable errors for:

- malformed YAML
- invalid top-level shape
- invalid spell ID key
- missing `roles`
- invalid role value type
- invalid binding source
- malformed expected binding
- unknown rule role when strict validation is enabled

Do not fail because an ability is simply unknown/unmapped.

---

# Testing Requirements

Tests should not require:

- WoW running
- Battle.net credentials
- network access

Use normalized fixtures.

Cover:

- valid role config
- malformed role config
- one role
- multiple roles
- unknown spell
- key source preservation
- click source preservation
- multiple assignments
- role aggregation
- valid binding rules
- malformed binding rules
- PASS
- MISMATCH
- MISSING
- NOT_APPLICABLE
- missing local capture
- account summary aggregation

---

# Maintenance Workflow

When adding a new role mapping:

1. Verify Blizzard spell ID.
2. Add/update `data/ability_roles.yaml`.
3. Include human-readable spell name.
4. Add appropriate role(s).
5. Add/update tests if the role introduces new behavior.
6. Do not modify Python simply to add another ordinary spell mapping.

When changing a preferred binding:

1. Update `data/binding_rules.yaml`.
2. Run tests.
3. Refresh/import local data as needed.
4. Review audit output.
5. Do not modify audit Python merely to change a personal preference.

---

# Initial File Status

These files are introduced during later implementation phases:

```text
data/ability_roles.yaml
data/binding_rules.yaml
src/control_analysis.py
src/binding_audit.py
```

Do not create empty runtime files solely for appearance if the corresponding phase has not started.

This document may exist before those implementation files.

---

# Design Rule Summary

Keep these rules durable:

1. Blizzard spell ID is canonical.
2. Ability names are display/documentation only.
3. Functional roles and expected bindings are separate concepts.
4. Actual binding identity includes source plus normalized binding.
5. Unknown abilities are allowed.
6. Role data is curated, not inferred from names.
7. Personal binding preferences belong in YAML, not Python.
8. Python performs analysis; JavaScript only presents results.
9. Missing client capture is different from missing ability binding.
10. Do not add speculative rule complexity before it is needed.
