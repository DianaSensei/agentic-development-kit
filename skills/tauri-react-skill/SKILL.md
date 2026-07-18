---
name: tauri-react-skill
description: Implementation knowledge for Tauri (Rust backend) + React (frontend) desktop apps — IPC commands/invoke, capabilities/permissions, standard plugins (dialog/fs/store/sql), local/offline storage design (SQLite/key-value/file), cross-OS handling (`#[cfg(target_os)]`), and React loading/error/empty state. Coordinates with `ui-ux-design-skill` (UX design) — this skill owns both storage design and the executable code for Tauri+React apps. Use when implementing/modifying code, or designing/changing the storage mechanism, in a Tauri+React app.
---

# Tauri + React — Implementation & Local Storage

## Reference Guide

Load detailed code patterns based on context:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| IPC Patterns | `references/ipc-patterns.md` | Writing commands, `Result<T, E>` error types, `tauri::State`, events (`emit`/`listen`), a shared `useInvoke` hook |
| Capabilities Examples | `references/capabilities-examples.md` | Writing `capabilities/*.json`, picking the right permission identifier, multi-window/platform-specific scoping, debugging a command blocked at runtime |
| Storage Implementation | `references/storage-implementation.md` | Actual `tauri-plugin-sql`/`-store`/`-fs` code: migrations, WAL mode, queries, backup-before-migrate |
| Cross-OS Patterns | `references/cross-os-patterns.md` | `#[cfg(target_os)]` code, OS-correct paths, normalizing behavior drift, CI build matrix, desktop E2E setup |
| Testing Patterns | `references/testing-patterns.md` | Rust command unit tests, mocking `invoke` in React, migration fixture tests, manual QA writeups |

## Discover

Read `src-tauri/Cargo.toml` + `src-tauri/tauri.conf.json` (Tauri version, installed plugins:
`tauri-plugin-sql`, `tauri-plugin-store`, `tauri-plugin-fs`, ...) and `package.json` (React version,
state management in use — Context/Redux/Zustand/React Query). Read the existing `capabilities/*.json`.
Do NOT assume a version, plugin, or storage mechanism without concrete evidence — the Tauri v1 and v2
APIs differ significantly, especially the permission/capabilities model.

## IPC: Commands & Invoke

- A Rust command (`#[tauri::command]`) should return a clear `Result<T, E>` instead of panicking — a
  panic inside a command crashes the entire backend process, not just that one request.
- Validate input on the Rust side even though React already validated it — never trust data coming
  from the frontend (it can be bypassed via devtools or the webview directly).
- Keep command naming consistent with the project's existing convention (`snake_case` in Rust, called
  via `invoke('command_name', {...})` from React).
- For long-running work (large I/O, heavy processing): avoid blocking Rust's main thread — use an
  `async fn` command or `tauri::async_runtime::spawn` for heavy work so the UI doesn't freeze.
- For continuous progress reporting (progress bars, live logs), use events (`emit`/`listen`) instead of
  polling with repeated `invoke` calls.

## Capabilities & Permissions (Tauri v2 — least privilege)

- Declare ONLY the scope actually needed in `capabilities/*.json` (e.g. `fs:allow-read-file` scoped to
  a specific `path`, not full filesystem access when only one config directory needs reading).
- Do not enable `"dangerousRemoteDomainIpcAccess"` or widen the CSP beyond what's actually required.
- Every plugin added must come with its matching permission declaration in capabilities — a missing
  declaration silently blocks the command at runtime even when the Rust code is correct (this is easy
  to misdiagnose as a logic bug when it's actually a missing permission).

## Standard Plugins

- **Before writing custom code**: check whether an official Tauri plugin (`tauri-plugin-*` in
  [tauri-apps/plugins-workspace](https://github.com/tauri-apps/plugins-workspace) — dialog, fs, store,
  sql, http, shell, clipboard-manager, notification, os, updater, window-state, etc.) or a vetted
  community plugin (see [tauri-apps/awesome-tauri](https://github.com/tauri-apps/awesome-tauri) or
  search `tauri-plugin-` on [crates.io](https://crates.io)) already covers the need, before
  implementing a `#[tauri::command]` from scratch. Hand-rolling a command for something a standard
  plugin already does (e.g. reading/writing files with raw `std::fs` instead of `tauri-plugin-fs`,
  parsing the clipboard manually instead of `tauri-plugin-clipboard-manager`) costs more to maintain
  and skips the permission/capability model the plugin was already built with — a common source of
  security gaps that the official plugin would have handled.
- **Dialog** (`tauri-plugin-dialog`): use for native open/save file pickers and confirm dialogs — do
  not build a fake HTML modal to imitate an OS file picker.
- **FS** (`tauri-plugin-fs`): raw file operations, always through the scope declared in capabilities;
  never build an absolute path by hand from unvalidated user input (path traversal risk — normalize and
  verify the path stays within the allowed base directory).
- **Store** (`tauri-plugin-store`): key-value JSON, call the correct API (`load`, `get`, `set`, `save`)
  — see **Local/Offline Storage Design** below for choosing/designing the data itself.
- **SQL** (`tauri-plugin-sql`): use the plugin's async API correctly (`Database.load`, `execute`,
  `select`) — see **Local/Offline Storage Design** below for connection string / schema / migration
  design.
- Add a standard plugin normally when the current task genuinely needs it (dialog/fs/store/sql above,
  or another official plugin that fits), declare the minimal matching permission, and just mention in
  the report that it was added. Do NOT add plugins OUTSIDE the current task's scope — every plugin adds
  system-level access and expands the attack surface, so adding one must be tied to a concrete need,
  not "might as well while we're here."

## Local/Offline Storage Design

This section applies to storage **local to the user's machine**, with no central server/DB. If the
project has a Java backend connecting to Oracle/Postgres/MySQL/Mongo, use `database-skill` instead. For
Redis/Elasticsearch, use `redis-skill`/`elasticsearch-skill` respectively.

### Change Classification

Classify the change first: **ADD** (new data), **MODIFY** (restructuring something that already
exists), **REMOVE/DEPRECATE**, or **NONE**.

### Choosing a Storage Mechanism (when not already constrained by existing choices)

- **`tauri-plugin-store`**: simple key-value JSON — fits settings/preferences, small data with no
  complex querying needs (e.g. theme, language, window position).
- **`tauri-plugin-sql`** (SQLite): fits conditional queries, relationships across multiple data types,
  or larger datasets that need an index for fast lookup.
- **`tauri-plugin-fs`**: raw files (JSON/CSV/binary in a custom format) — fits data the user handles
  directly as a file (export/import), or large blobs that don't belong in SQLite.

For **ADD** (new data, not present on any user's machine yet) — choose the mechanism that best fits
across 5 axes: storage footprint, access speed, permissions/security (per-OS file permissions), risk,
and future extensibility; briefly state the reasoning in the report instead of asking upfront. For
**MODIFY/REMOVE** of a mechanism that currently holds real user data — always present **options** with
tradeoffs across the same 5 axes and wait for the user's decision, since a wrong call here can destroy
data already stored on the user's machine (there's no DBA or centralized rollback like a server has).

### Schema & Migration

- SQLite: a **complete** Mermaid ERD (not a diff), with new/changed parts marked.
- Key-value/file: a JSON Schema describing the full structure.
- Migration: prefer backward-compatible changes (different users may be running different app
  versions) — migrations MUST run automatically at app startup, with a rollback plan or at minimum a
  guarantee that a failed migration doesn't corrupt existing data.

### Common Storage Issues

- **SQLite single-writer lock**: SQLite allows only one writer at a time — concurrent writes from
  multiple Tauri commands (e.g. two UI events triggering writes at once) commonly hit a "database is
  locked" error unless WAL mode is enabled (`PRAGMA journal_mode=WAL` — allows reads to proceed
  concurrently with a write) or writes are serialized at the application layer.

### Desktop/Offline-Specific Considerations (unlike server-side DBs)

- No DBA watching over it — a failed migration can leave the user unable to open the app at all;
  migration failure handling needs a fallback (back up the old file before migrating, or catch the
  error and let the app continue with empty data instead of crashing).
- Storage is bounded by the user's disk, not a server — avoid unnecessarily bloated designs (e.g.
  storing large images/files directly as SQLite blobs when `tauri-plugin-fs` fits better).
- No network to "back up to the cloud" by default — if the business need requires backup/sync, that's
  a significant architectural decision (adding new network/cloud infrastructure to an app that was
  offline-first), and always needs a separate discussion with the user's approval before adding it.

## Cross-OS (`#[cfg(target_os)]`)

- Where macOS/Windows/Linux need different logic (default paths, menu bar, tray icon, keyboard
  shortcut conventions), use `#[cfg(target_os = "macos")]`/`"windows"`/`"linux"` explicitly — handle
  ALL 3 target OS, not just the one you're developing on and leaving the other two unhandled (a common
  mistake: only testing on the dev machine, shipping broken behavior on the other OS).
- For system file paths (app data dir, config dir), use Tauri's path API
  (`app_handle.path().app_data_dir()`, etc.) instead of hardcoding Unix- or Windows-style paths, so it
  resolves correctly per OS automatically.
- The three WebView engines behind Tauri differ by OS — Windows uses WebView2 (Chromium), macOS uses
  WKWebView (Safari's engine), Linux uses WebKitGTK — with different CSS/JS feature support and
  different rendering/JS performance characteristics (Linux/WebKitGTK is typically the weakest of the
  three for complex rendering: animation, long lists, canvas). Testing on one OS's devtools does NOT
  guarantee correctness or acceptable performance on another — verify on all target OS before marking a
  cross-OS-sensitive or performance-sensitive feature done; if there's no machine/CI available for all
  of them, say explicitly which OS wasn't verified instead of implying full coverage.

### Behavior Consistency

The same feature must produce the **same business result** on all 3 OS — differences should be limited
to OS-specific UI conventions (macOS menu bar vs. Windows/Linux, Cmd vs. Ctrl shortcuts), never to
logic or output. Unintended behavioral drift between OS (e.g. sort order differing due to OS collation,
`\n` vs `\r\n` line endings when reading/writing text files) must be normalized explicitly in code, not
left to the OS default. Similarly, don't rely on OS default locale/timezone/number formatting when
consistent output across user machines is required — the OS default will format differently
machine-to-machine even for the identical app.

### Performance Consistency

Don't assume an optimization measured only on the dev OS (often a fast machine) is fast enough on the
others. Push heavy work (large data processing, computation) into the Rust backend via an `async fn`
command rather than doing it in React/JS — Rust gives more consistent performance across OS than JS
running on three different JS engines.

## React — State for Tauri Calls

- Every cross-process `invoke` call MUST have all 3 UI states: loading, error, and success/empty (no
  data) — don't let the UI sit unresponsive while waiting on Rust, and don't silently swallow an error
  when `invoke` rejects.
- Clean up listeners (`listen`/`once`) on component unmount (call the unlisten function `listen`
  returns) — otherwise listeners leak and duplicate events fire on repeated component mounts.
- Avoid unnecessary repeated `invoke` calls inside the render loop (use `useEffect` with correct
  dependencies, or React Query/SWR if the project already uses one, to cache results).

## Common Real-World Issues

- **CSP too strict**: an overly strict Content-Security-Policy in `tauri.conf.json` blocking valid
  resources (inline style/script, external fonts) usually fails silently in the browser console (it's
  blocked, not a React logic error) — easy to misdiagnose as a component bug when it's actually the CSP.
- **Missing permission doesn't always fail loudly**: some plugins fail silently or return a generic
  error when a capability is missing, easy to mistake for a Rust code bug — always check
  `capabilities/*.json` before debugging deep into command logic.

## Test

- Rust: unit test the pure command logic (extract business logic out of the `#[tauri::command]`
  wrapper so tests don't need to spin up the full Tauri runtime).
- React: test components with `invoke` mocked (never call the real Tauri runtime in a unit test) —
  cover all 3 branches: loading/error/success.
- Storage: test that migrations run correctly against an existing prior-version schema/data (use a DB
  file or store JSON fixture from a previous version) — not just against a freshly created empty DB.
- Cross-OS: for a feature with its own `#[cfg(target_os)]` logic or performance sensitivity, confirm
  it was tested/measured on all target OS before reporting it done (see **Cross-OS** above) — if a
  machine/CI isn't available for all of them, state which OS wasn't verified rather than implying it was.
- For real integration testing (both Rust and the WebView), label it explicit manual/QA testing if the
  project has no desktop E2E infrastructure yet (WebDriver/`tauri-driver`). Do NOT set up new E2E
  infrastructure unprompted (high setup cost, affects the whole project's test process) — propose it
  with reasoning and wait for the user's decision on whether to invest in it.

## Constraints

### MUST DO

- Confirm the actual Tauri version, installed plugins, and storage mechanism from `Cargo.toml` /
  `tauri.conf.json` / `package.json` before writing code — never assume.
- Return `Result<T, E>` from every `#[tauri::command]`; never let a command panic.
- Validate all input on the Rust side, even when the frontend already validated it.
- Declare the minimum required permission scope in `capabilities/*.json` for every plugin used.
- Use an `async fn` command or `tauri::async_runtime::spawn` for long-running work so the UI thread
  never blocks.
- Provide loading, error, and success/empty states for every `invoke` call in React.
- Clean up `listen`/`once` listeners on component unmount.
- Handle all 3 target OS for any OS-dependent logic, not just the developer's OS.
- Present options with tradeoffs and wait for user approval before changing an existing storage
  mechanism that holds real user data.
- Verify (test or measure) behavior and performance on all target OS before reporting a cross-OS or
  performance-sensitive feature as done, or state explicitly which OS was not verified.
- Test migrations against a fixture from a previous schema/data version, not only against an empty DB.

### MUST NOT DO

- Hand-implement functionality that an official or vetted community Tauri plugin already provides.
- Add a plugin outside the scope of the current task "just in case."
- Enable `dangerousRemoteDomainIpcAccess` or broaden the CSP without a concrete, current need.
- Hardcode OS-specific filesystem paths — use Tauri's path API instead.
- Change an existing storage mechanism that holds real user data without presenting options and
  getting user approval first.
- Set up new desktop E2E test infrastructure without being asked — propose it and wait for a decision.
- Rely on OS default locale, timezone, or collation where consistent cross-machine output is required.
- Assume behavior or performance verified on one OS carries over to the other target OS.

## Knowledge Reference

Tauri v2, `#[tauri::command]`, `tauri::State`, `Emitter`/`Listener` (emit/listen), capabilities/ACL
permission model, `tauri-plugin-dialog`/`fs`/`store`/`sql`/`clipboard-manager`/`shell`, WebView2/
WKWebView/WebKitGTK, React (Context/Redux/Zustand/React Query), `invoke`, SQLite/WAL mode, JSON Schema,
`tauri-action`, WebdriverIO `@wdio/tauri-service`/`tauri-driver`.

## Boundaries

This skill does not decide UI/UX layout or flow — that belongs to `ui-ux-design-skill`. It does not own
Rust language fundamentals unrelated to Tauri (complex ownership/lifetimes, trait hierarchy design,
`thiserror`-based error types, advanced tokio async patterns) — see `rust-engineer` for those. Final
review → `code-review-skill`.
