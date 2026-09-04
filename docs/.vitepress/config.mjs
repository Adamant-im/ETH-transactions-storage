import { defineConfig } from 'vitepress';

const hostname = 'https://eth-indexer.docs.adamant.im';
const repository = 'https://github.com/Adamant-im/ETH-transactions-storage';
const description =
  'Self-hosted Ethereum transaction indexer for native ETH and ERC-20 transfers with PostgreSQL and PostgREST';

/** Builds the canonical URL of a page from its source path. */
function canonicalUrl(relativePath) {
  const path = relativePath.replace(/(^|\/)index\.md$/, '$1').replace(/\.md$/, '');
  return `${hostname}/${path}`;
}

export default defineConfig({
  title: 'ETH Transactions Storage',
  description,
  lang: 'en-US',
  cleanUrls: true,
  metaChunk: true,
  lastUpdated: true,
  sitemap: {
    hostname,
  },
  head: [
    ['meta', { name: 'theme-color', content: '#2c4a7c' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'ETH Transactions Storage' }],
    ['meta', { property: 'og:description', content: description }],
    ['meta', { name: 'twitter:card', content: 'summary' }],
  ],
  transformPageData(pageData) {
    const url = canonicalUrl(pageData.relativePath);
    pageData.frontmatter.head ??= [];
    pageData.frontmatter.head.push(
      ['link', { rel: 'canonical', href: url }],
      ['meta', { property: 'og:url', content: url }],
    );
  },
  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'ETH Transactions Storage',
    nav: [
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'Reference', link: '/reference/api' },
      { text: 'Project', link: '/project/adamant' },
      { text: 'GitHub', link: repository },
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Introduction', link: '/guide/introduction' },
          { text: 'Architecture', link: '/guide/architecture' },
          { text: 'Quick Start: Docker Compose', link: '/guide/quick-start-docker' },
          { text: 'Quick Start: Manual and systemd', link: '/guide/quick-start-manual' },
          { text: 'Configuration', link: '/guide/configuration' },
          { text: 'Address Filter', link: '/guide/address-filter' },
          { text: 'Security and Public Deployment', link: '/guide/security' },
          { text: 'Upgrading', link: '/guide/upgrading' },
          { text: 'Troubleshooting', link: '/guide/troubleshooting' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'REST API', link: '/reference/api' },
          { text: 'Database and Indexes', link: '/reference/database' },
          { text: 'Docker Image', link: '/reference/docker-image' },
        ],
      },
      {
        text: 'Project',
        items: [
          { text: 'Used by ADAMANT', link: '/project/adamant' },
          { text: 'Contributing and Releases', link: '/project/contributing' },
        ],
      },
    ],
    socialLinks: [{ icon: 'github', link: repository }],
    editLink: {
      pattern: `${repository}/edit/dev/docs/:path`,
      text: 'Edit this page on GitHub',
    },
    footer: {
      message: 'Released under the GPL-3.0 License.',
      copyright: 'Copyright (c) ADAMANT community developers',
    },
    search: {
      provider: 'local',
    },
  },
});
