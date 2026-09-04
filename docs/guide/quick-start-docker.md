# Quick Start: Docker Compose

The repository ships a Compose stack that starts PostgreSQL, PostgREST, an optional local Geth dev node, and the indexer. It pulls the published indexer image, so nothing has to be built locally.

## Prerequisites

- Docker Engine 24+ with the Compose v2 plugin
- An Ethereum RPC endpoint for anything beyond local experimentation
- Free disk space matching your intended block range, see [storage planning](../reference/database.md#storage-planning)

## 1. Clone and Configure

```bash
git clone https://github.com/Adamant-im/ETH-transactions-storage.git
cd ETH-transactions-storage
cp .env.example .env
chmod 600 .env
```

Open `.env` and set at least:

```ini
POSTGRES_PASSWORD=replace-with-a-strong-password
DOCKER_ETH_URL=ws://publicnode:8546
START_BLOCK=1
```

Use only URL-safe characters in `POSTGRES_PASSWORD`: letters, digits, period, underscore, tilde, and hyphen. Compose treats `$` as interpolation, and `:`, `/`, and `@` are URI delimiters inside the generated connection string.

Every variable is described in the [configuration reference](./configuration.md).

## 2. Prepare the Address Filter Directory

Compose mounts the `filter` directory read-only into the indexer container. Create the file even when the filter stays disabled, so the mount has stable contents:

```bash
cp filter/addresses.txt.example filter/addresses.txt
chmod 600 filter/addresses.txt
```

To store only selected addresses, list them in that file and set `ADDRESS_FILTER_ENABLED=true`. See [Address filter](./address-filter.md).

## 3. Start the Stack

```bash
docker compose up -d
```

Compose starts four services:

| Service       | Image                                                | Purpose                                        |
| ------------- | ---------------------------------------------------- | ---------------------------------------------- |
| `db`          | `postgres:14`                                        | Database, initialized from `create_tables.sql` |
| `postgrest`   | `postgrest/postgrest:latest`                         | Read-only REST API on port 3000                |
| `publicnode`  | `ethereum/client-go:stable`                          | Local Geth dev node, for testing only          |
| `eth-storage` | `ghcr.io/adamant-im/eth-transactions-storage:latest` | The indexer                                    |

Pin the indexer to an immutable version instead of `latest` by setting `ETH_INDEXER_IMAGE` in `.env`:

```ini
ETH_INDEXER_IMAGE=ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

## 4. Verify

```bash
docker compose logs -f eth-storage
curl -s http://127.0.0.1:3000/max_block
curl -s http://127.0.0.1:3000/aval
```

`/max_block` returns the highest processed block and the indexer version:

```json
[{ "max": 128, "version": "2.5.0" }]
```

A `max` of `null` means no block has been processed yet. Give the indexer one `PERIOD` interval and check again.

## 5. Create Indexes

The schema is created automatically, but query indexes are not, because building them before the initial backfill makes ingestion much slower. Once the indexer has caught up to the chain head, apply them:

```bash
docker compose exec -T db sh -c \
  'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < create_indexes.sql

docker compose exec -T db sh -c \
  'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < create_indexes_add.sql
```

See [Database and Indexes](../reference/database.md) for what each index covers and what it costs.

## Pointing at a Real Ethereum Node

The bundled `publicnode` service runs Geth in `--dev` mode, pinned to the `stable` release tag because `latest` tracks unstable development builds. It produces empty blocks on a private chain and exists only so the stack starts without external dependencies. For anything real, set `DOCKER_ETH_URL` to your own endpoint:

```ini
DOCKER_ETH_URL=ws://host.docker.internal:8546
START_BLOCK=21000000
CONFIRMATIONS_BLOCK=12
```

To keep the dev node out of the picture, drop the dependency before starting anything. Naming a subset of services on the command line still starts their declared dependencies, so `docker compose up -d db postgrest eth-storage` would start `publicnode` and wait for it to become healthy. `--no-deps` would skip it, but it would also skip the database health gate that `eth-storage` needs, so use an override file instead. Compose loads `docker-compose.override.yml` automatically:

```yaml
# docker-compose.override.yml
services:
  eth-storage:
    depends_on: !override
      db:
        condition: service_healthy
```

With that file in place, `publicnode` stays stopped:

```bash
docker compose up -d db postgrest eth-storage
```

## Data Persistence

PostgreSQL data is bind-mounted to `./data/postgres` on the host. That directory holds the entire index — back it up, monitor its size, and never bake it into an image. Removing it resets the deployment to an empty database, and the indexer will re-index from `START_BLOCK`.

The Postgres entrypoint runs `create_tables.sql` only when the data directory is empty. If you upgrade an existing volume, apply the schema explicitly:

```bash
docker compose exec -T db sh -c \
  'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < create_tables.sql
```

## Building the Image Locally

Contributors who change the indexer can build instead of pulling, using the build override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

The override tags the result as `eth-transactions-storage:local`, so a local build never shadows the published image in your Docker cache.

## Stopping and Cleaning Up

```bash
docker compose down             # stop containers, keep the database directory
docker compose down --rmi local # also remove locally built images
rm -rf data/postgres            # destroy all indexed data
```

## Next Steps

- [Configuration reference](./configuration.md)
- [Security and public deployment](./security.md) before exposing port 3000
- [Docker image reference](../reference/docker-image.md) for tags, architectures, and rollback
