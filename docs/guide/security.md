# Security and Public Deployment

The indexer stores public blockchain data, so confidentiality is rarely the concern. Availability and cost are. An unguarded PostgREST endpoint over a multi-hundred-gigabyte table is a denial-of-service target that a single `curl` can trigger.

Read this page before binding the API to anything other than `127.0.0.1`.

## Threat Model

| Risk                                   | Mitigation                                            |
| -------------------------------------- | ----------------------------------------------------- |
| Writes or deletes through the API      | Anonymous role with `SELECT`-only grants              |
| Out-of-memory from unbounded responses | `db-max-rows`                                         |
| Full table scans on unindexed columns  | Reverse-proxy query validation                        |
| Expensive exact counts                 | Reject `Prefer: count=exact` at the proxy             |
| Deep pagination                        | Reject large `offset` values at the proxy             |
| Credential leakage                     | File permissions, redacted logs, no secrets in images |
| Address-list disclosure                | `filter/addresses.txt` ignored by Git and Docker      |

## Read-Only Database Access

PostgREST executes every anonymous request as the role named in `db-anon-role`. That role is `web_anon`, created by `create_tables.sql` with `NOLOGIN` and only these grants:

```sql
GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON public.ethtxs, public.aval, public.max_block TO web_anon;
```

`web_anon` has no `INSERT`, `UPDATE`, or `DELETE` anywhere, and no access to `sync_state`. Even a request that reaches PostgREST unfiltered cannot modify data.

The indexer role is separate and also unprivileged. It needs `SELECT, INSERT, DELETE` on `ethtxs` and `SELECT, INSERT, UPDATE` on `sync_state`, and never requires superuser.

Never point `db-anon-role` at the indexer role or at a superuser.

## Row Limits

```ini
db-max-rows = 10000
```

Without this, `GET /ethtxs` with no `limit` tries to serialize the entire table into one JSON document. PostgreSQL cannot build a value larger than 1 GB, so the request fails with a 500 after consuming a large amount of memory and I/O on both the database and the API process.

With it:

- An explicit `?limit=25` is honored and returns 25 rows
- A request with no `limit`, or one above the cap, returns at most 10,000 rows

`db-max-rows` bounds the rows **returned**, not the rows **scanned**. A query that reads 400 million rows and returns 10 is still expensive. That is what the proxy rules below are for.

## Reverse Proxy Rules

Put a proxy in front of PostgREST. This nginx configuration enforces the minimum:

```nginx
# Public ETH indexer API
location /ethtxs {
    # 1. The API is read-only; reject write verbs at the edge
    if ($request_method !~ ^(GET|HEAD|OPTIONS)$) { return 405; }

    # 2. Require an indexed address predicate.
    # Without txfrom or txto the query falls back to a sequential scan
    # over the whole table, which is hundreds of gigabytes on a full index.
    if ($args !~ "(txfrom|txto)") { return 400; }

    # 3. Reject exact counts, which force a full index or table scan
    if ($http_prefer ~* "count=") { return 400; }

    # 4. Reject deep pagination
    if ($args ~ "offset=[0-9]{7,}") { return 400; }

    proxy_pass http://127.0.0.1:3000;
}

location /aval {
    if ($request_method !~ ^(GET|HEAD|OPTIONS)$) { return 405; }
    proxy_pass http://127.0.0.1:3000;
}

location /max_block {
    if ($request_method !~ ^(GET|HEAD|OPTIONS)$) { return 405; }
    proxy_pass http://127.0.0.1:3000;
}
```

Notes on these rules:

- Keep the method allow-list inside the specific `location` blocks. If `location /` proxies to an Ethereum JSON-RPC endpoint on the same host, a server-level allow-list would break it, because JSON-RPC requires `POST`
- `txhash` is not in the minimal index set on purpose. Look transactions up by hash through the node's `eth_getTransactionByHash` instead of scanning the table
- Consider adding `limit_req` rate limiting and a request timeout. Neither is in the snippet because sensible values depend entirely on your traffic
- Terminate TLS at the proxy. PostgREST should keep listening on `127.0.0.1`

## Only Expose What You Need

`server-host = "127.0.0.1"` in `postgrest.conf` keeps the API unreachable from outside the host. In the Compose stack, `postgrest` publishes port 3000 and `db` publishes 5432 to make local development easy — remove or restrict those `ports:` entries before running the stack on a public network, and never publish PostgreSQL to the internet.

## Secrets Handling

- `.env` is git-ignored and excluded from image builds. Keep it at mode `600`
- `filter/addresses.txt` is git-ignored and excluded from image builds. Keep it at mode `600`
- The indexer redacts passwords from PostgreSQL error messages before logging them, in both URI and `password=` keyword forms
- `docker compose config` prints resolved secrets. Do not paste its output into issues, pull requests, or chat
- Nothing in the published image contains credentials, address lists, or database data. Configuration is supplied at run time
- Prefer a local socket, `.pgpass`, or a secrets manager over a password inside `DB_NAME`

## No Telemetry

The indexer opens outbound connections to two places: the Ethereum endpoint in `ETH_URL` and the PostgreSQL server in `DB_NAME`. There is no analytics, no crash reporting, no update check, and no usage beacon. Address lookups performed by your users are visible only to you.

The bundled local search on this documentation site runs entirely in the browser and sends no queries anywhere.

## Upgrading an Existing Public Node Safely

Switching an existing deployment to `web_anon` in the wrong order takes the public API down. Apply the database changes first:

1. Run `create_tables.sql`, or apply the role and grants manually
2. Verify the role works:

```bash
psql -d index -c "SET ROLE web_anon; SELECT 1 FROM public.ethtxs LIMIT 1; SELECT * FROM public.max_block; SELECT * FROM public.aval;"
```

3. Only then set `db-anon-role = "web_anon"` and `db-max-rows = 10000` in `postgrest.conf` and restart PostgREST

If PostgREST is switched to a role that does not exist or lacks grants, every anonymous request returns 500 immediately. Full sequence in [Upgrading](./upgrading.md).

## Reporting a Vulnerability

Report security issues privately to <devs@adamant.im> rather than opening a public issue. See [Contributing and Releases](../project/contributing.md#reporting-security-issues).
