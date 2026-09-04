# Contributing and Releases

The project is open source under the GPL-3.0 license and developed in the open at [github.com/Adamant-im/ETH-transactions-storage](https://github.com/Adamant-im/ETH-transactions-storage).

## Getting the Source

```bash
git clone https://github.com/Adamant-im/ETH-transactions-storage.git
cd ETH-transactions-storage
pip3 install -r requirements.txt
npm ci
```

`npm ci` installs the documentation and Markdown tooling from the committed lockfile. It is not needed to run the indexer.

Branches:

- `master` is the released state, and is what release tags and published images are built from
- `dev` is the integration branch, and the target for pull requests

## Working on the Documentation

```bash
npm run docs:dev       # local server with hot reload
npm run docs:build     # production build into docs/.vitepress/dist
npm run docs:preview   # serve the built site
```

Generated output under `docs/.vitepress/cache` and `docs/.vitepress/dist` is git-ignored and must never be committed.

## Checks

Run these before opening a pull request. They are the same commands CI runs.

```bash
npm run format:check                         # Prettier
npm run lint:md                              # markdownlint
npm run docs:build                           # documentation build, including link resolution
npm run lint:py                              # python3 -m py_compile on every module
npm test                                     # python3 -m unittest
flake8 ethsync.py                            # when flake8 is available
docker build -t eth-transactions-storage:local .
docker compose config --quiet
```

`npm run format` rewrites files in place when `format:check` fails.

## Pull Requests

- Target `dev` unless you were asked to do otherwise
- Use a Conventional Commits style title: `Type: Short summary`, for example `Docs: Document the address filter`. Square-bracket prefixes such as `[Docs]` are reserved for issues
- Follow the organization pull request sections: `## Summary`, `## Details`, `## Related issue`, `## Checklist`, `## Verification`
- Reference issues with closing keywords where appropriate, for example `Closes #30`
- Include the commands you ran and their results in the verification section
- Everything in the repository is written in English: code, comments, documentation, commit messages, and pull request text

Organization-wide conventions live in the [`.github` repository](https://github.com/Adamant-im/.github), with [issue prefix guidance](https://github.com/orgs/Adamant-im/discussions/5) and the [label catalog](https://github.com/orgs/Adamant-im/discussions/1).

Contributors working with AI assistants should also read [`AGENTS.md`](https://github.com/Adamant-im/ETH-transactions-storage/blob/dev/AGENTS.md), which records the invariants an automated change must not break.

## What Not to Break

Some things are contracts rather than implementation details:

- Endpoint names, column names, and value encodings in the [REST API](../reference/api.md#stability)
- The additive nature of `create_tables.sql`, so it stays safe to re-run on production databases
- The read-only posture of the anonymous role
- Zero telemetry. Nothing may report usage, errors, or addresses to any third party

## Release Process

1. Changes land on `dev` and are merged into `master`
2. The version in `package.json` and the version string in the `create_tables.sql` `max_block` view are updated together
3. A tag `vX.Y.Z` is created on `master` and a GitHub Release is published from it

Publishing a release triggers two workflows:

- **Docs.** Builds the VitePress site and deploys it to GitHub Pages at <https://eth-indexer.docs.adamant.im>. Pull requests are built but never deployed, so untrusted code cannot reach the Pages environment
- **Publish Docker image.** Verifies the release tag is an ancestor of `master`, then builds and pushes `ghcr.io/adamant-im/eth-transactions-storage` with an immutable `X.Y.Z` tag. `latest` moves only for non-prerelease releases

Both workflows request the minimum permissions they need: `contents: read`, `pages: write`, and `id-token: write` for the documentation deployment, and `contents: read` and `packages: write` for the image publication.

Version tags are immutable. The publish workflow refuses to run if the version tag already exists in the registry, so a rerun cannot replace a published digest with a rebuild — the base image and dependency constraints resolve differently over time, and a pinned version must keep pointing at the artifact it originally pinned. To ship a correction, publish a new version.

Release notes are published at [Releases](https://github.com/Adamant-im/ETH-transactions-storage/releases).

### One-Time Repository Setup

The documentation deployment depends on repository settings that no workflow can create for itself. The default `GITHUB_TOKEN` can neither enable Pages nor set a custom domain, so a maintainer with admin rights has to do them once, and the first deployment fails until they do.

1. **Settings → Pages → Source:** GitHub Actions
2. **Settings → Pages → Custom domain:** `eth-indexer.docs.adamant.im`, then Save

The `CNAME` file in `docs/public/` travels inside the Pages artifact, but GitHub ignores an artifact `CNAME` for Actions-based deployments — it is kept for provenance and for a fallback to branch-based publishing, not as configuration. The domain in the repository setting is the one that takes effect.

3. **Settings → Environments → `github-pages` → Deployment branches and tags:** add a tag rule `v*` alongside the `master` branch rule

   GitHub creates this environment automatically, restricted to the default branch. A release-triggered run deploys from `refs/tags/vX.Y.Z`, which that rule alone rejects, so publishing a release would fail the deployment while a push to `master` succeeded.

4. Wait for GitHub to provision the certificate, which can take up to 24 hours, then enable **Enforce HTTPS**
5. Verify that <https://eth-indexer.docs.adamant.im> serves the site over valid HTTPS before announcing it

The GHCR package also needs to be made public once, after the first release publishes it.

## Reporting Bugs

Open an issue with:

- The indexer version, from `/max_block`
- The deployment mode: Docker Compose, Docker, or systemd
- The execution client and version
- The PostgreSQL version
- Relevant log lines, with credentials removed

The [troubleshooting page](../guide/troubleshooting.md) covers the common cases and is worth checking first.

## Reporting Security Issues

Report vulnerabilities privately to <devs@adamant.im> instead of opening a public issue. Include reproduction steps and the affected version.

## License

Copyright © 2025–2026 ADAMANT developer community  
Copyright © 2020–2024 ADAMANT Foundation  
Copyright © 2017–2020 ADAMANT TECH LABS LP

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

The full text is in [`LICENSE`](https://github.com/Adamant-im/ETH-transactions-storage/blob/master/LICENSE).

## Support and Links

- Documentation: <https://eth-indexer.docs.adamant.im>
- Source: <https://github.com/Adamant-im/ETH-transactions-storage>
- Issues: <https://github.com/Adamant-im/ETH-transactions-storage/issues>
- Releases: <https://github.com/Adamant-im/ETH-transactions-storage/releases>
- Container image: <https://github.com/Adamant-im/ETH-transactions-storage/pkgs/container/eth-transactions-storage>
- Email: <devs@adamant.im>
