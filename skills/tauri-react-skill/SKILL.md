---
name: tauri-react-skill
description: Implementation knowledge for Tauri (Rust backend) + React (frontend) desktop apps - IPC commands/invoke, capabilities/permissions, standard plugins (dialog/fs/store/sql), local/offline storage design (SQLite/key-value/file), cross-OS handling (`#[cfg(target_os)]`), and React loading/error/empty state. Coordinates with `ui-ux-design-skill` (UX design) - this skill owns both storage design and the executable code for Tauri+React apps. Use when implementing/modifying code, or designing/changing the storage mechanism, in a Tauri+React app.
metadata:
  domain: desktop-app
  triggers: React desktop, tauri plugin, fs plugin, store plugin, sql plugin, SQLite desktop, loading state
  role: engineer
  scope: implementation
  output-format: code
  related-skills: rust-engineer, ui-ux-design-skill, database-skill, test-master, code-review-skill
---

# Tauri + React - Implementation & Local Storage

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| IPC Patterns | `references/ipc-patterns.md` | Writing commands, `Result<T, E>` error types, `tauri::State`, events (`emit`/`listen`), a shared `useInvoke` hook |
| Capabilities Examples | `references/capabilities-examples.md` | Writing `capabilities/*.json`, picking the right permission identifier, multi-window/platform-specific scoping, debugging a command blocked at runtime |
| Storage Implementation | `references/storage-implementation.md` | Actual `tauri-plugin-sql`/`-store`/`-fs` code: migrations, WAL mode, queries, backup-before-migrate |
| Cross-OS Patterns | `references/cross-os-patterns.md` | `#[cfg(target_os)]` code, OS-correct paths, normalizing behavior drift, CI build matrix, desktop E2E setup |
| Testing Patterns | `references/testing-patterns.md` | Rust command unit tests, mocking `invoke` in React, migration fixture tests, manual QA writeups |

## Discover

Read `src-tauri/Cargo.toml` + `src-tauri/tauri.conf.json` (Tauri version, installed plugins) and
`package.json` (React version, state management: Context/Redux/Zustand/React Query), plus the existing
`capabilities/*.json`. Never assume a version, plugin, or storage mechanism without concrete evidence -
Tauri v1 and v2 differ significantly, especially in the permission/capabilities model.

## IPC: Commands & Invoke

- Every `#[tauri::command]` returns a clear `Result<T, E>` - a panic inside a command kills the whole
  backend process, not just that request.
- Validate input on the Rust side even when React already did. Frontend validation is bypassable via
  devtools or the webview directly.
- Match the project's existing naming convention (`snake_case` in Rust, `invoke('command_name', {...})`).
- Long-running work (large I/O, heavy processing) goes in an `async fn` command or
  `tauri::async_runtime::spawn` - never block Rust's main thread, or the UI freezes.
- Continuous progress (progress bars, live logs) uses events (`emit`/`listen`), not repeated `invoke`
  polling.

## Capabilities & Permissions (v2 - least privilege)

- Declare only the scope actually needed - `fs:allow-read-file` scoped to one `path`, not blanket
  filesystem access to read one config directory.
- Never enable `dangerousRemoteDomainIpcAccess` or widen the CSP without a concrete, current need.
- Every plugin needs its matching permission declaration. A missing one **silently blocks the command at
  runtime** even when the Rust code is correct - check `capabilities/*.json` before debugging deep into
  command logic.

## Standard Plugins

**Check for an existing plugin before writing a command.** Official `tauri-plugin-*`
([plugins-workspace](https://github.com/tauri-apps/plugins-workspace): dialog, fs, store, sql, http,
shell, clipboard-manager, notification, os, updater, window-state...) or a vetted community one
([awesome-tauri](https://github.com/tauri-apps/awesome-tauri), or `tauri-plugin-` on crates.io).
Hand-rolling what a plugin already does (raw `std::fs` instead of `tauri-plugin-fs`, manual clipboard
parsing instead of `tauri-plugin-clipboard-manager`) costs more to maintain and skips the
permission/capability model the plugin was built around - a common source of security gaps.

- **Dialog** - native open/save pickers and confirm dialogs. Never fake an OS file picker with an HTML
  modal.
- **FS** - always through the capability-declared scope; never build an absolute path by hand from
  unvalidated input (path traversal - normalize and verify it stays inside the allowed base dir).
- **Store** - key-value JSON (`load`, `get`, `set`, `save`).
- **SQL** - `Database.load`, `execute`, `select`.

Add a plugin the current task genuinely needs, declare its minimal permission, and note it in the report.
Never add one outside the task's scope "while we're here" - each expands system access and attack
surface.

## Local/Offline Storage Design

Storage local to the user's machine, no central server. A Java backend on
Oracle/Postgres/MySQL/Mongo → `database-skill`; Redis/Elasticsearch → `redis-skill`/`elasticsearch-skill`.

Classify the change first: **ADD** / **MODIFY** / **REMOVE-DEPRECATE** / **NONE**.

**Choosing a mechanism** (when not already constrained):

- **`tauri-plugin-store`** - key-value JSON: settings/preferences, small data with no complex queries
  (theme, language, window position).
- **`tauri-plugin-sql`** (SQLite) - conditional queries, relationships across data types, larger datasets
  needing an index.
- **`tauri-plugin-fs`** - raw files (JSON/CSV/binary): data the user handles as a file (export/import),
  or large blobs that don't belong in SQLite.

For **ADD** (data on no user's machine yet), pick the best fit across 5 axes - footprint, access speed,
permissions/security, risk, extensibility - and state the reasoning in the report rather than asking
upfront. For **MODIFY/REMOVE** of a mechanism holding real user data, always present options with
tradeoffs across those same axes and **wait for the user's decision** - a wrong call destroys data on the
user's machine, with no DBA and no centralized rollback.

**Schema & migration**: SQLite → a *complete* Mermaid ERD (not a diff) with changed parts marked;
key-value/file → a JSON Schema of the full structure. Prefer backward-compatible changes (users run
different app versions). Migrations run automatically at startup and need a rollback plan, or at minimum a
guarantee that failure doesn't corrupt existing data. Test them against a fixture from a *previous*
schema version, never only against an empty DB.

**Desktop-specific realities**: nobody is watching the DB, so a failed migration can leave the user unable
to open the app at all - back up the old file first, or catch the error and continue with empty data
rather than crashing. Storage is bounded by the user's disk, so don't bloat it (large images as SQLite
blobs where `tauri-plugin-fs` fits better). There is no default cloud backup - adding backup/sync means
adding network infrastructure to an offline-first app, which is a separate architectural decision needing
the user's approval.

**SQLite single-writer lock**: only one writer at a time, so concurrent writes from two commands hit
"database is locked" unless WAL mode is on (`PRAGMA journal_mode=WAL`, letting reads proceed during a
write) or writes are serialized in the app layer.

## Cross-OS (`#[cfg(target_os)]`)

- Handle **all 3** target OS wherever logic differs (default paths, menu bar, tray icon, shortcut
  conventions) - not just the dev machine's, leaving the other two broken.
- Use Tauri's path API (`app_handle.path().app_data_dir()`) - never hardcode Unix- or Windows-style paths.
- **The WebView differs per OS**: WebView2/Chromium on Windows, WKWebView/Safari on macOS, WebKitGTK on
  Linux - different CSS/JS support and very different rendering performance (WebKitGTK is typically
  weakest for animation, long lists, canvas). One OS's devtools proves nothing about the others: verify on
  all target OS before calling a cross-OS or performance-sensitive feature done, and if no machine/CI
  exists for one, say explicitly which was not verified rather than implying full coverage.
- **Same business result on all 3 OS.** Differences belong only in OS-specific UI convention (menu bar,
  Cmd vs. Ctrl), never in logic or output. Normalize drift explicitly in code - sort order from OS
  collation, `\n` vs `\r\n` line endings - and never rely on OS default locale/timezone/number formatting
  where consistent cross-machine output matters.
- Don't assume an optimization measured on the dev OS holds elsewhere. Push heavy work into Rust via an
  `async fn` command; Rust is far more consistent across OS than JS on three different engines.

## React - State for Tauri Calls

- Every `invoke` needs all 3 states: loading, error, success/empty. Never leave the UI unresponsive while
  Rust works, never swallow a rejection silently.
- Clean up `listen`/`once` on unmount (call the returned unlisten function) - otherwise listeners leak and
  events fire multiple times after remounts.
- No repeated `invoke` in the render loop - `useEffect` with correct deps, or React Query/SWR if the
  project already uses one.

## Common Real-World Issues

- **CSP too strict** - an over-tight Content-Security-Policy in `tauri.conf.json` blocks valid resources
  (inline style/script, external fonts) and fails quietly in the console, easily misdiagnosed as a React
  component bug.
- **Missing permission fails quietly** - some plugins return a generic error or nothing at all, looking
  exactly like a Rust logic bug.

## Test

- **Rust**: unit test pure command logic - extract it out of the `#[tauri::command]` wrapper so tests
  don't need the Tauri runtime.
- **React**: mock `invoke` (never hit the real runtime in a unit test); cover loading/error/success.
- **Storage**: migrations against a prior-version fixture (see above).
- **Cross-OS**: for `#[cfg(target_os)]` or performance-sensitive features, confirm on all target OS or
  state which was skipped.
- **Integration**: with no desktop E2E infrastructure (WebDriver/`tauri-driver`) in the project, label it
  explicit manual/QA testing. Never set up E2E infrastructure unprompted - high setup cost affecting the
  whole project's test process; propose it with reasoning and wait for a decision.

## Boundaries

Doesn't decide UI/UX layout or flow (`ui-ux-design-skill`). Doesn't own Rust fundamentals unrelated to
Tauri - complex ownership/lifetimes, trait hierarchy design, `thiserror` error types, advanced tokio
(`rust-engineer`). Final review → `code-review-skill`.
