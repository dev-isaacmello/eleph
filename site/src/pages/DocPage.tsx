import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Pager } from '@/components/Pager'
import { Toc } from '@/components/Toc'
import { mdxComponents } from '@/components/mdx'
import { resolvePage, type PageModule } from '@/lib/content'
import { useLocale } from '@/lib/locale'
import { groupOf } from '@/lib/nav'
import { site } from '@/lib/site'

function setMeta(title: string, description?: string) {
  document.title =
    title === site.name ? `${site.name} — ${site.tagline}` : `${title} · ${site.name}`
  if (description) {
    document.querySelector('meta[name="description"]')?.setAttribute('content', description)
  }
}

export function DocPage() {
  const { locale, path, href, t } = useLocale()
  const route = path === '' ? '/docs' : path
  const [page, setPage] = useState<PageModule | null>(null)
  const [loaded, setLoaded] = useState('')
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    let live = true
    const found = resolvePage(locale, route)
    if (!found) {
      setMissing(true)
      setLoaded('')
      setMeta(t.notFoundTitle)
      return
    }
    setMissing(false)
    found.load().then((mod) => {
      if (!live) return
      setPage(() => mod)
      setLoaded(`${locale}${route}`)
      setMeta(mod.meta?.title ?? site.name, mod.meta?.description)
    })
    return () => {
      live = false
    }
  }, [route, locale, t.notFoundTitle])

  if (missing) {
    return (
      <>
        <main id="main" className="main">
          <article className="article prose">
            <h1>{t.notFoundTitle}</h1>
            <p className="lede">
              {t.notFoundBody} <code>{route}</code>.
            </p>
            <p>
              <Link to={href('/docs')}>{t.notFoundBack}</Link>.
            </p>
          </article>
        </main>
        <Toc />
      </>
    )
  }

  const Content = page?.default
  const group = groupOf(route, locale)

  return (
    <>
      <main id="main" className="main">
        <article id="article" className="article prose">
          {group ? (
            <nav className="breadcrumbs" aria-label="Breadcrumb">
              <Link to={href('/docs')}>{t.breadcrumbRoot}</Link>
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
