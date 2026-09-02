# IPC Patterns - Commands, State, and Events

## Command Returning `Result<T, E>`

The error type `E` must implement `serde::Serialize` - this is the single most common gotcha with
Tauri v2 commands. A plain `std::error::Error` type does NOT cross the IPC boundary; if it doesn't
serialize, the command fails at compile time (or, with `Box<dyn Error>`, at runtime with an opaque
message) instead of giving the frontend a structured error.

```rust
use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
#[serde(tag = "kind", content = "message")]
pub enum CommandError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("internal error")]
    Internal,
}

// io::Error, sqlx::Error, etc. don't implement Serialize - convert explicitly,
// and don't leak internal details (paths, SQL, stack traces) to the frontend.
impl From<std::io::Error> for CommandError {
    fn from(err: std::io::Error) -> Self {
        tracing::error!(?err, "io error in command");
        CommandError::Internal
    }
}

#[tauri::command]
fn get_project(id: u64) -> Result<Project, CommandError> {
    if id == 0 {
        return Err(CommandError::Validation("id must be non-zero".into()));
    }
    // ...
    Ok(Project { id, name: "Demo".into() })
}
```

```typescript
// React side - invoke rejects with the serialized CommandError, not a generic Error
import { invoke } from '@tauri-apps/api/core';

try {
  const project = await invoke<Project>('get_project', { id: 42 });
} catch (err) {
  const e = err as { kind: string; message: string };
  if (e.kind === 'Validation') {
    // show inline field error
  }
}
```

## Async Commands (Don't Block the Main Thread)

```rust
#[tauri::command]
async fn import_large_file(path: String) -> Result<ImportSummary, CommandError> {
    // Runs on Tokio's async runtime, not the UI-blocking main thread.
    let data = tokio::fs::read(&path).await?;
    let summary = tokio::task::spawn_blocking(move || parse_and_validate(&data))
        .await
        .map_err(|_| CommandError::Internal)?;
    Ok(summary)
}
```

## Sharing State Across Commands (`tauri::State`)

```rust
use std::sync::Mutex;
use tauri::{Manager, State};

struct AppState {
    counter: Mutex<i64>,
}

#[tauri::command]
fn increment(state: State<'_, AppState>) -> i64 {
    let mut counter = state.counter.lock().unwrap();
    *counter += 1;
    *counter
}

fn main() {
    tauri::Builder::default()
        .manage(AppState { counter: Mutex::new(0) })
        .invoke_handler(tauri::generate_handler![increment, get_project])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

Prefer async-aware locks (`tokio::sync::Mutex`) over `std::sync::Mutex` when the lock is held across an
`.await` point inside an async command - holding a `std::sync::Mutex` guard across `.await` can
deadlock the async runtime.

## Events for Streaming/Progress (v2 API)

Tauri v2 renamed the event API - `emit_all` (v1) is gone; use the `Emitter`/`Listener` traits.

```rust
use tauri::{AppHandle, Emitter};
use serde::Serialize;

#[derive(Clone, Serialize)]
struct ImportProgress {
    processed: usize,
    total: usize,
}

#[tauri::command]
async fn import_with_progress(app: AppHandle, path: String) -> Result<(), CommandError> {
    let total = 100;
    for processed in 0..=total {
        // ... do a chunk of work ...
        app.emit("import://progress", ImportProgress { processed, total })
            .map_err(|_| CommandError::Internal)?;
    }
    Ok(())
}

// Targeting one specific window instead of broadcasting to all:
// app.emit_to("main", "import://progress", payload)?;
```

```typescript
import { listen } from '@tauri-apps/api/event';
import { useEffect, useState } from 'react';

function useImportProgress() {
  const [progress, setProgress] = useState<{ processed: number; total: number } | null>(null);

  useEffect(() => {
    const unlistenPromise = listen<{ processed: number; total: number }>(
      'import://progress',
      (event) => setProgress(event.payload),
    );

    // MUST unlisten on unmount - otherwise listeners pile up across remounts.
    return () => {
      unlistenPromise.then((unlisten) => unlisten());
    };
  }, []);

  return progress;
}
```

## `useInvoke` Pattern - Loading/Error/Success in One Hook

Every `invoke` call needs all three states (see SKILL.md's React section). A small shared hook avoids
repeating the same three `useState` calls in every component:

```typescript
import { useCallback, useState } from 'react';
import { invoke, InvokeArgs } from '@tauri-apps/api/core';

type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };

function useInvoke<T>(command: string) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' });

  const run = useCallback(async (args?: InvokeArgs) => {
    setState({ status: 'loading' });
    try {
      const data = await invoke<T>(command, args);
      setState({ status: 'success', data });
      return data;
    } catch (err) {
      setState({ status: 'error', error: String(err) });
      throw err;
    }
  }, [command]);

  return { state, run };
}
```
