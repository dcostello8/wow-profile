# Windows Packaging

The project can run as a self-contained Windows application using PyInstaller. The packaged application remains local-only and opens the existing browser-based roster UI. Double-clicking `WowProfile.exe` is the normal workflow; no command-line parameter is required.

## Build

From `C:\github\wow-profile`, use either Command Prompt:

```powershell
build-windows.bat
```

or PowerShell with an execution-policy override for this process:

```powershell
.\build-windows.ps1
```

If PowerShell blocks the script, run `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1` or use `build-windows.bat`.

The distributable folder is created at `dist\WowProfile\`. Run `dist\WowProfile\WowProfile.exe` or copy the entire `dist\WowProfile\` folder together with the local data files. Do not run an older `dist\WowProfile.exe` left over from a previous one-file build.

## Local data

Keep these files beside the executable's working directory:

- `.env` for Blizzard credentials
- `characters.yaml` for the local roster
- `output\` for generated reports and cached reference data

The packaged application does not bundle credentials, account-specific roster state, generated output, or SavedVariables. Use the existing `import-local` command or the `roster-ui` startup workflow with the packaged executable.

## Application startup

Double-click:

```text
dist\WowProfile\WowProfile.exe
```

The application automatically starts the local server on `127.0.0.1:8765`, imports the newest detected SavedVariables file, refreshes local summaries, and opens the browser. Discovery and profile refresh are started from the page. The old subcommands remain available for development and troubleshooting, but are not needed for normal use.

## Notes

The initial build uses a windowed `onedir` package. Keep `.env`, `characters.yaml`, and `output\` in the application's working directory so the page can use editable local configuration. A later installer can add shortcuts, a Start Menu entry, and a writable data-directory selection without changing the core application.

## Troubleshooting

If Windows reports that Application Control blocked `WowProfile.exe`, the executable is being denied by a local or organizational Windows Defender/App Control policy. The application must be allowlisted by the machine administrator or security policy owner. This is separate from the Python DLL packaging issue; do not launch the stale top-level `dist\WowProfile.exe` from an earlier one-file build.