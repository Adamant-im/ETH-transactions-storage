# Database and Indexes

Everything the indexer produces lives in one PostgreSQL database that you own. This page documents the schema, the checkpoint, the index strategy, and how to size the disk.

## Schema

`create_tables.sql` creates all objects. It is idempotent, so re-running it on an existing database is safe and never deletes transaction data.

### `public.ethtxs`

The single storage table.

```sql
CREATE TABLE IF NOT EXISTS public.ethtxs
(
    time integer,
    txfrom citext,
    txto citext,
    gas bigint,
    gasprice bigint,
    block integer,
    txhash citext,
    value numeric,
    contract_to citext,
    contract_value citext
);
```

Column semantics and value encodings are documented in the [API reference](./api.md#transaction-object). Two design choices are worth calling out:

- Address and hash columns use `citext` so lookups are case-insensitive without a `LOWER()` call on every row. A functional index would work too, but `citext` keeps client queries simple and lets the plain B-tree indexes serve mixed-case input
- There is no primary key and no uniqueness constraint. Inserts stay cheap during backfill, and duplicate protection comes from the startup routine that rewinds and re-processes the highest block

### `public.sync_state`

```sql
CREATE TABLE IF NOT EXISTS public.sync_state
(
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    last_block integer NOT NULL
);
```

A one-row table holding the highest fully processed block. The `CHECK (singleton)` constraint on a boolean primary key makes a second row impossible, so `ON CONFLICT (singleton) DO UPDATE` is always the right upsert.

It exists because `MAX(block)` is not a checkpoint. Empty blocks produce no rows, and with the [address filter](../guide/address-filter.md) enabled most blocks produce no rows, so a `MAX(block)`-based indexer would rescan the same range forever.

Each block is inserted and its checkpoint advanced in the same database transaction, so the two can never disagree.

### `public.aval`

```sql
CREATE TABLE IF NOT EXISTS public.aval
(
    status boolean DEFAULT true
);
```

A single `true` row backing the `/aval` availability probe.

### `public.max_block`

```sql
CREATE OR REPLACE VIEW public.max_block AS
SELECT
    GREATEST(
        (SELECT MAX(block) FROM public.ethtxs),
        (SELECT last_block FROM public.sync_state WHERE singleton = true)
    ) AS max,
    '2.5.0'::text AS version;
```

The health-check view. Taking the greater of the two values keeps it correct on databases that predate `sync_state` and on freshly filtered deployments where no rows exist yet. The version string is updated with each release, which is why re-running `create_tables.sql` is part of every upgrade.

### Roles

`create_tables.sql` also creates the read-only role used by PostgREST:

```sql
CREATE ROLE web_anon NOLOGIN;
GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON public.ethtxs, public.aval, public.max_block TO web_anon;
```

When `api_user` or `app_user` already exist, the script grants them `web_anon` and the `sync_state` privileges the indexer needs. The indexer role requires:

```sql
GRANT SELECT, INSERT, DELETE ON public.ethtxs TO api_user;
GRANT SELECT, INSERT, UPDATE ON public.sync_state TO api_user;
GRANT SELECT ON public.aval, public.max_block TO api_user;
```

No superuser privileges are needed by either role.

## Index Strategy

Indexes are not created by `create_tables.sql`, on purpose: ingesting the initial history without them is dramatically faster. Backfill first, then build indexes.

### Minimal Set, Recommended

```bash
psql -d index -f create_indexes.sql       # four core indexes
psql -d index -f create_indexes_add.sql   # the ordering index
```

| Index                            | Definition                      | Query shape it serves                                               |
| -------------------------------- | ------------------------------- | ------------------------------------------------------------------- |
| `block_index`                    | `(block)`                       | `MAX(block)` for the `/max_block` health check                      |
| `txfrom_index`                   | `(txfrom)`                      | Outgoing transfers by sender, native and ERC-20                     |
| `txto_contract_to_index`         | `(txto, contract_to)`           | Token transfers: contract in `txto`, ABI recipient in `contract_to` |
| `txto_w_empty_contract_to_index` | `(txto) WHERE contract_to = ''` | Incoming native ETH transfers only, skipping all token rows         |
| `time_index`                     | `(time)`                        | `ORDER BY time DESC` for every history query                        |

Between them these five cover the query shapes any address-history consumer needs: transfers sent by an address, native transfers received by an address, token transfers for a contract and holder, ordering by recency, and the health check. The set was validated against production traffic from the [ADAMANT clients](../project/adamant.md), which is where the evidence comes from — but nothing in it is client-specific.

The partial index is the important one. Native-transfer lookups are the most common query, and restricting the index to `contract_to = ''` excludes every token row from it, which is a large majority of the table.

### Legacy Set, Optional

```bash
psql -d index -f create_indexes_legacy.sql
```

| Index               | Definition       | Why it is optional                                                   |
| ------------------- | ---------------- | -------------------------------------------------------------------- |
| `contract_to_index` | `(contract_to)`  | Only needed to query `contract_to` without a `txto` predicate        |
| `txto_index`        | `(txto)`         | Covered by the composite and partial indexes for the standard shapes |
| `txto_txfrom_index` | `(txto, txfrom)` | Only needed for simultaneous equality on both columns                |

Create these when a third-party consumer issues those non-standard queries. Otherwise they cost roughly 90–110 GB on a one-year dataset and serve nothing.

### Cost Comparison

| Configuration               | Index size, about 490M rows |
| --------------------------- | --------------------------- |
| Minimal five-index set      | 80–95 GB                    |
| Full eight-index legacy set | about 265 GB                |

### Locking

`CREATE INDEX` takes a `ShareLock` on `ethtxs`, which blocks the indexer's inserts for the whole build. On a live database use `CREATE INDEX CONCURRENTLY`, or schedule a maintenance window. `DROP INDEX CONCURRENTLY` has the same property for removals.

Migration steps for an existing deployment are in [Upgrading](../guide/upgrading.md#switching-to-the-minimal-index-set).

## Storage Planning

Disk is the constraint that decides most deployments. Measured reference points, table plus indexes:

| Block range                                        | Approximate size |
| -------------------------------------------------- | ---------------- |
| 5,555,555 → 9,000,000 (3.5M blocks)                | 190 GB           |
| 11,000,000 → 12,230,000 (1.2M blocks)              | 83 GB            |
| 14,600,000 → 15,100,000 (0.5M blocks)              | 27 GB            |
| 14,600,000 → 18,100,000 (3.5M blocks, all indexes) | 289 GB           |

Three levers control the total:

1. **`START_BLOCK`.** Indexing from a recent block instead of genesis is the largest single saving. Most wallets need months of history, not years
2. **Index set.** The minimal set saves 90–110 GB per year of data compared to the legacy set
3. **[Address filter](../guide/address-filter.md).** For a known address set this reduces storage by orders of magnitude, at the cost of losing general-purpose queryability

Plan for growth as well as the initial import, keep autovacuum enabled, and run `ANALYZE public.ethtxs;` after a large backfill so the planner has current statistics.

Useful size queries:

```sql
SELECT pg_size_pretty(pg_total_relation_size('public.ethtxs')) AS total,
       pg_size_pretty(pg_relation_size('public.ethtxs')) AS table_only;

SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname = 'ethtxs'
ORDER BY pg_relation_size(indexrelid) DESC;
```

Index usage counters tell you whether an index earns its disk:

```sql
SELECT indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE relname = 'ethtxs'
ORDER BY idx_scan;
```

## Backups

The table is derived data: it can always be rebuilt from a node, given time. Whether to back it up is a question of how long a rebuild takes.

- `pg_dump` is straightforward but slow to restore at this size
- Physical backups or filesystem snapshots restore much faster for large indexes
- Back up `sync_state` together with `ethtxs`. Restoring transactions without the checkpoint makes the indexer resume from `MAX(block)`, which is wrong for a filtered deployment
- Under Docker Compose all of this is the `./data/postgres` directory

## Schema Changes

The schema is additive across versions. `create_tables.sql` from a newer release can be applied to an older database without data loss, which is why it is a standard upgrade step. Column names and types are part of the [public API contract](./api.md#stability) and are not changed without a breaking-change release.
