# AGENTS.md

## Project Overview

This repository contains a small Python utility for retrieving World of Warcraft character information from Blizzard's Battle.net APIs.

Project root on the developer machine:

`C:\github\wow-profile`

The primary goal is to maintain a local, human-editable roster of World of Warcraft characters and selectively update detailed Blizzard profile data only for characters the user has enabled.

## Primary Commands

The intended CLI is:

```powershell
python wow_profile.py discover
python wow_profile.py update
```

### `discover`

The `discover` command should:

1. Authenticate the user with Battle.net using the OAuth Authorization Code flow.
2. Request the `wow.profile` scope.
3. Receive the OAuth redirect on a localhost callback.
4. Exchange the authorization code for an access token.
5. Call Blizzard's account-profile endpoint to retrieve all WoW characters associated with the authenticated Battle.net account.
6. Create or update `characters.yaml`.
7. Preserve all existing user configuration when rediscovering characters.
8. Add newly discovered characters with `enabled: false`.
9. Never silently remove a character merely because it is absent from one discovery response. Prefer marking or preserving stale entries unless the behavior is explicitly changed later.

### `update`

The `update` command will eventually:

1. Read `characters.yaml`.
2. Select only characters with `enabled: true`.
3. Query Blizzard character-profile endpoints for those characters.
4. Write generated data beneath `output/`.
5. Keep generated data separate from user-edited configuration.

Do not implement functionality beyond the current requested milestone unless it is necessary to support that milestone.

## Current Development Milestone

Implement OAuth and `discover` first.

Do not implement detailed character updating until OAuth and character discovery are working reliably.

The first successful milestone is:

```text
python wow_profile.py discover
```

which authenticates against Battle.net and produces a valid `characters.yaml`.

## Runtime Environment

- Operating system: Windows
- Python virtual environment: `.venv`
- Shell commonly used: PowerShell

Installed Python packages:

- `requests`
- `python-dotenv`
- `pyyaml`

Prefer the Python standard library where practical. Do not add dependencies unless they provide clear value.

## Blizzard OAuth Configuration

Configuration is stored locally in `.env`.

Expected variables:

```dotenv
BLIZZARD_CLIENT_ID=...
BLIZZARD_CLIENT_SECRET=...
BLIZZARD_REDIRECT_URI=http://localhost:8000/callback
BLIZZARD_REGION=us
```

The registered Blizzard redirect URI must exactly match `BLIZZARD_REDIRECT_URI`.

The account-character discovery flow requires user authorization with the `wow.profile` scope.

Use Blizzard's OAuth Authorization Code flow for account discovery. Do not substitute the Client Credentials flow for endpoints that require user authorization.

## Security Requirements

Treat Blizzard credentials and OAuth tokens as secrets.

Rules:

- Never print `BLIZZARD_CLIENT_SECRET`.
- Never commit `.env`.
- Never embed credentials in source code.
- Never write access tokens or refresh tokens into generated reports.
- Avoid logging authorization codes.
- Redact secrets from errors and diagnostics.
- Keep credentials local to the developer machine.
- Do not ask the user to paste their Blizzard Client Secret into ChatGPT or Codex conversations.

The `.gitignore` should include at least:

```gitignore
.env
.venv/
__pycache__/
output/
```

If token persistence is later added, its storage file must also be ignored by Git.

## Character Configuration

`characters.yaml` is user-editable configuration and is the source of truth for which characters should receive detailed updates.

A representative structure is:

```yaml
defaults:
  update:
    profile: true
    equipment: true
    talents: true
    professions: true
    mythic_plus: true
    statistics: true
    reputations: false
    achievements: false

characters:
  - id: 123456789
    name: Jaedon
    realm: Windrunner
    realm_slug: windrunner
    region: us
    enabled: true

  - id: 987654321
    name: ExampleAlt
    realm: Windrunner
    realm_slug: windrunner
    region: us
    enabled: false
```

The exact Blizzard response may require adjustments to these fields.

### Merge Rules

When `discover` runs repeatedly:

- Match existing characters using Blizzard's stable character identifier when available.
- Preserve `enabled`.
- Preserve any user-defined per-character update overrides.
- Refresh Blizzard-owned descriptive fields such as name, realm, realm slug, and level when appropriate.
- New characters default to `enabled: false`.
- Do not reorder the file unnecessarily.
- Do not destroy comments or hand-edited configuration if a reasonable implementation can preserve them. If PyYAML limitations make comment preservation impractical, prioritize preservation of values and stable ordering and document that limitation.

Character ID should be preferred over `name + realm` as the long-term identity key because characters may be renamed or transferred.

## Generated Output

Generated data belongs beneath:

```text
output/
```

Planned structure:

```text
output/
├── roster.json
├── roster.md
└── characters/
    ├── jaedon-windrunner.json
    └── ...
```

Do not place generated Blizzard API responses into `characters.yaml`.

Prefer one detailed JSON file per character rather than one large monolithic file.

## Planned Character Data

The later `update` command may retrieve:

- Basic character profile
- Active specialization
- Talent/specialization information
- Equipment
- Character statistics
- Professions
- Mythic+ profile
- Character media
- Reputations
- Achievements
- Other useful public profile resources

Do not assume every endpoint is available for every character. Handle missing resources gracefully.

## API Design Guidelines

Keep Blizzard-specific HTTP logic separate from CLI orchestration.

A reasonable eventual structure is:

```text
wow-profile/
├── .env
├── .gitignore
├── AGENTS.md
├── characters.yaml
├── wow_profile.py
├── blizzard_api.py
├── oauth.py
├── config.py
└── output/
```

This structure is guidance, not a hard requirement. Keep the initial implementation simple.

Suggested responsibilities:

### `wow_profile.py`

- CLI argument handling
- Coordinates `discover` and `update`
- User-facing status and errors

### `oauth.py`

- Construct authorization URL
- Open browser
- Run temporary localhost callback server
- Validate OAuth state
- Exchange authorization code for token

### `blizzard_api.py`

- Blizzard HTTP requests
- Namespace and locale handling
- Error handling
- Character/account endpoints

### `config.py`

- Read/write `.env`-independent application configuration
- Read/merge/write `characters.yaml`
- Preserve user choices

Avoid introducing a web framework such as Flask or FastAPI for the localhost OAuth callback unless the standard library becomes genuinely cumbersome. A temporary `http.server`-based callback is preferred initially.

## OAuth Callback Behavior

For local development:

- Bind only to localhost.
- Use the configured callback port and path.
- Validate the OAuth `state` parameter.
- Return a simple success page to the browser after receiving the code.
- Shut down the temporary callback server after success or failure.
- Give clear instructions if the port is already in use.
- Do not leave a persistent local web server running.

## Error Handling

Provide actionable errors rather than raw stack traces for expected failures.

Examples:

- Missing `.env`
- Missing Client ID or Client Secret
- Redirect URI mismatch
- OAuth authorization denied
- Callback timeout
- Port already in use
- Battle.net HTTP 401/403
- API rate limiting
- Network timeout
- Invalid or unexpected Blizzard response
- Malformed `characters.yaml`

For unexpected programming errors, preserving a useful traceback during development is acceptable.

Use reasonable HTTP timeouts. Do not make requests without a timeout.

## Data Quality

Do not invent values when Blizzard omits data.

Distinguish between:

- absent data
- API errors
- unsupported resources
- disabled updates
- stale previously generated data

When writing timestamps, use explicit ISO-8601 timestamps.

## Console Output

Keep CLI output useful and concise.

Example:

```text
Opening Battle.net authorization...
Authorization successful.
Discovered 27 characters.
Added 3 new characters.
Preserved 24 existing character settings.
Wrote characters.yaml.
```

Never expose secrets in console output.

## Coding Style

- Target modern Python.
- Use type hints for public functions where useful.
- Prefer `pathlib.Path` over manual path concatenation.
- Prefer small, focused functions.
- Avoid unnecessary object-oriented abstractions.
- Use descriptive names.
- Keep Windows compatibility in mind.
- Use UTF-8 for text files.
- Keep API transport logic testable.
- Avoid global mutable state.
- Avoid broad `except Exception` unless re-raising or providing useful context.

## Testing

For logic that does not require live Blizzard access, prefer unit-testable functions.

Important areas to test eventually:

- Character merge behavior
- New characters default to disabled
- Existing `enabled` flags survive discovery
- Per-character overrides survive discovery
- Rename/realm changes when character ID remains stable
- Missing API fields
- OAuth state validation
- Configuration validation

Do not require live Blizzard credentials for ordinary unit tests.

## Git Practices

Never commit secrets.

Before committing, verify:

```powershell
git status
```

and ensure `.env` and any token/cache files are not staged.

Do not rewrite unrelated files or perform broad repository cleanup unless requested.

## Working With the User

The user is an experienced software developer but is relatively new to Python.

When explaining Python-specific choices:

- Be concise.
- Relate concepts to common Java/C# equivalents when that helps.
- Do not over-explain elementary programming concepts unless asked.
- Prefer concrete commands and code changes.
- When an error occurs, diagnose the actual error before suggesting unrelated environment changes.

The user typically develops under `C:\github`.

## Immediate Next Task

Implement the first working `discover` flow.

Success criteria:

1. `python wow_profile.py discover` runs from the repository root.
2. Browser opens to Battle.net authorization.
3. OAuth callback succeeds at the configured localhost redirect URI.
4. The account WoW profile is retrieved.
5. Every discovered character is represented in `characters.yaml`.
6. New characters have `enabled: false`.
7. Re-running discovery preserves existing `enabled` values.
8. No secrets are logged or committed.

Stop at that milestone and verify it before expanding into detailed character updates.
