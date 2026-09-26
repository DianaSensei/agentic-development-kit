# Local Storage Implementation - SQL, Store, FS

Selection criteria and schema/migration design principles live in SKILL.md's **Local/Offline Storage
Design** section. This file covers the actual plugin code.

## SQLite (`tauri-plugin-sql`)

### Registering Migrations

```rust
use tauri_plugin_sql::{Builder, Migration, MigrationKind};

fn main() {
    let migrations = vec![
        Migration {
            version: 1,
            description: "create_projects_table",
            sql: include_str!("../migrations/001_create_projects.sql"),
            kind: MigrationKind::Up,
        },
        Migration {
            version: 2,
            description: "add_projects_archived_column",
            sql: include_str!("../migrations/002_add_archived.sql"),
            kind: MigrationKind::Up,
        },
    ];

    tauri::Builder::default()
        .plugin(
            Builder::default()
                .add_migrations("sqlite:app.db", migrations)
                .build(),
        )
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

Migrations run automatically on startup, in version order, and Tauri tracks which versions already
ran - never edit a migration that has already shipped to users; add a new one instead (an edited
migration won't re-run on machines that already applied the old version, silently diverging from fresh
installs).

### Enabling WAL Mode (avoids "database is locked")

```sql
-- migrations/001_create_projects.sql
PRAGMA journal_mode=WAL;

CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Querying from a Command

```rust
use tauri_plugin_sql::{Sql};
use tauri::AppHandle;

#[tauri::command]
async fn list_projects(app: AppHandle) -> Result<Vec<Project>, CommandError> {
    // Access pattern varies slightly by plugin version - check the version pinned in
    // Cargo.toml against https://github.com/tauri-apps/plugins-workspace/tree/v2/plugins/sql
    // before copying this verbatim; the shape (open pool by connection string, query, map rows) is stable.
    let pool = app.state::<Sql>(); // illustrative - resolve the actual DB handle type/version in use
    // ...
    Ok(vec![])
}
```

> The SQL plugin's exact Rust-side query API has shifted across 2.x releases. Confirm the pinned
> version in `Cargo.toml` and check that version's docs on docs.rs before writing query code - don't
> assume the frontend-side `Database.load()/execute()/select()` JS API (which is stable) mirrors 1:1
> onto whatever the Rust side looks like at that version.

### Frontend Query (JS API - stable across 2.x)

```typescript
import Database from '@tauri-apps/plugin-sql';

const db = await Database.load('sqlite:app.db');

const projects = await db.select<Project[]>(
  'SELECT id, name, archived FROM projects WHERE archived = $1',
  [0],
);

await db.execute(
  'INSERT INTO projects (name) VALUES ($1)',
  ['New Project'],
);
```

## Key-Value Store (`tauri-plugin-store`)

```rust
use tauri_plugin_store::StoreExt;
use serde_json::json;

#[tauri::command]
fn save_preference(app: tauri::AppHandle, key: String, value: serde_json::Value) -> Result<(), CommandError> {
    let store = app.store("settings.json").map_err(|_| CommandError::Internal)?;
    store.set(key, value);
    store.save().map_err(|_| CommandError::Internal)?; // flush to disk explicitly
    Ok(())
}
```

Values must be `serde_json::Value` - this is what makes them compatible with the JS-side bindings.
`store.set()` updates the in-memory store; `store.save()` is what actually persists to disk. Forgetting
`save()` is a common bug - the value looks correct for the rest of the session but is lost on restart.

```typescript
import { load } from '@tauri-apps/plugin-store';

const store = await load('settings.json');
await store.set('theme', 'dark');
await store.save();
const theme = await store.get<string>('theme');
```

## Raw Files (`tauri-plugin-fs`)

```rust
use tauri_plugin_fs::FsExt;

#[tauri::command]
fn export_report(app: tauri::AppHandle, filename: String, contents: String) -> Result<(), CommandError> {
    // filename comes from user input - never join it into a path without validating it
    // stays inside the allowed base dir (path traversal risk, e.g. "../../etc/passwd").
    if filename.contains("..") || filename.contains('/') || filename.contains('\\') {
        return Err(CommandError::Validation("invalid filename".into()));
    }

    let path = app
        .path()
        .app_data_dir()
        .map_err(|_| CommandError::Internal)?
        .join("exports")
        .join(&filename);

    std::fs::create_dir_all(path.parent().unwrap())?;
    std::fs::write(path, contents)?;
    Ok(())
}
```

The actual read/write must still be permitted by the `fs:*` scope declared in `capabilities/*.json` (see
`capabilities-examples.md`) - the Rust-side validation above prevents path traversal within the allowed
scope, it does not replace the capability scope itself.

## Backup-Before-Migrate Fallback (desktop-specific safety net)

```rust
fn backup_db_before_migration(app_data_dir: &std::path::Path) -> std::io::Result<()> {
    let db_path = app_data_dir.join("app.db");
    if db_path.exists() {
        let backup_path = app_data_dir.join(format!(
            "app.db.bak.{}",
            chrono::Utc::now().format("%Y%m%d%H%M%S")
        ));
        std::fs::copy(&db_path, &backup_path)?;
    }
    Ok(())
}
```

Call this before `add_migrations` runs (i.e. before `.build()` on the SQL plugin) when shipping a
migration to a mechanism already holding real user data - cheap insurance against a migration bug
bricking the app on next launch.
