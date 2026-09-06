# Collections Implementation

## Start Here

Before coding, read:

- `AGENTS.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_LOG.md`

Treat those files as authoritative for architecture, coding style, testing, Git practices, security, and current project state. Do not restate or redesign existing conventions unless required.

## Goal

Extend `wow-profile` to support:

1. Account/Warband mount collection.
2. Account/Warband companion pet collection.
3. Character-specific Hunter stable pets for Hunter characters, initially including `Kurjath-Windrunner`.
4. Later: owned-vs-missing account collection views and character-specific Hunter tame wishlists.

UI ownership must match data ownership:

- **Mounts and Battle Pets** are account/Warband-wide and belong in the Account Summary `Collections` UI.
- **Hunter Pets** are character-specific and belong in each Hunter character's own actions/details UI. Do not show Hunter stable data as an account-wide collection.

Use Blizzard APIs. Do **not** modify `WowProfileCollector` SavedVariables for this feature.

---

# Phase 1 — Account Collections

Existing service methods already exist in:

`src/blizzard/profile/account.py`

- `get_mounts()`
- `get_pets()`

They use:

- `/profile/user/wow/collections/mounts`
- `/profile/user/wow/collections/pets`

## Implement

During the existing OAuth `discover` flow:

1. Fetch account profile as today.
2. Fetch mounts and pets using the same user OAuth token.
3. Write:

```text
output/account_collections.json
```

Suggested structure:

```json
{
  "retrieved_at": "...",
  "mounts": {"status": "updated", "data": {}},
  "pets": {"status": "updated", "data": {}}
}
```

For failures, preserve status/error/status_code.

Collection failures must **not** fail roster discovery.

Prefer adding small facade functions to `src/blizzard_api.py` rather than constructing services directly in `cli.py`.

## Tests

Add mocked tests for:

- mount endpoint routing
- pet endpoint routing
- discovery writes `account_collections.json`
- mount failure does not fail discovery
- pet failure does not fail discovery

No live Blizzard credentials in unit tests.

---

# Phase 2 — Hunter Pets

The Character Profile API mapping already contains:

```python
"hunter_pets": "hunter-pets"
```

Endpoint:

```text
/profile/wow/character/{realmSlug}/{characterName}/hunter-pets
```

## Implement

Add `hunter_pets` as a supported character update section in `src/config.py`.

Default:

```python
hunter_pets = False
```

Do not enable it for all classes.

Initially enable it locally for Kurjath via ignored `characters.yaml`:

```yaml
update:
  hunter_pets: true
```

Do not hard-code Kurjath in Python or tracked example config.

The normal character JSON should store the response under:

```text
sections.hunter_pets
```

and use the existing `section_status` mechanism.

## Tests

Add tests for:

- `hunter_pets` is a supported section
- default is disabled
- per-character override enables it
- endpoint routing works
- section status is preserved

---

# Phase 3 — Automatic Hunter Detection

Avoid requiring manual overrides for every Hunter.

## Implement

During discovery, preserve:

```yaml
class_id: 3
class_name: Hunter
```

in `characters.yaml`.

Update effective section selection so Hunters automatically enable `hunter_pets`.

Prefer `class_id == 3` over name matching.

Preserve existing:

- `enabled`
- per-character `update` overrides
- stale-character behavior

Explicit user overrides should remain authoritative where practical.

## Tests

Add tests for:

- class metadata survives discovery/merge
- Hunter auto-enables `hunter_pets`
- non-Hunter does not
- existing config values survive rediscovery

---

# Phase 4 — Full Mount/Pet Catalogs

Add Game Data services:

```text
src/blizzard/game_data/mounts.py
src/blizzard/game_data/pets.py
```

Endpoints:

```text
/data/wow/mount/index
/data/wow/mount/{id}
/data/wow/pet/index
/data/wow/pet/{id}
```

Use existing `static-{region}` namespace and existing cache under:

```text
output/cache/blizzard/
```

Do not refetch cached detail objects unnecessarily.

## Tests

Cover:

- mount index/detail routes
- pet index/detail routes
- cache reuse

---

# Phase 5 — Owned vs Missing

Create `src/collections.py` only when this phase starts.

Responsibilities:

- normalize owned mounts/pets
- normalize static catalogs
- calculate owned/missing
- preserve unknown values rather than guessing
- support faction filtering from explicit Blizzard data

For Kurjath-focused mount views, default to:

- Alliance
- Neutral

Do not delete Horde-only records from underlying data.

Keep comparison logic out of `src/output.py`.

## Tests

Cover:

- owned mount matching
- missing mount calculation
- owned pet matching
- missing pet calculation
- Alliance/Neutral filtering
- unknown faction preservation

---

# Phase 6 — Collections And Hunter UI

Keep account-wide and character-specific data separate in the UI.

## Account Summary — Collections

Add a `Collections` section to the existing Account Summary containing only account/Warband collections.

Initial display:

```text
Collections
  Mounts: <owned> collected / <missing> missing
  Battle Pets: <owned> collected / <missing> missing
```

Later filters may include:

- owned/missing
- search
- faction
- source
- expansion if available

Do **not** show Hunter stable pets in the account-wide `Collections` section.

## Hunter Character UI

Add **Hunter Pets** to the existing `...` actions menu for Hunter characters only.

Requirements:

- Show the menu item only when the character is a Hunter (`class_id == 3`).
- Label the menu item **Hunter Pets** rather than `Pets` to avoid confusion with account-wide Battle Pets.
- Clicking **Hunter Pets** opens a character-specific modal using the existing modal/action-menu UI pattern.
- The modal reads only that character's:

```text
sections.hunter_pets
```

Example:

```text
Kurjath - Windrunner
  ...
  Refresh
  Equipment Sets
  Professions
  Hunter Pets
```

Non-Hunter characters must not show the **Hunter Pets** menu item.

If multiple Hunters are active, each Hunter gets its own independent Hunter Pets menu item and modal. Do not aggregate their stables into an account-wide Hunter collection.

Render gracefully when Hunter pet data is absent, disabled, or failed.

Do not add a new web framework.

---

# Later — Hunter Wishlist / Farming Planner

Hunter wishlists remain character-specific, just like Hunter stable data.

Blizzard does not provide complete Petopia-style tame/spawn metadata or detailed farming routes.

Keep curated planner data separate from raw Blizzard data.

Possible files:

```text
data/hunter_tame_targets.yaml
data/collection_targets.yaml
```

Do not scrape Wowhead or Petopia as part of the initial implementation.

---

# Implementation Order

Implement and validate one phase at a time:

1. Account mount/pet retrieval.
2. Hunter pet section.
3. Automatic Hunter detection.
4. Static catalogs.
5. Owned/missing calculations.
6. Account Collections UI + character-specific Hunter Pets UI.
7. Wishlist/routes later.

Run after each phase:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Do not proceed with unrelated refactors.

Update `docs/PROJECT_CONTEXT.md` and `docs/DEVELOPMENT_LOG.md` after each completed phase. Update `AGENTS.md` only for durable project rules or architecture changes.

---

# Recommended First Codex Task

Implement **Phase 1 only**.

Before editing, inspect the current implementations of:

- `src/blizzard/profile/account.py`
- `src/blizzard_api.py`
- `src/cli.py`
- relevant tests

Then make the smallest change that:

- fetches mounts/pets during `discover`
- writes `output/account_collections.json`
- isolates collection failures from roster discovery
- adds unit tests
- updates project docs

Stop after Phase 1 is tested and documented.
