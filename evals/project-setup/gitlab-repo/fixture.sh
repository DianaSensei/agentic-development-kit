#!/usr/bin/env bash
# A small Node service hosted on a self-managed GitLab, with a pipeline of its
# own whose stages do not include `test` - the kit's review job must be pointed
# at one of them.
set -euo pipefail
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
mkdir -p src test
cat > package.json <<'JSON'
{
  "name": "inventory-service",
  "version": "1.4.0",
  "scripts": {
    "test": "node --test test/",
    "lint": "eslint src test"
  }
}
JSON
printf '{"lockfileVersion": 3}\n' > package-lock.json
cat > src/stock.js <<'JS'
export function reserve(stock, qty) {
  if (qty > stock.available) throw new Error("insufficient stock");
  return { ...stock, available: stock.available - qty };
}
JS
cat > test/stock.test.js <<'JS'
import { test } from "node:test";
import assert from "node:assert";
import { reserve } from "../src/stock.js";

test("reserve lowers availability", () => {
  assert.equal(reserve({ available: 5 }, 2).available, 3);
});
JS
cat > .gitlab-ci.yml <<'YML'
stages:
  - build
  - verify

unit-tests:
  stage: verify
  image: node:22
  script:
    - npm ci
    - npm test
YML
printf 'node_modules/\n' > .gitignore
git init -q && git add -A && git commit -qm "Inventory service"
git remote add origin https://gitlab.example.com/shop/inventory-service.git
