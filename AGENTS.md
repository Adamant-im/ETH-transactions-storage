# ETH Transactions Storage: AI Agent Operating Manual

This document defines how AI agents must work in this repository.

## Mission

`ETH-transactions-storage` is a self-hosted Ethereum transaction indexer and REST API backend for any compatible consumer. It indexes native ETH transfers and ERC-20 token transfer transactions into PostgreSQL and exposes address-oriented transaction history through PostgREST.

It is a general-purpose product. Its users are wallets, block explorers, accounting and treasury tools, support and compliance systems, monitoring services, and custom applications, whether or not they have any connection to ADAMANT. ADAMANT maintains the project and runs it in production, which makes it a documented adopter and a source of compatibility evidence, not the boundary of the product.

Agent output must optimize for:

1. Indexing reliability and data integrity
2. Database query performance and storage efficiency
3. Security, access control, and metadata minimization
4. Open-source maintainability, clean documentation, and contributor clarity

If tradeoffs are required, preserve indexing correctness and database integrity first.

## Positioning Rules

When editing user-facing or contributor-facing text:

- Describe the project first as a self-hosted Ethereum transaction indexer and REST API backend for any consumer
- Explain general use cases before naming any specific adopter
- Keep ADAMANT visible as a production adopter and case study: ownership, copyright, repository URLs, organization governance, client compatibility contracts, and the traffic audit behind the index set all stay
- Do not remove legal attribution, authorship, organization links, issue and PR governance rules, or project provenance
- Do not claim support for transfer methods, token standards, or chains that are not actually indexed. Under-claim rather than over-claim
- Never change the PostgREST schema, endpoint names, database column names, value encodings, or response shapes without treating it as a breaking change

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

Ethereum execution clients do not maintain an address-to-transaction index, so this service acts as dedicated indexing middleware for anyone who needs address transaction history without depending on a third-party data provider.

Agent decisions must:

- Maintain zero tracking and zero telemetry. The only outbound connections are the configured Ethereum endpoint and the configured PostgreSQL server
- Preserve the documented API contract for all consumers, including the ADAMANT clients (`adamant-im`, `adamant-iOS`) whose production query shapes are recorded below
- Keep indexing and database queries lightweight for independent self-hosted operators
- Ensure resilience against Ethereum node disconnections, sync delays, and database restarts
- Keep operator state — credentials, address lists, database data — out of the repository and out of published container images

## Sources of Truth

Use these sources when implementing or reviewing changes:

- This repository: `README.md`, `docs/`, `ethsync.py`, SQL schemas, and configuration templates
- Documentation site: <https://eth-indexer.docs.adamant.im>, built from `docs/`
- ADAMANT organization guidelines: <https://github.com/Adamant-im/.github>
- Issue prefix guidance: <https://github.com/orgs/Adamant-im/discussions/5>
- Label catalog: <https://github.com/orgs/Adamant-im/discussions/1>
- Client integration references:
  - `adamant-im`: `src/lib/nodes/eth-indexer/EthIndexerClient.ts`
  - `adamant-iOS`: `Adamant/Modules/Wallets/Ethereum/EthWalletService.swift` and `ERC20WalletService.swift`
- PostgREST documentation: <https://postgrest.org/en/stable/api.html>
- Web3.py documentation: <https://web3py.readthedocs.io/>
- VitePress documentation: <https://vitepress.dev/>

If sources disagree:

1. Treat current repository code and consumer production contracts as implementation truth
2. Do not silently ignore mismatches; document them and propose synchronized updates

## System Map (What You Are Editing)

| File / Component                       | Purpose                          | Key Responsibilities                                                                                                                                  |
| -------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ethsync.py`                           | Main indexer daemon              | Connects to Ethereum RPC (HTTP/WS/IPC), polls blocks, parses and filters ETH/ERC-20 transfers, writes to PostgreSQL, handles reorg cleanup            |
| `address_filter.py`                    | Address filter helpers           | Loads and validates monitored addresses, normalizes native and ABI-encoded address values, and evaluates transaction matches                          |
| `database.py`                          | PostgreSQL connection helpers    | Supports database names and connection URIs while redacting credentials from diagnostics                                                              |
| `test_address_filter.py`               | Address filter unit tests        | Covers boolean parsing, list loading and validation, address normalization, and match evaluation                                                      |
| `test_database.py`                     | Database helper unit tests       | Covers URI handling and credential redaction                                                                                                          |
| `filter/addresses.txt`                 | Monitored address list           | Ignored private file containing one Ethereum address per line for optional filtered indexing                                                          |
| `create_tables.sql`                    | Base schema & views              | Creates `citext`, storage and sync-state tables, `public.max_block` health-check view, and the `web_anon` role                                        |
| `create_indexes.sql`                   | Core database indexes (4 of 5)   | Minimal core B-tree indexes for address and block lookups (`block_index`, `txfrom_index`, `txto_contract_to_index`, `txto_w_empty_contract_to_index`) |
| `create_indexes_add.sql`               | Additional index (5 of 5)        | Timestamp index (`time_index`) completing the recommended 5-index set                                                                                 |
| `create_indexes_legacy.sql`            | Deprecated / legacy indexes      | Optional indexes for non-standard queries (`contract_to_index`, `txto_index`, `txto_txfrom_index`)                                                    |
| `ethtest.py`                           | Ethereum node test script        | Verifies RPC connectivity and queries current block height                                                                                            |
| `pgtest.py`                            | Database test script             | Verifies PostgreSQL connectivity and queries table status                                                                                             |
| `requirements.txt`                     | Python dependencies              | Declares runtime dependencies (`web3`, `psycopg2-binary`, `python-dotenv`)                                                                            |
| `package.json`                         | Product metadata & Node tooling  | Release version logged at startup, product description and keywords, documentation and lint scripts                                                   |
| `package-lock.json`                    | Reproducible Node dependencies   | Committed lockfile consumed by `npm ci` locally and in CI                                                                                             |
| `Dockerfile`                           | Container build definition       | Builds the indexer runtime image and declares OCI labels linking it to this repository                                                                |
| `docker-compose.yml`                   | Multi-container setup            | Configures PostgreSQL, PostgREST (`web_anon`, `db-max-rows`), local Geth node, and the indexer using the published image                              |
| `docker-compose.build.yml`             | Local build override             | Builds the indexer from the checkout and tags it separately so it never shadows the published image                                                   |
| `ethsync.service`                      | Systemd unit template            | Manages background service execution, restart policies, and environment variables                                                                     |
| `.env.example`                         | Configuration template           | Documents every standalone, systemd, and Compose variable with safe defaults                                                                          |
| `docs/`                                | VitePress documentation site     | Product, deployment, configuration, API, and database documentation published to <https://eth-indexer.docs.adamant.im>                                |
| `docs/.vitepress/config.mjs`           | Documentation site configuration | Navigation, sidebar, sitemap, canonical URLs, and SEO metadata                                                                                        |
| `docs/public/CNAME`                    | Domain marker in the artifact    | Ships the domain inside the Pages artifact; the effective custom domain is a repository Pages setting                                                 |
| `.github/workflows/docs.yml`           | Pages deployment                 | Builds and deploys the site from trusted refs only, with `contents: read`, `pages: write`, `id-token: write`                                          |
| `.github/workflows/docs-build.yml`     | Documentation checks             | Builds the site and runs Markdown and formatting checks on pull requests                                                                              |
| `.github/workflows/docker-build.yml`   | Container checks                 | Non-publishing image build and Compose smoke test on pull requests                                                                                    |
| `.github/workflows/publish-docker.yml` | GHCR publication                 | Publishes release images to `ghcr.io/adamant-im/eth-transactions-storage` with `contents: read`, `packages: write`                                    |

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

Docker Compose consumes additional variables that `ethsync.py` never reads: `ETH_INDEXER_IMAGE`, `DOCKER_ETH_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and the `PGRST_*` settings. Keep the authoritative descriptions in `.env.example` and `docs/guide/configuration.md` synchronized with any change here.

## API Compatibility Contracts

Consumers query indexed transactions through PostgREST. These query shapes are the stable public contract and must keep working. They are recorded from ADAMANT client production traffic, which is the evidence that the contract is exercised in the field; they are not client-specific features.

### 1. Native ETH transfers, single request

```http
GET /ethtxs?and=(contract_to.eq.,or(txfrom.eq.{address},txto.eq.{address}))&order=time.desc&limit=25
```

### 2. ERC-20 / token transfers

```http
GET /ethtxs?and=(txto.eq.{contract_address},or(txfrom.eq.{address},contract_to.eq.000000000000000000000000{address_without_0x}))&order=time.desc&limit=25
```

### 3. Native ETH transfers, two-request pattern

```http
GET /ethtxs?txfrom=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
GET /ethtxs?txto=eq.{address}&contract_to=eq.&order=time.desc&limit={n}&offset={n}
```

### 4. Health check and service status

```http
GET /max_block
GET /aval
```

- `/max_block` returns the maximum processed block number and indexer version
- `/aval` provides an availability check endpoint

## Database and Indexing Discipline

- Use `citext` for address fields (`txfrom`, `txto`, `txhash`, `contract_to`) to ensure case-insensitive matching without costly `LOWER()` runtime conversions
- Keep table schema and index definitions synchronized with the documented query shapes
- Use the recommended 5-index set (`create_indexes.sql` + `create_indexes_add.sql`) as default, saving ~90–110 GB per 1-year dataset (~490M rows) compared to legacy sets
- Be aware of lock contention: `CREATE INDEX` takes a `ShareLock` that blocks `ethsync.py` inserts; recommend `CREATE INDEX CONCURRENTLY` in production deployment documentation
- In `ethsync.py`, ensure idempotent startup: remove the highest block on startup to cleanly recover from interrupted block writes
- Track the last processed block in `public.sync_state` so filtered or empty blocks do not get scanned repeatedly
- Use parameterized SQL queries (`%s` placeholders in psycopg2) for all database operations to eliminate SQL injection risks
- Keep `create_tables.sql` idempotent and additive so it stays safe to re-run on production databases
- Update the version string in the `public.max_block` view together with `package.json` on every release

## Security and Access Control Rules

- Never expose write permissions to public API consumers
- Configure PostgREST with a dedicated read-only role (`web_anon`) having only `SELECT` privileges on `public.ethtxs`, `public.aval`, and `public.max_block`
- The indexer user (`api_user`) requires `SELECT`, `INSERT`, and `DELETE` on `public.ethtxs`, plus `SELECT`, `INSERT`, and `UPDATE` on `public.sync_state`, and does not require PostgreSQL superuser privileges
- Enforce `db-max-rows = 10000` in PostgREST configuration to cap returned row volumes and prevent out-of-memory crashes on unbounded queries
- In reverse proxy configurations (nginx), enforce:
  - An HTTP method allow-list (`GET`, `HEAD`, `OPTIONS`) on public endpoints (`/ethtxs`, `/aval`, `/max_block`) to reject unexpected write verbs at the edge
  - Mandatory address filter validation (`txfrom` or `txto`) on `/ethtxs` to prevent catastrophic full table sequential scans on unindexed columns (e.g., `txhash`)
  - Prevention of expensive count aggregates (`Prefer: count=exact`) and unbounded offsets
- Never hardcode or log passwords, database credentials, or private keys
- Sanitize and validate raw transaction inputs; reject malformed `contract_to` fields exceeding standard length bounds before database insertion
- Never add `.env`, credentials, private address lists, database data, or logs to the Docker build context or a published image; keep `.dockerignore` and `.gitignore` covering them
- Keep GitHub Actions permissions minimal and never deploy or publish from untrusted pull-request code

## Documentation Site

The VitePress site in `docs/` is the primary product documentation. `README.md` stays a compact product overview that links into it, so detailed instructions live in exactly one place.

- Add a new page under `docs/guide/`, `docs/reference/`, or `docs/project/` and register it in the sidebar in `docs/.vitepress/config.mjs`
- Use relative Markdown links between documentation pages so the build verifies them; use absolute `https://eth-indexer.docs.adamant.im/...` links only from `README.md` and other repository-root files
- Never commit `docs/.vitepress/cache/` or `docs/.vitepress/dist/`
- Keep `docs/public/CNAME` set to `eth-indexer.docs.adamant.im`. It ships the domain inside the Pages artifact, but it does not configure it: GitHub ignores an artifact CNAME for Actions-based deployments, and the effective custom domain is a repository Pages setting
- Local commands: `npm run docs:dev`, `npm run docs:build`, `npm run docs:preview`
- Update `package-lock.json` with `npm install` whenever documentation dependencies change, and commit it

## Container Image and Release Discipline

- The published image is `ghcr.io/adamant-im/eth-transactions-storage`, built from `Dockerfile` and containing the indexer process only
- PostgreSQL, PostgREST, and the Ethereum execution client stay separate services and must never be merged into the indexer image
- Publication happens from a published GitHub Release whose tag is an ancestor of `master`. Version tags are immutable and carry no leading `v`; `latest` moves only for non-prerelease releases
- Keep the OCI labels in `Dockerfile` accurate so GitHub links the package to this repository
- `docker-compose.yml` runs the published image by default; `docker-compose.build.yml` is the documented local-build path for contributors

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

1. Read relevant files (`ethsync.py`, SQL scripts, configuration files, `README.md`, `docs/`) before making edits
2. Identify invariants that must stay unchanged (PostgREST schema compatibility, database column names, value encodings, consumer query shapes)
3. Make minimal, focused, and safe changes
4. Validate changes:
   - Check Python syntax and linting
   - Run the Python unit tests
   - Verify SQL script syntax and compatibility
   - Build the documentation site and check Markdown formatting
   - Verify Docker and Compose configuration
5. Report risks, assumptions, and test results clearly

## Testing and Validation Policy

Always run and report the outcome of validation steps:

- Python syntax and lint checks:
  - `npm run lint:py`, equivalent to `python3 -m py_compile address_filter.py database.py ethsync.py ethtest.py pgtest.py test_address_filter.py test_database.py`
  - `flake8 ethsync.py` (when flake8 is available)
- Python unit tests:
  - `npm test`, equivalent to `python3 -m unittest test_address_filter.py test_database.py`
- Node tooling and documentation:
  - `npm ci` (reproducible install from the committed lockfile)
  - `npm run format:check`
  - `npm run lint:md`
  - `npm run docs:build`
- SQL verification:
  - Review syntax for PostgreSQL 12+ compatibility
- Docker verification:
  - `docker compose config --quiet`
  - `docker build -t eth-transactions-storage:local .`

Always report:

- Exact commands executed
- Pass/fail result of each command
- What was intentionally not run and why

## Definition of Done

A task is complete only when:

- All repository artifacts (code, comments, commit messages, PR text, issues) are in English
- Product positioning stays general-purpose while ADAMANT attribution, governance, and compatibility evidence are preserved
- Indexing logic and database schema remain robust, performant, and backwards-compatible
- The documented API contract is unchanged for existing consumers
- Markdown linting, formatting, documentation build, and code syntax checks pass cleanly
- Issue and PR follow the documented conventions with temporary files in `.ai-ignored/`
- No sensitive credentials, secrets, or tracking mechanisms are introduced

## Related Repositories

| Repository                                                           | Relevance                                                                                                                                    |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [`adamant`](https://github.com/Adamant-im/adamant)                   | ADAMANT blockchain node repository; see its [`AGENTS.md`](https://github.com/Adamant-im/adamant/blob/dev/AGENTS.md) for node operating rules |
| [`adamant-im`](https://github.com/Adamant-im/adamant-im)             | ADAMANT client (Web/PWA/Electron/Android); production consumer of this API (`src/lib/nodes/eth-indexer/EthIndexerClient.ts`)                 |
| [`adamant-iOS`](https://github.com/Adamant-im/adamant-iOS)           | Native iOS client; queries `/ethtxs` for ETH and ERC-20 transfer histories (`EthWalletService.swift`, `ERC20WalletService.swift`)            |
| [`adamant-wallets`](https://github.com/Adamant-im/adamant-wallets)   | Coin and token specifications across ADAMANT applications                                                                                    |
| [`adamant-console`](https://github.com/Adamant-im/adamant-console)   | Reference for the VitePress documentation and GitHub Pages workflow used here                                                                |
| [`adamant-tradebot`](https://github.com/Adamant-im/adamant-tradebot) | Reference for the release-driven GHCR publishing workflow used here                                                                          |
| [`docs`](https://github.com/Adamant-im/docs)                         | Official ADAMANT documentation source (<https://docs.adamant.im>)                                                                            |
