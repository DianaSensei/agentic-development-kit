# Convention checks

`checks` in `.claude/quality-check.config.json` lists the project's own linters, formatters and rule
scripts. `hooks/check-conventions.sh` runs the file-scoped ones on every file Claude writes and hands a
failure straight back to it; the workflows run the project-scoped ones with the tests; CI runs them
all. A convention a machine can check is enforced that way, not by a sentence in `CLAUDE.md` that a
long session can forget.

```json
"checks": [
  {"name": "ruff", "match": "\\.py$", "run": "ruff check --quiet {file}"},
  {"name": "ruff-format", "match": "\\.py$", "run": "ruff format --check --quiet {file}"},
  {"name": "types", "scope": "project", "run": "npx tsc --noEmit", "timeout": 300}
]
```

| Key | Meaning |
|---|---|
| `name` | Shown in the report to Claude |
| `run` | A shell command run from the repository root; `{file}` becomes the written file's path, quoted. Exit 0 passes |
| `match` | ERE on the repo-relative path; only matching files run the check (`scope: file`) |
| `scope` | `file` (default): after each write, on that file. `project`: the whole repository, run with the tests |
| `timeout` | Seconds, default 20. A check that needs longer belongs at `project` scope |

## Detect, never introduce

A check is written only for a tool the repository already uses: its configuration file or its entry
in the manifest is the evidence. Adding a new linter or formatter is a team decision - it reformats or
flags existing code - so list it under follow-ups in the report instead.

| Evidence | Checks (file scope unless marked) |
|---|---|
| `ruff` in `pyproject.toml`/`ruff.toml` | `ruff check --quiet {file}` on `\.py$`; `ruff format --check --quiet {file}` when the project formats with ruff |
| `black` configured | `black --check --quiet {file}` on `\.py$` |
| `mypy`/`pyright` configured | `mypy .` / `pyright` - **project** |
| ESLint config (`eslint.config.*`, `.eslintrc*`) | `npx eslint --no-warn-ignored {file}` on `\.(js|jsx|ts|tsx|mjs|cjs)$` |
| Prettier config (`.prettierrc*`, `prettier` key) | `npx prettier --check {file}` on the extensions it formats |
| `tsconfig.json` | `npx tsc --noEmit` - **project** |
| `go.mod` | `gofmt -l {file} \| (! grep .)` on `\.go$`; `go vet ./...` - **project** |
| `Cargo.toml` | `rustfmt --check --edition <edition> {file}` on `\.rs$`; `cargo clippy -q -- -D warnings` - **project** |
| Spotless / Checkstyle / PMD / Error Prone in `pom.xml` or `build.gradle*` | The build's own goal - `mvn -q spotless:check`, `./gradlew -q checkstyleMain` - **project**, `timeout` 300 |
| ArchUnit tests | They run with the tests; nothing extra |
| `.semgrep.yml` / `.semgrep/` | `semgrep --error --quiet --config .semgrep {file}` |
| `sqlfluff` configured | `sqlfluff lint {file}` on `\.sql$` |
| `shellcheck` used in CI | `shellcheck {file}` on `\.(sh|bash)$` |

Use the command the project itself runs (its `Makefile`, `package.json` scripts, CI steps) when one
exists: the same flags, the same config. Prefer checking one file over the whole tree at file scope -
the hook runs after every write.

**The project's own rules.** A rule the linters do not know - "log through `app.log`", "no raw SQL
outside `repository/`", "every public handler has an authorization check" - is still a check when a
script or a semgrep rule can see it. When `CLAUDE.md` or `REVIEW.md` already states such a rule, say in
the report that it could become one, and offer to write it; never write the rule unasked.

## CI

The checks only bind if CI runs them too: a person's commit never passes through the hook. When the
project's CI does not already run a listed check, add it to the report's follow-ups with the exact
step, in the CI's own file - do not add a job.
