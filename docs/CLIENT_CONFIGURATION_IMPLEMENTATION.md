# Client Configuration Implementation

## Purpose

This document is the durable implementation plan for making practical use of the local World of Warcraft client configuration already captured by `WowProfileCollector`.

Before implementing any phase, read:

- `AGENTS.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_LOG.md`
- this file

Treat those files as authoritative for project architecture, coding style, testing, Git practices, security, local-only scope, and current project state.

The implementation should proceed in small tested phases. Do not redesign the addon or SavedVariables schema unless an actual defect requires it.

---

# Current Foundation

## WoW Addon

`addon/WowProfileCollector/WowProfileCollector.lua`

SavedVariables schema version 2 captures specialization-specific client data including:

- click-cast bindings
- normal keybindings
- action-bar slot mappings
- resolved action-bar actions
- macros
- specialization metadata
- capture timestamp
- spec item level

The addon stores data under:

```text
C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\<account>\SavedVariables\WowProfileCollector.lua
```

The addon remains responsible only for collecting client-only information that cannot be reliably obtained through Battle.net APIs.

Do not move analysis or user binding rules into the addon.

## Python Import And Normalization

`src/local_wow.py` already:

- parses `WowProfileCollectorDB`
- validates supported SavedVariables schema versions
- normalizes click bindings
- normalizes modifier information
- normalizes keybindings
- resolves action-bar action information
- normalizes macro metadata
- merges local data into generated character JSON
- preserves specialization-specific data
- generates `client_configuration`

A normalized specialization includes data conceptually like:

```json
{
  "spec_id": 263,
  "spec_name": "Enhancement",
  "captured_at": "...",
  "client_configuration": {
    "click_bindings": [],
    "key_bindings": [],
    "action_bars": [],
    "macros": []
  }
}
```

The existing compatibility fields should remain unless there is a deliberate migration plan.

## Existing Configuration Analysis

`src/config_analysis.py` already provides:

- presentation-ready keybinding rows
- presentation-ready click-cast rows
- cross-spec comparison by Blizzard spell ID
- shared-spell consistency information

Imported character data may contain:

```text
local_client_data
  specs
    <spec_id>
      configuration_presentation
  configuration_comparison
  shared_spell_consistency
```

This existing foundation must be reused rather than rebuilt.

---

# Design Principles

## Blizzard IDs Are Canonical

Use Blizzard IDs wherever possible.

Preferred identities:

- Character: region + Blizzard character ID when available
- Specialization: Blizzard specialization ID
- Spell: Blizzard spell ID
- Item: Blizzard item ID

Names are for display and documentation.

Do not use display names as canonical identifiers when Blizzard IDs are available.

## Keep Layers Separate

The intended pipeline is:

```text
WoW addon
   ↓
SavedVariables
   ↓
src/local_wow.py
   ↓
normalized client configuration
   ↓
analysis modules
   ↓
generated character JSON
   ↓
Account Summary UI
```

Do not make HTML/JavaScript parse SavedVariables.

Do not make the addon contain personal binding policy.

Do not make rendering code perform domain analysis that belongs in Python.

## Local-Only Scope

The project remains local-only.

Do not implement:

- DreamHost deployment
- AWS deployment
- Azure deployment
- public hosting
- SFTP publishing
- public profile sharing
- hosted authentication

Generated output remains local under `output/`.

---

# Phase 1 — Bindings UI

## Goal
## Phase 1 Status
Implemented in the Account Summary:
- Active-character `Bindings` action using the existing row-menu/template-modal pattern.
- Character-specific Bindings modal with specialization tabs keyed by Blizzard specialization ID.
- Capture timestamps rendered through the existing browser local-time convention.
- Keybinding rows from `configuration_presentation.key_bindings` with Binding, Action, Type, and Slot columns.
- Click-cast rows from `configuration_presentation.click_bindings` with Binding and Action columns.
- Macro names used as presentation labels when available through normalized presentation data.
- Display-only mouse names such as `LeftButton` and `Button4` normalized without changing raw data.
- Graceful empty states for missing local data, missing specs, and specs without bindings.

The existing normalized IDs remain in generated JSON. No addon or SavedVariables schema changes were needed.

Expose the client configuration already being captured and normalized.

Add a `Bindings` action to the existing active-character ellipsis menu.

Reuse the current Account Summary modal/template infrastructure used by features such as:

- Equipment Sets
- Professions
- Collections
- Hunter Pets

Do not create an unrelated UI pattern.

## Character Menu

Each active character should support:

```text
...
Refresh
Equipment Sets
Professions
Bindings
```

Existing class-specific actions such as `Hunter Pets` remain independent.

## Bindings Modal

The modal title should be:

```text
<Character Name> Bindings
```

When multiple specializations have captured local data, provide a simple specialization selector or tab control.

Underlying identity must use specialization ID.

Visible labels should use specialization names.

Example:

```text
[ Elemental ] [ Enhancement ] [ Restoration ]
```

## Capture Metadata

For the selected specialization, display:

```text
Captured: <captured_at>
```

Use the existing browser/local-time rendering convention.

Do not convert or rewrite stored timestamps solely for display.

## Keybindings View

Use existing presentation-ready data where practical:

```text
local_client_data.specs.<spec_id>.configuration_presentation.key_bindings
```

Display:

```text
Binding | Action | Type | Slot
```

Example:

```text
Alt-2 | Wind Shear | Spell | 26
```

The normal user-facing view should not expose Blizzard IDs unless required for troubleshooting.

Keep IDs in the generated JSON.

### Action labels

Prefer:

1. spell name
2. item name
3. macro name
4. useful normalized action label

For macro-backed bindings, show the macro name instead of an opaque macro ID.

## Click Casts View

Use:

```text
local_client_data.specs.<spec_id>.configuration_presentation.click_bindings
```

Display:

```text
Binding | Action
```

Example:

```text
Shift + Left Click | Chain Heal
```

Use normalized presentation values.

If display-only mouse naming still uses raw WoW button values, normalize only the presentation layer:

```text
LeftButton   -> Left Click
MiddleButton -> Middle Click
RightButton  -> Right Click
Button4      -> Mouse Button 4
Button5      -> Mouse Button 5
```

Preserve the underlying raw captured value.

## Empty States

Render gracefully when:

- no `local_client_data`
- no captured specs
- selected spec has no keybindings
- selected spec has no click casts
- old schema data lacks newer normalized fields

Examples:

```text
No local binding data captured for this character.
```

```text
No click-cast bindings captured for Enhancement.
```

Do not throw exceptions for missing local data.

## Phase 1 Scope Exclusions

Do not implement in Phase 1:

- functional ability roles
- personal expected binding rules
- cross-character audits
- configuration history
- profession specialization capture
- hosting

Do not rewrite existing comparison logic in this phase unless a blocking defect is found.

## Phase 1 Tests

Add or update tests for:

- Bindings menu action
- Bindings modal/template output
- multiple captured specializations
- keybinding table rows
- click-cast table rows
- macro labels
- capture timestamp
- missing local-data state
- mouse-button display normalization if changed
- regression coverage for Equipment Sets
- regression coverage for Professions
- regression coverage for Collections
- regression coverage for Hunter Pets

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

---

# Phase 2 — Compare Specs

## Goal

Allow the user to compare equivalent literal Blizzard spells across multiple specializations of the same character.

Before exposing comparison prominently, correct comparison semantics where necessary.

## Assignment Identity

A binding assignment must include both:

```text
source + binding
```

Examples:

```text
("key", "ALT-2")
("click", "Shift + Left Click")
```

Key and click assignments are not interchangeable.

## Comparison Semantics

For a given Blizzard spell ID, build the complete assignment set for each specialization.

Example:

```text
Enhancement:
  {("key", "1"), ("key", "ALT-1")}

Elemental:
  {("key", "1"), ("key", "ALT-1")}
```

This must be:

```text
exact_match
```

even though more than one unique binding exists globally.

### exact_match

All compared specs contain the spell and all complete assignment sets are equal.

### changed

All compared specs contain the spell but assignment sets differ.

### missing

At least one compared spec has no assignment for the spell.

Do not compare only a union of binding strings.

Do not compare only display names.

Use Blizzard spell ID as identity.

## Compare Specs UI

Extend the Bindings modal with:

```text
Compare Specs
```

Use:

```text
local_client_data.shared_spell_consistency
```

for the default comparison.

Do not flood the default view with spec-unique rotational abilities.

Example:

```text
Ability          Elemental       Enhancement      Restoration      Status
-------------------------------------------------------------------------------
Wind Shear       Alt-2           Alt-2            Alt-2            Match
Earth Shield     Shift-Middle    Shift-Middle     Shift-Middle     Match
Healing Surge    Left Click      Left Click       —                Missing
```

If multiple assignments exist for one spell/spec, render them clearly in the same cell.

Preserve Key versus Click semantics.

## Phase 2 Tests

Cover:

- identical single assignment
- changed assignment
- missing assignment
- identical multiple assignments
- same binding text with different source
- multiple key/click assignments
- Compare Specs UI exists
- exact-match rendering
- changed rendering
- missing rendering
- specialization names as visible headers
- empty comparison state

Run the full test suite.

---

# Phase 3 — Functional Ability Roles

## Goal

Compare equivalent gameplay functions across different classes and different spell IDs.

Example:

```text
Wind Shear
Rebuke
Pummel
Spear Hand Strike
```

can all map to:

```text
interrupt
```

This phase answers:

> How do I currently have equivalent functions bound across my characters?

It does not yet judge whether those bindings match the user's preferred convention.

## New Files

Create:

```text
data/ability_roles.yaml
src/control_analysis.py
docs/CONTROL_RULES.md
```

`docs/CONTROL_RULES.md` defines the durable schema and maintenance rules.

## Ability Role Data

Use a curated configuration file.

Conceptual schema:

```yaml
abilities:
  57994:
    name: Wind Shear
    roles:
      - interrupt
```

Rules:

- Spell ID is authoritative.
- Name is documentation only.
- One ability may have multiple roles.
- Unknown abilities are valid and remain unclassified.
- Do not infer roles from spell names.
- Do not attempt a complete WoW spell-role database in the first implementation.

Initial useful role vocabulary may include:

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

Only seed mappings that are intentionally verified.

## Control Analysis

`src/control_analysis.py` should:

- load and validate `data/ability_roles.yaml`
- classify normalized spell assignments
- work from normalized `local_client_data`
- preserve character identity
- preserve spec ID
- preserve spell ID
- preserve binding source
- support multiple assignments
- preserve unknown/unmapped spells
- aggregate across active character documents

Do not parse SavedVariables in this module.

## Cross-Character View

Produce data suitable for:

```text
Role       Character   Spec          Ability             Binding
----------------------------------------------------------------------
Interrupt  Thaigan     Enhancement   Wind Shear          Alt-2
Interrupt  ...         Retribution   Rebuke              Alt-2
Interrupt  ...         Fury          Pummel              Alt-2
```

Do not hard-code character names.

## Controls UI

Add a small Account Summary section:

```text
Controls
```

Initial summary should show configured functional roles and whether current active-character bindings are consistent.

Provide a View action/modal using the existing template/modal conventions.

Detail columns:

```text
Character | Spec | Ability | Binding | Source
```

Do not add expected/preferred binding rules in Phase 3.

## Phase 3 Tests

Cover:

- valid role file loading
- malformed role file
- spell ID classification
- multiple roles
- unknown spell behavior
- key/click source preservation
- cross-character aggregation
- same role with different spell IDs
- Controls summary rendering
- empty role state

No live Blizzard or WoW dependency.

---

# Phase 4 — Binding Rules And Audit

## Goal

Compare the user's actual bindings against user-defined conventions.

This phase answers:

> Is this character/spec using the control layout I intend?

Personal preferences must be configuration, not hard-coded Python behavior.

## New Data File

Create:

```text
data/binding_rules.yaml
```

Initial conceptual schema:

```yaml
rules:
  interrupt:
    expected:
      source: key
      binding: ALT-2
```

The schema should remain extensible toward optional scoping such as:

- class ID
- specialization ID
- gameplay spec role
- character-specific override
- key versus click source

Do not implement speculative complexity before it is needed.

## Audit Module

Prefer:

```text
src/binding_audit.py
```

if audit logic would make `control_analysis.py` too broad.

Recommended statuses:

```text
PASS
MISMATCH
MISSING
NOT_APPLICABLE
```

Only add `WARNING` if it has a distinct defined meaning.

## Audit Behavior

For each applicable functional role:

1. identify classified abilities
2. identify actual normalized assignments
3. compare actual source/binding to expected rule
4. preserve character/spec/spell IDs
5. avoid guessing when data is absent

Example:

```text
PASS
Wind Shear -> Alt-2
Expected -> Alt-2
```

```text
MISMATCH
Pummel -> Ctrl-2
Expected -> Alt-2
```

## Audit UI

Extend the existing Controls and/or Bindings UI.

Account-level summary example:

```text
Role                 Pass    Issues
------------------------------------
Interrupt              6       1
Self Heal              4       2
Defensive Cooldown     5       0
```

Detailed view should identify affected:

- character
- spec
- ability
- actual binding
- expected binding
- result

Per-character Bindings modal may also expose audit results.

Do not duplicate audit calculations in JavaScript.

Python analysis remains authoritative.

## Initial Rule Set

Only seed rules that have been intentionally confirmed.

It is acceptable for the first committed `binding_rules.yaml` to contain only a small set.

The framework matters more than immediately encoding every personal convention.

## Phase 4 Tests

Cover:

- rule loading
- malformed rule data
- PASS
- MISMATCH
- MISSING
- NOT_APPLICABLE
- key versus click mismatch
- multiple actual bindings
- unknown roles
- account-level audit aggregation
- per-character audit rendering

Run the full suite.

---

# Phase 5 — Configuration Fingerprints And History

## Goal

Track meaningful client configuration changes over time without storing duplicate snapshots every capture.

Do not begin this phase until Phases 1 through 4 are stable and useful.

## Fingerprints

Build fingerprints from normalized configuration.

Include meaningful:

- keybindings
- click bindings
- resolved actions

Exclude volatile metadata:

- capture timestamp
- import timestamp
- ordering artifacts

Canonicalize ordering before hashing.

Equivalent configuration must produce the same fingerprint regardless of input ordering.

## History Behavior

When a new capture is imported:

```text
new fingerprint == current fingerprint
    → do not create history record
```

```text
new fingerprint != current fingerprint
    → record meaningful prior/current change
```

Do not store unlimited duplicate history.

Define a reasonable retention policy.

Keep history separate from current-state configuration.

History belongs in ignored/generated local storage, not `characters.yaml`.

## History UI

Only after persistence and diff logic are tested, add a:

```text
Changes
```

view to the Bindings modal.

Show meaningful differences.

Example:

```text
Restoration

Before
Shift + Middle -> Earth Shield

After
Shift + Middle -> Spirit Link Totem
```

Do not expose raw JSON diffs as the primary UI.

## Phase 5 Tests

Cover:

- deterministic fingerprints
- ordering independence
- timestamps excluded
- unchanged capture produces no history entry
- changed binding produces history
- changed action produces history
- retention behavior
- human-readable difference rendering

---

# Implementation Order

Implement and validate one phase at a time:

1. Bindings UI
2. Compare Specs correctness and UI
3. Functional ability roles and cross-character Controls
4. Configurable binding rules and audit
5. Optional configuration fingerprint/history

After every phase:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Update:

- `docs/CLIENT_CONFIGURATION_IMPLEMENTATION.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_LOG.md`

Update `AGENTS.md` only when a durable architecture or development rule changes.

Do not proceed to unrelated refactors.

---

# Phase Completion Checklist

For each phase, record:

- implementation date
- Git commit
- files changed
- functionality added
- test count/result
- known limitations
- next phase

Suggested status block:

```text
## Phase Status

- Phase 1 — Pending
- Phase 2 — Pending
- Phase 3 — Pending
- Phase 4 — Pending
- Phase 5 — Pending
```

---

# Current Phase Status

- Phase 1 — Pending
- Phase 2 — Pending
- Phase 3 — Pending
- Phase 4 — Pending
- Phase 5 — Pending
