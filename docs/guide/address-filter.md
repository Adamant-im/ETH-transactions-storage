# Address Filter

The address filter narrows what the indexer stores to transfers involving a list of addresses you maintain. A full Ethereum index costs hundreds of gigabytes; a filtered index for a few thousand addresses costs almost nothing.

It is off by default, and the API contract does not change when it is on — the same endpoints return the same shapes over a smaller dataset.

## When to Use It

Use it when the set of interesting addresses is known in advance:

- A custodial service or exchange indexing only its own deposit addresses
- A treasury or accounting tool tracking company wallets
- A monitoring service watching a fixed set of contracts and counterparties
- A staging environment that should stay small

Do not use it for a general-purpose explorer, a non-custodial wallet where users import arbitrary addresses, or anything that must answer queries about an address you did not know about in advance. History for an address is only present from the moment it was on the list.

## Enabling It

1. Create the list from the template:

```bash
cp filter/addresses.txt.example filter/addresses.txt
chmod 600 filter/addresses.txt
```

2. Add one address per line:

```text
# Company hot wallet
0x1111111111111111111111111111111111111111
0x2222222222222222222222222222222222222222   # settlement
```

3. Enable the filter:

```ini
ADDRESS_FILTER_ENABLED=true
ADDRESS_FILTER_FILE=filter/addresses.txt
```

4. Start or restart the indexer.

## File Format

- One `0x`-prefixed, 40-hex-character address per line
- Empty lines are ignored
- Everything after `#` on a line is ignored, so full-line and trailing comments both work
- Matching is case-insensitive, so checksummed and lowercase forms are equivalent
- Duplicates are collapsed

Any line that is not a comment and not a valid address is a hard error. The file must contain at least one address.

`filter/addresses.txt` is git-ignored and excluded from Docker image builds. Only the `.example` template is tracked. The list is operator data — treat it like a customer list, because that is usually what it is.

## What Counts as a Match

For each candidate transaction the indexer compares the monitored set against three values:

| Value         | Meaning                                                                     |
| ------------- | --------------------------------------------------------------------------- |
| `txfrom`      | Transaction sender, which is also the token sender for ERC-20 transfers     |
| `txto`        | Transaction recipient, which is the token contract for ERC-20 transfers     |
| `contract_to` | ABI-encoded token recipient decoded from a `transfer(address,uint256)` call |

A transaction is stored when any of them is in the list. `contract_to` is stored as a 64-character ABI word, and the filter normalizes it back to a 20-byte address before comparing, so listing a plain address matches token transfers sent to it.

Because `txto` is compared too, listing a token contract address stores every direct `transfer` call to that contract, from anyone. That is useful for watching a token, and surprising if you meant to watch a holder.

## Reloading Without a Restart

The file is re-read at the start of every synchronization pass. Adding or removing an address takes effect within one `PERIOD`, and the indexer logs the new count whenever the set changes.

Under Docker Compose the whole `filter` directory is mounted, not a single file, so editors that save atomically by replacing the file stay visible to the running container.

## Fail-Closed Behavior

When the filter is enabled, a missing, empty, or invalid file stops block processing instead of silently indexing everything. At startup the process exits with status 2; during a pass the error is logged and the pass is abandoned without advancing the checkpoint. Nothing is lost — fix the file and the indexer resumes from where it stopped.

This is deliberate. A filter that silently turns itself off would fill the disk of a deployment sized for a few thousand addresses.

## Operational Tradeoffs

**No backfill.** The filter applies to blocks processed after it is enabled. Enabling it does not delete existing rows, and adding an address does not fetch its earlier history. To capture history for a newly added address you must re-index the range, which means re-scanning every block in it.

**Same RPC cost.** Every block is still fetched in full. The filter saves database writes and disk, not node bandwidth or CPU. Receipt lookups are avoided for skipped transactions, which is where the RPC saving actually is.

**Unchanged blind spots.** The filter cannot see what the indexer never parses. Internal ETH transfers and ERC-20 transfers made through `transferFrom`, multisig wallets, routers, batchers, or aggregators are invisible with or without it. See [what gets indexed](./introduction.md#what-gets-indexed).

**Checkpoint still advances.** Blocks that contribute no rows still move `sync_state.last_block` forward, so a filtered deployment never rescans the same range. This is exactly why the checkpoint is stored separately from `MAX(block)`.

## Rebuilding Filtered History

To rebuild everything for a new address list, stop the indexer, set `START_BLOCK` to the first block you want, and clear both the data and the checkpoint in one transaction:

```sql
BEGIN;
TRUNCATE TABLE public.ethtxs;
TRUNCATE TABLE public.sync_state;
COMMIT;
```

Truncating `ethtxs` alone does nothing, because `sync_state` still reports the processed height. For a partial rescan from block `N`, see [re-indexing a block range](./upgrading.md#re-indexing-a-block-range).
