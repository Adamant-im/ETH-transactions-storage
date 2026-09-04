# Troubleshooting

## Diagnostic Scripts

Two scripts isolate the two external dependencies before you debug the indexer itself.

```bash
ETH_URL=http://127.0.0.1:8545 python3 ethtest.py
```

Prints the current best block and the node's syncing status, or the connection error.

```bash
DB_NAME=index python3 pgtest.py
```

Prints `MAX(block)` from `ethtxs`, or the connection error with the password redacted.

Under Compose, run them inside the container so the network and environment match:

```bash
docker compose exec eth-storage python3 ethtest.py
docker compose exec eth-storage python3 pgtest.py
```

## The Indexer Exits Immediately

| Message                                                   | Cause                                                    |
| --------------------------------------------------------- | -------------------------------------------------------- |
| `Set PostgreSQL database in environment variable DB_NAME` | `DB_NAME` is unset                                       |
| `Set Ethereum node URL in environment variable ETH_URL`   | `ETH_URL` is unset                                       |
| `ADDRESS_FILTER_ENABLED must be one of: …`                | The value is not a recognized boolean                    |
| `Address filter file '…' contains no Ethereum addresses`  | The list is empty or fully commented out                 |
| `Invalid Ethereum address in '…' at line N`               | A line is neither a comment nor a valid address          |
| `Unable to read address filter file '…'`                  | Missing file, wrong path, or wrong permissions           |
| `Unable to connect to PostgreSQL database: …`             | Wrong host, database, credentials, or the server is down |

All of these exit with a non-zero status, which is what systemd `Restart=on-failure` and Docker restart policies react to.

## `Unable to initialize the database checkpoint`

The schema is missing or the role lacks permissions on `sync_state`. Apply the schema and the grants:

```bash
psql -v ON_ERROR_STOP=1 -d index -f create_tables.sql
```

```sql
GRANT SELECT, INSERT, UPDATE ON public.sync_state TO api_user;
```

Under Compose this happens when the database volume predates `sync_state` — the entrypoint script runs only on an empty data directory. Apply the schema manually, as shown in [Upgrading](./upgrading.md#docker-compose-deployments).

## Waiting for the Node to Synchronize

```text
Waiting for Ethereum node to finish synchronizing… (retrying in 5 minutes)
```

The indexer refuses to index from a node that reports `eth_syncing`, because a partially synced node returns incomplete data. Wait for the client to finish. This can take hours or days for a fresh node and is not an indexer problem.

## Indexing Is Too Slow

The dominant cost is one `eth_getTransactionReceipt` call per stored transaction, on top of one block fetch per block.

- Use a local node. A remote or metered RPC endpoint makes backfill impractical
- Prefer IPC, then WebSocket, then HTTP
- Raise `START_BLOCK` so there is less history to walk
- Enable the [address filter](./address-filter.md), which skips receipt lookups for transactions that do not match
- Create indexes **after** the initial backfill, not before
- Check that the node itself is not the bottleneck, with `eth_syncing` and the client's own metrics

`PERIOD` does not throttle the backfill. Within a pass, blocks are processed continuously.

## Queries Are Slow or Time Out

- Confirm the indexes exist: `\di public.*` in `psql`
- Confirm the query uses them: `EXPLAIN ANALYZE` on the generated SQL
- A query with neither `txfrom` nor `txto` has no usable index and will scan the table. This is why the [proxy rules](./security.md#reverse-proxy-rules) reject those requests
- `Prefer: count=exact` forces a full scan. Use `count=planned` or no count at all
- Large `offset` values get slower linearly. Paginate by `time` instead, as shown in the [API reference](../reference/api.md#pagination)
- Run `ANALYZE public.ethtxs;` after a large backfill so the planner has current statistics

## API Returns 500 for Every Request

Almost always the anonymous role. Check, in this order:

1. Does `web_anon` exist? `SELECT 1 FROM pg_roles WHERE rolname = 'web_anon';`
2. Can it read? `SET ROLE web_anon; SELECT * FROM public.max_block;`
3. Does `db-anon-role` in `postgrest.conf` name that exact role?
4. Can the PostgREST login role assume it? `GRANT web_anon TO api_user;`

An unbounded `GET /ethtxs` on a large table also returns 500 when `db-max-rows` is unset, because the JSON response exceeds PostgreSQL's 1 GB value limit.

## `/max_block` Returns `null`

`max` is `null` when no block has been processed and no transaction rows exist. On a new deployment, wait one `PERIOD`. If it stays `null`:

- Check the indexer logs for errors
- Confirm the node's height is above `START_BLOCK`
- Confirm the indexer and PostgREST point at the same database

A permission error rather than `null` means `GRANT SELECT ON public.max_block TO web_anon;` is missing.

## `/max_block` Stops Advancing

- Is the process running? `systemctl status ethsync.service` or `docker compose ps`
- Look for `Error during synchronization pass` in the logs; the pass is abandoned without advancing the checkpoint, and the next pass retries
- With the filter enabled, a broken address file stops processing by design. Fix the file
- Check free disk. A full disk stops PostgreSQL writes, and the indexer will log the failure every pass

## Missing Transactions

Before treating it as a bug, confirm the transfer is in scope. The indexer stores native ETH transfers and direct `transfer(address,uint256)` calls only. Internal transfers, `transferFrom`, multisig, router, batch, and aggregator flows, and non-ERC-20 token standards are never indexed. See [what gets indexed](./introduction.md#what-gets-indexed).

Then check:

- Is the block above `START_BLOCK`?
- Is the address filter on, and does the address appear in the list?
- Is the block within `CONFIRMATIONS_BLOCK` of the head, and therefore not yet indexed?
- Was the address added to the filter after the block was processed? There is no automatic backfill

## Duplicate Rows After a Crash

The table has no uniqueness constraint on `txhash`, so a crash between the insert and the commit could in principle duplicate a block's rows. The startup routine prevents this by deleting the highest indexed block and rewinding the checkpoint by one before the first pass. If duplicates do appear, re-index the affected range as described in [Upgrading](./upgrading.md#re-indexing-a-block-range).

## Disk Filling Up

- Check the split between table and indexes:

```sql
SELECT pg_size_pretty(pg_total_relation_size('public.ethtxs')) AS total,
       pg_size_pretty(pg_relation_size('public.ethtxs')) AS table_only;
```

- Drop the legacy indexes if you still have all eight, which frees roughly 90–110 GB on a one-year dataset. See [Upgrading](./upgrading.md#switching-to-the-minimal-index-set)
- Reduce scope with a higher `START_BLOCK` or the address filter, then re-index
- Review PostgreSQL autovacuum and WAL retention settings, which are outside this project but frequently the actual cause

## Getting Help

Open an issue at [github.com/Adamant-im/ETH-transactions-storage/issues](https://github.com/Adamant-im/ETH-transactions-storage/issues) with the indexer version from `/max_block`, the deployment mode, the execution client and version, the PostgreSQL version, and the relevant log lines. Remove credentials before pasting configuration.
