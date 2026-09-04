# ETH Transactions Storage

[![Docs](https://img.shields.io/badge/docs-eth--indexer.docs.adamant.im-2c4a7c)](https://eth-indexer.docs.adamant.im)
[![Container](https://img.shields.io/badge/ghcr.io-eth--transactions--storage-2c4a7c)](https://github.com/Adamant-im/ETH-transactions-storage/pkgs/container/eth-transactions-storage)
[![License: GPL v3](https://img.shields.io/badge/license-GPL--3.0-2c4a7c)](./LICENSE)

Self-hosted Ethereum transaction indexer for native ETH and ERC-20 transfers, with PostgreSQL storage and a read-only PostgREST API.

Ethereum nodes cannot answer "list the transactions for this address". `ETH-transactions-storage` builds that index for you: it reads blocks from your execution client, writes native ETH transfers and ERC-20 `transfer` calls into PostgreSQL, and serves address transaction history over HTTP. No third-party data provider, no rate limits, no telemetry.

📖 **Full documentation: <https://eth-indexer.docs.adamant.im>**

> Built and maintained by the ADAMANT developer community and **cryptofoundry**.
> Want custom crypto software, bots, payments or blockchain infrastructure built by engineers with production blockchain experience? [Tell us what to build](https://adamant.business#contact).

## What It Is For

- **Cryptocurrency wallets** rendering per-account ETH and token history
- **Block explorers and dashboards** backing address pages with SQL
- **Accounting and treasury tools** exporting transfers for reconciliation
- **Support and compliance systems** looking up on-chain activity
- **Monitoring services** watching a known address set with the optional address filter
- **Custom applications** that want direct SQL access to transfer data

Works with Geth, Nethermind, Besu, and Erigon over HTTP, WebSocket, or IPC, and with EVM-compatible networks exposing the same JSON-RPC surface.

![Indexer request example](./assets/indexer-request.png)

## How It Works

```text
Ethereum node  →  ethsync.py  →  PostgreSQL  →  PostgREST  →  your application
   JSON-RPC        indexer        ethtxs         REST API
```

The indexer polls new blocks, parses transfers, and writes each block together with its checkpoint in a single database transaction. Restarts resume exactly where they stopped. PostgREST turns the table into a read-only HTTP API with filtering, ordering, and pagination, so there is no API code to write or maintain.

See [Architecture](https://eth-indexer.docs.adamant.im/guide/architecture) for the full data flow.

## Quick Start

### Docker Compose

```bash
git clone https://github.com/Adamant-im/ETH-transactions-storage.git
cd ETH-transactions-storage
cp .env.example .env && chmod 600 .env
cp filter/addresses.txt.example filter/addresses.txt && chmod 600 filter/addresses.txt
# set POSTGRES_PASSWORD and DOCKER_ETH_URL in .env
docker compose up -d
curl -s http://127.0.0.1:3000/max_block
```

The stack runs PostgreSQL, PostgREST, an optional local Geth dev node, and the indexer image published to `ghcr.io/adamant-im/eth-transactions-storage`. Nothing is built locally.

Full walkthrough: [Docker Compose quick start](https://eth-indexer.docs.adamant.im/guide/quick-start-docker).

### Manual and systemd

```bash
pip3 install -r requirements.txt
createdb -O api_user index
psql -v ON_ERROR_STOP=1 -d index -f create_tables.sql
DB_NAME=index ETH_URL=http://127.0.0.1:8545 START_BLOCK=21000000 python3 ethsync.py
```

Then create the query indexes once the initial backfill has caught up:

```bash
psql -d index -f create_indexes.sql
psql -d index -f create_indexes_add.sql
```

Full walkthrough, including the systemd unit and PostgREST: [Manual and systemd quick start](https://eth-indexer.docs.adamant.im/guide/quick-start-manual).

## API at a Glance

| Endpoint     | Purpose                                     |
| ------------ | ------------------------------------------- |
| `/ethtxs`    | Indexed native ETH and ERC-20 transfers     |
| `/max_block` | Highest processed block and indexer version |
| `/aval`      | Availability probe                          |

```bash
# Last 25 native ETH transfers for an address, newest first
curl -s "http://127.0.0.1:3000/ethtxs?and=(contract_to.eq.,or(txfrom.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98,txto.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98))&order=time.desc&limit=25"
```

Endpoint names, column names, and value encodings are a stable contract across upgrades. Full query syntax, encodings, filtering, and pagination: [REST API reference](https://eth-indexer.docs.adamant.im/reference/api).

## Scope and Limitations

Stored: native ETH transfers, and ERC-20 transfers submitted as a direct top-level `transfer(address,uint256)` call.

Not stored: internal ETH transfers, ERC-20 transfers routed through `transferFrom`, multisig, router, batch, or aggregator flows, other token standards, and event logs. These are properties of the current indexing logic, not settings. See [what gets indexed](https://eth-indexer.docs.adamant.im/guide/introduction#what-gets-indexed).

Storage is the main planning constraint. A recent `START_BLOCK`, the recommended five-index set, and the optional address filter are the three levers: see [storage planning](https://eth-indexer.docs.adamant.im/reference/database#storage-planning).

## Documentation

| Page                                                                                       | Contents                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| [Introduction](https://eth-indexer.docs.adamant.im/guide/introduction)                     | What it does, use cases, scope, limitations             |
| [Architecture](https://eth-indexer.docs.adamant.im/guide/architecture)                     | Components, data flow, sync loop, deployment topologies |
| [Docker Compose quick start](https://eth-indexer.docs.adamant.im/guide/quick-start-docker) | The fastest path to a running stack                     |
| [Manual and systemd](https://eth-indexer.docs.adamant.im/guide/quick-start-manual)         | Bare-metal installation and the service unit            |
| [Configuration](https://eth-indexer.docs.adamant.im/guide/configuration)                   | Every environment variable                              |
| [Address filter](https://eth-indexer.docs.adamant.im/guide/address-filter)                 | Storing only the addresses you care about               |
| [Security](https://eth-indexer.docs.adamant.im/guide/security)                             | Read-only roles, row caps, proxy guards, secrets        |
| [Upgrading](https://eth-indexer.docs.adamant.im/guide/upgrading)                           | Upgrade order, index migration, re-indexing             |
| [Troubleshooting](https://eth-indexer.docs.adamant.im/guide/troubleshooting)               | Diagnostics and common failures                         |
| [REST API](https://eth-indexer.docs.adamant.im/reference/api)                              | Endpoints, encodings, filtering, pagination             |
| [Database and indexes](https://eth-indexer.docs.adamant.im/reference/database)             | Schema, checkpoint, index strategy, storage planning    |
| [Docker image](https://eth-indexer.docs.adamant.im/reference/docker-image)                 | Tags, architectures, running, upgrades, rollback        |

## Used by ADAMANT

[ADAMANT](https://adamant.im) maintains this project and runs it in production to power Ethereum and ERC-20 transaction history in its wallets: [`adamant-im`](https://github.com/Adamant-im/adamant-im) for Web, PWA, Electron, and Android, and [`adamant-iOS`](https://github.com/Adamant-im/adamant-iOS) on iOS.

That deployment is a documented adopter, not a requirement — no ADAMANT component is needed to run the indexer. It is useful to third-party operators as evidence: the API contract is exercised by shipping clients, and the recommended index set was derived from auditing real production query traffic, which is where the 90–110 GB saving over the legacy index set comes from.

The production query patterns, useful as a compatibility checklist for your own client, are documented on [Used by ADAMANT](https://eth-indexer.docs.adamant.im/project/adamant).

## Contributing

Pull requests target `dev`. Development setup, the checks CI runs, the release process, and the security contact are in [Contributing and Releases](https://eth-indexer.docs.adamant.im/project/contributing). Contributors working with AI assistants should also read [`AGENTS.md`](./AGENTS.md).

```bash
npm ci                # documentation and Markdown tooling
npm run docs:dev      # documentation site with hot reload
npm run lint:py       # Python syntax checks
npm test              # Python unit tests
```

## License

Copyright © 2025–2026 ADAMANT developer community  
Copyright © 2020–2024 ADAMANT Foundation  
Copyright © 2017–2020 ADAMANT TECH LABS LP

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
