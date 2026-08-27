declare const __ELEPH_VERSION__: string

/// <reference types="vite/client" />

declare module '*.mdx' {
  import type { ComponentType } from 'react'
  export const meta: { title?: string; description?: string } | undefined
  const MDXComponent: ComponentType<{ components?: Record<string, unknown> }>
  export default MDXComponent
}
