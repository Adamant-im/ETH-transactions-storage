# Introduction

`ETH-transactions-storage` is a self-hosted Ethereum transaction indexer and REST API backend. It reads blocks from an Ethereum execution client, stores native ETH transfers and ERC-20 token transfers in PostgreSQL, and exposes address-oriented transaction history over HTTP through PostgREST.

## The Problem It Solves

Ethereum execution clients do not maintain an address-to-transaction index. `eth_getTransactionByHash` works if you already know the hash, and `eth_getLogs` covers events but not native ETH transfers. There is no JSON-RPC method that answers the question every wallet screen asks:

> Which transactions involve this address, newest first?

Public data providers answer it, but they see every address your users look up, rate-limit you, and can disappear or change pricing. Running your own index removes that dependency: the data is derived from your own node and stored in your own database.

## What It Does

- Connects to an Ethereum execution client over HTTP, WebSocket, or IPC
- Polls new blocks, parses transactions, and writes them to a single PostgreSQL table
- Indexes native ETH transfers and ERC-20 `transfer(address,uint256)` calls
- Tracks synchronization progress in a dedicated `sync_state` row so restarts resume exactly where they stopped
- Optionally stores only transfers that involve a configured list of addresses
- Serves the result as a read-only REST API through PostgREST

## Use Cases

- **Cryptocurrency wallets.** Render per-account ETH and token history without calling a third-party explorer API.
- **Block explorers and dashboards.** Back address pages with SQL instead of scanning the chain on every request.
- **Accounting and treasury tools.** Export transfers for a set of company addresses into reconciliation pipelines.
- **Support and compliance systems.** Look up a user's on-chain activity from an internal tool.
- **Monitoring services.** Watch a known address set with the [address filter](./address-filter.md) enabled and keep the database small.
- **Custom applications.** Query the table directly with SQL when the REST API is not the right shape.

## What Gets Indexed

The indexer deliberately stores a narrow, cheap-to-maintain slice of chain activity.

Stored:

- Native ETH transfers, meaning any transaction with a non-zero `value`
- ERC-20 transfers submitted as a direct top-level `transfer(address,uint256)` call, identified by the `0xa9059cbb` method signature

Not stored:

- Internal ETH transfers produced by contract execution, because they are not top-level transactions
- ERC-20 transfers made through any other call path, including `transferFrom`, multisig wallets, routers, batchers, and aggregators
- ERC-721, ERC-1155, and other token standards
- Event logs, contract state, receipts beyond `gasUsed`, and pending transactions
- Zero-value transactions that are not ERC-20 `transfer` calls

These limits are properties of the current indexing logic, not configuration options. Plan around them: an application that must reflect every possible token movement needs a log-based indexer, while an application that shows user-initiated transfers is served well by this one.

## Chain Compatibility

The indexer speaks standard Ethereum JSON-RPC and injects the proof-of-authority middleware, so it also works against EVM-compatible networks whose clients expose the same methods and block structure. Only one chain is indexed per database: point `ETH_URL` at one endpoint and run a separate instance with its own database for each additional chain.

Verified execution clients: Geth, Nethermind, Besu, Erigon.

## Requirements

| Component     | Minimum        | Notes                                                             |
| ------------- | -------------- | ----------------------------------------------------------------- |
| Ethereum node | Synced, RPC on | Archive data is not required when starting from a recent block    |
| Python        | 3.9+           | Only for manual or systemd deployments                            |
| PostgreSQL    | 12+            | `citext` extension required                                       |
| PostgREST     | 10+            | Optional if you query the database directly                       |
| Disk          | Varies         | See [storage planning](../reference/database.md#storage-planning) |

## Privacy and Telemetry

The indexer makes outbound connections to exactly two endpoints: the Ethereum node and the PostgreSQL server you configure. There is no analytics, crash reporting, update check, or usage beacon of any kind. Nothing about your users, their addresses, or your queries leaves your infrastructure.

## Next Steps

- [Architecture](./architecture.md) — how the pieces fit together
- [Docker Compose quick start](./quick-start-docker.md) — fastest path to a running stack
- [Manual and systemd quick start](./quick-start-manual.md) — bare-metal deployment
- [Configuration](./configuration.md) — every environment variable
