import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { Pager } from '@/components/Pager'
import { Toc } from '@/components/Toc'
import { mdxComponents } from '@/components/mdx'
import { loaders, type PageModule } from '@/lib/content'
import { groupOf } from '@/lib/nav'
import { site } from '@/lib/site'

function setMeta(title: string, description?: string) {
  document.title = title === site.name ? `${site.name} — ${site.tagline}` : `${title} · ${site.name}`
  if (description) {
    const tag = document.querySelector('meta[name="description"]')
    if (tag) tag.setAttribute('content', description)
  }
}

export function DocPage() {
  const { pathname } = useLocation()
  const route = pathname.replace(/\/$/, '') || '/docs'
  const [page, setPage] = useState<PageModule | null>(null)
  /** The route whose module is rendered right now, which lags `route`. */
  const [loaded, setLoaded] = useState('')
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    let live = true
    const load = loaders.get(route)
    if (!load) {
      setMissing(true)
      setLoaded('')
      setMeta('Page not found')
      return
    }
    setMissing(false)
    load().then((mod) => {
      if (!live) return
      setPage(() => mod)
      setLoaded(route)
      setMeta(mod.meta?.title ?? site.name, mod.meta?.description)
    })
    return () => {
      live = false
    }
  }, [route])

  if (missing) {
    return (
      <>
        <main id="main" className="main">
          <article className="article prose">
            <h1>Page not found</h1>
            <p className="lede">
              Nothing is documented at <code>{route}</code>.
            </p>
            <p>
              <Link to="/docs">Back to the documentation index</Link>.
            </p>
          </article>
        </main>
        <Toc />
      </>
    )
  }

  const Content = page?.default
  const group = groupOf(route)

  return (
    <>
      <main id="main" className="main">
        <article id="article" className="article prose">
          {group ? (
            <nav className="breadcrumbs" aria-label="Breadcrumb">
              <Link to="/docs">Docs</Link>
              <span aria-hidden="true">/</span>
              <span>{group.title}</span>
            </nav>
          ) : null}

          {Content ? <Content components={mdxComponents} /> : <p aria-busy="true" />}

          <Pager href={route} />
        </article>
      </main>
      <Toc contentKey={loaded} />
    </>
  )
}
