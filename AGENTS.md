# Ethereum Transactions Storage: AI Agent Operating Manual

This document defines how AI agents must work in this repository.

## Mission

`ETH-transactions-storage` is a background indexing service and database backend for the ADAMANT ecosystem. It indexes Ethereum native transfers and ERC-20 token transfer transactions into PostgreSQL, exposing a performant RESTful API via PostgREST for ADAMANT clients (Web/PWA, iOS, Android, Desktop).

Agent output must optimize for:

1. Indexing reliability and data integrity
2. Database query performance and storage efficiency
3. Security, access control, and metadata minimization
4. Open-source maintainability, clean documentation, and contributor clarity

If tradeoffs are required, preserve indexing correctness and database integrity first.

## Language Policy

- Developers may communicate with AI in any language
- All repository artifacts must be in English only
- Write all code, comments, docs, commit messages, PR text, and issues in English

## Writing Style

- In bullet and numbered lists, do not add a trailing period when an item contains one sentence
- If an item contains two or more sentences, end every sentence with a period

## Markdown Lint Rules for AI-Generated Docs

- For every Markdown list, keep one blank line before the list and one blank line after the list
- Always keep a blank line between a heading and the list that follows it to satisfy MD032 (`blanks-around-lists`)
- Use fenced code blocks with matching opening and closing fences and include a language tag when applicable
- Follow project configuration in `.markdownlint.jsonc`

## Product Context and Values

ADAMANT is a decentralized, privacy-focused messaging and cryptocurrency ecosystem. Because native Ethereum nodes lack built-in address-indexed transaction history queries, this service acts as dedicated indexing middleware.

Agent decisions must:

- Maintain zero tracking and zero telemetry
- Preserve compatibility with ADAMANT client applications (`adamant-im`, `adamant-iOS`, etc.)
- Keep indexing and database queries lightweight for independent self-hosted operators
- Ensure resilience against Ethereum node disconnections, sync delays, and database restarts

## Sources of Truth

Use these sources when implementing or reviewing changes:

- This repository: `README.md`, `ethsync.py`, SQL schemas, and configuration templates
- ADAMANT organization guidelines: <https://github.com/Adamant-im/.github>
- Issue prefix guidance: <https://github.com/orgs/Adamant-im/discussions/5>
- Label catalog: <https://github.com/orgs/Adamant-im/discussions/1>
- Client integration references:
  - `adamant-im`: `src/lib/nodes/eth-indexer/EthIndexerClient.ts`
  - `adamant-iOS`: `Adamant/Modules/Wallets/Ethereum/EthWalletService.swift` and `ERC20WalletService.swift`
- PostgREST documentation: <https://postgrest.org/en/stable/api.html>
- Web3.py documentation: <https://web3py.readthedocs.io/>

If sources disagree:

1. Treat current repository code and client production contracts as implementation truth
2. Do not silently ignore mismatches; document them and propose synchronized updates

## System Map (What You Are Editing)

| File / Component            | Purpose                        | Key Responsibilities                                                                                                                                  |
| --------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ethsync.py`                | Main indexer daemon            | Connects to Ethereum RPC (HTTP/WS/IPC), polls blocks, parses and filters ETH/ERC-20 transfers, writes to PostgreSQL, handles reorg cleanup            |
| `address_filter.py`         | Address filter helpers         | Loads and validates monitored addresses, normalizes native and ABI-encoded address values, and evaluates transaction matches                          |
| `database.py`               | PostgreSQL connection helpers  | Supports database names and connection URIs while redacting credentials from diagnostics                                                              |
| `filter/addresses.txt`      | Monitored address list         | Ignored private file containing one Ethereum address per line for optional filtered indexing                                                          |
| `create_tables.sql`         | Base schema & views            | Creates `citext`, storage and sync-state tables, `public.max_block` health-check view, and the `web_anon` role                                        |
| `create_indexes.sql`        | Core database indexes (4 of 5) | Minimal core B-tree indexes for address and block lookups (`block_index`, `txfrom_index`, `txto_contract_to_index`, `txto_w_empty_contract_to_index`) |
| `create_indexes_add.sql`    | Additional index (5 of 5)      | Timestamp descending index (`time_index`) completing the minimal 5-index set                                                                          |
| `create_indexes_legacy.sql` | Deprecated / legacy indexes    | Optional indexes for non-standard queries (`contract_to_index`, `txto_index`, `txto_txfrom_index`)                                                    |
| `ethtest.py`                | Ethereum node test script      | Verifies RPC connectivity and queries current block height                                                                                            |
| `pgtest.py`                 | Database test script           | Verifies PostgreSQL connectivity and queries table status                                                                                             |
| `requirements.txt`          | Python dependencies            | Declares runtime dependencies (`web3`, `psycopg2-binary`)                                                                                             |
| `Dockerfile`                | Container build definition     | Builds minimal Python runtime environment for `ethsync.py`                                                                                            |
| `docker-compose.yml`        | Multi-container setup          | Configures PostgreSQL, PostgREST (`web_anon`, `db-max-rows`), local Geth node, and indexer service                                                    |
| `ethsync.service`           | Systemd unit template          | Manages background service execution, restart policies, and environment variables                                                                     |

## Environment Variables Configuration

`ethsync.py` is configured via environment variables:

| Variable                 | Default                | Description                                                                   |
| ------------------------ | ---------------------- | ----------------------------------------------------------------------------- |
| `DB_NAME`                | _(required)_           | PostgreSQL database name or connection URI                                    |
| `ETH_URL`                | _(required)_           | Ethereum node RPC endpoint (`http://...`, `ws://...`, or `/path/to/geth.ipc`) |
| `START_BLOCK`            | `1`                    | Starting block height when database is empty                                  |
| `CONFIRMATIONS_BLOCK`    | `0`                    | Number of trailing confirmation blocks to exclude from sync                   |
| `PERIOD`                 | `20`                   | Polling interval in seconds between synchronization passes                    |
| `LOG_FILE`               | `None`                 | Optional file path for file logging (defaults to stdout stream logging)       |
| `ADDRESS_FILTER_ENABLED` | `false`                | Enables storage filtering by the configured monitored-address list            |
| `ADDRESS_FILTER_FILE`    | `filter/addresses.txt` | Path to the monitored-address list                                            |

## Client Integration Contracts

ADAMANT clients query indexed transactions through PostgREST. AI agents must preserve compatibility with these query shapes:

### 1. Native ETH transfers (adamant-im)

```http
GET /ethtxs?and=(contract_to.eq.,or(txfrom.eq.{address},txto.eq.{address}))&order=time.desc&limit=25
```

### 2. ERC-20 / Token transfers (adamant-im & adamant-iOS)

```http
GET /ethtxs?and=(txto.eq.{contract_address},or(txfrom.eq.{address},contract_to.eq.000000000000000000000000{address_without_0x}))&order=time.desc&limit=25
```

### 3. Native ETH transfers (adamant-iOS two-request pattern)

```http
GET /ethtxs?txfrom=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
GET /ethtxs?txto=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
```

### 4. Health check and service status

```http
GET /max_block
GET /aval
```

- `/max_block` returns the maximum indexed block number and indexer version
- `/aval` provides an availability check endpoint

## Database and Indexing Discipline

- Use `citext` for address fields (`txfrom`, `txto`, `txhash`, `contract_to`) to ensure case-insensitive matching without costly `LOWER()` runtime conversions
- Keep table schema and index definitions synchronized with client query patterns
- Use the minimal 5-index set (`create_indexes.sql` + `create_indexes_add.sql`) as default, saving ~90–110 GB per 1-year dataset (~490M rows) compared to legacy sets
- Be aware of lock contention: `CREATE INDEX` takes a `ShareLock` that blocks `ethsync.py` inserts; recommend `CREATE INDEX CONCURRENTLY` in production deployment documentation
- In `ethsync.py`, ensure idempotent startup: remove the highest block on startup to cleanly recover from interrupted block writes
- Track the last processed block in `public.sync_state` so filtered or empty blocks do not get scanned repeatedly
- Use parameterized SQL queries (`%s` placeholders in psycopg2) for all database operations to eliminate SQL injection risks

## Security and Access Control Rules

- Never expose write permissions to public API consumers
- Configure PostgREST with a dedicated read-only role (`web_anon`) having only `SELECT` privileges on `public.ethtxs`, `public.aval`, and `public.max_block`
- The indexer user (`api_user`) requires only DML grants (`SELECT`, `INSERT`, `DELETE`) on indexing tables and does not require PostgreSQL superuser privileges
- Enforce `db-max-rows = 10000` in PostgREST configuration to cap returned row volumes and prevent out-of-memory crashes on unbounded queries
- In reverse proxy configurations (nginx), enforce:
  - An HTTP method allow-list (`GET`, `HEAD`, `OPTIONS`) on public endpoints (`/ethtxs`, `/aval`, `/max_block`) to reject unexpected write verbs at the edge
  - Mandatory address filter validation (`txfrom` or `txto`) on `/ethtxs` to prevent catastrophic full table sequential scans on unindexed columns (e.g., `txhash`)
  - Prevention of expensive count aggregates (`Prefer: count=exact`) and unbounded offsets
- Never hardcode or log passwords, database credentials, or private keys
- Sanitize and validate raw transaction inputs; reject malformed `contract_to` fields exceeding standard length bounds before database insertion

## Working with Command-Line Tools

When a CLI tool accepts multi-line input, always use a temporary file in `.ai-ignored/` instead of inline multi-line shell strings.

- Prefer file-based flags such as `gh pr create --body-file`, `gh issue create --body-file`, and `git commit -F`
- Use descriptive dated filenames such as `.ai-ignored/temp.YYYY-MM-DD.pr-description.md`
- Cleanup is optional because `.ai-ignored/` is git-ignored, but do not accidentally reuse stale content

Example:

```bash
gh issue create \
  --title "[Docs] Update indexer setup instructions" \
  --body-file .ai-ignored/temp.2026-08-23.issue-body.md \
  --label "documentation,Guideline"

gh pr create \
  --base dev \
  --title "Docs: Update indexer setup instructions" \
  --body-file .ai-ignored/temp.2026-08-23.pr-description.md \
  --label "documentation,Guideline"
```

## Issue, Label, and PR Conventions

Follow organization-wide conventions:

- Governance repository: <https://github.com/Adamant-im/.github>
- Issue prefix guidance: <https://github.com/orgs/Adamant-im/discussions/5>
- Label catalog: <https://github.com/orgs/Adamant-im/discussions/1>

### Issue workflow

1. Search existing issues before creating a new one to avoid duplicates
2. Use org issue structure (`## Summary`, `## Details`, `## Checklist`, `## Verification`)
3. Use a concise prefixed title (one or two prefixes maximum)
4. Apply relevant labels from `labels.json` (`documentation`, `Guideline`, `DB`, `APIs`, `Infrastructure`, `Task`, `bug`, `enhancement`, etc.)
5. Link related issues and PRs explicitly

### Recommended Issue title prefixes

- `[Bug]` — bug, crash, incorrect indexing, or unexpected behavior
- `[Feat]` — new functionality
- `[Enhancement]` — improvement of existing features or performance
- `[Refactor]` — code refactoring without behavior change
- `[Docs]` — documentation updates
- `[Test]` — testing additions or improvements
- `[Chore]` — routine maintenance (dependencies, Docker, tooling)
- `[Task]` — general task or operational work
- `[Composite]` — multi-part task with sub-tasks
- `[Security]` — security hardening and vulnerability mitigations

### PR conventions

- Target the `dev` branch for all development pull requests unless explicitly instructed otherwise
- Use org PR template sections (`## Summary`, `## Details`, `## Related issue`, `## Checklist`, `## Verification`)
- Reference issues with closing keywords where appropriate (`Closes #<id>`)
- Use Conventional Commits style for PR titles: `Type: Short summary` (for example: `Docs: Add AGENTS.md`)
- Do not use issue-style square-bracket prefixes in PR titles (`[Docs]`, `[Bug]`, etc. are reserved for Issues)
- Keep PR title type aligned with issue intent (`Docs:`, `Fix:`, `Feat:`, `Refactor:`, `Test:`, `Chore:`, `Perf:`, `Sec:`)
- Include testing and verification steps with explicit command outputs

## AI Change Workflow

1. Read relevant files (`ethsync.py`, SQL scripts, configuration files, README) before making edits
2. Identify invariants that must stay unchanged (PostgREST schema compatibility, database column names, client query shapes)
3. Make minimal, focused, and safe changes
4. Validate changes:
   - Check Python syntax and linting
   - Verify SQL script syntax and compatibility
   - Check Markdown formatting against `.markdownlint.jsonc`
5. Report risks, assumptions, and test results clearly

## Testing and Validation Policy

Always run and report the outcome of validation steps:

- Python syntax and lint checks:
  - `python3 -m py_compile ethsync.py ethtest.py pgtest.py`
  - `flake8 ethsync.py` (when flake8 is available)
- SQL verification:
  - Review syntax for PostgreSQL 12+ compatibility
- Markdown linting:
  - Check formatting against `.markdownlint.jsonc`
- Docker verification:
  - Verify `docker-compose.yml` and `Dockerfile` syntax and configurations

Always report:

- Exact commands executed
- Pass/fail result of each command
- What was intentionally not run and why

## Definition of Done

A task is complete only when:

- All repository artifacts (code, comments, commit messages, PR text, issues) are in English
- Indexing logic and database schema remain robust, performant, and backwards-compatible
- Markdown linting and code syntax checks pass cleanly
- Issue and PR follow the documented conventions with temporary files in `.ai-ignored/`
- No sensitive credentials, secrets, or tracking mechanisms are introduced

## Related Repositories

| Repository                                                         | Relevance                                                                                                                                    |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [`adamant`](https://github.com/Adamant-im/adamant)                 | ADAMANT blockchain node repository; see its [`AGENTS.md`](https://github.com/Adamant-im/adamant/blob/dev/AGENTS.md) for node operating rules |
| [`adamant-im`](https://github.com/Adamant-im/adamant-im)           | Main ADAMANT client (Web/PWA/Electron/Android); primary consumer of ETH indexer API (`src/lib/nodes/eth-indexer/EthIndexerClient.ts`)        |
| [`adamant-iOS`](https://github.com/Adamant-im/adamant-iOS)         | Native iOS client; queries `/ethtxs` for ETH and ERC-20 transfer histories (`EthWalletService.swift`, `ERC20WalletService.swift`)            |
| [`adamant-wallets`](https://github.com/Adamant-im/adamant-wallets) | Coin and token specifications across ADAMANT applications                                                                                    |
| [`docs`](https://github.com/Adamant-im/docs)                       | Official ADAMANT documentation source (<https://docs.adamant.im>)                                                                            |
