import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mdx from '@mdx-js/rollup'
import remarkGfm from 'remark-gfm'
import remarkFrontmatter from 'remark-frontmatter'
import remarkMdxFrontmatter from 'remark-mdx-frontmatter'
import rehypeSlug from 'rehype-slug'
import rehypeShiki from '@shikijs/rehype'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { elephGrammar, elephOutputGrammar } from './src/lib/eleph-grammar'
import { resolveOrigin } from './scripts/origin.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
const origin = resolveOrigin()

/**
 * Stamp the deployment's own origin into the document head.
 *
 * With no origin known the placeholder collapses to nothing, leaving
 * root-relative URLs -- correct on whatever host serves them, and the client
 * rewrites the canonical to an absolute one per route anyway.
 */
const stampOrigin = {
  name: 'eleph-stamp-origin',
  transformIndexHtml(html: string) {
    return html.replaceAll('__ORIGIN__', origin)
  },
}

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(here, 'src') },
  },
  plugins: [
    {
      enforce: 'pre',
      ...mdx({
        providerImportSource: '@mdx-js/react',
        remarkPlugins: [
          remarkGfm,
          remarkFrontmatter,
          [remarkMdxFrontmatter, { name: 'meta' }],
        ],
        rehypePlugins: [
          rehypeSlug,
          [
            rehypeShiki,
            {
              // Both themes are emitted as CSS variables, so switching the
              // page theme does not re-highlight anything at run time.
              themes: { light: 'github-light', dark: 'github-dark-default' },
              defaultColor: false,
              cssVariablePrefix: '--shiki-',
              addLanguageClass: true,
              langs: [
                'bash',
                'python',
                'json',
                'text',
                elephGrammar,
                elephOutputGrammar,
              ],
              langAlias: {
                session: 'text',
                out: 'eleph-output',
              },
            },
          ],
        ],
      }),
    },
    react({ include: /\.(jsx|js|mdx|md|tsx|ts)$/ }),
    stampOrigin,
  ],
  build: {
    target: 'es2022',
    cssTarget: 'chrome110',
  },
})
