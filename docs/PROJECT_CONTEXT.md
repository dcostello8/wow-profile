# Project Context

## Current Scope

`wow-profile` is a Windows-focused local utility for maintaining a World of Warcraft account roster and producing local reports from two data sources:

- Blizzard Battle.net APIs for account discovery and public character profile data.
- A local WoW Retail addon, `WowProfileCollector`, for in-game data that Blizzard's public profile API does not expose cleanly.

The project is local-first. `characters.yaml` is human-editable configuration and `output/` contains generated reports/data that are ignored by Git.

The UI uses the word `Active` for characters selected for updates. Internally this is stored as `enabled: true` in `characters.yaml`.

## Current Commands

Run from `C:\github\wow-profile`.

```powershell
.\.venv\Scripts\python.exe wow_profile.py discover
.\.venv\Scripts\python.exe wow_profile.py update
.\.venv\Scripts\python.exe wow_profile.py summary
.\.venv\Scripts\python.exe wow_profile.py fullroster
.\.venv\Scripts\python.exe wow_profile.py import-local --saved-variables "C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\<account>\SavedVariables\WowProfileCollector.lua"
.\.venv\Scripts\python.exe wow_profile.py roster-ui
```

Batch helpers:

```bat
start-roster-ui.bat
stop-roster-ui.bat
```

## Architecture

Top-level entry point:

- `wow_profile.py`: imports and runs `src.cli.main()`.

Python modules:

- `src/cli.py`: command routing and orchestration for discovery, updates, imports, summaries, full roster, and roster UI startup.
- `src/config.py`: `.env` loading, roster YAML parsing, character merge rules, active-character filtering, and per-character update settings.
- `src/oauth.py`: Blizzard OAuth Authorization Code flow, browser launch, localhost callback, state validation, and token exchange.
- `src/blizzard/`: reusable Battle.net API client, explicit namespace handling, profile services, game-data services, and JSON cache helpers.
- `src/blizzard_api.py`: backward-compatible facade over `src/blizzard/` for endpoint mapping, per-section fetches, and HTTP error summaries/status codes.
- `src/local_wow.py`: lightweight Lua SavedVariables parser, local addon data normalization, and merge into generated character JSON.
- `src/output.py`: JSON writers and self-contained HTML report generation.
- `src/roster_ui.py`: local `ThreadingHTTPServer`, roster editor page, command status/progress endpoints, and startup refresh behavior.

Addon:

- `addon/WowProfileCollector/WowProfileCollector.lua`
- `addon/WowProfileCollector/WowProfileCollector.toc`
- `addon/WowProfileCollector/README.md`

## Data Sources And Integrations

### Blizzard OAuth

`.env` contains:

```dotenv
BLIZZARD_CLIENT_ID=...
BLIZZARD_CLIENT_SECRET=...
BLIZZARD_REDIRECT_URI=http://localhost:8000/callback
BLIZZARD_REGION=us
```

`discover` uses OAuth Authorization Code flow with `wow.profile` and calls the account profile endpoint.

### Blizzard Public Profile API

`update` uses client credentials and fetches these sections for active characters by default:

- `profile`
- `equipment`
- `specializations`
- `statistics`
- `professions`
- `mythic_plus`
- `media`
- `reputations`
- `titles`

Per-section failures are retained in `section_status`. HTTP failures include `status_code`. If the `profile` section returns `403` or `404`, the character is marked inactive in `characters.yaml`.

The reusable Blizzard client applies explicit namespaces per service:

- Profile services use `profile-{region}`.
- Game Data services use `static-{region}`.

Account profile discovery remains a user OAuth flow. Public character profile updates and static Game Data lookups use client credentials.

Implemented Profile API service methods:

- `/profile/user/wow`
- `/profile/user/wow/collections`
- `/profile/user/wow/collections/mounts`
- `/profile/user/wow/collections/pets`
- `/profile/wow/character/{realmSlug}/{characterName}`
- `/equipment`
- `/specializations`
- `/statistics`
- `/professions`
- `/mythic-keystone-profile`
- `/mythic-keystone-profile/season/{seasonId}`
- `/character-media`
- `/reputations`
- `/titles`

Designed but not enabled by default: achievements, achievement statistics, appearance, collections, encounters, dungeon encounters, raid encounters, hunter pets, PvP summary/brackets, quests, completed quests, and soulbinds.

Implemented Game Data service methods cover playable classes, talents, PvP talents, talent trees, spells, items, professions/recipes, Mythic+ dungeons/periods/seasons/affixes, journal expansions/instances/encounters, realms, connected realms, and regions.

### WoW Addon SavedVariables

The addon stores data in:

```text
C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\<account>\SavedVariables\WowProfileCollector.lua
```

`import-local` parses the `WowProfileCollectorDB` Lua table and merges matched character data into generated JSON files. Matching is by character name and realm, case-insensitive.

`roster-ui` startup automatically finds the newest Retail `WowProfileCollector.lua`, imports it, refreshes local summary data, starts the server, and starts a public profile refresh.

## Character Configuration

`characters.yaml` is the configuration source of truth.

Representative shape:

```yaml
defaults:
  update:
    profile: true
    equipment: true
    specializations: true
    professions: true
    mythic_plus: true

characters:
  - key: us:id:170301178
    name: Jaedon
    enabled: true
    region: us
    id: 170301178
    realm: Windrunner
    realm_id: 87
    realm_slug: windrunner
    stale: false
    wow_account_id: 3845173
    protected_character_href: https://...
```

Important rules:

- `enabled: true` means Active in the UI.
- Newly discovered characters default to inactive (`enabled: false`).
- Rediscovery preserves existing active/inactive settings and update overrides.
- Characters missing from a discovery response are preserved and marked stale.
- Generated Blizzard/profile data must not be written into `characters.yaml`.

## Generated Data

`output/` is ignored by Git.

Current generated structure:

```text
output/
  roster.json
  roster.html
  fullroster.html
  account_summary.html
  cache/
    blizzard/
  characters/
    <name>-<realm_slug>-<id>.json
```

Generated character JSON contains:

```json
{
  "retrieved_at": "...",
  "source": "Battle.net World of Warcraft Profile API",
  "character": {},
  "update_settings": {},
  "sections": {},
  "section_status": {},
  "local_client_data": {}
}
```

`output/roster.json` also records refresh side effects when an update marks characters inactive because their public profile returned HTTP `403` or `404`:

```json
{
  "deactivated_count": 1,
  "deactivated_characters": [
    {
      "name": "Absecon",
      "realm": "Darrowmere",
      "status_code": 404,
      "reason": "public profile unavailable"
    }
  ]
}
```

`local_client_data` is preserved across `update` calls and contains addon-imported data:

```json
{
  "source": "WowProfileCollector SavedVariables",
  "imported_at": "...",
  "character": {},
  "specs": {
    "70": {
      "captured_at": "...",
      "spec_id": 70,
      "spec_name": "Retribution",
      "item_level": {},
      "click_bindings": [],
      "key_bindings": [],
      "action_bars": []
    }
  },
  "equipment_sets": [
    {
      "name": "Retribution",
      "assigned_spec_name": "Retribution",
      "item_level": {
        "equipped": 295.5,
        "counted_slots": 15,
        "expected_slots": 15,
        "slots": []
      }
    }
  ]
}
```

## Reports And UI

### Account Summary

Served as `/` by `roster-ui` and generated at `output/account_summary.html`.

Current behavior:

- Shows top-level roster/update stats.
- Last Update is a quiet metadata line and is formatted in the browser's local timezone.
- `Active Characters` only includes characters currently active in `characters.yaml`.
- Active character rows include Faction.
- Active character rows can be filtered by text, realm, faction, and class.
- Active character rows can be sorted by character, realm, faction, level, class, active spec, and iLevel.
- Expanding an active character shows Spec Details, Equipment Sets, and Expansion Skill Levels.
- Expansion Skill Levels are collapsible by profession.
- Individual expansion rows are sorted newest to oldest: Midnight first, Classic last.
- `Active Class Coverage` and `Active Profession Coverage` are based only on active generated character documents.
- Recent refresh-driven inactive changes are shown when the latest `output/roster.json` includes `deactivated_characters`.
- `Roster By Realm` starts as a collapsed realm/server list; expanding a realm shows its characters and Active switches when served through the local Account Summary server.
- `Roster By Realm` has a Discover button beside the section title; it opens a modal status window, starts discovery, polls status, refreshes the generated summary, then reloads after a short success message.
- `Active Characters` has a Refresh button beside the section title; it opens a modal status window, starts the active-character update, polls status/progress, refreshes the generated summary, then reloads after a short success message.
- Account Summary command buttons and Active switches require the page to be served by `wow_profile.py roster-ui`; if opened directly from `output/account_summary.html`, the page shows a status-window message explaining that the local API is unavailable.
- Turning a Roster By Realm switch on first fetches Battle.net character data. If the public profile fetch fails, the character remains inactive and the status window shows the error.
- Turning a Roster By Realm switch off immediately writes `enabled: false`, refreshes the generated summary, shows a modal status window, and reloads after a short success message.

### Roster UI

Transitional legacy page served at `/roster-ui`. The product direction is to make Account Summary the primary control surface and remove this separate page once any remaining useful controls are moved or retired.

Capabilities:

- View discovered characters.
- Filter by search, realm, state.
- Sort by character or realm.
- Toggle characters active/inactive.
- Activate/deactivate all currently visible characters.
- Run discovery.
- Run refresh/update.
- Display command status in a popup with progress indicator, current/total character counter, current character label, and recent command output.
- Display characters set inactive during a refresh because public profiles are unavailable.

The server starts a profile refresh immediately when `roster-ui` starts. The browser page polls `/api/update/status`.

### Full Roster

Generated at `output/fullroster.html`.

It lists all discovered characters grouped by realm. Realm groups are sorted descending by total number of characters.

## Addon Behavior

The addon captures on:

- Login/entering world.
- Logout.
- Specialization change.
- Equipment swap finished.
- Equipment set changes.
- Manual `/wowprofile capture`.

It captures:

- Character and realm.
- Class and specialization.
- Timestamps.
- Click bindings.
- Normal keybindings/action bar mappings.
- Action bars/action slot details.
- Spec item level from `GetAverageItemLevel()`.
- Equipment set metadata and per-set iLevel where available.

The addon avoids storing spec ID `0` captures and has retry logic for cases where WoW has not finished loading valid spec data. Equipment sets are stored at the character level, not under a specific spec, because equipment sets may be unassigned or not tied to a spec.

## Important Design Decisions

- Keep `characters.yaml` human-editable and generated output separate.
- Use `enabled` internally but display `Active` to the user.
- Preserve `local_client_data` when public API updates rewrite character JSON.
- Store equipment sets at the character level because they may not be tied to specs.
- Use standard-library HTTP server for the local UI rather than adding a web framework.
- Use a small local Lua parser for SavedVariables instead of adding a dependency.
- Automatically mark characters inactive only when the public `profile` endpoint returns HTTP `403` or `404`.
- Do not commit `output/`, `.env`, `.venv/`, or caches.

## Current Git State

As of this documentation update:

- Current branch: `main`.
- Last committed baseline observed: `5e4165a Document current workflow and handle inaccessible profiles`.
- There are uncommitted changes after that commit, including Account Summary active switches, guarded activation behavior, Phase 1 Blizzard API architecture, expanded default profile sections, tests, docs, and a local `characters.yaml` active-state change.

## Validation

Current test command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Most recent run in this thread passed:

```text
Ran 50 tests
OK
```

## Known Issues And Assumptions

- Live Blizzard API calls require valid local `.env` credentials.
- Tests do not require live Blizzard credentials.
- `output/` is ignored and must be regenerated locally.
- SavedVariables import matches local addon data by character name and realm. Character rename/realm-transfer matching for local addon data is not currently ID-based.
- `roster-ui` starts a live profile refresh on server startup, which may make startup network-dependent and can modify `characters.yaml` by marking 403/404 profile failures inactive.
