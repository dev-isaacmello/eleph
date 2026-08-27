import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { useCanonical } from '@/lib/canonical'
import { useLocale } from '@/lib/locale'
import { LOCALES } from '@/lib/nav'
import { Footer } from './Footer'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function Layout({ withSidebar }: { withSidebar: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname, hash } = useLocation()
  const { locale, t } = useLocale()

  useCanonical()

  // The document must declare the language it is actually in, or a screen
  // reader pronounces Portuguese with an English voice.
  useEffect(() => {
    const info = LOCALES.find((l) => l.code === locale)
    document.documentElement.lang = info?.htmlLang ?? 'en'
  }, [locale])

  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  useEffect(() => {
    if (hash) {
      const el = document.getElementById(decodeURIComponent(hash.slice(1)))
      if (el) {
        el.scrollIntoView({ block: 'start' })
        return
      }
    }
    window.scrollTo({ top: 0 })
  }, [pathname, hash])

  return (
    <>
      <a className="skip-link" href="#main">
        {t.skipToContent}
      </a>
      <Header menuOpen={menuOpen} onToggleMenu={() => setMenuOpen((v) => !v)} />
      {withSidebar ? (
        <div className="shell">
          <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
          <Outlet />
        </div>
      ) : (
        <Outlet />
      )}
      <Footer />
    </>
  )
}
