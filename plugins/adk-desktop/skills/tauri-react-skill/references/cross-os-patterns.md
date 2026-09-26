# Cross-OS Implementation Patterns

Principles (why cross-OS behavior/performance consistency matters) live in SKILL.md. This file covers
the actual code and CI setup.

## `#[cfg(target_os)]` - Divergent Logic

```rust
#[cfg(target_os = "macos")]
fn default_shortcut_modifier() -> &'static str {
    "Cmd"
}

#[cfg(any(target_os = "windows", target_os = "linux"))]
fn default_shortcut_modifier() -> &'static str {
    "Ctrl"
}
```

Handle all target OS explicitly - if the app targets macOS + Windows + Linux, write all three arms (or
the `any(...)` grouping above), not just the two you remembered. A missing arm is a compile error for
an exhaustive `match`, but `#[cfg]` functions fail silently (the function just doesn't exist on the
unhandled OS) if you forget one entirely - this is the actual footgun, not the compiler catching it for
you.

## OS-Correct Paths (Never Hardcode)

```rust
use tauri::Manager;

#[tauri::command]
fn get_export_dir(app: tauri::AppHandle) -> Result<String, CommandError> {
    // Resolves to the right location per OS automatically:
    // macOS: ~/Library/Application Support/<bundle-id>
    // Windows: C:\Users\<user>\AppData\Roaming\<bundle-id>
    // Linux: ~/.local/share/<bundle-id> (XDG)
    let dir = app.path().app_data_dir().map_err(|_| CommandError::Internal)?;
    Ok(dir.to_string_lossy().into_owned())
}
```

```rust
// WRONG - breaks on Windows (backslash separator, different root) and assumes a
// Unix-style home directory layout that doesn't hold on Windows.
let bad_path = format!("{}/Library/App Support/myapp", std::env::var("HOME").unwrap());
```

## Normalizing Behavior That Would Otherwise Drift by OS

```rust
// Line endings: normalize on read so downstream logic doesn't have to branch on OS.
fn normalize_line_endings(text: &str) -> String {
    text.replace("\r\n", "\n")
}

// Sort order: use an explicit, OS-independent comparator instead of relying on
// the OS's default string collation (which differs between macOS/Windows/Linux
// locale libraries and can reorder the same list differently per machine).
fn sort_by_name(items: &mut [Project]) {
    items.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
}
```

```typescript
// Dates/numbers: format explicitly with a fixed locale instead of the browser/OS
// default (`toLocaleDateString()` with no args resolves to the OS locale, which
// varies machine to machine even for the same app build).
const formatted = new Intl.DateTimeFormat('en-US', {
  year: 'numeric', month: '2-digit', day: '2-digit',
}).format(date);
```

## CI: Building and Testing on All Target OS

Use `tauri-apps/tauri-action` with a GitHub Actions matrix so every push actually builds on macOS,
Windows, and Linux - not just whichever OS the developer's machine happens to be.

```yaml
# .github/workflows/build.yml
name: build
on: [push, pull_request]

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - platform: 'macos-latest'   # Apple Silicon
            args: '--target aarch64-apple-darwin'
          - platform: 'macos-latest'   # Intel
            args: '--target x86_64-apple-darwin'
          - platform: 'ubuntu-22.04'
            args: ''
          - platform: 'windows-latest'
            args: ''
    runs-on: ${{ matrix.platform }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: actions/setup-node@v6
        with:
          node-version: lts/*
      - name: install Linux webview deps
        if: matrix.platform == 'ubuntu-22.04'
        run: |
          sudo apt-get update
          sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
      - run: npm ci
      - uses: tauri-apps/tauri-action@v1
        with:
          args: ${{ matrix.args }}
```

A build that only succeeds on the developer's OS but fails in this matrix (missing WebKitGTK deps on
Linux is the most common case) is a real, frequently-hit failure mode - don't treat "it built on my
machine" as done for a cross-OS-targeted app.

## Desktop E2E Across OS (WebdriverIO + Tauri)

The current recommended setup is WebdriverIO's `@wdio/tauri-service`, which wraps `tauri-driver`
(WebDriver server for Tauri's native webview) and supports Windows, Linux, and macOS:

```typescript
// wdio.conf.ts
export const config: WebdriverIO.Config = {
  services: [
    ['tauri', {
      appBinaryPath: './src-tauri/target/release/my-tauri-app',
      driverProvider: 'embedded',
    }],
  ],
  specs: ['./e2e/**/*.spec.ts'],
};
```

```jsonc
// package.json
{ "scripts": { "test:e2e": "wdio run wdio.conf.ts" } }
```

This still needs the compiled binary per OS, so E2E in CI runs per matrix leg after the build step, not
as a single cross-platform job - and per SKILL.md's boundary, don't set this infrastructure up
unprompted if the project doesn't already have it; propose it and wait for the user's decision.
