# Quick Start: Manual and systemd

This path installs the indexer directly on a host, which is the usual choice when PostgreSQL and the Ethereum node already run there.

## Prerequisites

- Synchronized Ethereum node with JSON-RPC enabled
- Python 3.9 or newer
- PostgreSQL 12 or newer
- PostgREST 10 or newer, if you want the REST API. Version 11 or newer for the role-level `statement_timeout` guard described in [Security](./security.md#these-rules-are-heuristics)
- An account able to administer PostgreSQL, for the schema and role setup in step 2

Verify the node first:

```bash
curl -H "Content-Type: application/json" \
  -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545
```

## 1. Install the Code and Dependencies

```bash
git clone https://github.com/Adamant-im/ETH-transactions-storage.git
cd ETH-transactions-storage
pip3 install -r requirements.txt
```

## 2. Create the Database and Role

Setup is privileged; running the indexer is not. `create_tables.sql` creates the `citext` extension and the `web_anon` role, so it has to run as a PostgreSQL administrator. `api_user`, the role the indexer connects as, never needs superuser privileges.

Create the role and the database:

```bash
sudo -u postgres createuser api_user
sudo -u postgres createdb -O api_user index
```

Apply the schema, views, and the read-only role. Redirect the file instead of passing `-f`, so your own shell reads it and the `postgres` user needs no access to the checkout:

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -d index < create_tables.sql
```

Grant the indexer the minimum it needs, in the same privileged session:

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -d index <<'SQL'
GRANT SELECT, INSERT, DELETE ON public.ethtxs TO api_user;
GRANT SELECT, INSERT, UPDATE ON public.sync_state TO api_user;
GRANT SELECT ON public.aval, public.max_block TO api_user;
SQL
```

Applying `create_tables.sql` as `api_user` fails at `CREATE ROLE web_anon` with `permission denied to create role`, and running it from a root shell without `-u postgres` fails earlier with `role "root" does not exist`. Use the administrator for this step.

`create_tables.sql` is idempotent and safe to re-run. Details on every object it creates are in the [database reference](../reference/database.md).

## 3. Configure the Environment

```bash
cp .env.example .env
chmod 600 .env
```

Set the values for this host:

```ini
DB_NAME=index
ETH_URL=http://127.0.0.1:8545
START_BLOCK=21000000
CONFIRMATIONS_BLOCK=12
PERIOD=20
LOG_FILE=/home/api_user/ETH-transactions-storage/ethsync.log
```

`ethsync.py`, `ethtest.py`, and `pgtest.py` load `.env` automatically from the repository directory. Values already present in the process environment win, so a one-off run can override a single setting without editing the file.

Choosing a `START_BLOCK` close to the current chain head is the single most effective way to control disk usage. See [storage planning](../reference/database.md#storage-planning).

## 4. Run the Indexer

```bash
python3 ethsync.py
```

Or with everything on the command line:

```bash
DB_NAME=index \
ETH_URL=http://127.0.0.1:8545 \
START_BLOCK=21000000 \
PERIOD=20 \
python3 ethsync.py
```

Watch progress:

```bash
psql -d index -c 'SELECT * FROM public.max_block;'
```

## 5. Create Indexes After the Backfill

Let the indexer reach the chain head first, then build the query indexes:

```bash
psql -d index -f create_indexes.sql
psql -d index -f create_indexes_add.sql
```

`CREATE INDEX` takes a `ShareLock` that blocks the indexer's inserts. On a live database, use `CREATE INDEX CONCURRENTLY` or a maintenance window. See [Database and Indexes](../reference/database.md#index-strategy).

## 6. Run as a systemd Service

The repository includes `ethsync.service` as a template. It requires `.env` to exist, so a missing production configuration fails before the indexer starts rather than silently falling back to defaults.

```bash
sudo cp ethsync.service /etc/systemd/system/ethsync.service
```

Adjust `User`, `Group`, `WorkingDirectory`, `ExecStart`, and `EnvironmentFile` to match your paths, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ethsync.service
sudo systemctl start ethsync.service
sudo systemctl status ethsync.service
```

Follow the logs:

```bash
journalctl -u ethsync.service -f     # when LOG_FILE is empty
tail -f /home/api_user/ETH-transactions-storage/ethsync.log
```

Do not replace a working systemd unit with the repository template until a production `.env` with equivalent values exists. See [Upgrading](./upgrading.md).

## 7. Set Up PostgREST

[Install PostgREST](https://postgrest.org/en/stable/install.html), then create `postgrest.conf`:

```ini
db-uri = "postgres://api_user@/index"
db-schema = "public"
db-anon-role = "web_anon"
db-pool = 10
db-max-rows = 10000
server-host = "127.0.0.1"
server-port = 3000
```

```bash
postgrest postgrest.conf
```

`db-anon-role` and `db-max-rows` are load-bearing security and stability settings, not style choices. Read [Security and public deployment](./security.md) before binding PostgREST to anything other than `127.0.0.1`.

## Diagnostics

```bash
ETH_URL=http://127.0.0.1:8545 python3 ethtest.py   # node connectivity and height
DB_NAME=index python3 pgtest.py                    # database connectivity and MAX(block)
```

## Next Steps

- [Configuration reference](./configuration.md)
- [Security and public deployment](./security.md)
- [Troubleshooting](./troubleshooting.md)
