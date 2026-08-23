# Java Code Style and Formatting

Formatting and naming conventions for Java code, based on the Google Java Style Guide — the most widely
adopted baseline for modern Java/Spring Boot projects and the basis for the `google-java-format` tool.

**The overriding rule**: if the project already has an established style (its own Checkstyle config, a
different formatter, a documented team convention), follow that instead — never impose Google Style over
an existing, working convention mid-task. Apply this guide as the default only for a project with no
established style yet, and say so explicitly when introducing it.

## Formatting

- **Indentation**: 2 spaces, never tabs. Continuation lines indent by 4 additional spaces.
- **Line length**: 100 characters max.
- **Braces (K&R/Egyptian style)**: opening brace on the same line as the statement; never omit braces
  for a single-statement `if`/`for`/`while`, even a one-liner.
  ```java
  if (condition) {
    doSomething();
  } else {
    doOtherThing();
  }
  ```
- **One top-level class per file**; filename matches the public class name exactly.
- **Imports**: no wildcard imports (`import java.util.*;`). Static imports first, then regular imports,
  each block sorted lexicographically (ASCII order) — no blank line separating sub-groups within a
  block (unlike some other style guides that split `java.*`/third-party/project imports into separate
  blocks).
- **Numeric literals**: uppercase suffix (`1000L`, not `1000l` — lowercase `l` is easily misread as the
  digit `1`).
- **Arrays**: C-style declaration on the type (`String[] args`), never `String args[]`.

## Naming

| Kind | Convention | Example |
| --- | --- | --- |
| Class / Interface / Enum / Annotation | `UpperCamelCase` | `OrderService`, `PaymentStatus` |
| Method / field / parameter / local variable | `lowerCamelCase` | `calculateTotal`, `orderId` |
| Constant (`static final`, truly immutable) | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Package | all lowercase, no underscores | `com.example.order` |
| Type parameter (generic) | single uppercase letter, optionally + digit | `T`, `E`, `K`, `V`, `T2` |

A `static final` field only qualifies as a "constant" (and gets `UPPER_SNAKE_CASE`) if its contents are
deeply immutable and its identity never observably changes — a `static final List` that's still mutated
is `lowerCamelCase`, not a constant, regardless of the modifier.

## Rules Commonly Missed in Review

- **`@Override`** is mandatory on every method that overrides a superclass method or implements an
  interface method — no exceptions, including for interface implementations.
- **Modifier order**: `public protected private abstract default static final transient volatile
  synchronized native strictfp` — in that sequence.
- **No finalizers** (`Object.finalize()`) — use `try-with-resources`/`AutoCloseable` for cleanup.
- **Javadoc required** on every public class and public method, except trivial overrides and
  self-explanatory getters/setters (see `code-documenter` for the actual doc-comment content standard —
  this file governs formatting/naming, not documentation completeness).
- **Switch statements**: every case falls through explicitly commented `// fall through` if intentional
  (or, preferably in modern Java, use arrow-form `switch` expressions to make fallthrough impossible by
  construction).

## Tooling — Enforce Automatically, Don't Rely on Manual Review

Style drifts the moment it depends on every reviewer catching every violation by eye. Wire it into the
build instead:

- **`google-java-format`** — the canonical formatter for this style; typically run via **Spotless**
  rather than invoked directly, so both format-checking and auto-fixing go through one Maven/Gradle
  goal.

  ```xml
  <!-- pom.xml -->
  <plugin>
    <groupId>com.diffplug.spotless</groupId>
    <artifactId>spotless-maven-plugin</artifactId>
    <version>2.43.0</version>
    <configuration>
      <java>
        <googleJavaFormat/>
        <removeUnusedImports/>
      </java>
    </configuration>
    <executions>
      <execution>
        <goals><goal>check</goal></goals>
        <phase>verify</phase>
      </execution>
    </executions>
  </plugin>
  ```
  `mvn spotless:apply` auto-fixes; `mvn spotless:check` (wired to the `verify` phase above) fails the
  build on drift — put this in CI so style never depends on a human catching it.

- **Checkstyle with `google_checks.xml`** — catches what a formatter can't auto-fix: naming violations,
  missing `@Override`, Javadoc coverage. Use alongside Spotless, not instead of it — Spotless fixes
  whitespace/layout, Checkstyle flags things that need a human decision.

- **`.editorconfig`** — keeps IDEs consistent on indent size/style and line endings *before* a commit
  even reaches the formatter check, reducing noisy diffs from IDE auto-formatting disagreements between
  team members.

  ```ini
  [*.java]
  indent_style = space
  indent_size = 2
  max_line_length = 100
  charset = utf-8
  insert_final_newline = true
  trim_trailing_whitespace = true
  ```

## Applying This Skill

1. Check for an existing formatter config (`.editorconfig`, a Spotless/Checkstyle block in
   `pom.xml`/`build.gradle`, a documented style in `CLAUDE.md`) before writing code — follow it.
2. If none exists and the codebase already has a de facto style (consistent brace/naming pattern across
   existing files even without a formal config), match that instead of introducing Google Style
   unprompted.
3. Only when neither exists — a genuinely fresh project — default to Google Java Style Guide as above,
   and mention in the report that this was the default applied, so the team can override it explicitly
   if they'd rather use something else.
