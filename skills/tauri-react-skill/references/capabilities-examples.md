# Capabilities & Permissions — Concrete Examples

## File Structure

Capability files live in `src-tauri/capabilities/*.json` (or `.toml`) and are referenced from
`tauri.conf.json` (or auto-discovered, depending on version/config). Each file declares an
`identifier`, which `windows` it applies to, and the `permissions` granted.

## Minimal Capability (default window, no plugins)

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "main-capability",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:path:default",
    "core:event:default",
    "core:window:default",
    "core:app:default",
    "core:resources:default"
  ]
}
```

## Scoped FS Permission (read one config directory, not the whole filesystem)

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "fs-config-access",
  "description": "Read-only access to the app's own config directory",
  "windows": ["main"],
  "permissions": [
    {
      "identifier": "fs:allow-read-file",
      "allow": [{ "path": "$APPCONFIG/*" }]
    }
  ]
}
```

Prefer the narrowest permission identifier available (`fs:allow-read-file` vs. blanket `fs:default`,
which grants broad read/write). Check the plugin's own permission list (each plugin ships
`permissions/*.toml` describing exactly which identifiers it exposes) before reaching for a wide
default.

## Per-Plugin Permission Identifiers (what to actually write)

| Plugin | Typical permission identifiers |
|---|---|
| `tauri-plugin-dialog` | `dialog:allow-open`, `dialog:allow-save`, `dialog:allow-confirm` |
| `tauri-plugin-fs` | `fs:allow-read-file`, `fs:allow-write-file`, `fs:allow-exists`, scoped with `allow`/`deny` path lists |
| `tauri-plugin-store` | `store:default`, `store:allow-get`, `store:allow-set`, `store:allow-save` |
| `tauri-plugin-sql` | `sql:allow-execute`, `sql:allow-select`, `sql:allow-load` |
| `tauri-plugin-clipboard-manager` | `clipboard-manager:allow-read-text`, `clipboard-manager:allow-write-text` |
| `tauri-plugin-shell` | `shell:allow-execute` (scoped to specific binaries — never a blanket allow) |

## Platform-Specific Capability (different scope per OS)

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "windows-only-registry-access",
  "windows": ["main"],
  "platforms": ["windows"],
  "permissions": ["registry:allow-read"]
}
```

Use `"platforms"` instead of writing OS branches into application logic when the difference is purely
about *what's allowed*, not *what the code does* — keep `#[cfg(target_os)]` for behavioral differences
(see the main SKILL.md's Cross-OS section), and `platforms` in capabilities for permission differences.

## Multi-Window Capability Isolation

A settings window that needs filesystem write access shouldn't grant that same access to a
lower-trust window (e.g. one rendering remote/untrusted content):

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "settings-window-fs-write",
  "windows": ["settings"],
  "permissions": ["fs:allow-write-file"]
}
```

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "main-window-readonly",
  "windows": ["main"],
  "permissions": ["fs:allow-read-file"]
}
```

## Debugging "Command Blocked at Runtime"

When a command that compiles fine fails silently or with a generic permission error at runtime:

1. Check the exact permission identifier the plugin's own docs/`permissions/*.toml` require — plugin
   permission names don't always match the command name.
2. Confirm the capability's `"windows"` list includes the window actually calling `invoke`.
3. Confirm the capability file is picked up (correct directory, valid JSON — a syntax error can cause
   the whole capability file to be silently skipped rather than erroring loudly).
