# REST API Reference

PostgREST exposes the indexed data as a read-only HTTP API. There is no custom API code: endpoints are tables and views, and the query language is [PostgREST's](https://postgrest.org/en/stable/api.html).

All examples use `http://127.0.0.1:3000` as the base URL and lowercase addresses. Address columns are `citext`, so case does not matter.

## Endpoints

| Endpoint     | Backing object     | Purpose                                     |
| ------------ | ------------------ | ------------------------------------------- |
| `/ethtxs`    | `public.ethtxs`    | Indexed native ETH and ERC-20 transfers     |
| `/max_block` | `public.max_block` | Highest processed block and indexer version |
| `/aval`      | `public.aval`      | Availability probe                          |

Only `GET`, `HEAD`, and `OPTIONS` are meaningful. The anonymous role has no write privileges, and public deployments should reject other verbs at the proxy.

## Transaction Object

```json
{
  "time": 1576008898,
  "txfrom": "0x6b924750e56a674a2ad01fbf09c7c9012f16f094",
  "txto": "0x1143e097e134f3407ef6b088672ccece9a4f8cdd",
  "value": 1200000000000000,
  "gas": 21000,
  "gasprice": 2500000000,
  "block": 9084957,
  "txhash": "0xcf56a031dfc89f5a3686cd441ea97ae96a66f5809a4c8c1b370485a04fb37e0e",
  "contract_to": "",
  "contract_value": ""
}
```

| Field            | Type      | Description                                                                                         |
| ---------------- | --------- | --------------------------------------------------------------------------------------------------- |
| `time`           | `integer` | Block timestamp in Unix epoch seconds. Identical for every transaction in a block                   |
| `txfrom`         | `citext`  | Transaction sender. For ERC-20 transfers this is the token sender                                   |
| `txto`           | `citext`  | Transaction recipient. For ERC-20 transfers this is the token contract address                      |
| `value`          | `numeric` | ETH amount in wei. `0` for ERC-20 transfers                                                         |
| `gas`            | `bigint`  | Gas actually used, from the receipt's `gasUsed`                                                     |
| `gasprice`       | `bigint`  | Gas price in wei                                                                                    |
| `block`          | `integer` | Block number                                                                                        |
| `txhash`         | `citext`  | Transaction hash, `0x`-prefixed                                                                     |
| `contract_to`    | `citext`  | Empty for native transfers. For ERC-20, the ABI-encoded recipient: a 64-character hex word, no `0x` |
| `contract_value` | `citext`  | Empty for native transfers. For ERC-20, the ABI-encoded amount as a hex string, no `0x`             |

Two encoding details matter when you build queries and parse results:

- `contract_to` is the raw calldata word, so the address is zero-padded to 32 bytes. To match address `0xabc…275`, query `contract_to=eq.000000000000000000000000abc…275` — the 40 hex characters without `0x`, prefixed by 24 zeros
- `contract_value` is hexadecimal without a `0x` prefix, so `parseInt(value, 16)` or an equivalent big-integer parse is required. It is raw token units; apply the token's decimals yourself

`contract_to = ''` is the marker that distinguishes a native ETH transfer from a token transfer, and it is what the partial index is built on. Always include it when you want native transfers only.

## Query Basics

PostgREST maps query parameters to SQL:

| Parameter                  | Effect                                      |
| -------------------------- | ------------------------------------------- |
| `column=eq.value`          | Equality filter                             |
| `column=gte.value`         | Comparison: `gt`, `gte`, `lt`, `lte`, `neq` |
| `or=(a.eq.1,b.eq.2)`       | Boolean OR of conditions                    |
| `and=(a.eq.1,b.eq.2)`      | Boolean AND, needed when nesting `or`       |
| `order=time.desc`          | Ordering                                    |
| `limit=25` and `offset=25` | Pagination                                  |
| `select=time,txhash,value` | Column projection                           |

## Native ETH Transfers for an Address

One request covering both directions:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?and=(contract_to.eq.,or(txfrom.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98,txto.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98))&order=time.desc&limit=25"
```

The same result as two direction-specific requests, which some clients prefer because each one uses a single index and merges client-side:

```bash
# Outgoing
curl -s "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&order=time.desc&limit=25"

# Incoming
curl -s "http://127.0.0.1:3000/ethtxs?txto=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&order=time.desc&limit=25"
```

## ERC-20 Transfers for an Address

Token transfers are selected by contract address in `txto`, then by the holder appearing as either the sender or the ABI-encoded recipient. This example uses USDT (`0xdac17f958d2ee523a2206206994597c13d831ec7`):

```bash
curl -s "http://127.0.0.1:3000/ethtxs?and=(txto.eq.0xdac17f958d2ee523a2206206994597c13d831ec7,or(txfrom.eq.0xabfdf505ffd5587d9e7707dfb47f45af1f03e275,contract_to.eq.000000000000000000000000abfdf505ffd5587d9e7707dfb47f45af1f03e275))&order=time.desc&limit=25"
```

All transfers of one token, regardless of participant:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txto=eq.0xdac17f958d2ee523a2206206994597c13d831ec7&order=time.desc&limit=100"
```

Everything an address did, native and tokens together:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?or=(txfrom.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98,txto.eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98)&order=time.desc&limit=25"
```

## Filtering

Block range:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&block=gte.21000000&block=lt.21100000&order=block.desc"
```

Time range, Unix seconds:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txto=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&time=gte.1735689600&time=lt.1738368000&order=time.desc"
```

Minimum amount, in wei:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txto=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&value=gte.1000000000000000000&order=time.desc"
```

Fewer columns, smaller responses:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&select=time,block,txhash,value&order=time.desc&limit=50"
```

Always include `txfrom` or `txto`. Filtering only by `txhash`, `value`, `gas`, or `block` has no supporting index in the recommended set and results in a sequential scan. Look up a single transaction by hash through the node's `eth_getTransactionByHash` instead.

## Pagination

Offset pagination, simple and adequate for the first pages:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&order=time.desc&limit=25&offset=25"
```

The equivalent using HTTP range headers, which also returns a `Content-Range` response header:

```bash
curl -s -H "Range-Unit: items" -H "Range: 0-24" \
  "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&order=time.desc"
```

Offsets get linearly slower, and public deployments commonly reject offsets above a threshold. For deep history, paginate on `time` using the last row you received:

```bash
curl -s "http://127.0.0.1:3000/ethtxs?txfrom=eq.0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98&contract_to=eq.&time=lt.1735689600&order=time.desc&limit=25"
```

Two caveats: every transaction in a block shares one timestamp, so a strict `lt` boundary can skip same-second rows — use `lte` plus client-side de-duplication when exactness matters. And `Prefer: count=exact` forces a full scan of the matching set; use `count=planned` or omit it.

Responses are capped by `db-max-rows`, 10,000 by default, whether or not `limit` is present.

## Health and Status

```bash
curl -s "http://127.0.0.1:3000/max_block"
```

```json
[{ "max": 19500000, "version": "2.5.0" }]
```

`max` is `GREATEST(MAX(ethtxs.block), sync_state.last_block)`, so it advances even through blocks that produced no rows. It is `null` only when nothing has been processed yet. `version` is the indexer version.

A practical liveness check compares `max` against the node's `eth_blockNumber` and alerts when the gap exceeds what `CONFIRMATIONS_BLOCK` and `PERIOD` explain.

```bash
curl -s "http://127.0.0.1:3000/aval"
```

```json
[{ "status": true }]
```

`/aval` is a static row. It confirms that PostgREST is up and can reach the database, and says nothing about indexing progress — use `/max_block` for that.

## Response and Error Codes

| Status | Meaning                                                              |
| ------ | -------------------------------------------------------------------- |
| 200    | Success. Body is a JSON array, empty when nothing matches            |
| 206    | Partial content, returned when a `Range` header was used             |
| 400    | Malformed query, or blocked by proxy validation rules                |
| 405    | Method not allowed by the proxy                                      |
| 416    | Requested range not satisfiable                                      |
| 500    | Database error. Most often a missing or misconfigured anonymous role |

PostgREST error bodies carry `message`, `details`, `hint`, and `code`. See [Troubleshooting](../guide/troubleshooting.md#api-returns-500-for-every-request) for the usual causes of a 500.

## Stability

Endpoint names, column names, and value encodings are a stable contract. Existing consumers keep working across indexer upgrades, and changes that would break them are treated as breaking changes to the project. Query patterns proven in production are listed on [Used by ADAMANT](../project/adamant.md).

## Querying SQL Directly

PostgREST is optional. Nothing stops an application from reading `public.ethtxs` with SQL, which is often the better choice for analytics, exports, and joins against your own tables:

```sql
SELECT time, txhash, value
FROM public.ethtxs
WHERE txfrom = '0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98'
  AND contract_to = ''
ORDER BY time DESC
LIMIT 25;
```

Use a dedicated read-only role for such consumers, as described in [Security](../guide/security.md#read-only-database-access).
