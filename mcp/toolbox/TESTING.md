# Local test databases for the toolbox MCP

`docker-compose.test.yml` in this directory starts 1 PostgreSQL, 2 MySQL instances, and 1
Redis, each seeded with a little sample data plus a read-only account (matching the "real
protection layer" this plugin's tools rely on - see `README.md`'s "Why the SQL templates
default to read-only" section).

This is a dev/testing convenience only - not part of the plugin, not something end users of
the plugin need. It's here to let you exercise the "add a connection" path (via
`examples/*.yaml.example` or the `toolbox-connections` skill) against real services without
needing a live DB.

## Start it

Needs Docker running (e.g. `colima start` if that's your Docker backend) and either
`docker-compose` or the `docker compose` plugin - use whichever is on your machine:

```bash
cd mcp/toolbox
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml ps   # wait for all to show "healthy"
```

## Add the connections

There are no pre-built connections to configure - add these the normal way (ask Claude Code,
or copy the matching `examples/*.yaml.example` template into the live connections directory
yourself). Values to use:

| Connection | host | port | database | user | password |
|---|---|---|---|---|---|
| PostgreSQL | `127.0.0.1` | `5432` | `testdb` | `toolbox_ro` | `toolbox_ro` |
| MySQL #1 | `127.0.0.1` | `3306` | `testdb1` | `toolbox_ro` | `toolbox_ro` |
| MySQL #2 | `127.0.0.1` | `3307` | `testdb2` | `toolbox_ro` | `toolbox_ro` |

Redis: address `127.0.0.1:6379`, no username/password.

The two MySQL instances are here specifically to test that adding a second connection of a
type you already have works cleanly - give them different names (e.g. `mysql_primary` /
`mysql_secondary`).

## Verify

After `claude mcp list` shows `toolbox` as `✔ Connected`, ask Claude Code (using whatever
names you gave the connections):

- "List the tables in the postgres database" → `users` (3 rows, one `inactive`)
- "List the tables in the mysql_primary database" → `orders` (3 rows)
- "List the tables in mysql_secondary" → `orders` (3 rows, independent data from the first)
- "Get the value of key session:abc123 in Redis" → `alice`
- "Get all fields of the Redis hash user:1" → `name`, `email`, `status`

## Tear down

```bash
docker-compose -f docker-compose.test.yml down       # keep seeded data for next time
docker-compose -f docker-compose.test.yml down -v     # also wipe it
```
