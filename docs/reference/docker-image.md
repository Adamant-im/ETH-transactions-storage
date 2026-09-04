# Docker Image

A maintained indexer image is published to the GitHub Container Registry, so operators do not have to build anything locally.

```text
ghcr.io/adamant-im/eth-transactions-storage
```

The package page is linked from the [repository](https://github.com/Adamant-im/ETH-transactions-storage) under Packages.

## Tags

| Tag      | Meaning                                                                   |
| -------- | ------------------------------------------------------------------------- |
| `X.Y.Z`  | An immutable release build, for example `2.5.0`. Never republished        |
| `latest` | The most recent stable release. Moves on every non-prerelease publication |

Version tags carry no leading `v`, even though the Git tag does: release `v2.5.0` publishes image tag `2.5.0`.

Prereleases publish their version tag but do not move `latest`.

Pin an exact version in production. `latest` is convenient for evaluation and makes rollback ambiguous.

## Supported Architectures

The image is published as a multi-architecture manifest for:

- `linux/amd64`
- `linux/arm64`

Docker selects the right one automatically. To check what you pulled:

```bash
docker image inspect --format '{{.Os}}/{{.Architecture}}' \
  ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

## Pulling

The package is public, so no authentication is needed:

```bash
docker pull ghcr.io/adamant-im/eth-transactions-storage:2.5.0
docker pull ghcr.io/adamant-im/eth-transactions-storage:latest
```

Record the digest if you want a reproducible deployment:

```bash
docker image inspect --format '{{index .RepoDigests 0}}' \
  ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

A digest can be used anywhere a tag can:

```bash
docker pull ghcr.io/adamant-im/eth-transactions-storage@sha256:<digest>
```

## What Is Inside

- `python:3.11-slim` base
- The dependencies from `requirements.txt`: `web3`, `psycopg2-binary`, `python-dotenv`
- The indexer modules: `ethsync.py`, `address_filter.py`, `database.py`, plus the `ethtest.py` and `pgtest.py` diagnostics
- `package.json`, which supplies the version the indexer logs at startup
- `filter/addresses.txt.example`
- Working directory `/eth-storage`, entrypoint `python3 ./ethsync.py`

What is deliberately **not** inside:

- No `.env`, credentials, or connection strings
- No `filter/addresses.txt`, so your monitored address list never ends up in a registry
- No database data, logs, or any other operator state
- No PostgreSQL, PostgREST, or Ethereum client — those stay separate services, so each can be versioned, scaled, and secured on its own

The image contains one process and holds no state. Everything it needs arrives through environment variables at run time.

## OCI Labels

The image carries standard annotations, which is what makes GitHub link the package to this repository:

| Label                                  | Value                               |
| -------------------------------------- | ----------------------------------- |
| `org.opencontainers.image.source`      | Repository URL                      |
| `org.opencontainers.image.revision`    | Commit SHA the image was built from |
| `org.opencontainers.image.version`     | Release version                     |
| `org.opencontainers.image.licenses`    | `GPL-3.0-or-later`                  |
| `org.opencontainers.image.title`       | `ETH Transactions Storage`          |
| `org.opencontainers.image.description` | Product description                 |
| `org.opencontainers.image.url`         | Documentation site                  |

```bash
docker image inspect --format '{{json .Config.Labels}}' \
  ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

## Running It

The indexer needs a reachable PostgreSQL database with the schema applied and an Ethereum RPC endpoint. See [Configuration](../guide/configuration.md) for every variable.

```bash
docker run -d --name eth-indexer \
  -e DB_NAME='postgres://api_user:password@db.internal:5432/index' \
  -e ETH_URL='ws://node.internal:8546' \
  -e START_BLOCK=21000000 \
  -e CONFIRMATIONS_BLOCK=12 \
  -e PERIOD=20 \
  --restart unless-stopped \
  ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

With the address filter, mount the directory read-only:

```bash
docker run -d --name eth-indexer \
  -e DB_NAME='postgres://api_user:password@db.internal:5432/index' \
  -e ETH_URL='ws://node.internal:8546' \
  -e ADDRESS_FILTER_ENABLED=true \
  -e ADDRESS_FILTER_FILE=/eth-storage/filter/addresses.txt \
  -v "$(pwd)/filter:/eth-storage/filter:ro" \
  --restart unless-stopped \
  ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

Notes on configuration handling:

- Prefer `--env-file` over repeated `-e` flags so credentials stay out of shell history and `docker inspect` output stays shorter. The file is still readable by anyone who can talk to the Docker daemon
- Mount the `filter` **directory**, not the file. Editors that save atomically replace the inode, and a file mount would keep showing the old contents
- The image logs to stdout by default. Leave `LOG_FILE` empty and let your container runtime collect logs
- The container is stateless. Restarting or replacing it is always safe: progress lives in `sync_state` in PostgreSQL, and the indexer rewinds one block on startup to discard any partial write

## Using It with Docker Compose

`docker-compose.yml` already references the published image:

```yaml
eth-storage:
  image: ${ETH_INDEXER_IMAGE:-ghcr.io/adamant-im/eth-transactions-storage:latest}
```

Pin a version in `.env`:

```ini
ETH_INDEXER_IMAGE=ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

The full stack walkthrough is in the [Docker Compose quick start](../guide/quick-start-docker.md).

## Upgrading

```bash
# 1. Stop the indexer so the deployed code and the schema cannot diverge
docker compose stop eth-storage

# 2. Apply any schema changes before the new image starts
docker compose exec -T db sh -c \
  'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < create_tables.sql

# 3. Point at the new version
sed -i 's/^ETH_INDEXER_IMAGE=.*/ETH_INDEXER_IMAGE=ghcr.io\/adamant-im\/eth-transactions-storage:2.5.0/' .env

# 4. Pull and start
docker compose pull eth-storage
docker compose up -d eth-storage

# 5. Verify
curl -s http://127.0.0.1:3000/max_block
```

The schema step comes first on purpose. A database that predates `sync_state` makes the new indexer's startup checkpoint query fail, and it exits with status 1 without a restart policy to bring it back. Full sequence and the failure mode in [Upgrading](../guide/upgrading.md#docker-compose-deployments).

Keep the repository checkout on the matching tag, because `create_tables.sql` and `docker-compose.yml` are versioned with the image.

## Rollback

Version tags are immutable, so rolling back is pointing at an earlier published version:

```ini
ETH_INDEXER_IMAGE=ghcr.io/adamant-im/eth-transactions-storage:<previous-version>
```

```bash
docker compose pull eth-storage
docker compose up -d eth-storage
```

Pick the target from the [published package versions](https://github.com/Adamant-im/ETH-transactions-storage/pkgs/container/eth-transactions-storage), not from the repository's Git tags. Only releases built by the current publishing workflow exist as images, so image rollback becomes available once a second such release has been published; before that there is no earlier image to roll back to. Git tags older than that, such as `v2.4.1`, were never published as images and predate `sync_state` entirely, which puts them outside the supported range in any case.

The database schema is additive, so an older indexer runs against a newer schema without changes — the extra objects are simply unused. Two limits apply: `max_block.version` keeps reporting whatever the last applied `create_tables.sql` wrote, and rolling back past the introduction of `sync_state` is not supported.

No data migration or re-index is required for a rollback.

## Building Locally

Contributors and anyone who prefers to build from source:

```bash
docker build -t eth-transactions-storage:local .
```

Or through Compose, which is what the build override file is for:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

The override tags the result `eth-transactions-storage:local`, so a local build never shadows the published image in your cache.

`.dockerignore` keeps `.env`, `filter/addresses.txt`, `data/`, `logs/`, `.git`, and `node_modules/` out of the build context. Verify before distributing an image you built yourself:

```bash
docker run --rm --entrypoint sh eth-transactions-storage:local -c 'ls -la /eth-storage /eth-storage/filter'
```

## Publishing

Images are published by a GitHub Actions workflow that runs when a GitHub Release is published, and only when the release tag is an ancestor of `master`. The workflow holds `contents: read` and `packages: write` and nothing else. See [Contributing and Releases](../project/contributing.md#release-process).
