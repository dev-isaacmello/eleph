import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { useCanonical } from '@/lib/canonical'
import { Footer } from './Footer'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function Layout({ withSidebar }: { withSidebar: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname, hash } = useLocation()

  useCanonical()

  // Close the drawer on navigation, and lock the body behind it while open.
  useEffect(() => setMenuOpen(false), [pathname])

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  // A route change starts at the top; a hash goes where the hash says.
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
        Skip to content
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
