---
name: elasticsearch-skill
description: In-depth Elasticsearch knowledge - index/mapping design, analyzers, Query DSL, aggregations, reindex strategy, shard/replica sizing. Use when the feature needs full-text search or analysis/aggregation over large datasets.
metadata:
  domain: database
  triggers: Elasticsearch, full-text search, index mapping, analyzer, Query DSL, aggregation, reindex, shard, replica, autocomplete, fuzzy search, search relevance, log analytics
  role: specialist
  scope: design-and-optimization
  output-format: analysis-and-code
  related-skills: database-skill, java-spring-skill, testcontainers-skill, monitoring-expert
---

# Elasticsearch

## Discover
Confirm the project already uses ES via its dependency (`spring-data-elasticsearch` or a direct client), read the existing index/mapping, and check the ES version in use (major versions differ significantly).

## When It Fits / When It Doesn't
Fits: full-text search, log analytics, aggregation over large datasets that needs to be fast. **Do NOT use ES as the primary source of truth** - always keep one primary DB (RDBMS/Mongo) holding the canonical data, with ES only as a derived index synced from it. That sync has latency (eventual consistency, `refresh_interval` defaults to 1s) - if the business needs to read the just-written data immediately after a write, don't rely on ES for that path.

## Common Real-World Issues
- **Cluster health**: `yellow` = missing a replica (still readable/writable, reduced fault tolerance), `red` = missing a primary shard (that portion of data is unreadable/unwritable, potentially lost) - monitor cluster health continuously as shard/replica counts are designed, not just set once at the start and forgotten.
- **Mapping explosion**: uncontrolled dynamic mapping (new fields auto-generated continuously from inconsistent data) can hit the `index.mapping.total_fields.limit` and cause write failures - this is the main reason to prefer explicit mapping over dynamic mapping for important fields.
- **Circuit breaker (memory)**: aggregating/sorting on an unbounded-size field can trigger a `CircuitBreakingException` (heap overflow) - bound response size, use `search_after` instead of `from`/`size` for deep pagination (deep pagination also gets progressively slower since ES has to load and sort every result from the start up to the offset).

## Index & Mapping Design
- Decide which fields need full-text search (`text` + analyzer) vs. which only need exact match/filter/sort (`keyword`) - using the wrong type causes incorrect search results or wastes resources.
- Prefer explicit mapping over relying on dynamic mapping for important fields (dynamic mapping can infer the wrong data type).
- Name indices with a version/date convention if using an alias-based reindex strategy (e.g. `products_v2`, with alias `products` pointing at the latest).

## Analyzer
- Choose an analyzer that fits the content's language (standard, or a language-specific analyzer if diacritics/compound words need special handling).
- Build a custom analyzer (tokenizer + filter) when a specific search requirement exists (synonyms, n-gram for autocomplete) - design and apply it once the search requirement is clear (e.g. "support fuzzy search/autocomplete"), stating the accepted complexity/indexing-performance trade-off briefly in the report rather than asking beforehand.

## Query DSL
- Use the right query type for the need: `match`/`multi_match` for full-text, `term`/`terms` for exact match, `bool` to combine must/should/filter (prefer `filter` for conditions that don't need a relevance score - faster because it's cacheable).
- Avoid leading-wildcard/regex queries (`*abc`) - extremely slow; consider redesigning the mapping (n-gram) if this kind of search is needed frequently.

## Aggregation
- Distinguish bucket aggregations (group by) from metric aggregations (sum/avg/min/max) - nest them in the right order for the analysis needed.
- Consider `cardinality` (approximate distinct count) instead of an exact count on large datasets when absolute precision isn't required (trades accuracy for speed).

## Reindex Strategy
When a mapping change is needed (breaking change): create a new index, reindex the old data into it, switch the alias to the new index, delete the old index once confirmed stable - do NOT edit the mapping directly on a running index (many mapping changes aren't allowed once a field already exists).

## Shard & Replica (note, and a trade-off discussion only if the impact is large)
Shard count is fixed at index creation and hard to change later (requires a reindex) - weigh it carefully against expected data volume. Replica count affects availability and read speed, not write speed.

## Test
Testcontainers Elasticsearch for integration tests - test that mappings produce the expected data types, test that queries return correct results, test that aggregations produce correct figures.

## Boundary
For a NEW index, or one with no real data yet, design the best mapping/analyzer for the requirement without asking back. Never change the mapping of an index ALREADY RUNNING in production with real data without a reindex plan - always present the migration plan and wait for user approval, since this is a hard-to-reverse change with real downtime/read-availability risk during reindex.

## Knowledge Reference

Explicit vs. dynamic mapping, `text` vs. `keyword` fields, analyzers and custom tokenizer/filter chains, Query DSL (`match`, `term`, `bool`, `filter` context), bucket vs. metric aggregations, alias-based reindex strategy, cluster health (green/yellow/red), shard/replica sizing.
