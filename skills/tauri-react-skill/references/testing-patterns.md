# Testing Patterns — Rust, React, Storage

What to test and when (see SKILL.md's Test section) — this file covers the actual test code.

## Rust: Testing Command Logic Without the Tauri Runtime

Extract the business logic out of the `#[tauri::command]` wrapper so it can be unit tested as a plain
function, with no Tauri runtime, no `AppHandle`, no async executor setup:

```rust
// Thin wrapper — not directly tested
#[tauri::command]
fn calculate_discount(price: f64, tier: String) -> Result<f64, CommandError> {
    apply_discount(price, &tier).map_err(CommandError::Validation)
}

// Pure function — this is what gets tested
fn apply_discount(price: f64, tier: &str) -> Result<f64, String> {
    if price < 0.0 {
        return Err("price must be non-negative".into());
    }
    let rate = match tier {
        "premium" => 0.10,
        "standard" => 0.0,
        other => return Err(format!("unknown tier: {other}")),
    };
    Ok(price * (1.0 - rate))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn applies_premium_discount() {
        assert_eq!(apply_discount(100.0, "premium").unwrap(), 90.0);
    }

    #[test]
    fn rejects_negative_price() {
        assert!(apply_discount(-1.0, "standard").is_err());
    }
}
```

For commands that need `tauri::State`, extract everything except the state access itself; test the
extracted function directly, and only cover the thin `State` unwrapping in a manual smoke test if a
full mock builder isn't already set up in the project.

## React: Mocking `invoke` (Never Call the Real Runtime in Unit Tests)

```typescript
// ProjectList.test.tsx (Vitest example — swap for Jest equivalents if that's the project's runner)
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ProjectList } from './ProjectList';

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

import { invoke } from '@tauri-apps/api/core';

describe('ProjectList', () => {
  beforeEach(() => vi.mocked(invoke).mockReset());

  it('shows loading then success', async () => {
    vi.mocked(invoke).mockResolvedValueOnce([{ id: 1, name: 'Demo' }]);
    render(<ProjectList />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Demo')).toBeInTheDocument());
  });

  it('shows an error state when invoke rejects', async () => {
    vi.mocked(invoke).mockRejectedValueOnce({ kind: 'Internal', message: 'boom' });
    render(<ProjectList />);

    await waitFor(() => expect(screen.getByText(/something went wrong/i)).toBeInTheDocument());
  });

  it('shows an empty state distinctly from loading/error', async () => {
    vi.mocked(invoke).mockResolvedValueOnce([]);
    render(<ProjectList />);

    await waitFor(() => expect(screen.getByText(/no projects yet/i)).toBeInTheDocument());
  });
});
```

Covering all three states (loading/error/success-or-empty) per component that calls `invoke` is the
concrete test-side check for the MUST DO rule in SKILL.md's Constraints section — a component that only
has a happy-path test hasn't actually verified the state machine it's supposed to implement.

## Storage: Migration Fixture Testing

Testing a migration only against a freshly created empty DB doesn't prove it's safe for users who
already have data from a previous app version — build the fixture from the prior schema explicitly:

```rust
#[cfg(test)]
mod migration_tests {
    use super::*;

    fn seed_v1_schema(conn: &rusqlite::Connection) {
        conn.execute_batch(
            "CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
             INSERT INTO projects (name) VALUES ('Legacy Project');",
        ).unwrap();
    }

    #[test]
    fn migration_v2_preserves_existing_rows_and_adds_column() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        seed_v1_schema(&conn); // starts from the OLD schema, not empty

        conn.execute_batch(include_str!("../../migrations/002_add_archived.sql")).unwrap();

        let name: String = conn
            .query_row("SELECT name FROM projects WHERE id = 1", [], |row| row.get(0))
            .unwrap();
        assert_eq!(name, "Legacy Project"); // old data survived

        let archived: i64 = conn
            .query_row("SELECT archived FROM projects WHERE id = 1", [], |row| row.get(0))
            .unwrap();
        assert_eq!(archived, 0); // new column got the expected default
    }
}
```

## E2E: Desktop Integration (Manual/QA vs. Automated)

If the project has no desktop E2E infrastructure yet, don't build one as a side effect of a feature
task — write the manual QA steps instead and flag automation as a proposal:

```markdown
## Manual QA — Import Flow (no automated E2E infra yet)
1. Launch the app on macOS, Windows, and Linux builds from CI.
2. Trigger Import from the toolbar; select a >50MB test file.
3. Confirm progress events update the UI (see `ipc-patterns.md`'s progress example) without freezing.
4. Confirm the imported data appears in the list on all 3 OS.

Proposal: automate this with `@wdio/tauri-service` (see `cross-os-patterns.md`) — not set up without
sign-off, since it adds CI time and a new dependency surface to maintain.
```
