# Analysis Process

## Step 0: Identify the Stack — always FIRST, never guess

```bash
Glob: **/pom.xml **/build.gradle           # Java/Spring
Glob: **/Cargo.toml                        # Rust/Tauri
Glob: **/package.json                      # Node/TypeScript
Glob: **/requirements.txt **/pyproject.toml # Python
Glob: **/go.mod                            # Go
```

Read whichever manifest is found to confirm the exact framework/version (e.g. `spring-boot-starter-web`
in `pom.xml`, `tauri` in `Cargo.toml`) before picking the Glob/Grep patterns below — a single project can
have multiple stacks at once (e.g. a Java/Spring backend with a Tauri/React frontend), in which case
repeat this process for each part.

## Step 1: Entry Points & Routes

```bash
# Java/Spring
Glob: **/src/main/java/**/*Application.java   # entry point
Glob: **/src/main/java/**/*Controller.java
Grep: @RestController|@Controller|@GetMapping|@PostMapping|@RequestMapping

# Rust/Tauri
Glob: **/src-tauri/src/main.rs
Grep: #\[tauri::command\]|invoke_handler

# Node/TypeScript
Glob: **/main.{ts,js}
Glob: **/routes/**/*.{ts,js}
Glob: **/controllers/**/*.{ts,js}
Grep: @Controller|@Get|@Post|router\.|app\.get

# Python
Glob: **/main.py **/app.py **/asgi.py **/wsgi.py
Grep: @app\.route|@router\.|APIRouter|urlpatterns

# Go
Glob: **/main.go
Grep: http\.HandleFunc|gin\.Default|mux\.Router
```

## Step 2: Data Models

```bash
# Java/Spring (JPA)
Glob: **/src/main/java/**/entity/**/*.java **/model/**/*.java
Grep: @Entity|@Table|@Id

# Rust
Glob: **/src/models/**/*.rs
Grep: struct .*\{|#\[derive\(.*Serialize

# Node/TypeScript (Prisma/TypeORM/Sequelize)
Glob: **/models/**/*.{ts,js} **/schema.prisma **/migrations/**/*

# Python (SQLAlchemy/Django ORM)
Grep: class .*\(.*Model\)|db\.Column|models\.Model

# Any stack — raw migration/schema files
Glob: **/migrations/**/* **/*.sql
```

## Step 3: Business Logic

```bash
# Java/Spring
Glob: **/service/**/*.java
Grep: @Service|@Transactional

# Rust
Grep: pub fn|impl .* for

# Node/TypeScript
Glob: **/services/**/*.{ts,js}
Grep: async.*function|export.*class

# Python
Grep: def .*\(self|async def
```

## Step 4: Authentication & Security

```bash
# Java/Spring
Grep: @PreAuthorize|SecurityFilterChain|JwtAuthenticationFilter

# Tauri
Grep: capabilities|allowlist|permissions

# Node/TypeScript
Glob: **/auth/**/* **/guards/**/*
Grep: @Guard|middleware|passport|jwt

# Python
Grep: @login_required|permission_classes|jwt
```

## Step 5: External Integrations

```bash
# Java
Grep: RestTemplate|WebClient|@FeignClient

# Rust/Tauri
Grep: reqwest::|tauri_plugin_http

# Node/TypeScript
Grep: fetch\(|axios\.|HttpService

# Python
Grep: requests\.|httpx\.|aiohttp
```

## Step 6: Configuration

```bash
Glob: **/application.yml **/application.properties   # Java/Spring
Glob: **/tauri.conf.json                              # Tauri
Glob: **/*.config.{ts,js} **/.env*                     # Node
Glob: **/settings.py **/.env                          # Python (Django)
Glob: **/config/**/*                                   # any stack
```

## Quick Reference — Entry Point by Stack

| Stack | Entry Point Pattern | Route/Controller Pattern |
|-------|---------------------|---------------------------|
| Java/Spring | `*Application.java` (`@SpringBootApplication`) | `@RestController`, `@GetMapping`/`@PostMapping` |
| Rust/Tauri | `src-tauri/src/main.rs` | `#[tauri::command]` |
| Node/TypeScript | `main.ts`, `app.ts`, `index.ts` | `@Controller`/`@Get` (NestJS), `router.`/`app.get` (Express) |
| Python | `main.py`, `app.py`, `manage.py` | `@app.route` (Flask), `APIRouter` (FastAPI), `urlpatterns` (Django) |
| Go | `main.go` | `http.HandleFunc`, `gin.Default()` |
