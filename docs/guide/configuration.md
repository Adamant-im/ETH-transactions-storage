# Configuration

The indexer is configured entirely through environment variables. There is no configuration file format of its own, and nothing is stored outside the database.

## Where Values Come From

`ethsync.py`, `ethtest.py`, and `pgtest.py` load `.env` from the repository directory at startup using `python-dotenv`. Precedence is:

1. Variables already present in the process environment, including systemd `Environment=` entries and `docker run -e`
2. Values from `.env`
3. Built-in defaults

Because the process environment wins, an existing systemd unit that sets its own variables keeps working after `.env` is introduced, and a one-off command can override a single setting without editing files.

Docker Compose reads the same `.env` file for its own interpolation, which is why the file carries both indexer settings and Compose settings. Start from the documented template:

```bash
cp .env.example .env
chmod 600 .env
```

`.env` is git-ignored and excluded from Docker image builds. Never commit it, and never bake it into an image.

## Indexer Variables

These are read by `ethsync.py` in every deployment mode.

| Variable                 | Default                | Description                                                                                                 |
| ------------------------ | ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| `DB_NAME`                | _(required)_           | PostgreSQL database name (`index`) or a full connection URI (`postgres://user:password@host:5432/database`) |
| `ETH_URL`                | _(required)_           | Ethereum RPC endpoint: `http://…`, `https://…`, `ws://…`, `wss://…`, or a path to an IPC socket             |
| `START_BLOCK`            | `1`                    | First block to index, used only when both `ethtxs` and `sync_state` are empty                               |
| `CONFIRMATIONS_BLOCK`    | `0`                    | Number of newest blocks to stay behind the chain head                                                       |
| `PERIOD`                 | `20`                   | Seconds to sleep between synchronization passes                                                             |
| `LOG_FILE`               | _(empty)_              | Path to a log file. Empty or unset logs to stdout                                                           |
| `ADDRESS_FILTER_ENABLED` | `false`                | Store only transfers involving addresses from `ADDRESS_FILTER_FILE`                                         |
| `ADDRESS_FILTER_FILE`    | `filter/addresses.txt` | Path to the monitored-address list                                                                          |

Missing `DB_NAME` or `ETH_URL` makes the process exit with status 2 and a message naming the variable.

### `DB_NAME`

A bare name connects over the local socket as the operating-system user, which is what the systemd template does. A URI connects anywhere:

```ini
DB_NAME=index
DB_NAME=postgres://api_user:password@db.internal:5432/index
```

Passwords are redacted from any error message the indexer logs, but a URI still puts the password in the process environment. Prefer a local socket, a `.pgpass` file, or a secrets manager when the deployment allows it.

### `ETH_URL`

The transport is chosen from the prefix:

| Value                           | Provider   |
| ------------------------------- | ---------- |
| `http://127.0.0.1:8545`         | HTTP       |
| `https://node.example.com`      | HTTP       |
| `ws://127.0.0.1:8546`           | WebSocket  |
| `wss://node.example.com`        | WebSocket  |
| `/home/geth/.ethereum/geth.ipc` | IPC socket |

Anything without a recognized URL scheme is treated as an IPC path.

### `START_BLOCK`

Only consulted on a completely empty deployment. Once `sync_state` holds a checkpoint, changing `START_BLOCK` has no effect — the indexer continues from the checkpoint. To move the starting point later, see [re-indexing a block range](./upgrading.md#re-indexing-a-block-range).

Starting from a recent block is the primary way to control disk usage. See [storage planning](../reference/database.md#storage-planning).

### `CONFIRMATIONS_BLOCK`

The indexer stops at `chain head − CONFIRMATIONS_BLOCK`. `0` indexes as close to the head as possible and can briefly surface transactions that a reorganization later removes. Values around `12` are a common compromise for wallet-facing deployments.

### `PERIOD`

Sleep between passes. It does not throttle the backfill: within a pass the indexer processes every block up to the target height without pausing. Lower values reduce the delay before a new block appears in the API; higher values reduce idle RPC and database traffic.

### `LOG_FILE`

An empty value logs to stdout, which is what container and `journalctl` deployments want. A path opens that file for append; the process must be able to create and write it, and rotation is left to the operating system.

### `ADDRESS_FILTER_ENABLED`

Accepted true values: `1`, `true`, `yes`, `on`. Accepted false values: `0`, `false`, `no`, `off`. Matching is case-insensitive. Any other value is a configuration error and the process exits with status 2 rather than guessing.

### `ADDRESS_FILTER_FILE`

A relative path is resolved against the repository directory, and `~` is expanded. Under Docker Compose the `filter` directory is mounted read-only at `/eth-storage/filter`, so keep the file inside it. Behavior is described in [Address filter](./address-filter.md).

## Docker Compose Variables

These are consumed by `docker-compose.yml` itself, not by `ethsync.py`. Remove them from a systemd environment file.

| Variable                         | Default                                              | Description                                                 |
| -------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------- |
| `ETH_INDEXER_IMAGE`              | `ghcr.io/adamant-im/eth-transactions-storage:latest` | Indexer image to run. Pin a version tag for production      |
| `DOCKER_ETH_URL`                 | `ws://publicnode:8546`                               | RPC endpoint passed to the container as `ETH_URL`           |
| `POSTGRES_DB`                    | `app_db`                                             | Database name created by the `db` service                   |
| `POSTGRES_USER`                  | `app_user`                                           | Database role created by the `db` service                   |
| `POSTGRES_PASSWORD`              | _(required)_                                         | Password for that role. Compose refuses to start without it |
| `PGRST_DB_SCHEMA`                | `public`                                             | Schema exposed by PostgREST                                 |
| `PGRST_DB_ANON_ROLE`             | `web_anon`                                           | Role used for unauthenticated requests. Keep it read-only   |
| `PGRST_DB_MAX_ROWS`              | `10000`                                              | Hard cap on rows returned per request                       |
| `PGRST_OPENAPI_SERVER_PROXY_URI` | `http://127.0.0.1:3000`                              | Public base URL advertised in the OpenAPI description       |

Compose builds `DB_NAME` and `PGRST_DB_URI` from `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`, so the password lives in exactly one field.

Use only URL-safe characters in `POSTGRES_PASSWORD`: letters, digits, period, underscore, tilde, and hyphen. `$` starts Compose interpolation, and `:`, `/`, and `@` break the generated URI.

## PostgREST Configuration

When running PostgREST outside Compose, the equivalent settings live in `postgrest.conf`:

```ini
db-uri = "postgres://api_user@/index"
db-schema = "public"
db-anon-role = "web_anon"
db-pool = 10
db-max-rows = 10000
server-host = "127.0.0.1"
server-port = 3000
```

`db-anon-role` and `db-max-rows` carry security and availability consequences that are explained in [Security and public deployment](./security.md).

## Verifying a Configuration

```bash
ETH_URL=http://127.0.0.1:8545 python3 ethtest.py
DB_NAME=index python3 pgtest.py
docker compose config          # render the resolved Compose configuration
```

`docker compose config` prints resolved values including the database password. Do not paste its output into issues or chat logs.
