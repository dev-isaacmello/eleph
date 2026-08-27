import { Link, NavLink } from 'react-router-dom'

import { site } from '@/lib/site'
import { IconGitHub, IconMenu, IconClose } from './Icons'
import { Search } from './Search'
import { ThemeToggle } from './ThemeToggle'

function Mark() {
  return (
    <svg className="header__mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--fg)" />
      <path
        d="M11 8v9a5 5 0 0 0 5 5h1a4 4 0 0 1 4 4v2"
        fill="none"
        stroke="var(--bg)"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="21" cy="10" r="2.4" fill="var(--bg)" />
    </svg>
  )
}

export function Header({
  menuOpen,
  onToggleMenu,
}: {
  menuOpen: boolean
  onToggleMenu: () => void
}) {
  return (
    <header className="header">
      <button
        type="button"
        className="icon-button menu-button"
        onClick={onToggleMenu}
        aria-expanded={menuOpen}
        aria-controls="sidebar"
        aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
      >
        {menuOpen ? <IconClose /> : <IconMenu />}
      </button>

      <Link to="/" className="header__brand">
        <Mark />
        <span>{site.name}</span>
      </Link>

      <a
        className="header__version"
        href={`${site.repo}/blob/main/CHANGELOG.md`}
        target="_blank"
        rel="noreferrer"
        title="Changelog"
      >
        v{site.version}
      </a>

      <nav className="header__nav" aria-label="Primary">
        <NavLink to="/docs">Docs</NavLink>
        <NavLink to="/docs/reference/program-structure">Reference</NavLink>
        <NavLink to="/docs/python-api">Python API</NavLink>
        <NavLink to="/docs/taubench">Benchmark</NavLink>
      </nav>

      <span className="header__spacer" />

      <div className="header__actions">
        <Search />
        <ThemeToggle />
        <a
          className="icon-button"
          href={site.repo}
          target="_blank"
          rel="noreferrer"
          aria-label="eleph on GitHub"
        >
          <IconGitHub />
        </a>
      </div>
    </header>
  )
}
