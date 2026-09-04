# Used by ADAMANT

[ADAMANT](https://adamant.im) is a decentralized, privacy-focused messenger and cryptocurrency wallet. It maintains this project and runs it in production to power Ethereum and ERC-20 transaction history in its wallets.

This page is here as a worked integration example. Nothing on it is required to run the indexer, and no ADAMANT component is a dependency — the software is a general-purpose Ethereum indexer that happens to have a well-documented production adopter.

## Why It Matters to Other Operators

- **The API contract is proven.** The endpoints, columns, and encodings described in the [API reference](../reference/api.md) are the ones shipping clients depend on, across two independent codebases and four platforms
- **The index set is evidence-based.** The [minimal five-index set](../reference/database.md#index-strategy) was derived by auditing real client traffic rather than indexing every column that might be useful, which is where the 90–110 GB saving comes from
- **The operational guidance is field-tested.** Row caps, proxy rules, upgrade ordering, and storage figures on this site come from running the indexer against mainnet at scale, not from a lab

## Deployment Shape

ADAMANT runs the standard topology documented in [Architecture](../guide/architecture.md): an Ethereum execution client, `ethsync.py`, PostgreSQL, PostgREST behind nginx with the [documented proxy guards](../guide/security.md#reverse-proxy-rules), and no address filter, because wallet users import arbitrary addresses.

Clients treat indexer nodes as an interchangeable pool: any host serving the same API contract can serve any client, which is the same property a third-party deployment gets for free.

## Client Query Patterns

These are the exact request shapes ADAMANT clients issue. They are useful as a compatibility checklist: a deployment that answers all four correctly is compatible with both clients.

### 1. Native ETH transfers, single request

Used by [`adamant-im`](https://github.com/Adamant-im/adamant-im), the Web, PWA, Electron, and Android client, in `src/lib/nodes/eth-indexer/EthIndexerClient.ts`:

```http
GET /ethtxs?and=(contract_to.eq.,or(txfrom.eq.{address},txto.eq.{address}))&order=time.desc&limit=25
```

Served by `txfrom_index`, `txto_w_empty_contract_to_index`, and `time_index`.

### 2. Native ETH transfers, two requests

Used by [`adamant-iOS`](https://github.com/Adamant-im/adamant-iOS) in `Adamant/Modules/Wallets/Ethereum/EthWalletService.swift`, which fetches each direction separately and merges client-side:

```http
GET /ethtxs?txfrom=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
GET /ethtxs?txto=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
```

Each request uses exactly one address index, which is why the split pattern performs well.

### 3. ERC-20 transfers

Used by both clients, and on iOS by `ERC20WalletService.swift`:

```http
GET /ethtxs?and=(txto.eq.{contract_address},or(txfrom.eq.{address},contract_to.eq.000000000000000000000000{address_without_0x}))&order=time.desc&limit=25
```

Served by `txto_contract_to_index` and `txfrom_index`. The 24 leading zeros are the ABI padding described in the [API reference](../reference/api.md#transaction-object).

### 4. Health and availability

```http
GET /max_block
GET /aval
```

Clients poll `/max_block` to decide whether an indexer node is healthy and current enough to use, comparing `max` against the expected chain height. This is why `GRANT SELECT ON public.max_block TO web_anon;` is a hard requirement — without it, healthy nodes look broken to every client.

## Compatibility Commitment

Endpoint names, column names, and value encodings are a stable contract for every consumer, not just ADAMANT ones. Changes that would break the query shapes above are treated as breaking changes to the project and are not made casually.

If you build a client against this indexer, the four patterns above are a good compatibility test suite: they cover both address directions, both native and token transfers, ordering, pagination, and health checking.

## Related ADAMANT Repositories

| Repository                                                         | Relevance                                                        |
| ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| [`adamant-im`](https://github.com/Adamant-im/adamant-im)           | Web, PWA, Electron, and Android client; consumes this API        |
| [`adamant-iOS`](https://github.com/Adamant-im/adamant-iOS)         | Native iOS client; consumes this API                             |
| [`adamant-wallets`](https://github.com/Adamant-im/adamant-wallets) | Coin and token specifications shared across ADAMANT applications |
| [`adamant`](https://github.com/Adamant-im/adamant)                 | ADAMANT blockchain node                                          |
| [`docs`](https://github.com/Adamant-im/docs)                       | ADAMANT documentation, <https://docs.adamant.im>                 |

## Using It Yourself

Nothing above needs replicating. Start from the [introduction](../guide/introduction.md) and the [Docker Compose quick start](../guide/quick-start-docker.md) — the defaults are chosen for a standalone operator, and the address filter, index set, and starting block are all yours to tune.

Running this indexer in production for something else? Open an issue or a pull request and we will list it here.
