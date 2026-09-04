---
layout: home

hero:
  name: ETH Transactions Storage
  text: Self-hosted Ethereum transaction indexer
  tagline: Index native ETH and ERC-20 transfers into PostgreSQL and serve address transaction history through a read-only PostgREST API. No third-party service, no telemetry, no vendor lock-in.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/introduction
    - theme: alt
      text: Quick Start with Docker
      link: /guide/quick-start-docker
    - theme: alt
      text: View on GitHub
      link: https://github.com/Adamant-im/ETH-transactions-storage

features:
  - title: Transaction history by address
    details: Ethereum nodes cannot answer "list transactions for this address". The indexer builds that index for you and keeps it current.
    link: /guide/introduction
    linkText: What it does
  - title: Works with any execution client
    details: Connects to Geth, Nethermind, Besu, or Erigon over HTTP, WebSocket, or IPC. Any EVM chain with a compatible JSON-RPC endpoint can be indexed.
    link: /guide/architecture
    linkText: Architecture
  - title: Plain PostgreSQL storage
    details: Data lives in a table you own. Query it with SQL, back it up with your existing tooling, or expose it through the bundled read-only REST API.
    link: /reference/database
    linkText: Database reference
  - title: Read-only REST API
    details: PostgREST serves filtering, ordering, and pagination over the indexed table without writing a line of API code.
    link: /reference/api
    linkText: API reference
  - title: Storage under control
    details: Start from any block height, pick a minimal index set, and optionally store only the addresses you care about.
    link: /guide/address-filter
    linkText: Address filter
  - title: Deploy your way
    details: Pull the published container image, run the full Docker Compose stack, or install as a systemd service on bare metal.
    link: /reference/docker-image
    linkText: Docker image
---

## Who This Is For

The indexer is a backend building block for anything that needs Ethereum transaction history by address:

- Cryptocurrency wallets that display per-account transaction lists
- Block explorers and internal dashboards
- Accounting, treasury, and reconciliation tools
- Support and compliance systems that look up user activity
- Monitoring services that watch a known set of addresses
- Custom applications that need SQL access to transfer data

## Documentation Scope

These pages cover the indexer itself: deployment, configuration, database layout, and the REST API contract. Ethereum protocol concepts and execution-client operation stay with the upstream client documentation, and PostgREST query syntax is documented in the [PostgREST API reference](https://postgrest.org/en/stable/api.html).

ADAMANT runs this indexer in production for its wallets. That deployment is documented as a real-world integration example on [Used by ADAMANT](./project/adamant.md), not as a requirement.

## Quick Links

- [Introduction and scope](./guide/introduction.md)
- [Architecture and data flow](./guide/architecture.md)
- [Docker Compose quick start](./guide/quick-start-docker.md)
- [Manual and systemd quick start](./guide/quick-start-manual.md)
- [Environment variable reference](./guide/configuration.md)
- [Security and public deployment](./guide/security.md)
- [REST API reference](./reference/api.md)
- [Database schema and index strategy](./reference/database.md)
- [Published Docker image](./reference/docker-image.md)
- [Troubleshooting](./guide/troubleshooting.md)
