# Architecture

The deployment is a small set of independent processes. Each one can be scaled, replaced, or hosted separately, and none of them stores state that another one owns.

## Components

| Component            | Role                                                                 | Required                      |
| -------------------- | -------------------------------------------------------------------- | ----------------------------- |
| Ethereum node        | Source of blocks and receipts over JSON-RPC                          | Yes                           |
| `ethsync.py` indexer | Polls blocks, parses transfers, writes rows, advances the checkpoint | Yes                           |
| PostgreSQL           | Stores `ethtxs`, `sync_state`, `aval`, and the `max_block` view      | Yes                           |
| PostgREST            | Turns the database into a read-only HTTP API                         | Only if you need the REST API |
| Reverse proxy        | TLS termination, method allow-list, query-cost guards, rate limiting | Only for public deployments   |

## Data Flow

```text
        ┌────────────────────┐
        │   Ethereum node    │  Geth / Nethermind / Besu / Erigon
        │  HTTP / WS / IPC   │
        └─────────┬──────────┘
                  │ 1. eth_blockNumber, eth_getBlockByNumber,
                  │    eth_getTransactionReceipt
                  ▼
        ┌────────────────────┐
        │     ethsync.py     │  parse value transfers and 0xa9059cbb calls,
        │      (indexer)     │  apply the optional address filter
        └─────────┬──────────┘
                  │ 2. INSERT INTO ethtxs
                  │    UPSERT sync_state.last_block  (one transaction per block)
                  ▼
        ┌────────────────────┐
        │     PostgreSQL     │  ethtxs, sync_state, aval, max_block view
        └─────────┬──────────┘
                  │ 3. SELECT as role web_anon
                  ▼
        ┌────────────────────┐
        │      PostgREST     │  /ethtxs, /max_block, /aval
        └─────────┬──────────┘
                  │ 4. HTTPS, GET/HEAD/OPTIONS only
                  ▼
        ┌────────────────────┐
        │   Reverse proxy    │  nginx or equivalent
        └─────────┬──────────┘
                  │ 5. JSON
                  ▼
            Client application
```

## The Synchronization Loop

Every `PERIOD` seconds the indexer performs one pass:

1. Reload the address filter file when the filter is enabled, so edits apply without a restart
2. Read the current checkpoint as `GREATEST(MAX(ethtxs.block), sync_state.last_block)`
3. Ask the node for the chain head and subtract `CONFIRMATIONS_BLOCK`
4. For each block in between, fetch the block with full transaction bodies, insert matching transfers, update `sync_state.last_block`, and commit
5. Close the connection and sleep

Each block is committed in its own database transaction, so an interruption at any point leaves the checkpoint consistent with the rows that were written.

On startup the indexer deletes the highest indexed block and rewinds the checkpoint by one. That makes a partially written block impossible to keep: the block is always re-fetched and re-inserted from scratch.

## Why `sync_state` Exists Separately

The checkpoint cannot be derived from `MAX(block)` alone. A block may contain no transactions, and with the address filter enabled most blocks contribute no rows at all. Without a dedicated checkpoint the indexer would rescan the same range forever. `sync_state` is a single-row table that records the highest fully processed block regardless of whether it produced any data.

The `max_block` view reports `GREATEST(MAX(ethtxs.block), sync_state.last_block)` so that health checks stay correct for both fresh and upgraded deployments.

## Confirmations and Reorganizations

`CONFIRMATIONS_BLOCK` keeps the indexer that many blocks behind the chain head. Blocks below the head are still reorganizable, and the indexer does not detect a reorg after the fact — it only guards the boundary at startup. Set a non-zero value in production when your application must not display transactions that a reorg can remove.

If a deep reorg does affect indexed data, re-index the affected range: delete rows at or above the first affected block and set `sync_state.last_block` to the block before it, in one database transaction. See [Upgrading](./upgrading.md#re-indexing-a-block-range).

## Deployment Topologies

**Single host.** Node, indexer, PostgreSQL, and PostgREST on one machine. Simplest, and the disk is usually the constraint.

**Split storage.** The indexer and PostgREST run next to the application while PostgreSQL sits on dedicated storage. Point `DB_NAME` at a connection URI instead of a local database name.

**Shared node.** One execution client serves several indexer instances, each with its own database and its own address filter. Receipt lookups dominate the RPC load, so watch the node's request budget.

**Read replicas.** PostgREST can read from a PostgreSQL replica while the indexer writes to the primary. The API is read-only, so no write path crosses the replica.
