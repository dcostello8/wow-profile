# Development Log

## Current Thread Summary

This Codex thread moved the project beyond the original discovery-only milestone. The project now has active character profile updates, local addon capture/import, generated HTML reports, a local roster UI, startup refresh behavior, and tests for the new behavior.

Current branch:

```text
main
```

Last committed baseline observed at the time of this documentation update:

```text
cb9cad3 Simplify account summary status area
```

There are uncommitted changes after that commit implementing stale-character behavior and moving account-specific roster state out of source control.

## Features Implemented

### Blizzard/API Workflow

- Implemented `update` flow for active characters using Blizzard public character profile endpoints.
- Default update sections are profile, equipment, specializations, professions, and mythic plus.
- Generated one JSON file per character under `output/characters/`.
- Generated `output/roster.json`.
- Preserved existing `local_client_data` across public API updates.
- Successful discovery now preserves characters absent from Blizzard's roster as stale historical entries, forces them inactive, and excludes stale entries from update selection.
- Runtime `characters.yaml` is now ignored by Git, with sanitized `characters.example.yaml` tracked as the source-control template.
- Added per-character update progress output:

```text
Updating [3/13] Thaigan - Windrunner...
```

- Added public profile unavailability handling:
  - Section failures now include `status_code`.
  - If the `profile` section returns HTTP `403` or `404`, the character is set inactive in `characters.yaml`.
  - Refreshes now write `deactivated_count` and `deactivated_characters` into `output/roster.json` for report/UI visibility.
- Added Phase 1 Blizzard API architecture:
  - `src/blizzard/client.py` centralizes API host, auth header, namespace, locale, timeout, response validation, and a conservative `429` retry.
  - `src/blizzard/profile/character.py` owns character Profile API endpoints.
  - `src/blizzard/profile/account.py` owns authenticated account Profile API endpoints.
  - `src/blizzard_api.py` remains as a compatibility facade for existing CLI/UI callers.
- Expanded default character update sections to include `statistics`, `media`, `reputations`, and `titles` in addition to existing profile, equipment, specializations, professions, and Mythic+.

### WoW Addon

Added `addon/WowProfileCollector/` with:

- `WowProfileCollector.toc`
- `WowProfileCollector.lua`
- `README.md`

The addon captures local in-game data on login, logout, specialization changes, equipment swap finished, equipment set changes, and manual `/wowprofile capture`.

The addon captures character/realm/class/spec metadata, timestamps, click bindings, keybindings, action bars, spec item level, and equipment sets with per-set iLevel where available.

Important bug fixed:

- Lua treats `0` as truthy, so spec ID validation must explicitly check `specID == 0`.
- The addon now avoids processing/storing spec ID `0` buckets and retries while waiting for valid spec data.

### Local SavedVariables Import

Added `src/local_wow.py`.

Capabilities:

- Parses `WowProfileCollectorDB` from Lua SavedVariables without adding external parser dependencies.
- Normalizes local spec captures.
- Normalizes click bindings and key bindings.
- Imports local spec and equipment set data into generated character JSON under `local_client_data`.
- Ignores invalid spec key `0` and the character-level `equipment_sets` key while processing specs.
- Merges specs with existing local data and replaces equipment sets with the latest imported equipment-set list.

Added CLI command:

```powershell
.\.venv\Scripts\python.exe wow_profile.py import-local --saved-variables "<path>"
```

### Game Data / Reference APIs

Added reusable Game Data service modules and JSON cache infrastructure:

- `src/blizzard/cache.py`
- `src/blizzard/game_data/classes.py`
- `src/blizzard/game_data/talents.py`
- `src/blizzard/game_data/spells.py`
- `src/blizzard/game_data/items.py`
- `src/blizzard/game_data/professions.py`
- `src/blizzard/game_data/mythic_plus.py`
- `src/blizzard/game_data/journal.py`
- `src/blizzard/game_data/realms.py`

Game Data services use `static-{region}` namespaces and cache object lookups beneath ignored `output/cache/blizzard/`. Search-style methods are available but not cached by default.

### HTML Reports

Converted generated report files from Markdown to self-contained HTML while keeping existing function names for compatibility:

- `output/roster.html`
- `output/fullroster.html`
- `output/account_summary.html`

Implemented Account Summary features:

- Low-prominence top stat row with only Characters Discovered, Active, and Realms.
- Quiet local-time timestamp metadata formatted as `YYYY-MM-DD hh:mm:ss AM/PM TZ`.
- `Active Characters` table.
- Refresh button next to the `Active Characters` title, using the local command/status endpoints from the Account Summary page.
- Faction column in Active Characters.
- Text, realm, faction, and class filters for Active Characters.
- Sortable character/realm/faction/level/class/spec/iLevel columns.
- Expandable active character rows.
- Per-character expanded details:
  - Spec Details.
  - Equipment Sets.
  - Collapsible Expansion Skill Levels.
- Equipment Sets table was refined to show only Set, Assigned Spec, iLevel, and Equipped.
- Expansion Skill Levels were moved under each active character, below Equipment Sets.
- Expansion details are collapsible by profession.
- Expansion rows render as individual rows and are sorted newest-to-oldest, with Midnight first and Classic last.
- `Active Class Coverage`.
- `Active Profession Coverage`, rolled up by realm.
- `Recent Inactive Changes` when the latest refresh set characters inactive due to public profile `403` or `404`.
- `Roster By Realm`, which now starts as a collapsed realm/server list and shows character Active switches when a realm is expanded.
- Discover button next to the `Roster By Realm` title, using the local command/status endpoints from the Account Summary page.
- Account Summary activation now fetches Battle.net character data before writing `enabled: true`; failed profile fetches leave the character inactive and show the error in a status window.
- Account Summary excludes stale characters from current discovered-character/realm counts and from `Roster By Realm`, while preserving historical generated JSON and local addon data under `output/`.

Bug fixed:

- Nested profession rows were being moved into the main Active Characters table by filter/sort JavaScript. Fixed by selecting only direct child character rows:

```js
#enabled-character-body > tr.expandable-row
```

Bug fixed:

- Active sections were initially built from all generated character documents. They now filter generated documents against the active state in `characters.yaml`, so inactive characters such as Absecon do not appear in Active Characters, Active Class Coverage, or Active Profession Coverage.

### Roster UI

Added `src/roster_ui.py`.

Serves:

- `/` Account Summary, now the primary local control surface.
- `/roster-ui` legacy roster editor, retained temporarily while remaining unique controls are moved or retired.
- `/api/characters`
- `/api/characters/enabled`
- `/api/characters/enabled-all`
- `/api/discover`
- `/api/discover/status`
- `/api/update`
- `/api/update/status`

UI capabilities:

- Shows discovered roster.
- Search/filter by realm/state.
- Sort by character and realm.
- Toggle Active/Inactive state for individual characters.
- Activate/deactivate visible characters.
- Run discovery.
- Run refresh/update.
- Status popup for command progress with running/success/failed indicator, progress bar, current/total character counter, current character label, and recent output.
- Status popup and inline status call out characters set inactive during refresh because public profiles are unavailable.
- Roster changes made through Account Summary switches regenerate the local summary before the page reloads.
- Account Summary switch activation uses a status window while the single-character profile update runs.
- Account Summary Refresh and Discover buttons open modal status windows immediately, poll command progress/output, refresh the generated summary, and delay reload briefly after success so the modal state is visible.
- Account Summary now shows a clear local-API message if opened directly from `output/account_summary.html` instead of through `wow_profile.py roster-ui`.
- Account Summary no longer renders header navigation buttons, including the redundant Account Summary self-link and the legacy `/roster-ui` link.

Startup behavior:

- `wow_profile.py roster-ui` imports the latest Retail `WowProfileCollector.lua` if found.
- It refreshes local summary data.
- It starts the server.
- The server starts a discovery check first, refreshes the generated Account Summary after successful discovery, opens the Account Summary page, then starts the same profile refresh that the Refresh button runs.

Batch helpers added:

- `start-roster-ui.bat`
- `stop-roster-ui.bat`

### Naming/Labels

Changed user-facing terminology from Enabled/Disabled to Active/Inactive:

- `Enabled Characters` -> `Active Characters`
- `Enabled` stat/column -> `Active`
- `Disabled` filter label -> `Inactive`
- `Enable Visible` -> `Activate Visible`
- `Disable Visible` -> `Deactivate Visible`
- `Class Coverage` -> `Active Class Coverage`
- `Profession Coverage` -> `Active Profession Coverage`

Internal config still uses `enabled` to avoid changing the YAML schema.

## Files Added

- `addon/WowProfileCollector/README.md`
- `addon/WowProfileCollector/WowProfileCollector.lua`
- `addon/WowProfileCollector/WowProfileCollector.toc`
- `characters.example.yaml`
- `src/local_wow.py`
- `src/blizzard/__init__.py`
- `src/blizzard/client.py`
- `src/blizzard/cache.py`
- `src/blizzard/profile/__init__.py`
- `src/blizzard/profile/account.py`
- `src/blizzard/profile/character.py`
- `src/blizzard/game_data/__init__.py`
- `src/blizzard/game_data/base.py`
- `src/blizzard/game_data/classes.py`
- `src/blizzard/game_data/items.py`
- `src/blizzard/game_data/journal.py`
- `src/blizzard/game_data/mythic_plus.py`
- `src/blizzard/game_data/professions.py`
- `src/blizzard/game_data/realms.py`
- `src/blizzard/game_data/spells.py`
- `src/blizzard/game_data/talents.py`
- `src/roster_ui.py`
- `start-roster-ui.bat`
- `stop-roster-ui.bat`
- `tests/fixtures/WowProfileCollector.lua`
- `tests/test_blizzard_api.py`
- `tests/test_cli.py`
- `tests/test_blizzard_client.py`
- `tests/test_local_wow.py`
- `tests/test_output.py`
- `tests/test_roster_ui.py`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_LOG.md`

## Files Substantially Changed

- `AGENTS.md`: updated durable project instructions to match the current architecture and workflow.
- `characters.yaml`: no longer tracked; local runtime roster state remains on disk and is ignored.
- `src/blizzard_api.py`: public profile section status codes are captured.
- `src/config.py`: default active update sections now include statistics, media, reputations, and titles.
- `src/cli.py`: update, summary, fullroster, import-local, roster-ui startup workflow, and inactive handling.
- `src/output.py`: HTML report rendering and Account Summary behavior.
- `src/roster_ui.py`: local server, UI, popup status, startup refresh.

## Important Technical Decisions

- Keep local `characters.yaml` as the editable runtime source of truth, track only `characters.example.yaml`, and keep generated data under ignored `output/`.
- Use `enabled` internally for compatibility but display `Active` to the user.
- Preserve local addon data across public API updates.
- Store equipment sets at the character level because they may not be tied to specs.
- Use standard-library HTTP server for the local UI rather than adding a web framework.
- Use a small local Lua parser for SavedVariables instead of adding a dependency.
- Use explicit namespace handling in `src/blizzard/`: `profile-{region}` for Profile APIs and `static-{region}` for Game Data APIs.
- Cache static/reference Game Data object lookups under ignored `output/cache/blizzard/`.
- Automatically mark characters inactive only when the public `profile` endpoint returns HTTP `403` or `404`.
- Do not commit `output/`, `.env`, `.venv/`, or caches.

## Tests Added Or Changed

Current test command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Test coverage now includes:

- SavedVariables parsing and local import.
- Local data merge into generated character JSON.
- Equipment set summary and details rendering.
- Spec detail rendering.
- Account Summary active-only filtering.
- Account Summary local-time Last Update markup.
- Active/Inactive user-facing labels.
- Profession coverage rollups.
- Collapsible profession expansion skill details.
- Expansion release-order sorting.
- Roster UI state changes and command progress parsing.
- Roster UI parsing of refresh-driven inactive changes.
- Account Summary rendering of refresh-driven inactive changes.
- Account Summary Roster By Realm active switches.
- Guarded Account Summary activation that does not make a character active when Battle.net profile data cannot be fetched.
- Blizzard client namespace, URL, auth header, and timeout construction.
- Character Profile API service routing for statistics, media, reputations, and titles.
- Game Data spell, item, profession lookup routing with static namespaces.
- JSON cache reuse for reference data.
- Expanded Phase 1 default update sections.
- Startup refresh behavior.
- Blizzard section `status_code` capture.
- Public profile unavailable detection and deactivation.
- Discovery stale-character merge behavior.
- Update selection excludes stale characters.
- Account Summary current roster counts and Roster By Realm exclude stale characters.

Most recent validation:

```text
Ran 54 tests in 0.612s
OK
```

## Validation Performed

During the thread:

- Repeatedly ran the unit test suite after changes.
- Regenerated `output/account_summary.html` with `wow_profile.py summary`.
- Started/restarted the local roster UI on `127.0.0.1:8765`.
- Verified `/` and `/roster-ui` returned HTTP 200.
- Verified UI/report content with `Invoke-WebRequest` and `rg`.
- Imported live Retail `WowProfileCollector.lua`.
- Confirmed Jaedon local equipment sets were recorded in SavedVariables, imported into JSON, and rendered on Account Summary.
- Confirmed Absecon public profile was HTTP 404 and should be inactive.
- Confirmed Absecon is excluded from Active Characters after the active-document filtering fix.

## Current Git State

Current branch:

```text
main
```

Last pushed commit noted at the start of this continuation:

```text
cb9cad3 Simplify account summary status area
```

Working tree after this continuation has uncommitted changes:

- `docs/DEVELOPMENT_LOG.md`
- `docs/PROJECT_CONTEXT.md`
- `AGENTS.md`
- `.gitignore`
- `characters.example.yaml`
- `characters.yaml` removed from Git tracking while preserved locally
- `src/cli.py`
- `src/config.py`
- `src/output.py`
- `src/roster_ui.py`
- `tests/test_config.py`
- `tests/test_output.py`
- `tests/test_roster_ui.py`

Ignored local files remain:

- `.env`
- `.venv/`
- `__pycache__/`
- `output/`

## Known Issues And Incomplete Work

- `roster-ui` startup intentionally runs live discovery and profile refresh work, which can modify `characters.yaml` by setting absent characters stale/inactive and public-profile 403/404 characters inactive.
- SavedVariables import matches local addon data by name and realm, not Blizzard character ID.
- Generated output is ignored by Git and must be regenerated locally.
- Some character JSON files may exist for inactive characters; active sections must filter them against `characters.yaml`.
- Live API validation requires local Blizzard credentials in `.env`.

## Next Logical Development Step

Continue moving any remaining useful `/roster-ui` controls into Account Summary, then retire or redirect the legacy roster editor page. Optionally run a live `wow_profile.py update`/`roster-ui` smoke test with local Blizzard credentials, then commit and push if the behavior is accepted.

After that, the next useful product step is to enrich generated character documents with selected cached reference data, starting with item/spell/profession IDs already present in profile and local addon data.

## Phase 1 Client Configuration Continuation

The local client model was extended without changing the existing import shape:

- The addon now writes SavedVariables schema version 2 and captures explicit macro metadata per specialization.
- The Python importer validates supported schema versions and rejects unsupported versions clearly.
- Click bindings now include structured modifier flags and display-ready binding text.
- Key bindings preserve the command-to-action-slot relationship while adding display keys, normalized action records, and macro bodies when available.
- Action bars and macros are normalized into a specialization-level `client_configuration` view.

Validation completed:

```text
Ran 11 tests in 0.011s
OK
```

Known limitations remain: no live WoW Lua execution test harness, no profession specialization capture, no ID-based local character matching, and no comparison/audit/history layer. The next logical implementation step is Phase 2 presentation and cross-spec comparison, beginning with tests over normalized configuration data.

## Phase 2: Configuration Presentation And Comparison

Implemented `src/config_analysis.py` as a Python-only analysis layer over normalized local configuration:

- Produces presentation-ready key-binding and click-binding rows with action labels and source metadata.
- Compares specs by Blizzard spell ID rather than display name.
- Reports `exact_match`, `changed`, and `missing` assignments.
- Filters shared-spell consistency results to abilities present in more than one spec.
- Persists per-spec presentation data and character-level comparison results during local SavedVariables import.

Validation completed:

```text
Ran 15 tests in 0.011s
OK
```

Known limitation: equivalent functions with different spell IDs are not compared yet. The next phase should add configurable functional-role classification before cross-character audits.

## Single-Character Refresh

Added an ellipsis actions menu to each Active Characters row. Its Refresh action imports the newest addon SavedVariables, fetches all configured sections for only that active character, writes the character document, refreshes the summary, and reloads the page. The endpoint has independent background status so the existing main refresh workflow remains unchanged.

Validation includes active-only guards, import-before-refresh ordering, menu rendering, and packaged-worker compatibility.

The same active-row menu now includes Equipment Sets. Existing equipment-set details are rendered into a character-specific modal template instead of the expanded row, keeping the row details focused on specs and expansion skills. Rendering tests cover the menu action and modal shell.
