# Upgrading

Upgrades touch three things that must stay consistent: the running code, the database schema, and the environment. This page covers the order that keeps them aligned.

Always read the [release notes](https://github.com/Adamant-im/ETH-transactions-storage/releases) for the version you are moving to before starting.

## Bare-Metal and systemd Deployments

1. **Stop the indexer** so the deployed code and the database checkpoint cannot diverge.

```bash
sudo systemctl stop ethsync.service
```

2. **Update the full checkout.** Runtime modules, dependencies, and SQL schema files are versioned together; updating only one file produces a mismatched deployment.

```bash
git fetch --tags
git checkout <version-tag>
```

3. **Install dependencies**, which is how `python-dotenv` and any other new requirement arrive.

```bash
pip3 install -r requirements.txt
```

4. **Apply the schema** as a role allowed to change grants. The script is idempotent: it creates missing objects, initializes `sync_state` from the existing highest block, grants permissions to existing `api_user` and `app_user` roles, and refreshes the `max_block` view. It never deletes transaction data.

```bash
psql -v ON_ERROR_STOP=1 -d index -f create_tables.sql
```

5. **Verify the environment.** Confirm the service still supplies the production `DB_NAME`, `ETH_URL`, `START_BLOCK`, `CONFIRMATIONS_BLOCK`, `PERIOD`, and `LOG_FILE` values. An existing systemd unit can stay as it is: process environment values take precedence over `.env`, and the address filter defaults to disabled.

6. **Start and confirm progress.**

```bash
sudo systemctl start ethsync.service
psql -d index -c 'SELECT * FROM public.max_block;'
```

`max` must advance within a few `PERIOD` intervals.

::: warning
Do not replace a working `ethsync.service` with the repository template until a production `.env` exists with equivalent values. The template requires `EnvironmentFile` to be present, and `.env.example` ships safe standalone defaults, not your endpoints or credentials.
:::

## Docker Compose Deployments

The schema must be in place before the new image starts, for the same reason it must on bare metal.

1. Update the checkout, so `create_tables.sql` and `docker-compose.yml` match the new image.

2. Stop the indexer:

```bash
docker compose stop eth-storage
```

3. Apply the schema, because the PostgreSQL entrypoint runs `create_tables.sql` only on an empty data directory:

```bash
docker compose exec -T db sh -c \
  'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' \
  < create_tables.sql
```

4. Pin the new version in `.env`:

```ini
ETH_INDEXER_IMAGE=ghcr.io/adamant-im/eth-transactions-storage:2.5.0
```

5. Pull and start the new indexer:

```bash
docker compose pull eth-storage
docker compose up -d eth-storage
```

6. Verify:

```bash
docker compose logs --tail=50 eth-storage
curl -s http://127.0.0.1:3000/max_block
```

::: warning
Do not start the new image before applying the schema. On a database created before `sync_state` existed, the startup checkpoint query fails with `relation "public.sync_state" does not exist` and the indexer exits with status 1. The Compose service declares no restart policy, so applying the schema afterwards does not bring the container back and indexing stays stopped until you start it again.
:::

Rolling back is setting `ETH_INDEXER_IMAGE` to the previous version tag and repeating steps 5 and 6. See [Docker image](../reference/docker-image.md#rollback).

## Switching to the Minimal Index Set

Existing deployments created eight indexes. The current recommendation is five. Adding the new ones does not remove the old ones, so reclaim the space explicitly.

1. Create the minimal set:

```bash
psql -d index -f create_indexes.sql
psql -d index -f create_indexes_add.sql
```

On a live database use `CREATE INDEX CONCURRENTLY` instead, because `CREATE INDEX` takes a `ShareLock` that blocks the indexer's inserts.

2. Confirm the new indexes are valid and in use, then drop the redundant ones without blocking writes:

```sql
DROP INDEX CONCURRENTLY IF EXISTS public.contract_to_index;
DROP INDEX CONCURRENTLY IF EXISTS public.txto_index;
DROP INDEX CONCURRENTLY IF EXISTS public.txto_txfrom_index;
```

This frees roughly 90–110 GB on a one-year dataset of about 490 million rows. If a third-party consumer issues queries the minimal set does not cover, keep the legacy indexes instead — `create_indexes_legacy.sql` recreates them. Details in [Database and Indexes](../reference/database.md#index-strategy).

## Switching PostgREST to `web_anon`

Order matters, or the public API returns 500 for every request:

1. Apply the role and grants with `create_tables.sql`
2. Verify:

```bash
psql -d index -c "SET ROLE web_anon; SELECT 1 FROM public.ethtxs LIMIT 1; SELECT * FROM public.max_block; SELECT * FROM public.aval;"
```

3. Set `db-anon-role = "web_anon"` and `db-max-rows = 10000` in `postgrest.conf`
4. Restart PostgREST

Older databases upgraded without re-running `create_tables.sql` must at minimum have `GRANT SELECT ON public.max_block TO web_anon;`. Without it the `/max_block` health check fails with a permission error, and clients that poll it treat the node as unavailable.

## Re-indexing a Block Range

Both the rows and the checkpoint have to move together, or the indexer will not revisit the range.

Full rebuild from a new `START_BLOCK`:

```sql
BEGIN;
TRUNCATE TABLE public.ethtxs;
TRUNCATE TABLE public.sync_state;
COMMIT;
```

Partial rescan from block `N`:

```sql
BEGIN;
DELETE FROM public.ethtxs WHERE block >= 21000000;
UPDATE public.sync_state SET last_block = 20999999 WHERE singleton = TRUE;
COMMIT;
```

Stop the indexer before either operation and start it afterwards. Re-indexing re-fetches every block in the range from the node, so a wide range is expensive in RPC calls and time.

## Version Compatibility

- The database schema is additive. `create_tables.sql` from a newer version can be applied to an older database without losing data
- API endpoint names, column names, and response shapes are treated as a stable contract. Existing consumers keep working across upgrades
- Downgrading the indexer while keeping a newer schema works, because the extra objects are ignored. Downgrading past the introduction of `sync_state` is not supported
