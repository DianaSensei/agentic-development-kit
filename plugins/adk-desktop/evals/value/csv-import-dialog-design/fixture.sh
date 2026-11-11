#!/usr/bin/env bash
# A dialog design for a desktop app. Measures what ui-ux-design-skill adds: system status, error recovery, a way back, keyboard use and window resizing.
set -euo pipefail
mkdir -p src-tauri src && echo '{"productName":"Ledger"}' > src-tauri/tauri.conf.json && echo "export default function App() { return null }" > src/App.tsx
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
